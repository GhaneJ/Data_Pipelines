import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ApplicationsBrowser } from "./ApplicationsBrowser";
import type { ApplicationRecord } from "../services/api";

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

const jsonResponse = (payload: unknown) => Promise.resolve(new Response(JSON.stringify(payload), { status: 200 }));

beforeEach(() => {
  vi.restoreAllMocks();
});

test("renders applications, applies filters, paginates, and loads a detail view", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.includes("/applications/MYH%202024%2F1")) {
      return jsonResponse(application);
    }

    const offset = new URL(url).searchParams.get("offset") ?? "0";
    return jsonResponse({ total: 40, limit: 25, offset: Number(offset), items: [application] });
  });

  render(<ApplicationsBrowser />);

  await waitFor(() => expect(screen.getAllByText("Data Engineer").length).toBeGreaterThan(0));
  await waitFor(() => expect(screen.getAllByText("Example Provider").length).toBeGreaterThan(0));
  expect(screen.getByText(/1–1 shown of 40/i)).toBeInTheDocument();

  await userEvent.selectOptions(screen.getByLabelText(/Year/i), "2024");
  await userEvent.selectOptions(screen.getByLabelText(/Decision/i), "approved");
  await userEvent.click(screen.getByRole("button", { name: /Apply filters/i }));

  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("source_year=2024"), expect.any(Object)));
  expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("decision=approved"), expect.any(Object));

  await userEvent.click(screen.getByRole("button", { name: /Next/i }));

  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("offset=25"), expect.any(Object)));
});

test("renders empty application state", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ total: 0, limit: 25, offset: 0, items: [] }), { status: 200 }));

  render(<ApplicationsBrowser />);

  await waitFor(() => expect(screen.getByText(/No applications matched/i)).toBeInTheDocument());
});
