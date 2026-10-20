"""API views."""
from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime

from django.conf import settings
from django.core.cache import cache
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.views import APIView

from api.responses import success
from api.serializers import AnalyzeTripSerializer
from services.analysis import corridor_service, pipeline
from services.geocoding import nominatim

logger = logging.getLogger(__name__)


class AnalyzeTripView(APIView):

    def post(self, request):
        serializer = AnalyzeTripSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        v = serializer.validated_data

        result = pipeline.run_analysis(
            origin_query=v["origin"].strip(),
            destination_query=v["destination"].strip(),
            departure_time=v["departure_time"],
            load_weight_lbs=v["load_weight_lbs"],
            checkpoint_interval_miles=v["checkpoint_interval_miles"],
        )
        return success(
            result,
            warnings=result.get("warnings"),
            meta=result.get("meta"),
        )


@api_view(["GET"])
def corridor_weather(request):
    analysis_id = (request.query_params.get("analysis_id") or "").strip()
    route_id = (request.query_params.get("route_id") or "").strip()

    if not analysis_id:
        raise DRFValidationError({"analysis_id": "This query parameter is required."})
    if not route_id:
        raise DRFValidationError({"route_id": "This query parameter is required."})

    payload = corridor_service.build_corridor(analysis_id, route_id)
    return success(
        payload,
        warnings=payload.get("notes"),
        meta={"hours": len(payload["hours"]), "points": len(payload["points"])},
    )


@api_view(["GET"])
def geocode_suggest(request):
    q = (request.query_params.get("q") or "").strip()
    if len(q) < 3:
        return success({"suggestions": []}, meta={"query": q})

    cache_key = "suggest:" + hashlib.sha1(q.lower().encode()).hexdigest()
    cached = cache.get(cache_key)
    if cached is not None:
        return success({"suggestions": cached}, meta={"query": q, "cache": "hit"})

    places = nominatim.suggest(q, limit=5)
    suggestions = [
        {"label": p.display_name, "lat": p.lat, "lon": p.lon} for p in places
    ]
    cache.set(cache_key, suggestions, settings.GEOCODE_CACHE_TTL)
    return success({"suggestions": suggestions}, meta={"query": q})


@api_view(["GET"])
def health(request):
    return success(
        {
            "status": "ok",
            "version": "1.0.0",
            "providers": {
                "openrouteservice": bool(settings.ORS_API_KEY),
                "graphhopper": bool(settings.GRAPHHOPPER_API_KEY),
                "osrm_fallback": settings.OSRM_BASE_URL,
                "nominatim": settings.NOMINATIM_BASE_URL,
                "open_meteo": settings.OPEN_METEO_BASE_URL,
            },
            "time": datetime.now(UTC).isoformat(),
        }
    )
