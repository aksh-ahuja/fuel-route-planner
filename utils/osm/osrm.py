import requests
from django.conf import settings

OSRM_TIMEOUT_SECONDS = 15


def get_driving_route(start_lat, start_lng, finish_lat, finish_lng):
    url = f"{settings.OSRM_BASE_URL}/route/v1/driving/{start_lng},{start_lat};{finish_lng},{finish_lat}"
    params = {"overview": "full", "geometries": "geojson"}
    response = requests.get(url, params=params, timeout=OSRM_TIMEOUT_SECONDS)
    # osrm sends 400 with a code like NoRoute, caller handles that
    if response.status_code != 400:
        response.raise_for_status()
    return response.json()
