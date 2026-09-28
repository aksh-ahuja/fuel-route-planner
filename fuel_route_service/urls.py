from django.urls import path

from .views import RouteMapView, RoutePlanView

urlpatterns = [
    path('plan/', RoutePlanView.as_view()),
    path('map/', RouteMapView.as_view()),
]
