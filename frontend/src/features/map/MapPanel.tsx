import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  AttributionControl,
  Map as MapLibreMap,
  NavigationControl,
  Popup,
  ScaleControl,
  setWorkerUrl,
  type GeoJSONSource,
  type MapLayerMouseEvent,
} from "maplibre-gl";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Analysis, Corridor, RouteOption } from "../../types";
import {
  buildCheckpointFeatures,
  buildHeatFeatures,
  buildRouteFeatures,
  routeBounds,
} from "../../lib/mapData";
import { RISK_COLORS, RISK_LABELS } from "../../lib/risk";
import { formatLocalDateTime, formatNumber, formatTime } from "../../lib/format";
import { MapLegend } from "./MapLegend";

setWorkerUrl(workerUrl);

const EMPTY_FC = { type: "FeatureCollection" as const, features: [] };

const BASEMAP_STYLE = "https://tiles.openfreemap.org/styles/positron";

interface MapPanelProps {
  analysis: Analysis | null;
  routes: RouteOption[];
  selectedRoute: RouteOption | null;
  selectedRouteId: string | null;
  recommendedRouteId: string | null;
  corridor: Corridor | null;
  heatmapHour: number;
  heatmapVisible: boolean;
  focusTarget: { coordinates: [number, number]; nonce: number } | null;
  children?: ReactNode;
}

