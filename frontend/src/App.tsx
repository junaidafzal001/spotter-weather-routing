import { lazy, Suspense, useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { AlertTriangle, CloudSun, Loader2, Route as RouteIcon } from "lucide-react";
import type { Analysis, AnalyzeTripInput } from "./types";
import { api, ApiError } from "./lib/api";
import { useCorridor } from "./hooks/useCorridor";
import { Card, SectionTitle } from "./components/ui";
import { Header } from "./features/Header";
import { TripPlanner } from "./features/trip-planner/TripPlanner";
import { RecommendationBanner } from "./features/route-comparison/RecommendationBanner";
import { RouteList } from "./features/route-comparison/RouteList";
import { RouteDetails } from "./features/route-comparison/RouteDetails";
import { HeatmapPanel } from "./features/weather/HeatmapPanel";
import { EmptyState } from "./features/EmptyState";
import { HowItWorks } from "./features/HowItWorks";

const MapPanel = lazy(() =>
  import("./features/map/MapPanel").then((module) => ({ default: module.MapPanel })),
);

export default function App() {
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null);
  const [preset, setPreset] = useState<{ origin: string; destination: string } | null>(null);
  const [focusTarget, setFocusTarget] = useState<{ coordinates: [number, number]; nonce: number } | null>(null);
  const [heatmapVisible, setHeatmapVisible] = useState(true);

  const mutation = useMutation({
    mutationFn: (input: AnalyzeTripInput) => api.analyzeTrip(input),
    onSuccess: (envelope) => {
      const data = envelope.data;
      setAnalysis(data);
      setSelectedRouteId(data.recommendation.recommended_route_id ?? data.routes[0]?.id ?? null);
      setFocusTarget(null);
      setHourState({ key: `${data.analysis_id}:${data.recommendation.recommended_route_id ?? data.routes[0]?.id ?? ""}`, value: 0 });
    },
  });

  const selectedRoute = useMemo(
    () => analysis?.routes.find((route) => route.id === selectedRouteId) ?? null,
    [analysis, selectedRouteId],
  );

  const corridorQuery = useCorridor(analysis?.analysis_id, selectedRouteId);
  const corridor = corridorQuery.data?.data ?? null;

  const corridorKey = `${analysis?.analysis_id ?? "none"}:${selectedRouteId ?? "none"}`;
  const [hourState, setHourState] = useState<{ key: string; value: number }>({ key: corridorKey, value: 0 });
  const heatmapHour = hourState.key === corridorKey ? hourState.value : 0;
  const setHeatmapHour = (value: number) => setHourState({ key: corridorKey, value });

  const maxHour = Math.max(0, (corridor?.hours.length ?? 1) - 1);
  const safeHour = Math.min(heatmapHour, maxHour);

  const error = mutation.error instanceof ApiError ? mutation.error : mutation.error ? new ApiError(String(mutation.error), "unknown", 0) : null;

  return (
    <div className="flex min-h-screen flex-col">
      <Header />

      <main className="mx-auto grid w-full max-w-[1600px] flex-1 gap-4 px-4 py-4 lg:grid-cols-[400px_minmax(0,1fr)] lg:gap-5 lg:px-6 lg:py-5">
        <aside className="scroll-thin space-y-4 lg:max-h-[calc(100vh-6.6rem)] lg:overflow-y-auto lg:pr-1">
          <Card className="p-4">
            <SectionTitle
              icon={<RouteIcon size={15} aria-hidden />}
              title="Plan a trip"
              subtitle="Weather risk is evaluated at each checkpoint's projected arrival time."
            />
            <div className="mt-3">
              <TripPlanner
                onAnalyze={(input) => mutation.mutate(input)}
                isPending={mutation.isPending}
                error={error}
                preset={preset}
                onPresetConsumed={() => setPreset(null)}
              />
            </div>
          </Card>

          {analysis ? (
            <>
              <RecommendationBanner recommendation={analysis.recommendation} routes={analysis.routes} />
              <RouteList
                routes={analysis.routes}
                recommendation={analysis.recommendation}
                selectedRouteId={selectedRouteId}
                onSelect={setSelectedRouteId}
              />
              {analysis.warnings.length > 0 ? (
                <Card className="border-amber-200 bg-amber-50/60 p-3">
                  <div className="flex items-start gap-1.5 text-[11px] font-semibold text-amber-900">
                    <AlertTriangle size={13} className="mt-0.5 shrink-0" aria-hidden />
                    Data-quality notes
                  </div>
                  <ul className="mt-1.5 list-disc space-y-1 pl-4 text-[11px] leading-relaxed text-amber-900/90">
                    {analysis.warnings.map((warning, index) => (
                      <li key={index}>{warning}</li>
                    ))}
                  </ul>
                </Card>
              ) : null}
            </>
          ) : (
            <HowItWorks />
          )}
        </aside>

        <section className="min-w-0 space-y-4">
          <div className="relative h-[420px] overflow-hidden rounded-2xl border border-line bg-slate-100 shadow-[0_1px_2px_rgba(15,23,42,0.04)] sm:h-[480px] xl:h-[560px]">
            <Suspense
              fallback={
                <div className="flex h-full w-full items-center justify-center bg-slate-100">
                  <div className="flex items-center gap-2 text-xs font-medium text-muted">
                    <Loader2 size={14} className="animate-spin text-brand" aria-hidden />
                    Loading map…
                  </div>
                </div>
              }
            >
              <MapPanel
                analysis={analysis}
                routes={analysis?.routes ?? []}
                selectedRoute={selectedRoute}
                selectedRouteId={selectedRouteId}
                recommendedRouteId={analysis?.recommendation.recommended_route_id ?? null}
                corridor={corridor}
                heatmapHour={safeHour}
                heatmapVisible={heatmapVisible}
                focusTarget={focusTarget}
              >
                {analysis ? (
                  <HeatmapPanel
                    corridor={corridor ?? undefined}
                    hour={safeHour}
                    onHourChange={setHeatmapHour}
                    visible={heatmapVisible}
                    onVisibleChange={setHeatmapVisible}
                    isLoading={corridorQuery.isLoading}
                    error={
                      corridorQuery.isError
                        ? corridorQuery.error instanceof ApiError
                          ? corridorQuery.error.message
                          : "Could not load corridor weather."
                        : null
                    }
                    onRetry={() => void corridorQuery.refetch()}
                  />
                ) : (
                  <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
                    <div className="rounded-full bg-white/90 px-3.5 py-1.5 text-[11px] font-medium text-slate-600 shadow-sm ring-1 ring-line">
                      <CloudSun size={12} className="mr-1 inline text-brand" aria-hidden />
                      Enter a trip to plot routes and weather
                    </div>
                  </div>
                )}
                {mutation.isPending ? (
                  <div className="absolute inset-0 z-20 flex items-center justify-center bg-white/65 backdrop-blur-[2px]">
                    <div className="flex items-center gap-2 rounded-xl border border-line bg-white px-4 py-3 text-sm font-medium text-ink shadow-lg">
                      <Loader2 size={16} className="animate-spin text-brand" aria-hidden />
                      Analyzing alternatives &amp; checkpoint forecasts…
                    </div>
                  </div>
                ) : null}
              </MapPanel>
            </Suspense>
          </div>

          {analysis && selectedRoute ? (
            <RouteDetails
              route={selectedRoute}
              globalWarnings={analysis.warnings}
              onFocusCheckpoint={(coordinates) =>
                setFocusTarget({ coordinates, nonce: Date.now() })
              }
            />
          ) : (
            <EmptyState
              onUseSample={(origin, destination) => setPreset({ origin, destination })}
            />
          )}
        </section>
      </main>
    </div>
  );
}
