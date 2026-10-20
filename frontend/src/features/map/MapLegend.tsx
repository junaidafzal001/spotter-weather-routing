import { MapPin } from "lucide-react";
import { RISK_COLORS, RISK_LABELS, RISK_ORDER } from "../../lib/risk";

export function MapLegend() {
  return (
    <div className="pointer-events-none absolute bottom-3 left-3 z-10 max-w-[240px] rounded-xl border border-line bg-white/95 p-2.5 shadow-lg backdrop-blur">
      <div className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
        <MapPin size={11} aria-hidden />
        Route risk
      </div>
      <ul className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-1">
        {RISK_ORDER.map((level) => (
          <li key={level} className="flex items-center gap-1.5 text-[10px] font-medium text-slate-700">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: RISK_COLORS[level] }} aria-hidden />
            {RISK_LABELS[level]}
          </li>
        ))}
        <li className="flex items-center gap-1.5 text-[10px] font-medium text-slate-500">
          <span className="h-2 w-2 rounded-full" style={{ backgroundColor: RISK_COLORS.UNKNOWN }} aria-hidden />
          Unknown
        </li>
      </ul>
      <div className="mt-2 border-t border-line pt-1.5">
        <div className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
          Heatmap
        </div>
        <div
          className="mt-1 h-1.5 w-full rounded-full"
          style={{
            background:
              "linear-gradient(90deg, #16a34a 0%, #eab308 35%, #f97316 60%, #dc2626 82%, #7f1d1d 100%)",
          }}
          aria-hidden
        />
        <p className="mt-1 text-[10px] leading-snug text-slate-500">
          Corridor forecast at the slider hour (spatial estimate between samples).
        </p>
      </div>
    </div>
  );
}
