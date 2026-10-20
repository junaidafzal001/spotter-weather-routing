from django.urls import path

from api import views

urlpatterns = [
    path("routes/analyze/", views.AnalyzeTripView.as_view(), name="analyze-trip"),
    path("weather/corridor/", views.corridor_weather, name="corridor-weather"),
    path("geocode/suggest/", views.geocode_suggest, name="geocode-suggest"),
    path("health/", views.health, name="health"),
]
