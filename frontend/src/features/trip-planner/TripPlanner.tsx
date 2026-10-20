import { useEffect } from "react";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { AlertTriangle, Clock, Gauge, Loader2, Route, Weight } from "lucide-react";
import type { AnalyzeTripInput } from "../../types";
import { ApiError } from "../../lib/api";
import { defaultDeparture, toIsoWithOffset } from "../../lib/format";
import { cn, Spinner } from "../../components/ui";
import { LocationField } from "./LocationField";
import { tripFormSchema, type FormValues } from "./schema";

interface TripPlannerProps {
  onAnalyze: (input: AnalyzeTripInput) => void;
  isPending: boolean;
  error: ApiError | null;
  preset: { origin: string; destination: string } | null;
  onPresetConsumed: () => void;
}

const LOAD_PRESETS = [
  { label: "Empty", value: 0 },
  { label: "20k", value: 20_000 },
  { label: "35k", value: 35_000 },
  { label: "44k", value: 44_000 },
];

const INTERVALS = [10, 25, 50] as const;

const SERVER_FIELD_MAP: Record<string, keyof FormValues> = {
  origin: "origin",
  destination: "destination",
  departure_time: "departure",
  load_weight_lbs: "loadWeight",
};

function departureValidationError(value: string): string | null {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Choose a valid departure date and time";
  if (date.getTime() < Date.now() - 60_000) return "Departure must be in the future";
  return null;
}

