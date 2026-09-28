import requests
from django.conf import settings

NOMINATIM_TIMEOUT_SECONDS = 10
USER_AGENT = "fuel-route-planner/1.0"


def search_us_location(query):
    params = {"q": query, "format": "json", "limit": 1, "countrycodes": "us"}
    response = requests.get(f"{settings.NOMINATIM_BASE_URL}/search", params=params,
                            headers={"User-Agent": USER_AGENT}, timeout=NOMINATIM_TIMEOUT_SECONDS)
    response.raise_for_status()
    results = response.json()
    if not results:
        return None
    return float(results[0]["lat"]), float(results[0]["lon"])
