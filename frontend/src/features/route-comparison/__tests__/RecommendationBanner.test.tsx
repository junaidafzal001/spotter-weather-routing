import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { RecommendationBanner } from "../RecommendationBanner";
import { makeAnalysis } from "../../../test/factories";

describe("RecommendationBanner", () => {
  it("explains a safe recommendation", () => {
    const analysis = makeAnalysis();
    render(<RecommendationBanner recommendation={analysis.recommendation} routes={analysis.routes} />);
    expect(screen.getByText(/recommended · route 1/i)).toBeInTheDocument();
    expect(screen.getByText(/avoids severe weather/i)).toBeInTheDocument();
    expect(screen.getByText(/fewest Severe miles/i)).toBeInTheDocument();
  });

  it("refuses to declare a safe route when every option has No-Travel exposure", () => {
    const analysis = makeAnalysis();
    render(
      <RecommendationBanner
        recommendation={{
          recommended_route_id: null,
          reason:
            "No safe route is currently available under the selected conditions: every alternative passes through No-Travel weather. route-1 has the least exposure (12.0 mi No-Travel, 4.0 mi Severe). Consider delaying departure or waiting for conditions to improve.",
          eligible: false,
          ranking: ["route-2", "route-1"],
          least_exposed_route_id: "route-1",
          least_exposed_reason: null,
        }}
        routes={analysis.routes}
      />,
    );
    expect(screen.getByText(/no safe route available/i)).toBeInTheDocument();
    expect(screen.getByText(/consider delaying departure/i)).toBeInTheDocument();
    expect(screen.getByText(/least-exposure comparison: Route 1/i)).toBeInTheDocument();
  });
});
