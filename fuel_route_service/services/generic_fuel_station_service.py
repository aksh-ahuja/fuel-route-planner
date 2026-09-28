from functools import cache

import numpy as np
from django.db import transaction

from fuel_route_service.models import FuelStation


class GenericFuelStationService:

    @classmethod
    def get_fuel_station(cls, id=None, ids=None, state=None, is_geocoded=None):
        qs = FuelStation.objects
        if id is not None:
            qs = qs.filter(id=id)
        if ids is not None:
            qs = qs.filter(id__in=ids)
        if state is not None:
            qs = qs.filter(state=state)
        if is_geocoded is not None:
            qs = qs.filter(lat__isnull=not is_geocoded)
        return qs

    @classmethod
    @transaction.atomic()
    def replace_fuel_stations(cls, stations):
        FuelStation.objects.all().delete()
        FuelStation.objects.bulk_create([FuelStation(**station) for station in stations], batch_size=2000)
        cls.get_station_arrays.cache_clear()

    @classmethod
    @cache
    def get_station_arrays(cls):
        # loaded once per process, route matching runs on numpy instead of hitting the db
        rows = list(cls.get_fuel_station(is_geocoded=True).values_list("id", "lat", "lng", "retail_price"))
        return {
            "ids": np.array([row[0] for row in rows]),
            "lats": np.array([row[1] for row in rows], dtype=float),
            "lngs": np.array([row[2] for row in rows], dtype=float),
            "prices": np.array([row[3] for row in rows], dtype=float),
        }
