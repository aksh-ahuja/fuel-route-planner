import logging
from urllib.parse import urlencode

from rest_framework import status
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from utils.decorator import validate_input_data
from utils.helpers import get_error_response, get_success_response
from .messages import SuccessMessage
from .serializers import RoutePlanInputSerializer
from .services import GenericRouteService

logger = logging.getLogger(__name__)


class RoutePlanView(APIView):

    @validate_input_data(RoutePlanInputSerializer)
    def post(self, request, *args, **kwargs):
        validated_data = kwargs.get("validated_data", {})
        start = validated_data.get("start")
        finish = validated_data.get("finish")

        plan_resp = GenericRouteService.plan_trip(start, finish)
        if not plan_resp.success:
            return Response(get_error_response(plan_resp.message), status=status.HTTP_400_BAD_REQUEST)

        data = plan_resp.data
        data["map_url"] = request.build_absolute_uri(f"/api/route/map/?{urlencode({'start': start, 'finish': finish})}")
        message = SuccessMessage.ROUTE_PLANNED if data["fuel_stops"] else SuccessMessage.NO_FUEL_STOP_NEEDED
        return Response(get_success_response(message, data), status=status.HTTP_200_OK)


class RouteMapView(APIView):
    renderer_classes = (TemplateHTMLRenderer,)
    template_name = "fuel_route_service/route_map.html"

    def get(self, request, *args, **kwargs):
        serializer = RoutePlanInputSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response({"error": "Pass start and finish as query params"}, status=status.HTTP_400_BAD_REQUEST)

        plan_resp = GenericRouteService.plan_trip(serializer.data.get("start"), serializer.data.get("finish"))
        if not plan_resp.success:
            return Response({"error": plan_resp.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"plan": plan_resp.data}, status=status.HTTP_200_OK)
