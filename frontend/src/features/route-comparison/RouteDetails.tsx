import { useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Cloud,
  CloudDrizzle,
  CloudFog,
  CloudLightning,
  CloudRain,
  CloudSnow,
  CloudSun,
  Info,
  ListOrdered,
  Sun,
} from "lucide-react";
import type { Checkpoint, RouteOption } from "../../types";
import { cn, RiskBadge, SectionTitle } from "../../components/ui";
import { formatDuration, formatLocalDateTime, formatMiles, formatNumber, formatTime, localTimezoneLabel } from "../../lib/format";
import { RiskBar, RiskBarLegend } from "../route-comparison/RiskBar";

type Tab = "checkpoints" | "exposure" | "notes";

export function RouteDetails({
  route,
  globalWarnings,
  onFocusCheckpoint,
}: {
  route: RouteOption;
  globalWarnings: string[];
  onFocusCheckpoint: (coordinates: [number, number]) => void;
}) {
  const [tab, setTab] = useState<Tab>("checkpoints");
  const exposure = route.exposure;

  return (
    <div className="rounded-2xl border border-line bg-surface p-4 shadow-[0_1px_2px_rgba(15,23,42,0.04)]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <SectionTitle
          icon={<ListOrdered size={15} aria-hidden />}
          title={`${route.id.replace("route-", "Route ")} details`}
          subtitle={`${route.provider} · ${route.profile} · timing from ${route.timing_source === "provider" ? "provider segments" : "distance fallback"} · times in ${localTimezoneLabel()}`}
        />
        <div className="flex gap-4 text-right">
          <Stat label="Distance" value={formatMiles(route.distance_miles)} />
          <Stat label="Duration" value={formatDuration(route.duration_minutes)} />
          <Stat label="Arrival" value={formatTime(route.arrival_time)} />
        </div>
      </div>

      <div className="mt-3 flex gap-1 border-b border-line" role="tablist" aria-label="Route detail tabs">
        {(
          [
            ["checkpoints", "Checkpoints"],
            ["exposure", "Exposure"],
            ["notes", "Notes & warnings"],
          ] as [Tab, string][]
        ).map(([value, label]) => (
          <button
            key={value}
            type="button"
            role="tab"
            aria-selected={tab === value}
            onClick={() => setTab(value)}
            className={cn(
              "-mb-px border-b-2 px-3 py-2 text-xs font-medium transition",
              tab === value
                ? "border-brand text-brand-dark"
                : "border-transparent text-muted hover:text-ink",
            )}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "checkpoints" ? (
        <div className="mt-2 max-h-[360px] overflow-auto scroll-thin">
          <table className="w-full border-collapse text-left text-[11px]">
            <thead className="sticky top-0 z-10 bg-surface">
              <tr className="text-[10px] uppercase tracking-wide text-muted">
                <th className="py-1.5 pr-2 font-medium">Mile</th>
                <th className="py-1.5 pr-2 font-medium">ETA</th>
                <th className="py-1.5 pr-2 font-medium">Conditions</th>
                <th className="hidden py-1.5 pr-2 text-right font-medium sm:table-cell">Wind</th>
                <th className="hidden py-1.5 pr-2 text-right font-medium sm:table-cell">Rain</th>
                <th className="hidden py-1.5 pr-2 text-right font-medium sm:table-cell">Snow</th>
                <th className="hidden py-1.5 pr-2 text-right font-medium md:table-cell">Temp</th>
                <th className="py-1.5 text-right font-medium">Risk</th>
              </tr>
            </thead>
            <tbody>
              {route.checkpoints.map((checkpoint) => (
                <CheckpointRow
                  key={checkpoint.index}
                  checkpoint={checkpoint}
                  onFocus={() => onFocusCheckpoint(checkpoint.coordinates)}
                />
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {tab === "exposure" ? (
        <div className="mt-3 space-y-3">
          <RiskBar exposure={exposure} className="h-2.5" />
          <RiskBarLegend exposure={exposure} />
          <dl className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <DetailStat label="Average risk" value={exposure.average_risk === null ? "—" : exposure.average_risk.toFixed(2)} hint="distance-weighted, assessed miles only" />
            <DetailStat label="Max risk" value={exposure.max_risk ?? "—"} hint="worst interval on the route" />
            <DetailStat label="Total miles" value={formatMiles(exposure.total_miles)} hint="per-level miles sum to this" />
            <DetailStat
              label="Unassessed"
              value={`${Math.round(exposure.unassessed_share * 100)}%`}
              hint="weather unavailable → UNKNOWN, never LOW"
            />
          </dl>
          <p className="text-[11px] leading-relaxed text-muted">
            Miles are attributed per checkpoint interval to the higher-severity endpoint, so totals remain
            stable when the checkpoint interval changes (10/25/50 mi).
          </p>
        </div>
      ) : null}

      {tab === "notes" ? (
        <div className="mt-3 space-y-2">
          {route.warnings.length === 0 && globalWarnings.length === 0 ? (
            <p className="flex items-center gap-1.5 text-[11px] text-emerald-700">
              <CheckCircle2 size={12} aria-hidden />
              No data-quality warnings for this route.
            </p>
          ) : null}
          {[...route.warnings, ...globalWarnings].map((warning, index) => (
            <p
              key={index}
              className="flex items-start gap-1.5 rounded-lg border border-amber-200 bg-amber-50 px-2.5 py-2 text-[11px] leading-relaxed text-amber-900"
            >
              <AlertTriangle size={13} className="mt-0.5 shrink-0" aria-hidden />
              {warning}
            </p>
          ))}
          <p className="flex items-start gap-1.5 rounded-lg border border-line bg-slate-50 px-2.5 py-2 text-[11px] leading-relaxed text-slate-600">
            <Info size={13} className="mt-0.5 shrink-0" aria-hidden />
            Routing is truck-aware only when an ORS key with the driving-hgv profile is configured. Bridge
            clearance, axle limits, and posted road-weight restrictions must still be verified before dispatch.
          </p>
        </div>
      ) : null}
    </div>
  );
}

function CheckpointRow({ checkpoint, onFocus }: { checkpoint: Checkpoint; onFocus: () => void }) {
  const weather = checkpoint.weather;
  const level = checkpoint.risk.available ? checkpoint.risk.level : "UNKNOWN";
  const hasLoadRule = Boolean(checkpoint.risk.load_rule_applied);

  return (
    <tr
      className="cursor-pointer border-t border-line/70 align-middle hover:bg-slate-50"
      onClick={onFocus}
      title="Show this checkpoint on the map"
    >
      <td className="py-1.5 pr-2 font-medium tabular-nums text-ink">{checkpoint.mile.toFixed(1)}</td>
      <td className="py-1.5 pr-2 tabular-nums text-slate-600" title={formatLocalDateTime(checkpoint.eta)}>
        {formatTime(checkpoint.eta)}
      </td>
      <td className="py-1.5 pr-2">
        <span className="inline-flex items-center gap-1.5 text-slate-700">
          <WeatherIcon code={weather.weather_code} />
          <span className="max-w-[110px] truncate">{weather.available ? (weather.condition ?? "—") : "Unavailable"}</span>
        </span>
      </td>
      <td className="hidden py-1.5 pr-2 text-right tabular-nums sm:table-cell">
        {formatNumber(weather.wind_mph, 1)}
        {hasLoadRule ? <AlertTriangle size={10} className="ml-1 inline text-amber-600" aria-label="Load rule applied" /> : null}
      </td>
      <td className="hidden py-1.5 pr-2 text-right tabular-nums sm:table-cell">{formatNumber(weather.rain_in_hr, 2)}</td>
      <td className="hidden py-1.5 pr-2 text-right tabular-nums sm:table-cell">{formatNumber(weather.snow_in_hr, 2)}</td>
      <td className="hidden py-1.5 pr-2 text-right tabular-nums md:table-cell">{formatNumber(weather.temperature_f, 0)}°</td>
      <td className="py-1.5 text-right">
        <RiskBadge level={level} size="xs" />
      </td>
    </tr>
  );
}

function WeatherIcon({ code }: { code: number | null }) {
  const className = "h-3.5 w-3.5 text-slate-500";
  if (code === null) return <Cloud className={className} aria-hidden />;
  if (code === 0) return <Sun className={className} aria-hidden />;
  if (code <= 3) return <CloudSun className={className} aria-hidden />;
  if (code === 45 || code === 48) return <CloudFog className={className} aria-hidden />;
  if (code >= 51 && code <= 57) return <CloudDrizzle className={className} aria-hidden />;
  if (code >= 61 && code <= 67) return <CloudRain className={className} aria-hidden />;
  if (code >= 71 && code <= 77) return <CloudSnow className={className} aria-hidden />;
  if (code >= 80 && code <= 82) return <CloudRain className={className} aria-hidden />;
  if (code >= 85 && code <= 86) return <CloudSnow className={className} aria-hidden />;
  if (code >= 95) return <CloudLightning className={className} aria-hidden />;
  return <Cloud className={className} aria-hidden />;
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10px] font-medium uppercase tracking-wide text-muted">{label}</div>
      <div className="mt-0.5 text-xs font-semibold tabular-nums text-ink">{value}</div>
    </div>
  );
}

function DetailStat({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <div className="rounded-lg border border-line bg-slate-50/60 p-2">
      <dt className="text-[10px] font-medium uppercase tracking-wide text-muted">{label}</dt>
      <dd className="mt-0.5 text-sm font-semibold tabular-nums text-ink">{value}</dd>
      <dd className="mt-0.5 text-[10px] leading-snug text-muted">{hint}</dd>
    </div>
  );
}
