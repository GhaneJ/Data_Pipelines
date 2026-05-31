import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "@/App";

const jsonResponse = (payload: unknown, status = 200) => Promise.resolve(new Response(JSON.stringify(payload), { status, headers: { "Content-Type": "application/json", "X-Request-ID": "test-request" } }));

function mockPublicDashboardFetch() {
  return vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    const url = String(input);
    expect(init?.headers ? JSON.stringify(init.headers) : "").not.toContain("X-API-Key");
    if (url.includes("/health/db")) return jsonResponse({ status: "ready", database_connected: true, required_tables: { ok: true, checked: ["applications"], missing: [] }, applications: { table: "applications", ok: true, row_count: 7641 }, lookup_tables: [] });
    if (url.includes("/health")) return jsonResponse({ status: "ok" });
    if (url.includes("/stats/by-year")) return jsonResponse([{ source_year: 2020, total_applications: 100, approved_applications: 50, rejected_applications: 50, withdrawn_applications: 0, approval_rate_percent: 50 }]);
    if (url.includes("/stats/by-decision")) return jsonResponse([{ decision_code: "approved", decision_label: "Approved", total_applications: 50, application_share_percent: 50 }, { decision_code: "rejected", decision_label: "Rejected", total_applications: 50, application_share_percent: 50 }]);
    if (url.includes("/stats/by-region")) return jsonResponse([{ lan: "Stockholm", total_applications: 50, approved_applications: 25, rejected_applications: 25, withdrawn_applications: 0, approval_rate_percent: 50 }]);
    if (url.includes("/stats/by-education-area")) return jsonResponse([{ education_area_id: 1, utbildningsomrade: "Data/IT", total_applications: 30, approved_applications: 15, rejected_applications: 15, withdrawn_applications: 0, approval_rate_percent: 50 }]);
    if (url.includes("/stats/trends/by-decision")) return jsonResponse([{ source_year: 2020, decision_code: "approved", decision_label: "Approved", application_count: 50 }]);
    if (url.includes("/stats/trends/by-education-area")) return jsonResponse([{ source_year: 2020, education_area_id: 1, utbildningsomrade: "Data/IT", application_count: 30 }]);
    if (url.includes("/applications")) return jsonResponse({ total: 1, limit: 25, offset: 0, items: [{ diarienummer: "MYH 2024/1", source_year: 2024, source_file: "source.xlsx", source_sheet: "Tabell 3", source_row: 10, utbildningsnamn: "Data Engineer", utbildningsomrade: "Data/IT", beslut: "Beviljad", beslut_normalized: "approved", is_approved: true, lan: "Stockholm", kommun: "Stockholm", flera_kommuner: "Nej", has_multiple_municipalities: false, antal_kommuner: 1, yh_poang: 400, studieform: "Bunden", is_distance_based: false, studietakt_procent: 100, examenstyp: null, utbildningsanordnare: "Example Provider", huvudmannatyp: "Privat", huvudmannatyp_normalized: "private", sokta_utbildningsomgangar: 2, beviljade_utbildningsomgangar: 1, sun5_inriktning: null, sun5_inriktning_namn: null, seqf_niva: null, smalt_yrkesomrade: null, sokta_platser_per_utbildningsomgang: null, sokta_platser_totalt: null, beviljade_platser_totalt: null }] });
    return jsonResponse({});
  });
}

beforeEach(() => {
  vi.restoreAllMocks();
  sessionStorage.clear();
  window.history.pushState({}, "", "/");
});

test("renders login shell and controlled signup entry without using API keys", async () => {
  render(<App />);

  await waitFor(() => expect(screen.getByRole("heading", { name: /Sign in to the MYH portal/i })).toBeInTheDocument());
  expect(screen.getByText(/database-issued human session token/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Request provider access/i })).toBeInTheDocument();
});