export function TripPlanner({ onAnalyze, isPending, error, preset, onPresetConsumed }: TripPlannerProps) {
  const {
    register,
    handleSubmit,
    control,
    setValue,
    setError,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(tripFormSchema),
    defaultValues: {
      origin: "",
      destination: "",
      departure: defaultDeparture(),
      loadWeight: 35_000,
      interval: 25,
    },
  });

  const interval = useWatch({ control, name: "interval" });
  const loadWeight = useWatch({ control, name: "loadWeight" });

  useEffect(() => {
    if (!preset) return;
    setValue("origin", preset.origin, { shouldValidate: true });
    setValue("destination", preset.destination, { shouldValidate: true });
    onPresetConsumed();
  }, [preset, setValue, onPresetConsumed]);

  useEffect(() => {
    if (!error) return;
    for (const [serverField, message] of Object.entries(error.fields)) {
      const formField = SERVER_FIELD_MAP[serverField];
      if (formField) setError(formField, { type: "server", message });
    }
  }, [error, setError]);

  const submit = handleSubmit((values) => {
    const departureError = departureValidationError(values.departure);
    if (departureError) {
      setError("departure", { message: departureError });
      return;
    }
    onAnalyze({
      origin: values.origin.trim(),
      destination: values.destination.trim(),
      departure_time: toIsoWithOffset(values.departure),
      load_weight_lbs: values.loadWeight,
      checkpoint_interval_miles: values.interval,
    });
  });

  return (
    <form onSubmit={submit} noValidate className="space-y-3.5">
      <LocationField
        control={control}
        name="origin"
        label="Origin"
        placeholder="Chicago, IL"
        error={errors.origin?.message}
      />
      <LocationField
        control={control}
        name="destination"
        label="Destination"
        placeholder="Detroit, MI"
        error={errors.destination?.message}
      />

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label htmlFor="departure" className="mb-1 flex items-center gap-1.5 text-xs font-medium text-muted">
            <Clock size={13} className="text-slate-400" aria-hidden />
            Departure
          </label>
          <input
            id="departure"
            type="datetime-local"
            aria-invalid={Boolean(errors.departure)}
            className={cn(
              "w-full rounded-lg border bg-white px-2.5 py-2 text-sm text-ink shadow-sm outline-none transition focus:border-brand focus:ring-2 focus:ring-brand/20",
              errors.departure ? "border-red-400" : "border-line",
            )}
            {...register("departure")}
          />
          {errors.departure ? (
            <p role="alert" className="mt-1 text-xs font-medium text-red-600">
              {errors.departure.message}
            </p>
          ) : null}
        </div>

        <div>
          <label htmlFor="loadWeight" className="mb-1 flex items-center gap-1.5 text-xs font-medium text-muted">
            <Weight size={13} className="text-slate-400" aria-hidden />
            Load weight (lb)
          </label>
          <input
            id="loadWeight"
            type="number"
            inputMode="numeric"
            min={0}
            max={80_000}
            step={500}
            aria-invalid={Boolean(errors.loadWeight)}
            className={cn(
              "w-full rounded-lg border bg-white px-2.5 py-2 text-sm tabular-nums text-ink shadow-sm outline-none transition focus:border-brand focus:ring-2 focus:ring-brand/20",
              errors.loadWeight ? "border-red-400" : "border-line",
            )}
            {...register("loadWeight", { valueAsNumber: true })}
          />
          {errors.loadWeight ? (
            <p role="alert" className="mt-1 text-xs font-medium text-red-600">
              {errors.loadWeight.message}
            </p>
          ) : null}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-1.5">
        <span className="text-[11px] font-medium text-muted">Load presets:</span>
        {LOAD_PRESETS.map((presetValue) => (
          <button
            key={presetValue.value}
            type="button"
            onClick={() => setValue("loadWeight", presetValue.value, { shouldValidate: true })}
            className={cn(
              "rounded-full border px-2 py-0.5 text-[11px] font-medium transition",
              loadWeight === presetValue.value
                ? "border-brand bg-brand-soft text-brand-dark"
                : "border-line text-muted hover:border-slate-300 hover:text-ink",
            )}
          >
            {presetValue.label}
          </button>
        ))}
      </div>

      <div>
        <span className="mb-1 flex items-center gap-1.5 text-xs font-medium text-muted">
          <Gauge size={13} className="text-slate-400" aria-hidden />
          Weather checkpoint interval
        </span>
        <div className="grid grid-cols-3 gap-1 rounded-lg border border-line bg-slate-50 p-1" role="group" aria-label="Checkpoint interval">
          {INTERVALS.map((value) => (
            <button
              key={value}
              type="button"
              aria-pressed={interval === value}
              onClick={() => setValue("interval", value, { shouldValidate: true })}
              className={cn(
                "rounded-md px-2 py-1.5 text-xs font-semibold transition",
                interval === value
                  ? "bg-white text-brand-dark shadow-sm ring-1 ring-line"
                  : "text-muted hover:text-ink",
              )}
            >
              {value} mi
            </button>
          ))}
        </div>
      </div>

      {error ? (
        <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-2.5 text-xs text-red-800">
          <div className="flex items-start gap-1.5 font-semibold">
            <AlertTriangle size={14} className="mt-0.5 shrink-0" aria-hidden />
            <span>{error.message}</span>
          </div>
          {Object.keys(error.fields).length > 0 ? (
            <ul className="mt-1 list-inside list-disc pl-5">
              {Object.entries(error.fields).map(([field, message]) => (
                <li key={field}>
                  {field}: {message}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      <button
        type="submit"
        disabled={isPending}
        className={cn(
          "flex w-full items-center justify-center gap-2 rounded-lg px-3 py-2.5 text-sm font-semibold text-white shadow-sm transition",
          isPending ? "cursor-wait bg-brand/70" : "bg-brand hover:bg-brand-dark active:scale-[0.99]",
        )}
      >
        {isPending ? <Spinner className="border-white/40 border-t-white" /> : <Route size={16} aria-hidden />}
        {isPending ? "Analyzing route weather…" : "Analyze routes"}
      </button>

      <p className="text-[11px] leading-relaxed text-muted">
        Forecasts are sampled at each checkpoint&rsquo;s projected arrival time. Routing uses truck-capable
        providers when configured; verify bridge, axle, and road-weight restrictions before dispatch.
      </p>
      {isPending ? (
        <span className="sr-only" role="status">
          <Loader2 /> Analyzing routes and weather
        </span>
      ) : null}
    </form>
  );
}
