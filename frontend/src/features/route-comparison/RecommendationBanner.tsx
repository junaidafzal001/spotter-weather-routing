import type { Recommendation, RouteOption } from "../../types";
import { CheckCircle2, ShieldAlert, Sparkles } from "lucide-react";
import { cn } from "../../components/ui";

export function RecommendationBanner({
  recommendation,
  routes,
}: {
  recommendation: Recommendation;
  routes: RouteOption[];
}) {
  const recommendedRoute = routes.find((route) => route.id === recommendation.recommended_route_id);

  if (!recommendation.eligible || !recommendation.recommended_route_id) {
    return (
      <div
        role="status"
        className={cn(
          "animate-rise rounded-2xl border border-red-300 bg-gradient-to-br from-red-50 to-white p-3.5",
        )}
      >
        <div className="flex items-start gap-2">
          <ShieldAlert className="mt-0.5 shrink-0 text-red-700" size={18} aria-hidden />
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wide text-red-800">
              No safe route available
            </div>
            <p className="mt-1 text-xs leading-relaxed text-red-900">{recommendation.reason}</p>
            {recommendation.least_exposed_route_id ? (
              <p className="mt-1.5 text-[11px] font-semibold text-red-800">
                Least-exposure comparison: {recommendation.least_exposed_route_id.replace("route-", "Route ")}
              </p>
            ) : null}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-rise rounded-2xl border border-emerald-200 bg-gradient-to-br from-emerald-50 to-white p-3.5" role="status">
      <div className="flex items-start gap-2">
        <CheckCircle2 className="mt-0.5 shrink-0 text-emerald-600" size={18} aria-hidden />
        <div>
          <div className="flex flex-wrap items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-emerald-800">
            <Sparkles size={11} aria-hidden />
            Recommended · {recommendedRoute ? recommendedRoute.id.replace("route-", "Route ") : ""}
          </div>
          <p className="mt-1 text-xs leading-relaxed text-emerald-950">{recommendation.reason}</p>
          <p className="mt-1.5 text-[10px] leading-relaxed text-emerald-800/80">
            Ranked by fewest Severe miles → fewest High miles → lowest distance-weighted risk → shortest travel time.
          </p>
        </div>
      </div>
    </div>
  );
}
