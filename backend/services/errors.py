"""Typed service errors mapped to API responses."""


class ServiceError(Exception):

    code = "service_error"
    status = 500

    def __init__(self, detail: str, *, code: str | None = None, status: int | None = None, fields: dict | None = None):
        super().__init__(detail)
        self.detail = detail
        self.fields = fields or {}
        if code:
            self.code = code
        if status:
            self.status = status


class GeocodingError(ServiceError):
    code = "geocoding_failed"
    status = 502


class GeocodeNotFoundError(ServiceError):
    code = "geocode_not_found"
    status = 422


class RoutingError(ServiceError):
    code = "routing_failed"
    status = 502


class NoRouteFoundError(RoutingError):
    code = "no_route_found"
    status = 422


class WeatherProviderError(ServiceError):
    code = "weather_provider_failed"
    status = 502


class ValidationError(ServiceError):
    code = "invalid_request"
    status = 400
