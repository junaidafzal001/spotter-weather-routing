import { describe, expect, it } from "vitest";
import { buildCheckpointFeatures, buildHeatFeatures, buildRouteFeatures, routeBounds } from "../mapData";
import { makeCorridor, makeRoute } from "../../test/factories";

describe("map data builders", () => {
  it("builds colored route features with selection flags", () => {
    const routes = [makeRoute(), makeRoute({ id: "route-2" })];
    const fc = buildRouteFeatures(routes, "route-2", "route-1");
    expect(fc.features).toHaveLength(4); // 2 segments per route
    const selected = fc.features.filter((f) => f.properties.selected);
    expect(selected.every((f) => f.properties.route_id === "route-2")).toBe(true);
    const recommended = fc.features.filter((f) => f.properties.recommended);
    expect(recommended.every((f) => f.properties.route_id === "route-1")).toBe(true);
    expect(fc.features.map((f) => f.properties.level)).toContain("MODERATE");
  });

  it("draws checkpoints only for the selected route", () => {
    expect(buildCheckpointFeatures(null).features).toHaveLength(0);
    const fc = buildCheckpointFeatures(makeRoute());
    expect(fc.features).toHaveLength(3);
    expect(fc.features[0].properties.checkpoint_index).toBe(0);
    expect(fc.features[0].geometry.type).toBe("Point");
  });

  it("uses the requested slider hour for heat features (never one fixed timestamp)", () => {
    const corridor = makeCorridor();
    const hour0 = buildHeatFeatures(corridor, 0);
    const hour9 = buildHeatFeatures(corridor, 9);
    expect(hour0.features).toHaveLength(3);
    expect(hour9.features).toHaveLength(3);
    expect(hour9.features[0].properties.weight).toBeGreaterThan(hour0.features[0].properties.weight);
    expect(hour9.features[0].properties.hour).toBe(9);

    // hour 22 is a uniform MODERATE window
    const hour22 = buildHeatFeatures(corridor, 22);
    expect(hour22.features.every((f) => f.properties.level === "MODERATE")).toBe(true);
  });

  it("omits unknown severity points from the heatmap", () => {
    const corridor = makeCorridor();
    corridor.points[0].severity_by_hour = Array.from({ length: 49 }, () => "UNKNOWN" as const);
    const fc = buildHeatFeatures(corridor, 0);
    expect(fc.features).toHaveLength(2);
  });

  it("computes route bounds across all segments", () => {
    const bounds = routeBounds([makeRoute()]);
    expect(bounds).not.toBeNull();
    const [[minLon, minLat], [maxLon, maxLat]] = bounds!;
    expect(minLon).toBeLessThan(maxLon);
    expect(minLat).toBeLessThan(maxLat);
    expect(routeBounds([])).toBeNull();
  });
});
