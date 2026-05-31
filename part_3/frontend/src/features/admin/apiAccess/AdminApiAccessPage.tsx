import { FormEvent, useEffect, useMemo, useState } from "react";
import { createApiKey, listApiKeys, revokeApiKey } from "@/api/apiKeys";
import type { ApiKeyMetadata } from "@/api/types";
import { ConfirmButton } from "@/components/shared/ConfirmButton";
import { EmptyState, ErrorPanel, LoadingState } from "@/components/shared/Feedback";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export function AdminApiAccessPage() {
  const [keys, setKeys] = useState<ApiKeyMetadata[]>([]);
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState<unknown>(null);
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [name, setName] = useState("Local export client");

  async function load() {
    setStatus("loading");
    try {
      setKeys(await listApiKeys());
      setStatus("success");
    } catch (err) {
      setError(err);
      setStatus("error");
    }
  }

  useEffect(() => { void load(); }, []);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const result = await createApiKey({
        name: name.trim(),
        description: "Created from admin workspace",
        scopes: ["export:read"],
        expires_in_days: 30,
      });
      setCreatedKey(result.api_key);
      await load();
    } catch (err) {
      setError(err);
    }
  }

  const exampleKey = createdKey ?? "<paste-created-api-key-here>";
  const curlExample = useMemo(() => {
    return `curl.exe -H "X-API-Key: ${exampleKey}" "${API_BASE_URL}/export/applications?year=2024&decision=approved" -o applications_export.csv`;
  }, [exampleKey]);

  return (
    <div className="page-stack api-access-page">
      <section className="panel api-access-hero">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Machine access</p>
            <h2>Export API keys</h2>
            <p className="muted">Create scoped keys for scripts and external tools that need CSV exports. These keys are not used for browser login.</p>
          </div>
          <div className="api-boundary-card">
            <strong>Boundary</strong>
            <span>People sign in with browser sessions.</span>
            <span>Automated clients send <code>X-API-Key</code>.</span>
          </div>
        </div>

        <form className="api-key-form" onSubmit={onCreate}>
          <label className="field">Client name
            <input value={name} onChange={(event) => setName(event.target.value)} required />
          </label>
          <button className="button primary" type="submit">Create export API key</button>
        </form>

        {createdKey && (
          <div className="api-key-reveal">
            <div>
              <p className="eyebrow">Copy once</p>
              <strong>New API key created</strong>
              <p>This full key is shown only now. Store it in the script or tool that will call the export endpoint.</p>
            </div>
            <code>{createdKey}</code>
          </div>
        )}
        {error !== null && <ErrorPanel error={error} />}
      </section>

      <section className="panel api-usage-panel">
        <div className="section-heading compact">
          <div>
            <p className="eyebrow">How to use</p>
            <h2>CSV export client example</h2>
          </div>
        </div>
        <div className="usage-grid">
          <article>
            <span>Endpoint</span>
            <strong>/export/applications</strong>
            <p>Downloads filtered historical MYH application records as CSV.</p>
          </article>
          <article>
            <span>Required header</span>
            <strong>X-API-Key</strong>
            <p>Use the API key value from the green box after creation.</p>
          </article>
          <article>
            <span>Scope</span>
            <strong>export:read</strong>
            <p>This key cannot open the admin panel or provider workspace.</p>
          </article>
        </div>
        <pre className="command-card"><code>{curlExample}</code></pre>
      </section>

      <section className="panel table-panel api-key-list-panel">
        <div className="section-heading compact">
          <div>
            <p className="eyebrow">Inventory</p>
            <h2>Created API keys</h2>
          </div>
        </div>
        {status === "loading" && <LoadingState text="Loading API key metadata..." />}
        {status === "success" && keys.length === 0 && <EmptyState title="No API keys" text="Create a scoped key for machine exports." />}
        {status === "success" && keys.length > 0 && (
          <table className="records-table api-keys-table">
            <thead><tr><th>Name</th><th>Prefix</th><th>Scopes</th><th>Status</th><th>Created</th><th>Actions</th></tr></thead>
            <tbody>{keys.map((key) => (
              <tr key={key.id}>
                <td><strong>{key.name}</strong><span>{key.description ?? ""}</span></td>
                <td><code>{key.key_prefix}</code></td>
                <td>{key.scopes.join(", ")}</td>
                <td><span className={key.is_active ? "status-dot-label success" : "status-dot-label muted"}>{key.is_active ? "Active" : "Revoked"}</span></td>
                <td>{new Date(key.created_at).toLocaleDateString("sv-SE")}</td>
                <td>
                  {key.is_active && (
                    <ConfirmButton
                      confirmText={`Revoke API key “${key.name}”?`}
                      title="Revoke machine access"
                      detailText="The key will stop working for export clients. Browser login and user accounts are not affected."
                      confirmLabel="Revoke key"
                      danger
                      onConfirm={async () => { await revokeApiKey(key.id); await load(); }}
                    >
                      Revoke
                    </ConfirmButton>
                  )}
                </td>
              </tr>
            ))}</tbody>
          </table>
        )}
      </section>
    </div>
  );
}
