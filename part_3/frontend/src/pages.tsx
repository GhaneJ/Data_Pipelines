import { FormEvent, useState } from "react";
import { submitRegistrationRequest } from "@/api/auth";
import { useAuth } from "@/auth/AuthContext";
import { ErrorPanel } from "@/components/shared/Feedback";
import { ProviderSearchSelect } from "@/components/shared/ProviderSearchSelect";

export function LoginPage({ onNavigate }: { onNavigate: (path: string) => void }) {
  const { login } = useAuth();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin-password");
  const [error, setError] = useState<unknown>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      const user = await login(username, password);
      onNavigate(user.role === "admin" ? "/admin" : "/provider");
    } catch (err) {
      setError(err);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="auth-card login-card">
      <div className="auth-visual">
        <p className="eyebrow">Enterprise workspace</p>
        <h2>Sign in to the MYH portal</h2>
        <p className="muted">Use a database-issued human session token. API keys stay reserved for machine/export access.</p>
      </div>
      <form className="form-grid single" onSubmit={onSubmit}>
        <label>Username<input value={username} autoComplete="username" required onChange={(event) => setUsername(event.target.value)} /></label>
        <label>Password<input type="password" value={password} autoComplete="current-password" required onChange={(event) => setPassword(event.target.value)} /></label>
        <button className="button primary" type="submit" disabled={isSubmitting}>{isSubmitting ? "Signing in..." : "Log in"}</button>
      </form>
      {error !== null && <ErrorPanel error={error} />}
      <div className="auth-actions">
        <button className="button secondary" type="button" onClick={() => onNavigate("/signup")}>Request provider access</button>
        <button className="button link" type="button" onClick={() => onNavigate("/data")}>Open public data explorer</button>
      </div>
    </section>
  );
}

export function SignupPage({ onNavigate }: { onNavigate: (path: string) => void }) {
  const [form, setForm] = useState({ requested_username: "", display_name: "", password: "", provider_id: "", email: "", organization_name: "", message: "" });
  const [error, setError] = useState<unknown>(null);
  const [success, setSuccess] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await submitRegistrationRequest({
        requested_username: form.requested_username,
        display_name: form.display_name,
        password: form.password,
        provider_id: form.provider_id,
        email: form.email || undefined,
        organization_name: form.organization_name || undefined,
        message: form.message || undefined,
      });
      setSuccess(true);
    } catch (err) {
      setError(err);
    }
  }

  if (success) {
    return (
      <section className="auth-card success-card">
        <p className="eyebrow">Access request submitted</p>
        <h2>Admin approval is required</h2>
        <p>Your request was saved for admin review. You are not logged in automatically, and no active account exists until an admin approves the request from the admin panel.</p>
        <button className="button primary" onClick={() => onNavigate("/login")}>Back to login</button>
      </section>
    );
  }

  return (
    <section className="auth-card wide-auth request-access-card">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Controlled access request</p>
          <h2>Request provider workspace access</h2>
        </div>
        <p className="muted">This is not self-registration. It creates a pending request that an admin reviews, approves, or rejects.</p>
      </div>
      <form className="form-grid" onSubmit={onSubmit}>
        <label>Username<input value={form.requested_username} required onChange={(event) => setForm({ ...form, requested_username: event.target.value })} /></label>
        <label>Display name<input value={form.display_name} required onChange={(event) => setForm({ ...form, display_name: event.target.value })} /></label>
        <label>Password<input type="password" value={form.password} required minLength={8} onChange={(event) => setForm({ ...form, password: event.target.value })} /></label>
        <label>Email optional<input type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} /></label>
        <ProviderSearchSelect
          value={form.provider_id}
          required
          label="Provider organization"
          onChange={(provider_id, provider) => setForm({ ...form, provider_id, organization_name: provider?.utbildningsanordnare ?? form.organization_name })}
        />
        <label>Organization note optional<input value={form.organization_name} onChange={(event) => setForm({ ...form, organization_name: event.target.value })} /></label>
        <label className="wide">Reason/message<textarea value={form.message} onChange={(event) => setForm({ ...form, message: event.target.value })} /></label>
        <button className="button primary" type="submit">Submit access request for admin review</button>
      </form>
      {error !== null && <ErrorPanel error={error} />}
      <button className="button link" type="button" onClick={() => onNavigate("/login")}>Back to login</button>
    </section>
  );
}

export function ForbiddenPage({ onNavigate }: { onNavigate: (path: string) => void }) {
  return <section className="auth-card"><p className="eyebrow">Forbidden</p><h2>Wrong role for this workspace</h2><p>Your authenticated role cannot access this route. The backend authorization dependency remains the source of truth.</p><button className="button primary" onClick={() => onNavigate("/")}>Return to home</button></section>;
}
