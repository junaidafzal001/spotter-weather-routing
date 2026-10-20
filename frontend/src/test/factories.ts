import type { Analysis, Checkpoint, Corridor, RouteOption, RouteSegment } from "../types";

export function makeCheckpoint(index: number, level: Checkpoint["risk"]["level"] = "LOW"): Checkpoint {
  const available = level !== "UNKNOWN";
  return {
    index,
    mile: index * 25,
    coordinates: [-87.6 + index * 0.4, 41.8],
    eta: new Date(Date.UTC(2026, 9, 20, 15 + index)).toISOString(),
    weather: {
      available,
      eta_utc: new Date(Date.UTC(2026, 9, 20, 15 + index)).toISOString(),
      forecast_time: new Date(Date.UTC(2026, 9, 20, 15 + index)).toISOString(),
      wind_mph: available ? 12.5 : null,
      wind_gust_mph: available ? 18 : null,
      rain_in_hr: available ? 0.05 : null,
      snow_in_hr: available ? 0 : null,
      temperature_f: available ? 55 : null,
      weather_code: available ? 3 : null,
      condition: available ? "Overcast" : null,
      source: available ? "open-meteo" : null,
      unavailability_reason: available ? null : "outside forecast range",
      interpolated: available,
    },
    risk: {
      available,
      level,
      score: available ? 0 : null,
      contributions: {
        wind: available ? "LOW" : null,
        rain: available ? "LOW" : null,
        snow: available ? "LOW" : null,
      },
      load_rule_applied: null,
      complete: available,
    },
  };
}

export function makeRoute(overrides: Partial<RouteOption> = {}): RouteOption {
  const segments: RouteSegment[] = [
    {
      from_mile: 0,
      to_mile: 25,
      level: "LOW",
      coordinates: [
        [-87.6, 41.8],
        [-87.2, 41.9],
      ],
    },
    {
      from_mile: 25,
      to_mile: 50,
      level: "MODERATE",
      coordinates: [
        [-87.2, 41.9],
        [-86.8, 42.0],
      ],
    },
  ];
  return {
    id: "route-1",
    provider: "openrouteservice",
    profile: "driving-hgv",
    timing_source: "provider",
    distance_miles: 50,
    duration_minutes: 60,
    departure_time: "2026-10-20T15:00:00Z",
    arrival_time: "2026-10-20T16:00:00Z",
    checkpoint_count: 3,
    checkpoints: [makeCheckpoint(0), makeCheckpoint(1, "MODERATE"), makeCheckpoint(2)],
    segments,
    exposure: {
      low_miles: 30,
      moderate_miles: 20,
      high_miles: 0,
      severe_miles: 0,
      no_travel_miles: 0,
      unassessed_miles: 0,
      total_miles: 50,
      average_risk: 0.4,
      max_risk: "MODERATE",
      unassessed_share: 0,
    },
    warnings: [],
    ...overrides,
  };
}

export function makeAnalysis(overrides: Partial<Analysis> = {}): Analysis {
  const route1 = makeRoute();
  const route2 = makeRoute({
    id: "route-2",
    distance_miles: 56,
    duration_minutes: 70,
    checkpoints: [makeCheckpoint(0), makeCheckpoint(1, "HIGH"), makeCheckpoint(2, "SEVERE")],
    exposure: {
      low_miles: 20,
      moderate_miles: 10,
      high_miles: 12,
      severe_miles: 14,
      no_travel_miles: 0,
      unassessed_miles: 0,
      total_miles: 56,
      average_risk: 1.36,
      max_risk: "SEVERE",
      unassessed_share: 0,
    },
  });
  return {
    analysis_id: "abc123",
    request: {
      origin: { input: "Chicago, IL", resolved: "Chicago, IL, USA", lat: 41.88, lon: -87.63 },
      destination: { input: "Detroit, MI", resolved: "Detroit, MI, USA", lat: 42.33, lon: -83.05 },
      departure_time_utc: "2026-10-20T15:00:00Z",
      load_weight_lbs: 35_000,
      checkpoint_interval_miles: 25,
    },
    routes: [route1, route2],
    recommendation: {
      recommended_route_id: "route-1",
      reason: "Recommended because this route avoids severe weather.",
      eligible: true,
      ranking: ["route-1", "route-2"],
      least_exposed_route_id: null,
      least_exposed_reason: null,
    },
    warnings: [],
    meta: {
      generated_at: "2026-10-20T12:00:00Z",
      route_count: 2,
      providers: { routing: ["openrouteservice"], geocoding: ["nominatim"], weather: ["open-meteo"] },
    },
    ...overrides,
  };
}

export function makeCorridor(overrides: Partial<Corridor> = {}): Corridor {
  const hours = Array.from({ length: 49 }, (_, i) =>
    new Date(Date.UTC(2026, 9, 20, 12 + i)).toISOString(),
  );
  // Time-varying severity profile: LOW early, SEVERE mid-window, MODERATE late.
  const severityAtHour = (hour: number): "LOW" | "SEVERE" | "MODERATE" =>
    hour < 8 ? "LOW" : hour < 20 ? "SEVERE" : "MODERATE";
  const points = [0, 1, 2].map((index) => ({
    lat: 41.8 + index * 0.2,
    lon: -87.6 + index * 0.5,
    mile: index * 25,
    offset_miles: index === 1 ? 0 : index === 0 ? -15 : 15,
    severity_by_hour: Array.from({ length: 49 }, (_, hour) => severityAtHour(hour)),
    values_by_hour: hours.map(() => ({ wind_mph: 12, rain_in_hr: 0.02, snow_in_hr: 0 })),
  }));
  return {
    analysis_id: "abc123",
    route_id: "route-1",
    load_weight_lbs: 35_000,
    generated_at: "2026-10-20T12:00:00Z",
    slider_start_utc: hours[0],
    hours,
    points,
    notes: ["Heatmap intensity is a spatial interpolation between sample locations."],
    ...overrides,
  };
}
