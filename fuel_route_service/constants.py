MAX_STATION_NAME_LENGTH = 255
MAX_ADDRESS_LENGTH = 255
MAX_CITY_LENGTH = 100
MAX_STATE_LENGTH = 2
MAX_LOCATION_QUERY_LENGTH = 200

VEHICLE_MAX_RANGE_MILES = 500
VEHICLE_MILES_PER_GALLON = 10

# stations are geocoded to city centroid so allow some slack around the route
ROUTE_CORRIDOR_MILES = 10
ROUTE_SAMPLE_STEP_MILES = 1
STOP_PENALTY_DOLLARS = 5

METERS_PER_MILE = 1609.344
SECONDS_PER_HOUR = 3600

ROUTE_CACHE_TIMEOUT = 60 * 60 * 24
GEOCODE_CACHE_TIMEOUT = 60 * 60 * 24 * 7

US_LAT_RANGE = (18.0, 72.0)
US_LNG_RANGE = (-180.0, -65.0)

US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI", "ID", "IL", "IN", "IA",
    "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM",
    "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA",
    "WV", "WI", "WY",
}


class CacheKey:
    ROUTE = "route:{}:{}:{}:{}"
    GEOCODE = "geocode:{}"
