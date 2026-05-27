import { render, screen } from "@testing-library/react";
import { ApplicationDetailPanel } from "./ApplicationDetailPanel";
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

test("renders selected application details", () => {
  render(<ApplicationDetailPanel application={application} status="success" errorMessage={null} />);

  expect(screen.getByRole("heading", { name: "Data Engineer" })).toBeInTheDocument();
  expect(screen.getByText("Example Provider")).toBeInTheDocument();
  expect(screen.getByText("Stockholm / Stockholm")).toBeInTheDocument();
});

test("renders empty detail guidance", () => {
  render(<ApplicationDetailPanel application={null} status="idle" errorMessage={null} />);

  expect(screen.getByText(/Choose a row/i)).toBeInTheDocument();
});
