import { CloudSun, Map, ShieldCheck, Sparkles } from "lucide-react";
import { Card } from "../components/ui";

const SAMPLES = [
  { origin: "Chicago, IL", destination: "Detroit, MI", label: "Chicago → Detroit" },
  { origin: "Denver, CO", destination: "Kansas City, MO", label: "Denver → Kansas City" },
  { origin: "Dallas, TX", destination: "Atlanta, GA", label: "Dallas → Atlanta" },
];

export function EmptyState({ onUseSample }: { onUseSample: (origin: string, destination: string) => void }) {
  return (
    <Card className="animate-rise overflow-hidden">
      <div className="relative overflow-hidden bg-gradient-to-br from-brand-dark via-brand to-slate-700 px-6 py-10 text-white">
        <div className="absolute -right-10 -top-10 h-44 w-44 rounded-full bg-white/10 blur-2xl" aria-hidden />
        <div className="absolute -bottom-16 left-16 h-48 w-48 rounded-full bg-sky-400/20 blur-3xl" aria-hidden />
        <div className="relative max-w-lg">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-white/10 px-2.5 py-1 text-[11px] font-medium text-white/90 ring-1 ring-white/20">
            <Sparkles size={11} aria-hidden />
            Plan around the weather, not through it
          </span>
          <h2 className="mt-3 text-xl font-bold tracking-tight sm:text-2xl">
            Compare routes by the weather your truck will actually meet.
          </h2>
          <p className="mt-2 max-w-md text-sm leading-relaxed text-white/80">
            Enter an origin, destination, departure time, and load weight. We sample forecasts at every
            checkpoint ETA, score the risk, and recommend the safest of up to three distinct routes.
          </p>
          <div className="mt-4 flex flex-wrap gap-1.5">
            {SAMPLES.map((sample) => (
              <button
                key={sample.label}
                type="button"
                onClick={() => onUseSample(sample.origin, sample.destination)}
                className="rounded-full border border-white/25 bg-white/10 px-2.5 py-1 text-[11px] font-medium text-white transition hover:bg-white/20"
              >
                {sample.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="grid gap-4 p-5 sm:grid-cols-3">
        <Feature
          icon={<Map size={16} aria-hidden />}
          title="Distinct alternatives"
          body="Up to three genuinely different routes — never duplicated geometry dressed up as an alternative."
        />
        <Feature
          icon={<CloudSun size={16} aria-hidden />}
          title="ETA-aware forecasts"
          body="Checkpoint weather is selected at the projected arrival time, with a 48-hour corridor heatmap for the bigger picture."
        />
        <Feature
          icon={<ShieldCheck size={16} aria-hidden />}
          title="Safety first"
          body="No-Travel conditions exclude a route from recommendation — the highest severity is never averaged away."
        />
      </div>
    </Card>
  );
}

function Feature({ icon, title, body }: { icon: React.ReactNode; title: string; body: string }) {
  return (
    <div className="flex gap-2.5">
      <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand-soft text-brand">
        {icon}
      </span>
      <div>
        <h3 className="text-xs font-semibold text-ink">{title}</h3>
        <p className="mt-0.5 text-[11px] leading-relaxed text-muted">{body}</p>
      </div>
    </div>
  );
}
