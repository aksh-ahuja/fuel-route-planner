class FailureMessage:
    LOCATION_NOT_FOUND = "We couldn't find '{}' in the USA, try 'City, ST' or 'lat,lng'"
    LOCATION_OUTSIDE_USA = "'{}' is outside the USA, we only plan trips within the USA"
    ROUTE_NOT_FOUND = "No drivable route found between these two places"
    FUEL_GAP_TOO_LARGE = "There's a stretch of more than 500 miles without any fuel station from our price list on this route"


class SuccessMessage:
    ROUTE_PLANNED = "Route planned, happy driving!"
    NO_FUEL_STOP_NEEDED = "A full tank gets you there, no fuel stop needed!"
