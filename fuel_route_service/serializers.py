from rest_framework import serializers

from .constants import MAX_LOCATION_QUERY_LENGTH


class RoutePlanInputSerializer(serializers.Serializer):
    start = serializers.CharField(max_length=MAX_LOCATION_QUERY_LENGTH)
    finish = serializers.CharField(max_length=MAX_LOCATION_QUERY_LENGTH)
