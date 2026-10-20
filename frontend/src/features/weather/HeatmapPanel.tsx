import { RefreshCw, Snowflake } from "lucide-react";
import type { Corridor } from "../../types";
import { summarizeHour, RISK_COLORS, RISK_LABELS, RISK_ORDER } from "../../lib/risk";
import { cn, Spinner } from "../../components/ui";
import { formatHourLabel, localTimezoneLabel } from "../../lib/format";

interface HeatmapPanelProps {
  corridor: Corridor | undefined;
  hour: number;
  onHourChange: (hour: number) => void;
  visible: boolean;
  onVisibleChange: (visible: boolean) => void;
  isLoading: boolean;
  error: string | null;
  onRetry: () => void;
}

export function HeatmapPanel({
  corridor,
  hour,
  onHourChange,
  visible,
  onVisibleChange,
  isLoading,
  error,
  onRetry,
}: HeatmapPanelProps) {
  const hours = corridor?.hours ?? [];
  const maxHour = Math.max(0, hours.length - 1);
  const safeHour = Math.min(hour, maxHour);
  const summary = corridor ? summarizeHour(corridor.points, safeHour) : null;
  const activeLevels = summary
    ? RISK_ORDER.filter((level) => summary.counts[level] > 0)
    : [];

  return (
    <div className="pointer-events-auto absolute left-3 top-3 z-10 w-[290px] max-w-[calc(100%-1.5rem)] rounded-xl border border-line bg-white/95 p-3 shadow-lg backdrop-blur">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <Snowflake size={14} className="text-brand" aria-hidden />
          <span className="text-xs font-semibold text-ink">Corridor weather</span>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={visible}
          aria-label="Toggle corridor weather heatmap"
          onClick={() => onVisibleChange(!visible)}
          className={cn(
            "relative h-5 w-9 rounded-full transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/40",
            visible ? "bg-brand" : "bg-slate-300",
          )}
        >
          <span
            className={cn(
              "absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-all",
              visible ? "left-[18px]" : "left-0.5",
            )}
          />
        </button>
      </div>

      {isLoading ? (
        <div className="mt-3 space-y-2" aria-live="polite">
          <div className="flex items-center gap-2 text-[11px] text-muted">
            <Spinner className="border-brand/30 border-t-brand" />
            Loading 48-hour corridor forecast…
          </div>
          <div className="h-2 w-full animate-pulse rounded-full bg-slate-100" />
          <div className="h-2 w-2/3 animate-pulse rounded-full bg-slate-100" />
        </div>
      ) : error ? (
        <div className="mt-3 space-y-2">
          <p className="text-[11px] leading-relaxed text-red-700">{error}</p>
          <button
            type="button"
            onClick={onRetry}
            className="inline-flex items-center gap-1 rounded-md border border-line px-2 py-1 text-[11px] font-medium text-ink hover:bg-slate-50"
          >
            <RefreshCw size={11} aria-hidden />
            Retry
          </button>
        </div>
      ) : corridor && visible ? (
        <>
          <div className="mt-2.5 flex items-baseline justify-between">
            <span className="text-[11px] font-semibold text-ink" aria-live="polite">
              {formatHourLabel(hours[safeHour], safeHour)}
            </span>
            <span className="text-[10px] text-muted">+{safeHour}h · {localTimezoneLabel()}</span>
          </div>
          <input
            type="range"
            className="slider mt-2"
            min={0}
            max={maxHour}
            step={1}
            value={safeHour}
            aria-label="Forecast hour"
            aria-valuetext={`${safeHour} hours from now`}
            onChange={(event) => onHourChange(Number(event.target.value))}
          />
          <div className="mt-1 flex justify-between text-[10px] text-muted">
            <span>Now</span>
            <span>+{maxHour}h</span>
          </div>

          {summary ? (
            <div className="mt-2 flex flex-wrap gap-1" aria-label="Corridor severity at selected hour">
              {activeLevels.length === 0 ? (
                <span className="text-[10px] text-muted">No severity data for this hour.</span>
              ) : (
                activeLevels.map((level) => (
                  <span
                    key={level}
                    className="inline-flex items-center gap-1 rounded-full border border-line bg-white px-1.5 py-0.5 text-[10px] font-medium text-slate-700"
                  >
                    <span
                      className="h-1.5 w-1.5 rounded-full"
                      style={{ backgroundColor: RISK_COLORS[level] }}
                      aria-hidden
                    />
                    {RISK_LABELS[level]} {summary.counts[level]}
                  </span>
                ))
              )}
            </div>
          ) : null}

          <p className="mt-2 text-[10px] leading-snug text-muted">
            {corridor.points.length} corridor samples · each hour is its own forecast. Intensity is a spatial
            interpolation between samples, not a point observation.
          </p>
        </>
      ) : (
        <p className="mt-2 text-[11px] leading-relaxed text-muted">
          Heatmap hidden. Route colors and checkpoint weather remain active.
        </p>
      )}
    </div>
  );
}
