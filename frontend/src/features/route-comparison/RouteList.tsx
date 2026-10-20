import { Route as RouteIcon } from "lucide-react";
import type { Recommendation, RouteOption } from "../../types";
import { SectionTitle } from "../../components/ui";
import { RouteCard } from "./RouteCard";

export function RouteList({
  routes,
  recommendation,
  selectedRouteId,
  onSelect,
}: {
  routes: RouteOption[];
  recommendation: Recommendation;
  selectedRouteId: string | null;
  onSelect: (routeId: string) => void;
}) {
  const ordered = [...routes].sort((a, b) => {
    const ai = recommendation.ranking.indexOf(a.id);
    const bi = recommendation.ranking.indexOf(b.id);
    return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
  });

  return (
    <div className="space-y-2">
      <SectionTitle
        icon={<RouteIcon size={15} aria-hidden />}
        title={`Route options (${routes.length})`}
        subtitle="Select a route to inspect checkpoints, exposure, and corridor weather."
      />
      <div className="space-y-2">
        {ordered.map((route) => (
          <RouteCard
            key={route.id}
            route={route}
            selected={route.id === selectedRouteId}
            recommended={route.id === recommendation.recommended_route_id}
            onSelect={onSelect}
          />
        ))}
      </div>
    </div>
  );
}
