# Fuel Route Planner

Django API that takes a start and finish in the USA, returns the driving route, where to fuel up (cheapest plan for a
500 mile range truck doing 10 mpg) and the total fuel cost.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py load_fuel_data
python manage.py runserver
```

`load_fuel_data` is a one time step. The price CSV has no coordinates, so stations are geocoded offline by matching
city + state against the US Census gazetteer files in `data/` (~96% of US stations match, the rest are skipped).
Canadian stations are dropped since trips are USA only.

## API

`POST /api/route/plan/`

```json
{"start": "New York, NY", "finish": "Los Angeles, CA"}
```

`start` / `finish` can be `"City, ST"`, `"lat,lng"` or a free text address.

Response (trimmed):

```json
{
  "status": true,
  "message": "Route planned, happy driving!",
  "data": {
    "distance_miles": 2810.4,
    "duration_hours": 50.3,
    "fuel_stops": [
      {"name": "SHEETZ #639", "city": "Youngstown", "state": "OH", "price_per_gallon": 3.059,
       "mile_marker": 395.0, "gallons": 35.51, "cost": 108.62, "lat": 41.1, "lng": -80.65}
    ],
    "total_gallons": 230.61,
    "total_fuel_cost": 709.16,
    "route": {"type": "LineString", "coordinates": [[-73.93, 40.66], "..."]},
    "map_url": "http://localhost:8000/api/route/map/?start=New+York%2C+NY&finish=Los+Angeles%2C+CA"
  }
}
```

`GET /api/route/map/?start=...&finish=...` renders the route and fuel stops on a Leaflet map. Same plan as above,
served from cache so it doesn't hit the routing API again.

Postman collection is in `postman_collection.json`.

## How it works

- **Routing**: [OSRM](https://project-osrm.org/) public server, free and no key. **One call per trip**, cached for a
  day. `City, ST` and `lat,lng` inputs are resolved from the local census table, so no geocoding call is made. Only a
  free text address falls back to Nominatim (max 2 extra calls, also cached).
- **Stations on the route**: route geometry is sampled at every mile, stations are pre-filtered with a bounding box and
  then matched to the nearest route point with numpy. Anything within 10 miles of the route counts, and its mile marker
  is the position of that nearest point.
- **Picking stops**: shortest path over origin -> stations -> finish where no leg is longer than 500 miles. The truck
  leaves with a full tank and at every stop buys just enough fuel for the next leg, so the cost is the actual money
  spent on the trip. A $5 penalty per stop stops it from pulling over twice in 10 miles to save a few cents.

## Assumptions

- Truck starts with a full tank (50 gal), so trips under 500 miles don't need a stop.
- Station coordinates are the city centroid, which is good enough to place truck stops along the interstate.
- If the same truckstop id shows up multiple times in the CSV, the cheapest price is kept.

## Tests

```bash
python manage.py test
```
