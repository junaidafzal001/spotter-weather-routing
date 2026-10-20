import { Clock3, MapPin, Star, TriangleAlert } from "lucide-react";
import type { RouteOption } from "../../types";
import { cn, RiskBadge } from "../../components/ui";
import { formatDuration, formatLocalDateTime, formatMiles, formatTime } from "../../lib/format";
import { RiskBar } from "./RiskBar";

interface RouteCardProps {
  route: RouteOption;
  selected: boolean;
  recommended: boolean;
  onSelect: (routeId: string) => void;
}

export function RouteCard({ route, selected, recommended, onSelect }: RouteCardProps) {
  const exposure = route.exposure;
  const noTravel = exposure.no_travel_miles > 0;
  const providerLabel = route.provider === "openrouteservice" ? "ORS" : route.provider === "graphhopper" ? "GraphHopper" : "OSRM";

  return (
    <button
      type="button"
      onClick={() => onSelect(route.id)}
      aria-pressed={selected}
      className={cn(
        "w-full rounded-xl border bg-white p-3 text-left transition",
        "hover:border-slate-300 hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/40",
        selected ? "border-brand ring-1 ring-brand/30 shadow-sm" : "border-line",
        noTravel && !selected ? "border-red-200" : "",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex min-w-0 items-center gap-1.5">
          <span className="truncate text-sm font-semibold text-ink">
            {route.id.replace("route-", "Route ")}
          </span>
          <span className="rounded border border-line bg-slate-50 px-1 py-0.5 text-[10px] font-medium uppercase tracking-wide text-slate-500">
            {providerLabel}
          </span>
        </div>
        {recommended ? (
          <span className="inline-flex shrink-0 items-center gap-1 rounded-full bg-brand px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white">
            <Star size={10} fill="currentColor" aria-hidden />
            Recommended
          </span>
        ) : null}
      </div>

      <div className="mt-2 grid grid-cols-3 gap-2">
        <Metric icon={<MapPin size={11} aria-hidden />} label="Distance" value={formatMiles(route.distance_miles)} />
        <Metric icon={<Clock3 size={11} aria-hidden />} label="Drive" value={formatDuration(route.duration_minutes)} />
        <div>
          <div className="text-[10px] font-medium uppercase tracking-wide text-muted">Arrive</div>
          <div className="mt-0.5 text-xs font-semibold tabular-nums text-ink" title={formatLocalDateTime(route.arrival_time)}>
            {formatTime(route.arrival_time)}
          </div>
        </div>
      </div>

      <div className="mt-2.5">
        <RiskBar exposure={exposure} />
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        {exposure.max_risk ? <RiskBadge level={exposure.max_risk} size="xs" suffix=" max" /> : null}
        <span className="rounded-full border border-line px-1.5 py-0.5 text-[10px] font-medium text-muted">
          avg {exposure.average_risk === null ? "—" : exposure.average_risk.toFixed(2)}
        </span>
        <span className="rounded-full border border-line px-1.5 py-0.5 text-[10px] font-medium text-muted">
          {route.checkpoint_count} checkpoints
        </span>
        {noTravel ? (
          <span className="inline-flex items-center gap-1 rounded-full border border-red-300 bg-red-50 px-1.5 py-0.5 text-[10px] font-semibold text-red-800">
            <TriangleAlert size={10} aria-hidden />
            {exposure.no_travel_miles.toFixed(0)} mi No Travel
          </span>
        ) : null}
        {exposure.unassessed_share > 0 ? (
          <span className="rounded-full border border-slate-300 bg-slate-50 px-1.5 py-0.5 text-[10px] font-medium text-slate-600">
            {Math.round(exposure.unassessed_share * 100)}% unassessed
          </span>
        ) : null}
      </div>
    </button>
  );
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div>
      <div className="flex items-center gap-1 text-[10px] font-medium uppercase tracking-wide text-muted">
        {icon}
        {label}
      </div>
      <div className="mt-0.5 text-xs font-semibold tabular-nums text-ink">{value}</div>
    </div>
  );
}
