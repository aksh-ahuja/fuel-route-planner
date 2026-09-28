import csv
import gzip
import logging
import re

from django.conf import settings
from django.core.management.base import BaseCommand

from fuel_route_service.constants import US_STATES
from fuel_route_service.services import GenericFuelStationService, GenericPlaceService
from utils.helpers import normalize_place_name

logger = logging.getLogger(__name__)

GAZETTEER_FILES = ["2023_Gaz_place_national.txt.gz", "2023_Gaz_cousubs_national.txt.gz"]
FUEL_PRICES_FILE = "fuel_prices.csv"

# census names come as "Tomah city", "Boise City city", "Athens-Clarke County unified government (balance)"
CENSUS_SUFFIX = re.compile(
    r"\s+(city and borough|consolidated government|unified government|metropolitan government|urban county|"
    r"city|town|village|CDP|borough|municipality|township|plantation|gore|grant|location|purchase)$",
    re.IGNORECASE,
)


class Command(BaseCommand):
    help = "Load census places and fuel stations, geocoding stations by city + state"

    def handle(self, *args, **options):
        places = self.read_places()
        GenericPlaceService.replace_places(places.values())
        self.stdout.write(f"Loaded {len(places)} places")

        stations = self.read_stations()
        missing = 0
        for station in stations:
            place = places.get((normalize_place_name(station["city"]), station["state"]))
            if place is None:
                missing += 1
                continue
            station["lat"], station["lng"] = place["lat"], place["lng"]

        GenericFuelStationService.replace_fuel_stations(stations)
        self.stdout.write(f"Loaded {len(stations)} US stations, {missing} could not be geocoded and will be ignored for routing")

    def read_places(self):
        places = {}
        for file_name in GAZETTEER_FILES:
            with gzip.open(settings.DATA_DIR / file_name, "rt", encoding="latin-1") as f:
                for row in csv.DictReader(f, delimiter="\t"):
                    row = {key.strip(): value.strip() for key, value in row.items()}
                    name = re.sub(r"\s*\(.*\)$", "", row["NAME"])
                    short_name = CENSUS_SUFFIX.sub("", name)
                    for variant in {name, short_name, short_name.split("-")[0]}:
                        key = (normalize_place_name(variant), row["USPS"])
                        if key in places:
                            continue
                        places[key] = {
                            "name": name,
                            "normalized_name": key[0],
                            "state": row["USPS"],
                            "lat": float(row["INTPTLAT"]),
                            "lng": float(row["INTPTLONG"]),
                        }
        return places

    def read_stations(self):
        stations = {}
        with open(settings.DATA_DIR / FUEL_PRICES_FILE, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                state = row["State"].strip()
                if state not in US_STATES:
                    continue
                opis_id = int(row["OPIS Truckstop ID"])
                price = float(row["Retail Price"])
                # same truckstop shows up multiple times with different prices, keep the cheapest
                if opis_id in stations and stations[opis_id]["retail_price"] <= price:
                    continue
                stations[opis_id] = {
                    "opis_id": opis_id,
                    "name": row["Truckstop Name"].strip(),
                    "address": row["Address"].strip(),
                    "city": row["City"].strip(),
                    "state": state,
                    "rack_id": int(row["Rack ID"]) if row["Rack ID"].strip() else None,
                    "retail_price": price,
                }
        return list(stations.values())
