"""Success and error response envelope."""
from __future__ import annotations

from rest_framework.response import Response


def success(data, warnings=None, meta=None, status: int = 200) -> Response:
    return Response({"data": data, "warnings": warnings or [], "meta": meta or {}}, status=status)


def failure(code: str, detail: str, status: int, fields: dict | None = None) -> Response:
    return Response({"error": {"code": code, "detail": detail, "fields": fields or {}}}, status=status)