test("public data explorer keeps the original dashboard available", async () => {
  mockPublicDashboardFetch();
  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /Open public data explorer/i }));

  expect(screen.getByRole("heading", { name: /Historical MYH applications, ready to explore/i })).toBeInTheDocument();
  await waitFor(() => expect(screen.getAllByText((text) => text.replace(/\s/g, "") === "100").length).toBeGreaterThan(0));
  await waitFor(() => expect(screen.getAllByText(/Historical insights/i).length).toBeGreaterThan(0));
  await user.click(screen.getByRole("button", { name: /Browse archive/i }));
  await waitFor(() => expect(screen.getByRole("heading", { name: /Applications browser/i })).toBeInTheDocument());
  await waitFor(() => expect(screen.getAllByText("Data Engineer").length).toBeGreaterThan(0));
});

test("admin login routes to the admin workspace", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    const url = String(input);
    const headers = JSON.stringify(init?.headers ?? {});
    if (url.includes("/auth/login")) return jsonResponse({ access_token: "admin-token", token_type: "bearer", expires_at: "2030-01-01T00:00:00Z" });
    if (url.includes("/auth/whoami")) {
      expect(headers).toContain("Bearer admin-token");
      return jsonResponse({ subject: "user:admin", username: "admin", display_name: "Local Admin", role: "admin", provider_id: null });
    }
    if (url.includes("/admin/users")) return jsonResponse({ items: [{ id: "u1", username: "admin", display_name: "Local Admin", role: "admin", provider_id: null, is_active: true, failed_login_count: 0, locked_until: null, last_login_at: null, password_changed_at: "2030-01-01T00:00:00Z", created_at: "2030-01-01T00:00:00Z", updated_at: "2030-01-01T00:00:00Z" }], limit: 100, offset: 0 });
    if (url.includes("/admin/registration-requests")) return jsonResponse({ items: [], limit: 100, offset: 0 });
    if (url.includes("/admin/provider-submissions")) return jsonResponse({ items: [], limit: 100, offset: 0 });
    if (url.includes("/admin/api-keys")) return jsonResponse([]);
    if (url.includes("/health/db")) return jsonResponse({ status: "ready", database_connected: true, required_tables: { ok: true, checked: ["applications"], missing: [] }, applications: { table: "applications", ok: true, row_count: 7641 }, lookup_tables: [] });
    if (url.includes("/health")) return jsonResponse({ status: "ok" });
    return jsonResponse({});
  });
  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getAllByRole("button", { name: /^Log in$/i }).at(-1)!);

  await waitFor(() => expect(screen.getByRole("heading", { name: /Operational control room/i })).toBeInTheDocument());
  expect(screen.getByText(/identity, access requests, provider reviews/i)).toBeInTheDocument();
});

test("signup submits a pending provider access request and does not create a session", async () => {
  const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.includes("/providers")) return jsonResponse({ items: [{ provider_id: "999999", utbildningsanordnare: "Example Provider", total_applications: 25, approved_applications: 12, first_year: 2020, last_year: 2025 }], total: 1, limit: 50, offset: 0 });
    if (url.includes("/auth/registration-requests")) return jsonResponse({ id: "r1", requested_username: "new-provider", display_name: "New Provider", email: null, provider_id: "999999", requested_role: "provider", organization_name: "Example Provider", message: "Please approve", status: "pending", created_at: "2030-01-01T00:00:00Z", reviewed_by_user_id: null, reviewed_at: null, review_notes: null, created_user_id: null }, 201);
    return jsonResponse({});
  });
  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /Request provider access/i }));
  await user.type(screen.getByLabelText(/Username/i), "new-provider");
  await user.type(screen.getByLabelText(/Display name/i), "New Provider");
  await user.type(screen.getByLabelText(/^Password/i), "NewProvider1!");
  await user.type(screen.getByLabelText(/Provider organization search/i), "Example");
  await waitFor(() => expect(screen.getByRole("button", { name: /Example Provider/i })).toBeInTheDocument());
  await user.click(screen.getByRole("button", { name: /Example Provider/i }));
  await user.type(screen.getByLabelText(/Reason/i), "Please approve");
  await user.click(screen.getByRole("button", { name: /Submit access request for admin review/i }));

  await waitFor(() => expect(screen.getByRole("heading", { name: /Admin approval is required/i })).toBeInTheDocument());
  expect(sessionStorage.getItem("part3.sessionToken")).toBeNull();
  expect(fetchSpy).toHaveBeenCalledWith(expect.stringContaining("/auth/registration-requests"), expect.objectContaining({ method: "POST" }));
});
