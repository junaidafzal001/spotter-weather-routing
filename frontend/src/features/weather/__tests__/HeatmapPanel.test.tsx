import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HeatmapPanel } from "../HeatmapPanel";
import { makeCorridor } from "../../../test/factories";

function renderPanel(overrides: Partial<Parameters<typeof HeatmapPanel>[0]> = {}) {
  const props = {
    corridor: makeCorridor(),
    hour: 0,
    onHourChange: vi.fn(),
    visible: true,
    onVisibleChange: vi.fn(),
    isLoading: false,
    error: null,
    onRetry: vi.fn(),
    ...overrides,
  };
  render(<HeatmapPanel {...props} />);
  return props;
}

describe("HeatmapPanel", () => {
  it("shows the 0–48h slider starting at Now", () => {
    renderPanel();
    const slider = screen.getByRole("slider", { name: /forecast hour/i });
    expect(slider).toHaveValue("0");
    expect(slider).toHaveAttribute("max", "48");
    expect(screen.getAllByText("Now").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/\+48h/)).toBeInTheDocument();
  });

  it("reports slider changes with the chosen hour", () => {
    const props = renderPanel();
    fireEvent.change(screen.getByRole("slider", { name: /forecast hour/i }), { target: { value: "24" } });
    expect(props.onHourChange).toHaveBeenCalledWith(24);
  });

  it("summarizes severity for the selected hour (not a fixed timestamp)", () => {
    renderPanel({ hour: 22 }); // uniform MODERATE window in the factory
    expect(screen.getByText(/Moderate 3/)).toBeInTheDocument();
    expect(screen.getByRole("slider")).toHaveAttribute("aria-valuetext", "22 hours from now");
  });

  it("toggles the heatmap visibility", async () => {
    const user = userEvent.setup();
    const props = renderPanel();
    await user.click(screen.getByRole("switch", { name: /toggle corridor weather heatmap/i }));
    expect(props.onVisibleChange).toHaveBeenCalledWith(false);
  });

  it("renders loading and error states", () => {
    renderPanel({ corridor: undefined, isLoading: true });
    expect(screen.getByText(/loading 48-hour corridor forecast/i)).toBeInTheDocument();
  });

  it("offers a retry when the corridor request fails", async () => {
    const user = userEvent.setup();
    const props = renderPanel({ corridor: undefined, error: "Corridor weather failed" });
    expect(screen.getByText("Corridor weather failed")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /retry/i }));
    expect(props.onRetry).toHaveBeenCalled();
  });

  it("explains when the heatmap is hidden", () => {
    renderPanel({ visible: false });
    expect(screen.getByText(/heatmap hidden/i)).toBeInTheDocument();
  });
});
