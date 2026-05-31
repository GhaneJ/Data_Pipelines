import { Fragment, FormEvent, useEffect, useMemo, useState } from "react";
import { ActiveBadge, RoleBadge } from "@/components/shared/Badges";
import { ConfirmButton } from "@/components/shared/ConfirmButton";
import { EmptyState, ErrorPanel, LoadingState } from "@/components/shared/Feedback";
import { ProviderSearchSelect } from "@/components/shared/ProviderSearchSelect";
import { createUser, deactivateUser, listUserSessions, listUsers, reactivateUser, resetPassword, revokeUserSession, updateUser } from "@/api/adminUsers";
import type { ManagedUser, ProviderSummary, Role, SessionInfo } from "@/api/types";
import { getPasswordPolicy, passwordPolicyMessage } from "@/auth/passwordPolicy";

type UserFormMode = "create" | "edit" | "reset";

const blankForm = {
  username: "",
  display_name: "",
  role: "provider" as Role,
  provider_id: "",
  provider_name: "",
  password: "",
};

function modeTitle(mode: UserFormMode) {
  if (mode === "edit") return "Edit managed user";
  if (mode === "reset") return "Reset user password";
  return "Create managed user";
}

function modeAction(mode: UserFormMode) {
  if (mode === "edit") return "Save changes";
  if (mode === "reset") return "Reset password";
  return "Create user";
}

