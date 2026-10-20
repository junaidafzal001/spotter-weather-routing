import type { ReactNode } from "react";
import type { RiskLevel } from "../types";
import { RISK_BG_CLASSES, RISK_LABELS, RISK_TEXT_CLASSES } from "../lib/risk";

export function cn(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(" ");
}

export function Card({
  children,
  className,
  as: Tag = "div",
}: {
  children: ReactNode;
  className?: string;
  as?: "div" | "section" | "aside";
}) {
  return (
    <Tag className={cn("rounded-2xl border border-line bg-surface shadow-[0_1px_2px_rgba(15,23,42,0.04)]", className)}>
      {children}
    </Tag>
  );
}

export function SectionTitle({
  icon,
  title,
  subtitle,
  action,
}: {
  icon?: ReactNode;
  title: string;
  subtitle?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-3">
      <div className="flex items-start gap-2.5">
        {icon ? <span className="mt-0.5 text-brand">{icon}</span> : null}
        <div>
          <h2 className="text-sm font-semibold tracking-tight text-ink">{title}</h2>
          {subtitle ? <p className="mt-0.5 text-xs leading-relaxed text-muted">{subtitle}</p> : null}
        </div>
      </div>
      {action}
    </div>
  );
}

export function RiskBadge({
  level,
  size = "sm",
  suffix,
}: {
  level: RiskLevel;
  size?: "xs" | "sm";
  suffix?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border font-semibold whitespace-nowrap",
        size === "xs" ? "px-1.5 py-0.5 text-[10px]" : "px-2 py-0.5 text-[11px]",
        RISK_BG_CLASSES[level],
      )}
    >
      <span
        aria-hidden
        className="h-1.5 w-1.5 rounded-full"
        style={{ backgroundColor: riskDot(level) }}
      />
      {RISK_LABELS[level]}
      {suffix ? <span className={cn("font-normal", RISK_TEXT_CLASSES[level])}>{suffix}</span> : null}
    </span>
  );
}

function riskDot(level: RiskLevel): string {
  switch (level) {
    case "LOW":
      return "#16a34a";
    case "MODERATE":
      return "#eab308";
    case "HIGH":
      return "#f97316";
    case "SEVERE":
      return "#dc2626";
    case "NO_TRAVEL":
      return "#7f1d1d";
    default:
      return "#9ca3af";
  }
}

export function Spinner({ className }: { className?: string }) {
  return (
    <span
      aria-hidden
      className={cn(
        "inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent",
        className,
      )}
    />
  );
}
