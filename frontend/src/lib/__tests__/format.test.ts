import { describe, expect, it } from "vitest";
import {
  formatDuration,
  formatHourLabel,
  formatMiles,
  formatTime,
  percent,
  toDateTimeLocalValue,
  toIsoWithOffset,
} from "../format";

describe("format helpers", () => {
  it("formats miles and durations", () => {
    expect(formatMiles(281.53)).toBe("281.5 mi");
    expect(formatDuration(48)).toBe("48 min");
    expect(formatDuration(318)).toBe("5 h 18 min");
    expect(formatDuration(120)).toBe("2 h");
    expect(formatDuration(0)).toBe("0 min");
  });

  it("labels the first slider position as Now and later ones as times", () => {
    const iso = new Date(Date.UTC(2026, 9, 20, 15, 0)).toISOString();
    expect(formatHourLabel(iso, 0)).toBe("Now");
    expect(formatTime(iso)).toMatch(/\d/);
    expect(formatHourLabel(iso, 5)).not.toBe("Now");
  });

  it("produces datetime-local values and ISO instants", () => {
    const local = toDateTimeLocalValue(new Date(2026, 9, 20, 8, 30));
    expect(local).toBe("2026-10-20T08:30");
    const iso = toIsoWithOffset("2026-10-20T08:30");
    expect(new Date(iso).getMilliseconds()).toBe(0);
    expect(iso.endsWith("Z")).toBe(true);
  });

  it("computes bounded percentages", () => {
    expect(percent(25, 100)).toBe(25);
    expect(percent(0, 100)).toBe(0);
    expect(percent(5, 0)).toBe(0);
    expect(percent(150, 100)).toBe(100);
  });
});
