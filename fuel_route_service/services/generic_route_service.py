import logging
import math
import re

import numpy as np
from django.core.cache import cache

from fuel_route_service.constants import (CacheKey, GEOCODE_CACHE_TIMEOUT, METERS_PER_MILE, ROUTE_CACHE_TIMEOUT,
                                          ROUTE_CORRIDOR_MILES, ROUTE_SAMPLE_STEP_MILES, SECONDS_PER_HOUR,
                                          STOP_PENALTY_DOLLARS, US_LAT_RANGE, US_LNG_RANGE, US_STATES,
                                          VEHICLE_MAX_RANGE_MILES, VEHICLE_MILES_PER_GALLON)
from fuel_route_service.messages import FailureMessage
from utils.dto import GenericFuncResp
from utils.geo_util import haversine_miles
from utils.helpers import normalize_place_name
from utils.osm.nominatim import search_us_location
from utils.osm.osrm import get_driving_route
from .generic_fuel_station_service import GenericFuelStationService
from .generic_place_service import GenericPlaceService

logger = logging.getLogger(__name__)

LAT_LNG_PATTERN = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$")
CITY_STATE_PATTERN = re.compile(r"^\s*(.+?)\s*,\s*([A-Za-z]{2})\s*$")
STATION_BATCH_SIZE = 500