export function MapPanel({
  analysis,
  routes,
  selectedRoute,
  selectedRouteId,
  recommendedRouteId,
  corridor,
  heatmapHour,
  heatmapVisible,
  focusTarget,
  children,
}: MapPanelProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const popupRef = useRef<Popup | null>(null);
  const lastFitAnalysisRef = useRef<string | null>(null);
  const dataRef = useRef<{ route: RouteOption | null }>({ route: null });
  const [ready, setReady] = useState(false);
  const analysisId = analysis?.analysis_id ?? null;

  useEffect(() => {
    dataRef.current.route = selectedRoute;
  }, [selectedRoute]);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = new MapLibreMap({
      container: containerRef.current,
      style: BASEMAP_STYLE,
      center: [-86.6, 41.9],
      zoom: 5.4,
      attributionControl: false,
    });
    mapRef.current = map;

    map.addControl(new NavigationControl({ showCompass: false }), "top-right");
    map.addControl(new ScaleControl({ unit: "imperial", maxWidth: 90 }), "bottom-right");
    map.addControl(new AttributionControl({ compact: true }), "bottom-right");

    map.on("load", () => {
      map.addSource("corridor-heat", { type: "geojson", data: EMPTY_FC });
      map.addLayer({
        id: "corridor-heat-layer",
        type: "heatmap",
        source: "corridor-heat",
        layout: { visibility: "none" },
        paint: {
          "heatmap-weight": ["interpolate", ["linear"], ["get", "weight"], 0, 0, 1, 1],
          "heatmap-intensity": ["interpolate", ["linear"], ["zoom"], 5, 0.9, 11, 1.8],
          "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 5, 34, 9, 46, 13, 70],
          "heatmap-opacity": ["interpolate", ["linear"], ["zoom"], 5, 0.55, 12, 0.7],
          "heatmap-color": [
            "interpolate",
            ["linear"],
            ["heatmap-density"],
            0,
            "rgba(22,163,74,0)",
            0.15,
            "rgba(22,163,74,0.45)",
            0.35,
            "rgba(234,179,8,0.6)",
            0.55,
            "rgba(249,115,22,0.72)",
            0.78,
            "rgba(220,38,38,0.85)",
            1,
            "rgba(127,29,29,0.95)",
          ],
        },
      });

      map.addSource("route-lines", { type: "geojson", data: EMPTY_FC });
      map.addLayer({
        id: "route-casing",
        type: "line",
        source: "route-lines",
        layout: { "line-cap": "round", "line-join": "round" },
        paint: {
          "line-color": "#0f172a",
          "line-width": ["case", ["get", "selected"], 9, 6],
          "line-opacity": ["case", ["get", "selected"], 0.22, 0.12],
        },
      });
      map.addLayer({
        id: "route-lines-layer",
        type: "line",
        source: "route-lines",
        layout: { "line-cap": "round", "line-join": "round" },
        paint: {
          "line-color": [
            "match",
            ["get", "level"],
            "LOW",
            RISK_COLORS.LOW,
            "MODERATE",
            RISK_COLORS.MODERATE,
            "HIGH",
            RISK_COLORS.HIGH,
            "SEVERE",
            RISK_COLORS.SEVERE,
            "NO_TRAVEL",
            RISK_COLORS.NO_TRAVEL,
            RISK_COLORS.UNKNOWN,
          ],
          "line-width": ["case", ["get", "selected"], 6.5, 4],
          "line-opacity": ["case", ["get", "selected"], 1, 0.42],
        },
      });

      map.addSource("route-checkpoints", { type: "geojson", data: EMPTY_FC });
      map.addLayer({
        id: "route-checkpoints-layer",
        type: "circle",
        source: "route-checkpoints",
        paint: {
          "circle-radius": 5,
          "circle-color": [
            "match",
            ["get", "level"],
            "LOW",
            RISK_COLORS.LOW,
            "MODERATE",
            RISK_COLORS.MODERATE,
            "HIGH",
            RISK_COLORS.HIGH,
            "SEVERE",
            RISK_COLORS.SEVERE,
            "NO_TRAVEL",
            RISK_COLORS.NO_TRAVEL,
            RISK_COLORS.UNKNOWN,
          ],
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 1.6,
          "circle-opacity": 0.95,
        },
      });

      map.on("click", "route-checkpoints-layer", (event: MapLayerMouseEvent) => {
        const feature = event.features?.[0];
        const route = dataRef.current.route;
        if (!feature || !route) return;
        const checkpoint = route.checkpoints[Number(feature.properties?.checkpoint_index)];
        if (!checkpoint) return;
        popupRef.current?.remove();
        popupRef.current = new Popup({ closeButton: true, maxWidth: "300px", offset: 10 })
          .setLngLat(checkpoint.coordinates)
          .setDOMContent(buildPopupContent(route, checkpoint))
          .addTo(map);
      });
      map.on("mouseenter", "route-checkpoints-layer", () => {
        map.getCanvas().style.cursor = "pointer";
      });
      map.on("mouseleave", "route-checkpoints-layer", () => {
        map.getCanvas().style.cursor = "";
      });

      setReady(true);
    });

    return () => {
      popupRef.current?.remove();
      popupRef.current = null;
      map.remove();
      mapRef.current = null;
      setReady(false);
    };
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const observer = new ResizeObserver(() => {
      mapRef.current?.resize();
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  const routeFeatures = useMemo(
    () => buildRouteFeatures(routes, selectedRouteId, recommendedRouteId),
    [routes, selectedRouteId, recommendedRouteId],
  );
  const checkpointFeatures = useMemo(() => buildCheckpointFeatures(selectedRoute), [selectedRoute]);
  const heatFeatures = useMemo(() => buildHeatFeatures(corridor, heatmapHour), [corridor, heatmapHour]);

  useEffect(() => {
    if (!ready) return;
    const source = mapRef.current?.getSource("route-lines") as GeoJSONSource | undefined;
    source?.setData(routeFeatures);
  }, [ready, routeFeatures]);

  useEffect(() => {
    if (!ready) return;
    const source = mapRef.current?.getSource("route-checkpoints") as GeoJSONSource | undefined;
    source?.setData(checkpointFeatures);
  }, [ready, checkpointFeatures]);

  useEffect(() => {
    if (!ready) return;
    const source = mapRef.current?.getSource("corridor-heat") as GeoJSONSource | undefined;
    source?.setData(heatFeatures);
  }, [ready, heatFeatures]);

  useEffect(() => {
    if (!ready) return;
    const map = mapRef.current;
    if (!map) return;
    map.setLayoutProperty("corridor-heat-layer", "visibility", heatmapVisible && corridor ? "visible" : "none");
  }, [ready, heatmapVisible, corridor]);

  // Fit all alternatives on a new analysis, the selected route on selection.
  useEffect(() => {
    if (!ready) return;
    const map = mapRef.current;
    if (!map) return;
    const analysisChanged = lastFitAnalysisRef.current !== analysisId;
    lastFitAnalysisRef.current = analysisId;

    const target = analysisChanged
      ? routeBounds(routes)
      : selectedRoute
        ? routeBounds([selectedRoute])
        : routeBounds(routes);
    if (target) {
      map.fitBounds(target, {
        padding: { top: 64, bottom: 64, left: 56, right: 56 },
        duration: 650,
        maxZoom: analysisChanged ? 10.5 : 12,
      });
    }
  }, [ready, analysisId, selectedRouteId, routes, selectedRoute]);

  useEffect(() => {
    if (!ready || !focusTarget) return;
    const map = mapRef.current;
    if (!map) return;
    map.flyTo({
      center: focusTarget.coordinates,
      zoom: Math.max(map.getZoom(), 9),
      duration: 700,
    });
  }, [ready, focusTarget]);

  return (
    <div className="relative h-full w-full overflow-hidden rounded-2xl">
      <div
        ref={containerRef}
        className="h-full w-full"
        aria-label="Interactive route weather map"
        role="application"
      />
      {children}
      <MapLegend />
    </div>
  );
}

function buildPopupContent(route: RouteOption, checkpoint: RouteOption["checkpoints"][number]): HTMLElement {
  const wrapper = document.createElement("div");
  wrapper.className = "w-[270px] text-slate-900";

  const riskLevel = checkpoint.risk.available ? checkpoint.risk.level : "UNKNOWN";
  const color = RISK_COLORS[riskLevel];

  const header = document.createElement("div");
  header.className = "border-b border-slate-200 px-3 py-2";
  const eyebrow = document.createElement("div");
  eyebrow.className = "text-[10px] font-semibold uppercase tracking-wide text-slate-500";
  eyebrow.textContent = `${route.id.replace("route-", "Route ")} · Mile ${checkpoint.mile.toFixed(1)}`;
  const titleRow = document.createElement("div");
  titleRow.className = "mt-0.5 flex items-center justify-between gap-2";
  const title = document.createElement("div");
  title.className = "text-sm font-semibold";
  title.textContent = checkpoint.weather.available
    ? (checkpoint.weather.condition ?? "Forecast")
    : "Weather unavailable";
  const badge = document.createElement("span");
  badge.className = "rounded-full px-2 py-0.5 text-[10px] font-bold text-white";
  badge.style.backgroundColor = color;
  badge.textContent = RISK_LABELS[riskLevel];
  titleRow.append(title, badge);
  const eta = document.createElement("div");
  eta.className = "mt-0.5 text-[11px] text-slate-500";
  eta.textContent = `ETA ${formatLocalDateTime(checkpoint.eta)}`;
  header.append(eyebrow, titleRow, eta);

  wrapper.append(header);

  if (!checkpoint.weather.available) {
    const unavailable = document.createElement("div");
    unavailable.className = "px-3 py-2 text-[11px] leading-relaxed text-slate-600";
    unavailable.textContent = checkpoint.weather.unavailability_reason ?? "No forecast available for this ETA.";
    wrapper.append(unavailable);
    return wrapper;
  }

  const grid = document.createElement("dl");
  grid.className = "grid grid-cols-2 gap-x-2 gap-y-1 px-3 py-2 text-[11px]";
  const rows: [string, string][] = [
    ["Wind", `${formatNumber(checkpoint.weather.wind_mph, 1)} mph`],
    ["Gusts", `${formatNumber(checkpoint.weather.wind_gust_mph, 1)} mph`],
    ["Rain", `${formatNumber(checkpoint.weather.rain_in_hr, 2)} in/hr`],
    ["Snow", `${formatNumber(checkpoint.weather.snow_in_hr, 2)} in/hr`],
    ["Temp", `${formatNumber(checkpoint.weather.temperature_f, 0)} °F`],
    ["Risk", riskLevel === "UNKNOWN" ? "Unknown" : `${RISK_LABELS[riskLevel]} (${checkpoint.risk.score})`],
  ];
  for (const [label, value] of rows) {
    const dt = document.createElement("dt");
    dt.className = "text-slate-500";
    dt.textContent = label;
    const dd = document.createElement("dd");
    dd.className = "text-right font-semibold tabular-nums";
    dd.textContent = value;
    grid.append(dt, dd);
  }
  wrapper.append(grid);

  if (checkpoint.risk.load_rule_applied) {
    const rule = document.createElement("div");
    rule.className = "border-t border-amber-200 bg-amber-50 px-3 py-1.5 text-[10px] font-medium text-amber-900";
    rule.textContent = `Load rule: ${checkpoint.risk.load_rule_applied}`;
    wrapper.append(rule);
  }

  const footer = document.createElement("div");
  footer.className = "border-t border-slate-200 px-3 py-1.5 text-[10px] text-slate-500";
  footer.textContent = `Open-Meteo · forecast for ${formatTime(checkpoint.weather.forecast_time)}${checkpoint.weather.interpolated ? " (interpolated to ETA)" : ""}`;
  wrapper.append(footer);

  return wrapper;
}
