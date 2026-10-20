import type { RiskLevel } from "../types";

export const RISK_ORDER: RiskLevel[] = ["LOW", "MODERATE", "HIGH", "SEVERE", "NO_TRAVEL"];

export const RISK_COLORS: Record<RiskLevel, string> = {
  LOW: "#16a34a",
  MODERATE: "#eab308",
  HIGH: "#f97316",
  SEVERE: "#dc2626",
  NO_TRAVEL: "#7f1d1d",
  UNKNOWN: "#9ca3af",
};

export const RISK_LABELS: Record<RiskLevel, string> = {
  LOW: "Low",
  MODERATE: "Moderate",
  HIGH: "High",
  SEVERE: "Severe",
  NO_TRAVEL: "No Travel",
  UNKNOWN: "Unknown",
};

export const RISK_TEXT_CLASSES: Record<RiskLevel, string> = {
  LOW: "text-risk-low",
  MODERATE: "text-yellow-600",
  HIGH: "text-risk-high",
  SEVERE: "text-risk-severe",
  NO_TRAVEL: "text-red-900",
  UNKNOWN: "text-risk-unknown",
};

export const RISK_BG_CLASSES: Record<RiskLevel, string> = {
  LOW: "bg-risk-low/10 text-risk-low border-risk-low/30",
  MODERATE: "bg-yellow-400/10 text-yellow-700 border-yellow-400/40",
  HIGH: "bg-orange-500/10 text-orange-600 border-orange-500/30",
  SEVERE: "bg-red-600/10 text-risk-severe border-red-600/30",
  NO_TRAVEL: "bg-red-900/10 text-red-900 border-red-900/30",
  UNKNOWN: "bg-gray-400/10 text-gray-500 border-gray-400/30",
};

export function riskColor(level: RiskLevel | null | undefined): string {
  return RISK_COLORS[level ?? "UNKNOWN"] ?? RISK_COLORS.UNKNOWN;
}

export function heatmapWeight(level: RiskLevel): number {
  switch (level) {
    case "LOW":
      return 0.12;
    case "MODERATE":
      return 0.38;
    case "HIGH":
      return 0.62;
    case "SEVERE":
      return 0.85;
    case "NO_TRAVEL":
      return 1;
    default:
      return 0;
  }
}

export function severityScore(level: RiskLevel): number {
  const idx = RISK_ORDER.indexOf(level);
  return idx === -1 ? 0 : idx;
}

export interface HourSummary {
  counts: Record<RiskLevel, number>;
  total: number;
  worst: RiskLevel | null;
}

export function summarizeHour(
  points: { severity_by_hour: RiskLevel[] }[],
  hour: number,
): HourSummary {
  const counts: Record<RiskLevel, number> = {
    LOW: 0,
    MODERATE: 0,
    HIGH: 0,
    SEVERE: 0,
    NO_TRAVEL: 0,
    UNKNOWN: 0,
  };
  for (const point of points) {
    const level = point.severity_by_hour[hour];
    if (level) counts[level] += 1;
  }
  const worst = [...RISK_ORDER].reverse().find((level) => counts[level] > 0) ?? null;
  return { counts, total: points.length, worst };
}