class GenericRouteService:

    @classmethod
    def plan_trip(cls, start, finish):
        start_resp = cls.resolve_location(start)
        if not start_resp.success:
            return start_resp
        finish_resp = cls.resolve_location(finish)
        if not finish_resp.success:
            return finish_resp

        start_location, finish_location = start_resp.data, finish_resp.data
        route_resp = cls.get_route(start_location["lat"], start_location["lng"],
                                   finish_location["lat"], finish_location["lng"])
        if not route_resp.success:
            return route_resp
        route = route_resp.data

        stations = cls.__get_stations_along_route(route["lats"], route["lngs"], route["route_miles"])
        stops_resp = cls.pick_fuel_stops(stations, route["route_miles"][-1])
        if not stops_resp.success:
            return stops_resp

        fuel_stops = cls.__attach_station_details(stops_resp.data)
        return GenericFuncResp(success=True, data={
            "start": start_location,
            "finish": finish_location,
            "distance_miles": round(route["distance_miles"], 1),
            "duration_hours": round(route["duration_hours"], 1),
            "vehicle": {
                "max_range_miles": VEHICLE_MAX_RANGE_MILES,
                "miles_per_gallon": VEHICLE_MILES_PER_GALLON,
                "tank_gallons": VEHICLE_MAX_RANGE_MILES / VEHICLE_MILES_PER_GALLON,
                "starts_with_full_tank": True,
            },
            "fuel_stops": fuel_stops,
            "total_gallons": round(sum(stop["gallons"] for stop in fuel_stops), 2),
            "total_fuel_cost": round(sum(stop["cost"] for stop in fuel_stops), 2),
            "route": {
                "type": "LineString",
                "coordinates": [[round(lng, 5), round(lat, 5)] for lat, lng in zip(route["lats"], route["lngs"])],
            },
        })

    @classmethod
    def resolve_location(cls, query):
        match = LAT_LNG_PATTERN.match(query)
        if match:
            lat, lng = float(match.group(1)), float(match.group(2))
        else:
            match = CITY_STATE_PATTERN.match(query)
            if match and match.group(2).upper() not in US_STATES:
                return GenericFuncResp(success=False, message=FailureMessage.LOCATION_OUTSIDE_USA.format(query))
            coords = cls.__lookup_place(query) or cls.__geocode_online(query)
            if coords is None:
                return GenericFuncResp(success=False, message=FailureMessage.LOCATION_NOT_FOUND.format(query))
            lat, lng = coords

        if not (US_LAT_RANGE[0] <= lat <= US_LAT_RANGE[1] and US_LNG_RANGE[0] <= lng <= US_LNG_RANGE[1]):
            return GenericFuncResp(success=False, message=FailureMessage.LOCATION_OUTSIDE_USA.format(query))
        return GenericFuncResp(success=True, data={"query": query, "lat": lat, "lng": lng})

    @classmethod
    def get_route(cls, start_lat, start_lng, finish_lat, finish_lng):
        cache_key = CacheKey.ROUTE.format(round(start_lat, 4), round(start_lng, 4),
                                          round(finish_lat, 4), round(finish_lng, 4))
        route = cache.get(cache_key)
        if route is not None:
            return GenericFuncResp(success=True, data=route)

        osrm_resp = get_driving_route(start_lat, start_lng, finish_lat, finish_lng)
        if osrm_resp.get("code") != "Ok" or not osrm_resp.get("routes"):
            logger.info(f"osrm returned {osrm_resp.get('code')} for {start_lat},{start_lng} -> {finish_lat},{finish_lng}")
            return GenericFuncResp(success=False, message=FailureMessage.ROUTE_NOT_FOUND)

        osrm_route = osrm_resp["routes"][0]
        points = np.array(osrm_route["geometry"]["coordinates"])
        lngs, lats = points[:, 0], points[:, 1]
        route_miles = np.concatenate([[0], np.cumsum(haversine_miles(lats[:-1], lngs[:-1], lats[1:], lngs[1:]))])

        # full geometry can be 20k+ points, one point per mile is plenty for matching and drawing
        sample_idx = np.unique(np.floor(route_miles / ROUTE_SAMPLE_STEP_MILES), return_index=True)[1]
        sample_idx = np.append(sample_idx, len(route_miles) - 1)

        route = {
            "distance_miles": osrm_route["distance"] / METERS_PER_MILE,
            "duration_hours": osrm_route["duration"] / SECONDS_PER_HOUR,
            "lats": lats[sample_idx].tolist(),
            "lngs": lngs[sample_idx].tolist(),
            "route_miles": route_miles[sample_idx].tolist(),
        }
        cache.set(cache_key, route, ROUTE_CACHE_TIMEOUT)
        return GenericFuncResp(success=True, data=route)

    @classmethod
    def pick_fuel_stops(cls, stations, total_miles):
        # cheapest path over origin -> stations -> finish with every leg <= max range. truck leaves with a full tank,
        # at each stop it buys only what the next leg needs. STOP_PENALTY_DOLLARS avoids stops that save pennies.
        nodes = [{"position": 0, "price": 0}] + stations + [{"position": total_miles, "price": 0}]
        best_cost = [0] + [math.inf] * (len(nodes) - 1)
        came_from = [None] * len(nodes)
        for j in range(1, len(nodes)):
            for i in range(j - 1, -1, -1):
                leg_miles = nodes[j]["position"] - nodes[i]["position"]
                if leg_miles > VEHICLE_MAX_RANGE_MILES:
                    break
                cost = best_cost[i]
                if i > 0:
                    buy_miles = cls.__buy_miles(nodes, came_from, i, leg_miles)
                    if buy_miles == 0:
                        continue
                    cost += buy_miles / VEHICLE_MILES_PER_GALLON * nodes[i]["price"] + STOP_PENALTY_DOLLARS
                if cost < best_cost[j]:
                    best_cost[j], came_from[j] = cost, i

        if best_cost[-1] == math.inf:
            return GenericFuncResp(success=False, message=FailureMessage.FUEL_GAP_TOO_LARGE)

        path = []
        j = len(nodes) - 1
        while came_from[j]:
            path.append(came_from[j])
            j = came_from[j]
        path.reverse()

        stops = []
        for index, i in enumerate(path):
            next_position = nodes[path[index + 1]]["position"] if index + 1 < len(path) else total_miles
            gallons = cls.__buy_miles(nodes, came_from, i, next_position - nodes[i]["position"]) / \
                VEHICLE_MILES_PER_GALLON
            stops.append({**nodes[i], "gallons": gallons, "cost": gallons * nodes[i]["price"]})
        return GenericFuncResp(success=True, data=stops)

    @classmethod
    def __buy_miles(cls, nodes, came_from, i, leg_miles):
        # only the first stop still has fuel left from the starting tank, later stops arrive empty
        fuel_left = VEHICLE_MAX_RANGE_MILES - nodes[i]["position"] if came_from[i] == 0 else 0
        return max(leg_miles - fuel_left, 0)

    @classmethod
    def __get_stations_along_route(cls, lats, lngs, route_miles):
        lats, lngs, route_miles = np.array(lats), np.array(lngs), np.array(route_miles)
        stations = GenericFuelStationService.get_station_arrays()

        # rough bounding box first so we only do the distance matrix for nearby stations
        pad = ROUTE_CORRIDOR_MILES / 40
        in_box = np.nonzero(
            (stations["lats"] >= lats.min() - pad) & (stations["lats"] <= lats.max() + pad) &
            (stations["lngs"] >= lngs.min() - pad) & (stations["lngs"] <= lngs.max() + pad)
        )[0]

        result = []
        for batch_start in range(0, len(in_box), STATION_BATCH_SIZE):
            idx = in_box[batch_start:batch_start + STATION_BATCH_SIZE]
            distances = haversine_miles(stations["lats"][idx][:, None], stations["lngs"][idx][:, None],
                                        lats[None, :], lngs[None, :])
            nearest = distances.argmin(axis=1)
            off_route = distances[np.arange(len(idx)), nearest]
            for i in np.nonzero(off_route <= ROUTE_CORRIDOR_MILES)[0]:
                result.append({
                    "id": int(stations["ids"][idx[i]]),
                    "position": float(route_miles[nearest[i]]),
                    "price": float(stations["prices"][idx[i]]),
                    "off_route_miles": float(off_route[i]),
                })
        # stations in the same city share a centroid, only the cheapest one there matters
        cheapest_at_position = {}
        for station in sorted(result, key=lambda station: station["price"]):
            cheapest_at_position.setdefault(station["position"], station)
        return sorted(cheapest_at_position.values(), key=lambda station: station["position"])

    @classmethod
    def __attach_station_details(cls, stops):
        stations = GenericFuelStationService.get_fuel_station(ids=[stop["id"] for stop in stops]).in_bulk()
        fuel_stops = []
        for stop in stops:
            station = stations[stop["id"]]
            fuel_stops.append({
                "name": station.name,
                "address": station.address,
                "city": station.city,
                "state": station.state,
                "lat": station.lat,
                "lng": station.lng,
                "price_per_gallon": round(stop["price"], 3),
                "mile_marker": round(stop["position"], 1),
                "off_route_miles": round(stop["off_route_miles"], 1),
                "gallons": round(stop["gallons"], 2),
                "cost": round(stop["cost"], 2),
            })
        return fuel_stops

    @classmethod
    def __lookup_place(cls, query):
        match = CITY_STATE_PATTERN.match(query)
        if not match:
            return None
        place = GenericPlaceService.get_place(normalized_name=normalize_place_name(match.group(1)),
                                              state=match.group(2).upper()).order_by("id").first()
        if place is None:
            return None
        return place.lat, place.lng

    @classmethod
    def __geocode_online(cls, query):
        cache_key = CacheKey.GEOCODE.format(query.lower().strip())
        coords = cache.get(cache_key)
        if coords is None:
            coords = search_us_location(query)
            cache.set(cache_key, coords, GEOCODE_CACHE_TIMEOUT)
        return coords
