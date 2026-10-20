import type {
  Analysis,
  AnalyzeTripInput,
  ApiEnvelope,
  Corridor,
  Health,
  Suggestion,
} from "../types";

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ?? "";

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly fields: Record<string, string>;

  constructor(message: string, code: string, status: number, fields: Record<string, string> = {}) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.fields = fields;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<ApiEnvelope<T>> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch {
    throw new ApiError(
      "Could not reach the routing API. Is the backend running?",
      "network_error",
      0,
    );
  }

  const body = await response.json().catch(() => null);
  if (!response.ok || !body) {
    const error = body?.error;
    throw new ApiError(
      error?.detail ?? `Request failed with status ${response.status}`,
      error?.code ?? "request_failed",
      response.status,
      error?.fields ?? {},
    );
  }
  return body as ApiEnvelope<T>;
}

export const api = {
  analyzeTrip: (input: AnalyzeTripInput) =>
    request<Analysis>("/api/routes/analyze/", {
      method: "POST",
      body: JSON.stringify(input),
    }),

  corridor: (analysisId: string, routeId: string) =>
    request<Corridor>(
      `/api/weather/corridor/?analysis_id=${encodeURIComponent(analysisId)}&route_id=${encodeURIComponent(routeId)}`,
    ),

  health: () => request<Health>("/api/health/"),

  suggest: (query: string) =>
    request<{ suggestions: Suggestion[] }>(
      `/api/geocode/suggest/?q=${encodeURIComponent(query)}`,
    ),
};
