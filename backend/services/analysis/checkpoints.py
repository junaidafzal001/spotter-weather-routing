"""Checkpoint sampling along a route at fixed mile intervals."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from services.geo.geometry import (
    interpolate_coordinate,
    interpolate_scalar,
    meters_to_miles,
    miles_to_meters,
)


@dataclass(frozen=True)
class Checkpoint:
    index: int
    target_m: float              # cumulative distance from origin (meters)
    mile: float                  # same, in miles
    coord: tuple[float, float]   # (lon, lat)
    eta: datetime


def build_checkpoints(
    *,
    coords: list[tuple[float, float]],
    cumdist_m: list[float],
    cumdur_s: list[float],
    interval_miles: int,
    departure_utc: datetime,
) -> list[Checkpoint]:
    total_m = cumdist_m[-1]
    interval_m = miles_to_meters(interval_miles)

    targets: list[float] = [0.0]
    k = 1
    while interval_m * k < total_m - 1.0:  # avoid a duplicate checkpoint at the destination
        targets.append(interval_m * k)
        k += 1
    targets.append(total_m)

    checkpoints: list[Checkpoint] = []
    for idx, target in enumerate(targets):
        lon, lat = interpolate_coordinate(coords, cumdist_m, target)
        eta_s = interpolate_scalar(cumdist_m, cumdur_s, target)
        checkpoints.append(
            Checkpoint(
                index=idx,
                target_m=target,
                mile=round(meters_to_miles(target), 2),
                coord=(lon, lat),
                eta=departure_utc + timedelta(seconds=eta_s),
            )
        )
    return checkpoints


def checkpoint_interval_targets(interval_miles: int, total_m: float) -> list[float]:
    interval_m = miles_to_meters(interval_miles)
    targets = [0.0]
    k = 1
    while interval_m * k < total_m - 1.0:
        targets.append(interval_m * k)
        k += 1
    targets.append(total_m)
    return targets
