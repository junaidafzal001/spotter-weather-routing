from django.http import JsonResponse
from django.urls import include, path


def root(request):
    return JsonResponse(
        {
            "service": "spotter-weather-routing-api",
            "health": "/api/health/",
            "endpoints": ["/api/routes/analyze/", "/api/weather/corridor/", "/api/geocode/suggest/", "/api/health/"],
        }
    )


urlpatterns = [
    path("", root),
    path("api/", include("api.urls")),
]
