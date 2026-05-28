import { buildApiUrl } from "@/services/api";

test("builds API URLs with the configured base URL and query parameters", () => {
  const url = buildApiUrl("/applications", {
    source_year: 2024,
    decision: "approved",
    provider: "Academy",
    empty: "",
  });

  expect(url).toContain("/applications");
  expect(url).toContain("source_year=2024");
  expect(url).toContain("decision=approved");
  expect(url).toContain("provider=Academy");
  expect(url).not.toContain("empty=");
});
