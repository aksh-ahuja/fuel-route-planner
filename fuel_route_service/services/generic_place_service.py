from django.db import transaction

from fuel_route_service.models import Place


class GenericPlaceService:

    @classmethod
    def get_place(cls, normalized_name=None, state=None):
        qs = Place.objects
        if normalized_name is not None:
            qs = qs.filter(normalized_name=normalized_name)
        if state is not None:
            qs = qs.filter(state=state)
        return qs

    @classmethod
    @transaction.atomic()
    def replace_places(cls, places):
        Place.objects.all().delete()
        Place.objects.bulk_create([Place(**place) for place in places], batch_size=5000)