export function AdminUsersPage() {
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [sessionsByUser, setSessionsByUser] = useState<Record<string, SessionInfo[]>>({});
  const [openSessionsUserId, setOpenSessionsUserId] = useState<string | null>(null);
  const [form, setForm] = useState(blankForm);
  const [formMode, setFormMode] = useState<UserFormMode>("create");
  const [selectedUser, setSelectedUser] = useState<ManagedUser | null>(null);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<"" | Role>("");
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [passwordFocused, setPasswordFocused] = useState(false);
  const requiresPassword = formMode === "create" || formMode === "reset";
  const passwordPolicy = getPasswordPolicy(form.password);
  const showPasswordPolicy = requiresPassword && (passwordFocused || form.password.length > 0);

  async function load() {
    setStatus("loading");
    setError(null);
    try {
      const result = await listUsers({ limit: 100, role: roleFilter || undefined, search: search || undefined });
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

  const userCounts = useMemo(() => {
    const providers = users.filter((user) => user.role === "provider").length;
    const admins = users.filter((user) => user.role === "admin").length;
    const inactive = users.filter((user) => !user.is_active).length;
    return { providers, admins, inactive };
  }, [users]);

  function clearForm() {
    setForm(blankForm);
    setFormMode("create");
    setSelectedUser(null);
    setPasswordFocused(false);
    setError(null);
  }

  function startEdit(user: ManagedUser) {
    setFormMode("edit");
    setSelectedUser(user);
    setForm({
      username: user.username,
      display_name: user.display_name,
      role: user.role,
      provider_id: user.provider_id ?? "",
      provider_name: "",
      password: "",
    });
    setMessage(null);
    setError(null);
    document.getElementById("managed-user-form")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function startReset(user: ManagedUser) {
    setFormMode("reset");
    setSelectedUser(user);
    setForm({
      username: user.username,
      display_name: user.display_name,
      role: user.role,
      provider_id: user.provider_id ?? "",
      provider_name: "",
      password: "",
    });
    setMessage(null);
    setError(null);
    document.getElementById("managed-user-form")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setMessage(null);

    if (requiresPassword && !passwordPolicy.isValid) {
      setError(new Error(passwordPolicyMessage()));
      return;
    }
    if (form.role === "provider" && !form.provider_id) {
      setError(new Error("Select a provider organization."));
      return;
    }

    try {
      if (formMode === "create") {
        await createUser({
          username: form.username.trim(),
          display_name: form.display_name.trim(),
          role: form.role,
          provider_id: form.role === "provider" ? form.provider_id : null,
          password: form.password,
        });
        setMessage("User created successfully.");
      } else if (formMode === "edit" && selectedUser) {
        await updateUser(selectedUser.id, {
          display_name: form.display_name.trim(),
          role: form.role,
          provider_id: form.role === "provider" ? form.provider_id : null,
        });
        setMessage("User updated successfully.");
      } else if (formMode === "reset" && selectedUser) {
        await resetPassword(selectedUser.id, form.password);
        setMessage("Password reset successfully.");
      }
      clearForm();
      await load();
    } catch (err) {
      setError(err);
    }
  }

  async function toggleActive(user: ManagedUser) {
    if (user.is_active) {
      await deactivateUser(user.id);
      setMessage("User deactivated successfully.");
    } else {
      await reactivateUser(user.id);
      setMessage("User reactivated successfully.");
    }
    await load();
  }

  async function loadSessions(user: ManagedUser) {
    if (openSessionsUserId === user.id) {
      setOpenSessionsUserId(null);
      return;
    }
    setError(null);
    try {
      const result = await listUserSessions(user.id);
      setSessionsByUser((current) => ({ ...current, [user.id]: result.items }));
      setOpenSessionsUserId(user.id);
    } catch (err) {
      setError(err);
    }
  }

  async function revokeSession(user: ManagedUser, session: SessionInfo) {
    setError(null);
    try {
      await revokeUserSession(user.id, session.id);
      setMessage("Session revoked successfully.");
      const result = await listUserSessions(user.id);
      setSessionsByUser((current) => ({ ...current, [user.id]: result.items }));
    } catch (err) {
      setError(err);
    }
  }

  function onProviderSelected(provider_id: string, provider: ProviderSummary | null) {
    setForm((current) => ({ ...current, provider_id, provider_name: provider?.utbildningsanordnare ?? "" }));
  }

  return (
    <div className="page-stack admin-users-page">
      <section className="hero admin-hero">
        <div>
          <p className="eyebrow">Admin control center</p>
          <h2>User management</h2>
          <p>Create, edit, deactivate, reactivate, reset credentials, and inspect account sessions from one controlled workspace.</p>
        </div>
        <div className="mini-metric-grid">
          <article><span>Admins</span><strong>{userCounts.admins}</strong></article>
          <article><span>Providers</span><strong>{userCounts.providers}</strong></article>
          <article><span>Inactive</span><strong>{userCounts.inactive}</strong></article>
        </div>
      </section>

      <section id="managed-user-form" className={`panel create-user-panel elevated-panel mode-${formMode}`}>
        <div className="section-heading user-form-heading">
          <div>
            <p className="eyebrow">Managed access</p>
            <h2>{modeTitle(formMode)}</h2>
            {selectedUser && <p className="muted">Selected account: <strong>{selectedUser.username}</strong></p>}
          </div>
          {formMode !== "create" && <button type="button" className="button secondary" onClick={clearForm}>Cancel</button>}
        </div>

        <div className="create-user-layout">
          <form className="user-create-grid" onSubmit={onSubmit} aria-label="Managed user form">
            <label className="field">Username
              <input
                value={form.username}
                required
                disabled={formMode !== "create"}
                onChange={(event) => setForm({ ...form, username: event.target.value })}
              />
            </label>
            <label className="field">Display name
              <input
                value={form.display_name}
                required
                disabled={formMode === "reset"}
                onChange={(event) => setForm({ ...form, display_name: event.target.value })}
              />
            </label>
            <label className="field">Role
              <select
                value={form.role}
                disabled={formMode === "reset"}
                onChange={(event) => setForm({ ...form, role: event.target.value as Role, provider_id: "", provider_name: "" })}
              >
                <option value="provider">Provider</option>
                <option value="admin">Admin</option>
              </select>
            </label>
            {requiresPassword && (
              <label className="field password-field">{formMode === "reset" ? "New password" : "Password"}
                <input
                  type="password"
                  value={form.password}
                  required
                  minLength={10}
                  onFocus={() => setPasswordFocused(true)}
                  onBlur={() => setPasswordFocused(false)}
                  onChange={(event) => setForm({ ...form, password: event.target.value })}
                />
                {showPasswordPolicy && (
                  <div className="password-policy inline-password-policy" aria-live="polite">
                    {passwordPolicy.checks.map((check) => <span key={check.label} className={check.passed ? "passed" : ""}>{check.passed ? "✓" : "○"} {check.label}</span>)}
                  </div>
                )}
              </label>
            )}
            {form.role === "provider" && formMode !== "reset" && (
              <ProviderSearchSelect
                value={form.provider_id}
                required
                label="Provider organization"
                helperText="Search organization name and select one result."
                onChange={onProviderSelected}
              />
            )}
            {form.role === "provider" && formMode === "reset" && form.provider_id && (
              <div className="selected-provider-card readonly-selection">
                <strong>Provider ID {form.provider_id}</strong>
                <span>Provider ownership is unchanged during password reset.</span>
              </div>
            )}
            <div className="form-actions-row">
              <button className="button primary" type="submit" disabled={requiresPassword && !passwordPolicy.isValid}>{modeAction(formMode)}</button>
              {formMode !== "create" && <button className="button secondary" type="button" onClick={clearForm}>Cancel</button>}
            </div>
          </form>
          <aside className="policy-card" aria-label="Access policy">
            <span>Access policy</span>
            <strong>Controlled account administration</strong>
            <p>New accounts, safe profile edits, role changes, provider ownership, and password resets are handled from this managed form.</p>
          </aside>
        </div>
        {message && <div className="alert alert-success compact-alert">{message}</div>}
        {error !== null && <ErrorPanel error={error} />}
      </section>

      <section className="panel users-filter-panel">
        <div className="section-heading compact">
          <div>
            <p className="eyebrow">Directory</p>
            <h2>Managed users</h2>
          </div>
          <form className="users-filter-form" onSubmit={(event) => { event.preventDefault(); void load(); }}>
            <input value={search} placeholder="Search username or display name..." onChange={(event) => setSearch(event.target.value)} />
            <select value={roleFilter} onChange={(event) => setRoleFilter(event.target.value as "" | Role)}>
              <option value="">All roles</option>
              <option value="admin">Admin</option>
              <option value="provider">Provider</option>
            </select>
            <button className="button secondary" type="submit">Filter</button>
          </form>
        </div>
      </section>

      {status === "loading" && <LoadingState text="Loading users..." />}
      {status === "success" && users.length === 0 && <EmptyState title="No users" text="Create the first managed user above." />}
      {status === "success" && users.length > 0 && (
        <section className="panel table-panel users-table-panel">
          <table>
            <thead><tr><th>User</th><th>Role</th><th>Provider ownership</th><th>Status</th><th>Last login</th><th>Actions</th></tr></thead>
            <tbody>
              {users.map((user) => (
                <Fragment key={user.id}>
                  <tr>
                    <td><strong>{user.username}</strong><span>{user.display_name}</span></td>
                    <td><RoleBadge role={user.role} /></td>
                    <td>
                      {user.provider_id ? <code>{user.provider_id}</code> : "—"}
                      <span>{user.role === "provider" ? "Provider workspace owner" : "Admin account"}</span>
                    </td>
                    <td><ActiveBadge active={user.is_active} /></td>
                    <td>{user.last_login_at ? new Date(user.last_login_at).toLocaleString() : "Never"}</td>
                    <td className="actions action-cluster">
                      <button type="button" className="button secondary" onClick={() => startEdit(user)}>Edit</button>
                      <button type="button" className="button secondary" onClick={() => startReset(user)}>Reset password</button>
                      <ConfirmButton confirmText={`${user.is_active ? "Deactivate" : "Reactivate"} ${user.username}?`} onConfirm={() => toggleActive(user)}>{user.is_active ? "Deactivate" : "Reactivate"}</ConfirmButton>
                      <button type="button" className="button secondary" onClick={() => void loadSessions(user)}>{openSessionsUserId === user.id ? "Hide sessions" : "View sessions"}</button>
                    </td>
                  </tr>
                  {openSessionsUserId === user.id && (
                    <tr className="expanded-row">
                      <td colSpan={6}>
                        <div className="session-panel-inline">
                          <div className="section-heading compact">
                            <div>
                              <p className="eyebrow">Session management</p>
                              <h3>{user.username}</h3>
                            </div>
                          </div>
                          {(sessionsByUser[user.id] ?? []).length === 0 ? (
                            <p className="muted">No sessions found for this user.</p>
                          ) : (
                            <ul className="session-list">
                              {(sessionsByUser[user.id] ?? []).map((session) => (
                                <li key={session.id}>
                                  <div>
                                    <strong>{session.is_active ? "Active session" : "Inactive session"}</strong>
                                    <span>Created {new Date(session.created_at).toLocaleString()} · expires {new Date(session.expires_at).toLocaleString()}</span>
                                  </div>
                                  {session.is_active && <ConfirmButton confirmText="Revoke this user session?" onConfirm={() => revokeSession(user, session)}>Revoke</ConfirmButton>}
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </section>
      )}

    </div>
  );
}
