from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin-5f2c9e1a/", admin.site.urls),
    path("api/route/", include("fuel_route_service.urls")),
]
