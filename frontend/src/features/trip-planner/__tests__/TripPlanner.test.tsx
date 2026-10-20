import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { TripPlanner } from "../TripPlanner";

vi.mock("../../../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../../lib/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      suggest: vi.fn().mockResolvedValue({ data: { suggestions: [] }, warnings: [], meta: {} }),
    },
  };
});

function renderPlanner(overrides: Partial<Parameters<typeof TripPlanner>[0]> = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const onAnalyze = vi.fn();
  const onPresetConsumed = vi.fn();
  const ui = (
    <QueryClientProvider client={queryClient}>
      <TripPlanner
        onAnalyze={onAnalyze}
        isPending={false}
        error={null}
        preset={null}
        onPresetConsumed={onPresetConsumed}
        {...overrides}
      />
    </QueryClientProvider>
  ) as ReactNode;
  render(ui);
  return { onAnalyze, onPresetConsumed, queryClient };
}

describe("TripPlanner", () => {
  it("shows useful validation errors when required fields are empty", async () => {
    const user = userEvent.setup();
    const { onAnalyze } = renderPlanner();

    await user.click(screen.getByRole("button", { name: /analyze routes/i }));

    expect(await screen.findByText(/enter an origin city/i)).toBeInTheDocument();
    expect(screen.getByText(/enter a destination city/i)).toBeInTheDocument();
    expect(onAnalyze).not.toHaveBeenCalled();
  });

  it("rejects an out-of-range load weight", async () => {
    const user = userEvent.setup();
    const { onAnalyze } = renderPlanner();

    const weight = screen.getByLabelText(/load weight/i);
    await user.clear(weight);
    await user.type(weight, "90000");
    await user.type(screen.getByLabelText(/^origin$/i), "Chicago, IL");
    await user.type(screen.getByLabelText(/^destination$/i), "Detroit, MI");
    await user.click(screen.getByRole("button", { name: /analyze routes/i }));

    expect(await screen.findByText(/maximum supported load weight/i)).toBeInTheDocument();
    expect(onAnalyze).not.toHaveBeenCalled();
  });

  it("submits a valid trip with the selected interval and local ISO departure", async () => {
    const user = userEvent.setup();
    const { onAnalyze } = renderPlanner();

    await user.type(screen.getByLabelText(/^origin$/i), "Chicago, IL");
    await user.type(screen.getByLabelText(/^destination$/i), "Detroit, MI");
    await user.click(screen.getByRole("button", { name: "10 mi" }));
    await user.click(screen.getByRole("button", { name: /analyze routes/i }));

    expect(onAnalyze).toHaveBeenCalledTimes(1);
    const input = onAnalyze.mock.calls[0][0];
    expect(input.origin).toBe("Chicago, IL");
    expect(input.destination).toBe("Detroit, MI");
    expect(input.checkpoint_interval_miles).toBe(10);
    expect(input.load_weight_lbs).toBe(35_000);
    expect(input.departure_time.endsWith("Z")).toBe(true);
  });

  it("applies a sample-trip preset and notifies the parent", async () => {
    const { onPresetConsumed } = renderPlanner({ preset: { origin: "Denver, CO", destination: "Kansas City, MO" } });
    expect(screen.getByLabelText(/^origin$/i)).toHaveValue("Denver, CO");
    expect(screen.getByLabelText(/^destination$/i)).toHaveValue("Kansas City, MO");
    expect(onPresetConsumed).toHaveBeenCalled();
  });

  it("disables submission while analyzing", () => {
    renderPlanner({ isPending: true });
    const button = screen.getByRole("button", { name: /analyzing route weather/i });
    expect(button).toBeDisabled();
  });

  it("renders a structured server error", () => {
    const error = Object.assign(new Error("Origin could not be resolved"), {
      code: "geocode_not_found",
      status: 422,
      fields: { origin: "No match for 'Xyzzy'" },
    });
    renderPlanner({ error });
    expect(screen.getByText(/origin could not be resolved/i)).toBeInTheDocument();
    expect(screen.getByText(/origin: No match/i)).toBeInTheDocument();
  });
});
