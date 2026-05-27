import { render, screen, waitFor } from "@testing-library/react";
import App from "./App";

const jsonResponse = (payload: unknown) => Promise.resolve(new Response(JSON.stringify(payload), { status: 200 }));

beforeEach(() => {
  vi.restoreAllMocks();
});

test("renders dashboard shell, backend status, and metric sections", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.includes("/health/db")) {
      return jsonResponse({
        status: "ready",
        database_connected: true,
        required_tables: { ok: true, checked: ["applications"], missing: [] },
        applications: { table: "applications", ok: true, row_count: 7641 },
        lookup_tables: [],
      });
    }
    if (url.includes("/health")) {
      return jsonResponse({ status: "ok" });
    }
    if (url.includes("/stats/by-year")) {
      return jsonResponse([
        {
          source_year: 2020,
          total_applications: 100,
          approved_applications: 50,
          rejected_applications: 50,
          withdrawn_applications: 0,
          approval_rate_percent: 50,
        },
      ]);
    }
    if (url.includes("/stats/by-decision")) {
      return jsonResponse([
        { decision_code: "approved", decision_label: "Approved", total_applications: 50, application_share_percent: 50 },
        { decision_code: "rejected", decision_label: "Rejected", total_applications: 50, application_share_percent: 50 },
      ]);
    }
    if (url.includes("/stats/by-region")) {
      return jsonResponse([{ lan: "Stockholm", total_applications: 50, approved_applications: 25, rejected_applications: 25, withdrawn_applications: 0, approval_rate_percent: 50 }]);
    }
    if (url.includes("/stats/by-education-area")) {
      return jsonResponse([{ education_area_id: 1, utbildningsomrade: "Data/IT", total_applications: 30, approved_applications: 15, rejected_applications: 15, withdrawn_applications: 0, approval_rate_percent: 50 }]);
    }
    if (url.includes("/stats/trends/by-decision")) {
      return jsonResponse([{ source_year: 2020, decision_code: "approved", decision_label: "Approved", application_count: 50 }]);
    }
    if (url.includes("/stats/trends/by-education-area")) {
      return jsonResponse([{ source_year: 2020, education_area_id: 1, utbildningsomrade: "Data/IT", application_count: 30 }]);
    }

    if (url.includes("/applications/MYH%202024%2F1")) {
      return jsonResponse({
        diarienummer: "MYH 2024/1",
        source_year: 2024,
        source_file: "source.xlsx",
        source_sheet: "Tabell 3",
        source_row: 10,
        utbildningsnamn: "Data Engineer",
        utbildningsomrade: "Data/IT",
        beslut: "Beviljad",
        beslut_normalized: "approved",
        is_approved: true,
        lan: "Stockholm",
        kommun: "Stockholm",
        flera_kommuner: "Nej",
        has_multiple_municipalities: false,
        antal_kommuner: 1,
        yh_poang: 400,
        studieform: "Bunden",
        is_distance_based: false,
        studietakt_procent: 100,
        examenstyp: null,
        utbildningsanordnare: "Example Provider",
        huvudmannatyp: "Privat",
        huvudmannatyp_normalized: "private",
        sokta_utbildningsomgangar: 2,
        beviljade_utbildningsomgangar: 1,
        sun5_inriktning: null,
        sun5_inriktning_namn: null,
        seqf_niva: null,
        smalt_yrkesomrade: null,
        sokta_platser_per_utbildningsomgang: null,
        sokta_platser_totalt: null,
        beviljade_platser_totalt: null,
      });
    }
    if (url.includes("/applications")) {
      return jsonResponse({
        total: 1,
        limit: 25,
        offset: 0,
        items: [{
          diarienummer: "MYH 2024/1",
          source_year: 2024,
          source_file: "source.xlsx",
          source_sheet: "Tabell 3",
          source_row: 10,
          utbildningsnamn: "Data Engineer",
          utbildningsomrade: "Data/IT",
          beslut: "Beviljad",
          beslut_normalized: "approved",
          is_approved: true,
          lan: "Stockholm",
          kommun: "Stockholm",
          flera_kommuner: "Nej",
          has_multiple_municipalities: false,
          antal_kommuner: 1,
          yh_poang: 400,
          studieform: "Bunden",
          is_distance_based: false,
          studietakt_procent: 100,
          examenstyp: null,
          utbildningsanordnare: "Example Provider",
          huvudmannatyp: "Privat",
          huvudmannatyp_normalized: "private",
          sokta_utbildningsomgangar: 2,
          beviljade_utbildningsomgangar: 1,
          sun5_inriktning: null,
          sun5_inriktning_namn: null,
          seqf_niva: null,
          smalt_yrkesomrade: null,
          sokta_platser_per_utbildningsomgang: null,
          sokta_platser_totalt: null,
          beviljade_platser_totalt: null,
        }],
      });
    }
    return jsonResponse({});
  });

  render(<App />);

  expect(screen.getByRole("heading", { name: /MYH Applications Dashboard/i })).toBeInTheDocument();
  await waitFor(() => expect(screen.getByText(/7,641 application rows/i)).toBeInTheDocument());
  await waitFor(() => expect(screen.getByText(/Curated application story/i)).toBeInTheDocument());
  expect(screen.getByText(/Applications by year/i)).toBeInTheDocument();
  await waitFor(() => expect(screen.getAllByText("Data Engineer").length).toBeGreaterThan(0));
});

test("shows helpful message when backend is unreachable", async () => {
  vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("Failed to fetch"));

  render(<App />);

  await waitFor(() => expect(screen.getByText(/Start the backend from/i)).toBeInTheDocument());
});
