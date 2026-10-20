"""Shared respx responders that adapt fixture templates to any request shape.

Open-Meteo's multi-location contract returns one location object per
requested coordinate.  These helpers replicate a template location so tests
stay realistic regardless of how many lattice/checkpoint points the pipeline
requests.
"""
from __future__ import annotations

from copy import deepcopy

from httpx import Response

from tests.conftest import load_fixture


def open_meteo_multi(template_name: str = "open_meteo_corridor.json"):
    def handler(request) -> Response:
        template = load_fixture(template_name)
        template = template[0] if isinstance(template, list) else template
        params = request.url.params
        lats = str(params.get("latitude", "")).split(",")
        lons = str(params.get("longitude", "")).split(",")
        entries = []
        for lat, lon in zip(lats, lons, strict=True):
            entry = deepcopy(template)
            entry["latitude"] = float(lat)
            entry["longitude"] = float(lon)
            entries.append(entry)
        return Response(200, json=entries)

    return handler


def open_meteo_by_forecast_days(
    corridor_template: str = "open_meteo_corridor.json",
    checkpoint_template: str = "open_meteo_checkpoints.json",
):
    def handler(request) -> Response:
        params = request.url.params
        if str(params.get("forecast_days")) == "3":
            return open_meteo_multi(corridor_template)(request)
        return Response(200, json=load_fixture(checkpoint_template))

    return handler


def nominatim_by_query(chicago: str = "nominatim_chicago.json", detroit: str = "nominatim_detroit.json"):

    def handler(request) -> Response:
        q = str(request.url.params.get("q", "")).lower()
        if "detroit" in q:
            return Response(200, json=load_fixture(detroit))
        return Response(200, json=load_fixture(chicago))

    return handler
