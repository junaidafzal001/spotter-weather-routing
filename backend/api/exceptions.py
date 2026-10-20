"""Maps service and DRF errors to the response envelope."""
from __future__ import annotations

import logging

from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler as drf_exception_handler

from api.responses import failure
from services.errors import ServiceError

logger = logging.getLogger(__name__)


def service_exception_handler(exc, context):
    if isinstance(exc, ServiceError):
        return failure(exc.code, exc.detail, exc.status, exc.fields)

    response = drf_exception_handler(exc, context)
    if response is None:
        logger.exception("Unhandled exception", exc_info=exc)
        return failure("internal_error", "An unexpected error occurred.", 500)

    if isinstance(exc, APIException):
        detail = response.data
        fields: dict = {}
        text = "Invalid request."
        if isinstance(detail, dict):
            fields = {k: (", ".join(map(str, v)) if isinstance(v, list) else str(v)) for k, v in detail.items()}
            first = next(iter(detail.values()), None)
            text = ", ".join(map(str, first)) if isinstance(first, list) else str(first)
        elif isinstance(detail, list):
            text = ", ".join(map(str, detail))
        return failure("invalid_request", text, response.status_code, fields)

    return response
