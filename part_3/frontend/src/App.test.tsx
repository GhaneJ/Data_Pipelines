import { render, screen, waitFor } from "@testing-library/react";
import App from "./App";

beforeEach(() => {
  vi.restoreAllMocks();
});

test("renders dashboard shell and backend status", async () => {
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(new Response(JSON.stringify({ status: "ok" }), { status: 200 }))
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          status: "ready",
          database_connected: true,
          required_tables: { ok: true, checked: ["applications"], missing: [] },
          applications: { table: "applications", ok: true, row_count: 7641 },
          lookup_tables: [],
        }),
        { status: 200 },
      ),
    );

  render(<App />);

  expect(screen.getByRole("heading", { name: /MYH Applications Dashboard/i })).toBeInTheDocument();
  expect(screen.getByText(/Backend status/i)).toBeInTheDocument();

  await waitFor(() => expect(screen.getByText(/7,641 application rows/i)).toBeInTheDocument());
});

test("shows helpful message when backend is unreachable", async () => {
  vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new Error("Failed to fetch"));

  render(<App />);

  await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/Start the backend/i));
});
