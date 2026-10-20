"""Request validation for /api/routes/analyze/."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from rest_framework import serializers


class AnalyzeTripSerializer(serializers.Serializer):
    origin = serializers.CharField(
        min_length=2, max_length=200, help_text="Free-text origin, e.g. 'Chicago, IL'"
    )
    destination = serializers.CharField(
        min_length=2, max_length=200, help_text="Free-text destination, e.g. 'Detroit, MI'"
    )
    departure_time = serializers.DateTimeField(help_text="ISO-8601 with offset, e.g. 2026-10-22T08:00:00-05:00")
    load_weight_lbs = serializers.IntegerField(
        min_value=0,
        max_value=80_000,
        help_text="Load weight in pounds (0–80,000). Drives the load-dependent wind rules.",
    )
    checkpoint_interval_miles = serializers.ChoiceField(
        choices=[10, 25, 50], default=25, help_text="Weather checkpoint spacing in miles"
    )

    def validate_departure_time(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            # Treat naive input as the server's UTC clock — documented behavior.
            value = value.replace(tzinfo=UTC)
        if value < datetime.now(UTC) - timedelta(minutes=5):
            raise serializers.ValidationError("departure_time must not be in the past.")
        if value > datetime.now(UTC) + timedelta(days=15):
            raise serializers.ValidationError(
                "departure_time is beyond the 15-day forecast horizon of the weather provider."
            )
        return value

    def validate(self, attrs):
        if attrs["origin"].strip().lower() == attrs["destination"].strip().lower():
            raise serializers.ValidationError(
                {"destination": "Origin and destination must be different."}
            )
        return attrs
