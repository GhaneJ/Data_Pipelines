import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ApplicationsBrowser } from "@/components/ApplicationsBrowser";
import type { ApplicationRecord } from "@/services/api";

const application: ApplicationRecord = {
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
};

const jsonResponse = (payload: unknown) => Promise.resolve(new Response(JSON.stringify(payload), { status: 200, headers: { "Content-Type": "application/json" } }));

function mockApplicationsFetch(items: ApplicationRecord[], total = items.length) {
  return vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.includes("/applications/MYH%202024%2F1")) {
      return jsonResponse(application);
    }
    if (url.includes("/stats/by-year")) {
      return jsonResponse([
        { source_year: 2025, total_applications: 20, approved_applications: 10, rejected_applications: 10, withdrawn_applications: 0, approval_rate_percent: 50 },
        { source_year: 2024, total_applications: 20, approved_applications: 10, rejected_applications: 10, withdrawn_applications: 0, approval_rate_percent: 50 },
      ]);
    }
    if (url.includes("/stats/by-region")) {
      return jsonResponse([{ lan: "Stockholm", total_applications: 50, approved_applications: 25, rejected_applications: 25, withdrawn_applications: 0, approval_rate_percent: 50 }]);
    }
    if (url.includes("/stats/by-education-area")) {
      return jsonResponse([{ education_area_id: 1, utbildningsomrade: "Data/IT", total_applications: 30, approved_applications: 15, rejected_applications: 15, withdrawn_applications: 0, approval_rate_percent: 50 }]);
    }
    if (url.includes("/providers")) {
      return jsonResponse({ items: [{ provider_id: "999", utbildningsanordnare: "Example Provider", total_applications: 10, approved_applications: 5, first_year: 2020, last_year: 2025 }], total: 1, limit: 50, offset: 0 });
    }

    const offset = new URL(url).searchParams.get("offset") ?? "0";
    return jsonResponse({ total, limit: 25, offset: Number(offset), items });
  });
}

beforeEach(() => {
  vi.restoreAllMocks();
});

test("renders applications, applies filters, paginates, and loads a detail view", async () => {
  const fetchMock = mockApplicationsFetch([application], 40);
  const user = userEvent.setup();

  render(<ApplicationsBrowser />);

  await waitFor(() => expect(screen.getAllByText("Data Engineer").length).toBeGreaterThan(0));
  await waitFor(() => expect(screen.getAllByText("Example Provider").length).toBeGreaterThan(0));
  expect(screen.getByText(/Showing 1–1 of 40/i)).toBeInTheDocument();

  await user.type(screen.getByLabelText(/Year/i), "2024");
  await user.type(screen.getByLabelText(/Decision/i), "approved");
  await user.click(screen.getByRole("button", { name: /Apply filters/i }));

  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("source_year=2024"), expect.any(Object)));
  expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("decision=approved"), expect.any(Object));

  await user.click(screen.getByRole("button", { name: /Next/i }));

  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("offset=25"), expect.any(Object)));
});

test("renders empty application state", async () => {
  mockApplicationsFetch([], 0);

  render(<ApplicationsBrowser />);

  await waitFor(() => expect(screen.getByText(/No applications matched/i)).toBeInTheDocument());
});
