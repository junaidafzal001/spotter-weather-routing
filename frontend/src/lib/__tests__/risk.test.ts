import { describe, expect, it } from "vitest";
import type { RiskLevel } from "../../types";
import { heatmapWeight, riskColor, RISK_COLORS, RISK_ORDER, summarizeHour } from "../risk";

describe("risk utilities", () => {
  it("has distinct, accessible colors for every severity", () => {
    for (const level of [...RISK_ORDER, "UNKNOWN" as const]) {
      expect(RISK_COLORS[level]).toMatch(/^#[0-9a-f]{6}$/i);
    }
    expect(new Set(Object.values(RISK_COLORS)).size).toBe(6);
  });

  it("maps null to the unknown grey", () => {
    expect(riskColor(null)).toBe(RISK_COLORS.UNKNOWN);
    expect(riskColor("NO_TRAVEL")).toBe(RISK_COLORS.NO_TRAVEL);
  });

  it("weights heatmap severity monotonically", () => {
    const weights = RISK_ORDER.map(heatmapWeight);
    for (let i = 1; i < weights.length; i += 1) {
      expect(weights[i]).toBeGreaterThan(weights[i - 1]);
    }
    expect(heatmapWeight("UNKNOWN")).toBe(0);
  });

  it("summarizes one hour across corridor samples", () => {
    const points: { severity_by_hour: RiskLevel[] }[] = [
      { severity_by_hour: ["LOW", "SEVERE", "NO_TRAVEL"] },
      { severity_by_hour: ["MODERATE", "SEVERE", "LOW"] },
      { severity_by_hour: ["LOW", "HIGH", "LOW"] },
    ];
    const hour1 = summarizeHour(points, 1);
    expect(hour1.counts.SEVERE).toBe(2);
    expect(hour1.counts.HIGH).toBe(1);
    expect(hour1.worst).toBe("SEVERE");
    expect(hour1.total).toBe(3);

    const hour2 = summarizeHour(points, 2);
    expect(hour2.worst).toBe("NO_TRAVEL");
  });
});
