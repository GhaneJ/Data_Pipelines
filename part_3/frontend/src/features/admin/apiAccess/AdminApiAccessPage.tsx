import { FormEvent, useEffect, useState } from "react";
import { createApiKey, listApiKeys, revokeApiKey } from "@/api/apiKeys";
import type { ApiKeyMetadata } from "@/api/types";
import { ConfirmButton } from "@/components/shared/ConfirmButton";
import { EmptyState, ErrorPanel, LoadingState } from "@/components/shared/Feedback";

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
      const result = await createApiKey({ name, description: "Created from admin workspace", scopes: ["export:read"], expires_in_days: 30 });
      setCreatedKey(result.api_key);
      await load();
    } catch (err) {
      setError(err);
    }
  }

  return (
    <div className="page-stack">
      <section className="panel">
        <div className="section-heading"><div><p className="eyebrow">Machine access</p><h2>API access boundary</h2></div><p className="muted">Human users use bearer sessions. API keys use X-API-Key only for scoped machine endpoints such as /export/applications.</p></div>
        <form className="inline-form" onSubmit={onCreate}><input value={name} onChange={(event) => setName(event.target.value)} required /><button className="button primary" type="submit">Create export API key</button></form>
        {createdKey && <div className="alert alert-success"><strong>Copy this API key now:</strong><code>{createdKey}</code><span>It will not be shown again and is not used for React login.</span></div>}
        {error !== null && <ErrorPanel error={error} />}
      </section>
      <section className="panel table-panel">
        {status === "loading" && <LoadingState text="Loading API key metadata..." />}
        {status === "success" && keys.length === 0 && <EmptyState title="No API keys" text="Create a scoped key for machine exports." />}
        {status === "success" && keys.length > 0 && <table><thead><tr><th>Name</th><th>Prefix</th><th>Scopes</th><th>Status</th><th>Actions</th></tr></thead><tbody>{keys.map((key) => <tr key={key.id}><td><strong>{key.name}</strong><span>{key.description ?? ""}</span></td><td><code>{key.key_prefix}</code></td><td>{key.scopes.join(", ")}</td><td>{key.is_active ? "active" : "revoked"}</td><td>{key.is_active && <ConfirmButton confirmText={`Revoke ${key.name}?`} onConfirm={async () => { await revokeApiKey(key.id); await load(); }}>Revoke</ConfirmButton>}</td></tr>)}</tbody></table>}
      </section>
    </div>
  );
}
