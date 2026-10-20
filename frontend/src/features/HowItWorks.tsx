import { CloudSun, Gauge, Route, ShieldAlert } from "lucide-react";

const STEPS = [
  {
    icon: Route,
    title: "Enter the trip",
    body: "Origin, destination, departure time, load weight, and the checkpoint interval (10/25/50 mi).",
  },
  {
    icon: CloudSun,
    title: "Sample forecasts at ETAs",
    body: "Each checkpoint gets the forecast for its projected arrival hour — wind, rain, snow, temperature.",
  },
  {
    icon: Gauge,
    title: "Score and rank",
    body: "Deterministic risk rules, distance-weighted exposure, and the assessment's four-tier ranking.",
  },
  {
    icon: ShieldAlert,
    title: "Exclude unsafe options",
    body: "Any route with No-Travel conditions is removed from the safe ranking and flagged explicitly.",
  },
];

export function HowItWorks() {
  return (
    <div className="rounded-2xl border border-line bg-surface p-4">
      <h2 className="text-sm font-semibold text-ink">How the analysis works</h2>
      <ol className="mt-3 space-y-3">
        {STEPS.map((step, index) => (
          <li key={step.title} className="flex gap-2.5">
            <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-brand-soft text-brand">
              <step.icon size={13} aria-hidden />
            </span>
            <div>
              <div className="text-xs font-semibold text-ink">
                {index + 1}. {step.title}
              </div>
              <p className="mt-0.5 text-[11px] leading-relaxed text-muted">{step.body}</p>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
