CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "fuel-route-cache",
        "OPTIONS": {"MAX_ENTRIES": 5000},
    }
}
