import type { Exposure } from "../../types";
import { percent } from "../../lib/format";
import { cn } from "../../components/ui";

const SEGMENTS = [
  { key: "low_miles", label: "Low", color: "#16a34a" },
  { key: "moderate_miles", label: "Moderate", color: "#eab308" },
  { key: "high_miles", label: "High", color: "#f97316" },
  { key: "severe_miles", label: "Severe", color: "#dc2626" },
  { key: "no_travel_miles", label: "No Travel", color: "#7f1d1d" },
  { key: "unassessed_miles", label: "Unassessed", color: "#cbd5e1" },
] as const;

export function RiskBar({ exposure, className }: { exposure: Exposure; className?: string }) {
  const total = exposure.total_miles || 0;
  return (
    <div>
      <div
        className={cn("flex h-2 w-full overflow-hidden rounded-full bg-slate-100", className)}
        role="img"
        aria-label={`Risk exposure: ${SEGMENTS.map(
          (segment) => `${segment.label} ${exposure[segment.key].toFixed(1)} miles`,
        ).join(", ")}`}
      >
        {SEGMENTS.map((segment) => {
          const width = percent(exposure[segment.key], total);
          if (width <= 0) return null;
          return (
            <div
              key={segment.key}
              style={{ width: `${width}%`, backgroundColor: segment.color }}
              title={`${segment.label}: ${exposure[segment.key].toFixed(1)} mi`}
            />
          );
        })}
      </div>
    </div>
  );
}

export function RiskBarLegend({ exposure }: { exposure: Exposure }) {
  const total = exposure.total_miles || 0;
  return (
    <div className="flex flex-wrap gap-x-3 gap-y-1">
      {SEGMENTS.map((segment) => {
        const miles = exposure[segment.key];
        const width = percent(miles, total);
        if (width <= 0) return null;
        return (
          <span key={segment.key} className="inline-flex items-center gap-1 text-[11px] text-muted">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: segment.color }} aria-hidden />
            {segment.label}
            <span className="font-medium text-ink tabular-nums">{miles.toFixed(1)} mi</span>
          </span>
        );
      })}
    </div>
  );
}
