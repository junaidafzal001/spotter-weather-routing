import type { Corridor, RouteOption } from "../types";
import { heatmapWeight, riskColor } from "./risk";

export interface RouteFeatureCollection {
  type: "FeatureCollection";
  features: {
    type: "Feature";
    geometry: { type: "LineString"; coordinates: [number, number][] };
    properties: {
      route_id: string;
      level: string;
      selected: boolean;
      recommended: boolean;
    };
  }[];
}

export interface CheckpointFeatureCollection {
  type: "FeatureCollection";
  features: {
    type: "Feature";
    geometry: { type: "Point"; coordinates: [number, number] };
    properties: {
      route_id: string;
      checkpoint_index: number;
      level: string;
      selected: boolean;
    };
  }[];
}

export interface HeatFeatureCollection {
  type: "FeatureCollection";
  features: {
    type: "Feature";
    geometry: { type: "Point"; coordinates: [number, number] };
    properties: { weight: number; level: string; hour: number };
  }[];
}

export function buildRouteFeatures(
  routes: RouteOption[],
  selectedRouteId: string | null,
  recommendedRouteId: string | null,
): RouteFeatureCollection {
  const features: RouteFeatureCollection["features"] = [];
  for (const route of routes) {
    const selected = route.id === selectedRouteId;
    for (const segment of route.segments) {
      features.push({
        type: "Feature",
        geometry: { type: "LineString", coordinates: segment.coordinates },
        properties: {
          route_id: route.id,
          level: segment.level ?? "UNKNOWN",
          selected,
          recommended: route.id === recommendedRouteId,
        },
      });
    }
  }
  return { type: "FeatureCollection", features };
}

export function buildCheckpointFeatures(
  route: RouteOption | null,
): CheckpointFeatureCollection {
  if (!route) return { type: "FeatureCollection", features: [] };
  return {
    type: "FeatureCollection",
    features: route.checkpoints.map((checkpoint) => ({
      type: "Feature",
      geometry: { type: "Point", coordinates: checkpoint.coordinates },
      properties: {
        route_id: route.id,
        checkpoint_index: checkpoint.index,
        level: checkpoint.risk.available ? checkpoint.risk.level : "UNKNOWN",
        selected: true,
      },
    })),
  };
}

export function buildHeatFeatures(
  corridor: Corridor | null,
  hour: number,
): HeatFeatureCollection {
  if (!corridor) return { type: "FeatureCollection", features: [] };
  const features: HeatFeatureCollection["features"] = [];
  for (const point of corridor.points) {
    const level = point.severity_by_hour[hour];
    if (!level) continue;
    const weight = heatmapWeight(level);
    if (weight <= 0) continue;
    features.push({
      type: "Feature",
      geometry: { type: "Point", coordinates: [point.lon, point.lat] },
      properties: { weight, level, hour },
    });
  }
  return { type: "FeatureCollection", features };
}

export function routeBounds(
  routes: RouteOption[],
): [[number, number], [number, number]] | null {
  let minLon = Infinity;
  let minLat = Infinity;
  let maxLon = -Infinity;
  let maxLat = -Infinity;
  for (const route of routes) {
    for (const segment of route.segments) {
      for (const [lon, lat] of segment.coordinates) {
        minLon = Math.min(minLon, lon);
        minLat = Math.min(minLat, lat);
        maxLon = Math.max(maxLon, lon);
        maxLat = Math.max(maxLat, lat);
      }
    }
  }
  if (!Number.isFinite(minLon)) return null;
  return [
    [minLon, minLat],
    [maxLon, maxLat],
  ];
}

export { riskColor };
