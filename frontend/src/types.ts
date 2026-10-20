
export type RiskLevel = "LOW" | "MODERATE" | "HIGH" | "SEVERE" | "NO_TRAVEL" | "UNKNOWN";

export interface WeatherSample {
  available: boolean;
  eta_utc: string;
  forecast_time: string | null;
  wind_mph: number | null;
  wind_gust_mph: number | null;
  rain_in_hr: number | null;
  snow_in_hr: number | null;
  temperature_f: number | null;
  weather_code: number | null;
  condition: string | null;
  source: string | null;
  unavailability_reason: string | null;
  interpolated: boolean;
}

export interface RiskContributions {
  wind: RiskLevel | null;
  rain: RiskLevel | null;
  snow: RiskLevel | null;
}

export interface RiskInfo {
  available: boolean;
  level: RiskLevel;
  score: number | null;
  contributions: RiskContributions;
  load_rule_applied: string | null;
  complete: boolean;
}

export interface Checkpoint {
  index: number;
  mile: number;
  coordinates: [number, number];
  eta: string;
  weather: WeatherSample;
  risk: RiskInfo;
}

export interface RouteSegment {
  from_mile: number;
  to_mile: number;
  level: RiskLevel | null;
  coordinates: [number, number][];
}

export interface Exposure {
  low_miles: number;
  moderate_miles: number;
  high_miles: number;
  severe_miles: number;
  no_travel_miles: number;
  unassessed_miles: number;
  total_miles: number;
  average_risk: number | null;
  max_risk: RiskLevel | null;
  unassessed_share: number;
}

export interface RouteOption {
  id: string;
  provider: string;
  profile: string;
  timing_source: string;
  distance_miles: number;
  duration_minutes: number;
  departure_time: string;
  arrival_time: string;
  checkpoint_count: number;
  checkpoints: Checkpoint[];
  segments: RouteSegment[];
  exposure: Exposure;
  warnings: string[];
}

export interface Recommendation {
  recommended_route_id: string | null;
  reason: string;
  eligible: boolean;
  ranking: string[];
  least_exposed_route_id: string | null;
  least_exposed_reason: string | null;
}

export interface ResolvedPlace {
  input: string;
  resolved: string;
  lat: number;
  lon: number;
}

export interface Analysis {
  analysis_id: string;
  request: {
    origin: ResolvedPlace;
    destination: ResolvedPlace;
    departure_time_utc: string;
    load_weight_lbs: number;
    checkpoint_interval_miles: number;
  };
  routes: RouteOption[];
  recommendation: Recommendation;
  warnings: string[];
  meta: {
    generated_at: string;
    route_count: number;
    providers: { routing: string[]; geocoding: string[]; weather: string[] };
  };
}

export interface CorridorPoint {
  lat: number;
  lon: number;
  mile: number;
  offset_miles: number;
  severity_by_hour: RiskLevel[];
  values_by_hour: {
    wind_mph: number | null;
    rain_in_hr: number | null;
    snow_in_hr: number | null;
  }[];
}

export interface Corridor {
  analysis_id: string;
  route_id: string;
  load_weight_lbs: number;
  generated_at: string;
  slider_start_utc: string;
  hours: string[];
  points: CorridorPoint[];
  notes: string[];
}

export interface Suggestion {
  label: string;
  lat: number;
  lon: number;
}

export interface Health {
  status: string;
  version: string;
  providers: {
    openrouteservice: boolean;
    graphhopper: boolean;
    osrm_fallback: string;
    nominatim: string;
    open_meteo: string;
  };
  time: string;
}

export interface ApiEnvelope<T> {
  data: T;
  warnings: string[];
  meta: Record<string, unknown>;
}

export interface AnalyzeTripInput {
  origin: string;
  destination: string;
  departure_time: string;
  load_weight_lbs: number;
  checkpoint_interval_miles: 10 | 25 | 50;
}
