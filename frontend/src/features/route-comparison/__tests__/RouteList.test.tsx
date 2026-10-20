import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouteList } from "../RouteList";
import { makeAnalysis, makeRoute } from "../../../test/factories";

describe("RouteList", () => {
  it("marks exactly one recommended route and lists all alternatives", () => {
    const analysis = makeAnalysis();
    render(
      <RouteList
        routes={analysis.routes}
        recommendation={analysis.recommendation}
        selectedRouteId="route-1"
        onSelect={vi.fn()}
      />,
    );

    expect(screen.getByText("Route options (2)")).toBeInTheDocument();
    expect(screen.getByText("Route 1")).toBeInTheDocument();
    expect(screen.getByText("Route 2")).toBeInTheDocument();
    expect(screen.getAllByText(/recommended/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Recommended")).toHaveLength(1);
  });

  it("calls onSelect when a route card is clicked", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    const analysis = makeAnalysis();
    render(
      <RouteList
        routes={analysis.routes}
        recommendation={analysis.recommendation}
        selectedRouteId="route-1"
        onSelect={onSelect}
      />,
    );

    await user.click(screen.getByRole("button", { name: /route 2/i }));
    expect(onSelect).toHaveBeenCalledWith("route-2");
  });

  it("surfaces No-Travel miles on affected routes", () => {
    const risky = makeRoute({
      id: "route-2",
      exposure: {
        low_miles: 10,
        moderate_miles: 0,
        high_miles: 0,
        severe_miles: 5,
        no_travel_miles: 15,
        unassessed_miles: 0,
        total_miles: 30,
        average_risk: 2.17,
        max_risk: "NO_TRAVEL",
        unassessed_share: 0,
      },
    });
    render(
      <RouteList
        routes={[risky]}
        recommendation={{
          recommended_route_id: null,
          reason: "No safe route is currently available under the selected conditions",
          eligible: false,
          ranking: ["route-2"],
          least_exposed_route_id: "route-2",
          least_exposed_reason: null,
        }}
        selectedRouteId="route-2"
        onSelect={vi.fn()}
      />,
    );
    expect(screen.getByText(/15 mi No Travel/i)).toBeInTheDocument();
    expect(screen.getAllByText(/No Travel/i).length).toBeGreaterThanOrEqual(2);
  });
});
