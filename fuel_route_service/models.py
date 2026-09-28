from django.db import models

from utils.abstract_models import TimeStampedModel
from .constants import MAX_ADDRESS_LENGTH, MAX_CITY_LENGTH, MAX_STATE_LENGTH, MAX_STATION_NAME_LENGTH


class Place(TimeStampedModel):
    """US census places + county subdivisions, used to geocode stations and 'City, ST' inputs offline."""
    name = models.CharField(max_length=MAX_CITY_LENGTH)
    normalized_name = models.CharField(max_length=MAX_CITY_LENGTH)
    state = models.CharField(max_length=MAX_STATE_LENGTH)
    lat = models.FloatField()
    lng = models.FloatField()

    class Meta:
        db_table = "places"
        indexes = [models.Index(fields=["normalized_name", "state"])]


class FuelStation(TimeStampedModel):
    opis_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=MAX_STATION_NAME_LENGTH)
    address = models.CharField(max_length=MAX_ADDRESS_LENGTH)
    city = models.CharField(max_length=MAX_CITY_LENGTH)
    state = models.CharField(max_length=MAX_STATE_LENGTH)
    rack_id = models.IntegerField(null=True, blank=True)
    retail_price = models.DecimalField(max_digits=8, decimal_places=5)
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = "fuel_stations"
