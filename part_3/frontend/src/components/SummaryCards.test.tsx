import { render, screen } from "@testing-library/react";
import { SummaryCards } from "./SummaryCards";

test("renders summary values from year and decision statistics", () => {
  render(
    <SummaryCards
      yearStats={[
        {
          source_year: 2020,
          total_applications: 100,
          approved_applications: 40,
          rejected_applications: 60,
          withdrawn_applications: 0,
          approval_rate_percent: 40,
        },
        {
          source_year: 2025,
          total_applications: 150,
          approved_applications: 75,
          rejected_applications: 75,
          withdrawn_applications: 0,
          approval_rate_percent: 50,
        },
      ]}
      decisionStats={[
        { decision_code: "approved", decision_label: "Approved", total_applications: 115, application_share_percent: 46 },
        { decision_code: "rejected", decision_label: "Rejected", total_applications: 135, application_share_percent: 54 },
      ]}
    />,
  );

  expect(screen.getByText("250")).toBeInTheDocument();
  expect(screen.getByText("2020-2025")).toBeInTheDocument();
  expect(screen.getByText("115 / 135")).toBeInTheDocument();
});
