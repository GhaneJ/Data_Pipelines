import { FormEvent, useEffect, useState } from "react";
import { ActiveBadge, RoleBadge } from "@/components/shared/Badges";
import { ConfirmButton } from "@/components/shared/ConfirmButton";
import { EmptyState, ErrorPanel, LoadingState } from "@/components/shared/Feedback";
import { createUser, deactivateUser, listUserSessions, listUsers, reactivateUser, resetPassword } from "@/api/adminUsers";
import type { ManagedUser, Role, SessionInfo } from "@/api/types";

const blankForm = { username: "", display_name: "", role: "provider" as Role, provider_id: "", password: "" };

export function AdminUsersPage() {
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [sessionsByUser, setSessionsByUser] = useState<Record<string, SessionInfo[]>>({});
  const [form, setForm] = useState(blankForm);
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    setStatus("loading");
    setError(null);
    try {
      const result = await listUsers({ limit: 100 });
      setUsers(result.items);
      setStatus("success");
    } catch (err) {
      setError(err);
      setStatus("error");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await createUser({
        username: form.username,
        display_name: form.display_name,
        role: form.role,
        provider_id: form.role === "provider" ? form.provider_id : null,
        password: form.password,
      });
      setForm(blankForm);
      setMessage("User created. Password was not displayed or stored in the browser.");
      await load();
    } catch (err) {
      setError(err);
    }
  }

  async function toggleActive(user: ManagedUser) {
    if (user.is_active) {
      await deactivateUser(user.id);
    } else {
      await reactivateUser(user.id);
    }
    await load();
  }

  async function reset(user: ManagedUser) {
    const newPassword = window.prompt(`Enter a new password for ${user.username}. It will not be shown again.`);
    if (!newPassword) return;
    try {
      await resetPassword(user.id, newPassword);
      setMessage(`Password reset for ${user.username}. Existing sessions were revoked.`);
      await load();
    } catch (err) {
      setError(err);
    }
  }

  async function loadSessions(user: ManagedUser) {
    const result = await listUserSessions(user.id);
    setSessionsByUser((current) => ({ ...current, [user.id]: result.items }));
  }

  return (
    <div className="page-stack">
      <section className="panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Admin panel</p>
            <h2>User management</h2>
          </div>
          <p className="muted">Create admin/provider users, soft-disable accounts, reset passwords, and inspect sessions.</p>
        </div>
        <form className="form-grid" onSubmit={onCreate} aria-label="Create user form">
          <label>Username<input value={form.username} required onChange={(event) => setForm({ ...form, username: event.target.value })} /></label>
          <label>Display name<input value={form.display_name} required onChange={(event) => setForm({ ...form, display_name: event.target.value })} /></label>
          <label>Role<select value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value as Role })}><option value="provider">Provider</option><option value="admin">Admin</option></select></label>
          {form.role === "provider" && <label>Provider ID<input value={form.provider_id} required onChange={(event) => setForm({ ...form, provider_id: event.target.value })} /></label>}
          <label>Password<input type="password" value={form.password} required minLength={8} onChange={(event) => setForm({ ...form, password: event.target.value })} /></label>
          <button className="button primary" type="submit">Create user</button>
        </form>
        {message && <div className="alert alert-success">{message}</div>}
        {error !== null && <ErrorPanel error={error} />}
      </section>

      {status === "loading" && <LoadingState text="Loading users..." />}
      {status === "success" && users.length === 0 && <EmptyState title="No users" text="Create the first managed user above." />}
      {status === "success" && users.length > 0 && (
        <section className="panel table-panel">
          <table>
            <thead><tr><th>User</th><th>Role</th><th>Provider</th><th>Status</th><th>Last login</th><th>Actions</th></tr></thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id}>
                  <td><strong>{user.username}</strong><span>{user.display_name}</span></td>
                  <td><RoleBadge role={user.role} /></td>
                  <td>{user.provider_id ?? "—"}</td>
                  <td><ActiveBadge active={user.is_active} /></td>
                  <td>{user.last_login_at ? new Date(user.last_login_at).toLocaleString() : "Never"}</td>
                  <td className="actions">
                    <ConfirmButton confirmText={`${user.is_active ? "Deactivate" : "Reactivate"} ${user.username}?`} onConfirm={() => toggleActive(user)}>{user.is_active ? "Deactivate" : "Reactivate"}</ConfirmButton>
                    <ConfirmButton confirmText={`Reset password for ${user.username}?`} onConfirm={() => reset(user)}>Reset password</ConfirmButton>
                    <button type="button" className="button secondary" onClick={() => void loadSessions(user)}>Sessions</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
      {Object.entries(sessionsByUser).map(([userId, sessions]) => (
        <section className="panel" key={userId}>
          <h3>Sessions for {users.find((user) => user.id === userId)?.username}</h3>
          {sessions.length === 0 ? <p className="muted">No sessions found.</p> : <ul className="timeline">{sessions.map((session) => <li key={session.id}>{session.is_active ? "Active" : "Inactive"} session · expires {new Date(session.expires_at).toLocaleString()}</li>)}</ul>}
        </section>
      ))}
    </div>
  );
}
