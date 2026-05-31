import { useAuth } from "@/auth/AuthContext";

export interface NavTarget {
  path: string;
  label: string;
  roles?: string[];
}

const NAV_TARGETS: NavTarget[] = [
  { path: "/data", label: "Public data" },
  { path: "/admin", label: "Admin dashboard", roles: ["admin"] },
  { path: "/admin/users", label: "Users", roles: ["admin"] },
  { path: "/admin/signup-requests", label: "Signup requests", roles: ["admin"] },
  { path: "/admin/provider-submissions", label: "Review queue", roles: ["admin"] },
  { path: "/admin/api-access", label: "API access", roles: ["admin"] },
  { path: "/provider", label: "Provider workspace", roles: ["provider"] },
  { path: "/provider/submissions", label: "My submissions", roles: ["provider"] },
];

export function AppShell({ currentPath, onNavigate, children }: { currentPath: string; onNavigate: (path: string) => void; children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const targets = NAV_TARGETS.filter((target) => !target.roles || (user && target.roles.includes(user.role)));

  return (
    <div className="portal-shell">
      <aside className="sidebar">
        <div className="brand-card">
          <span className="brand-mark">MYH</span>
          <div>
            <strong>Applications Portal</strong>
            <span>Part 3 authenticated workspace</span>
          </div>
        </div>
        <nav aria-label="Workspace navigation">
          {targets.map((target) => (
            <button
              key={target.path}
              type="button"
              className={currentPath === target.path || currentPath.startsWith(`${target.path}/`) ? "nav-link active" : "nav-link"}
              onClick={() => onNavigate(target.path)}
            >
              {target.label}
            </button>
          ))}
        </nav>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">Data Pipeline Project — Part 3</p>
            <h1>Authenticated React Workspace</h1>
          </div>
          <div className="user-card">
            {user ? (
              <>
                <span>{user.display_name}</span>
                <strong>{user.role}{user.provider_id ? ` · provider ${user.provider_id}` : ""}</strong>
                <button type="button" className="button ghost" onClick={() => void logout().then(() => onNavigate("/login"))}>
                  Log out
                </button>
              </>
            ) : (
              <>
                <span>Public visitor</span>
                <button type="button" className="button ghost" onClick={() => onNavigate("/login")}>
                  Log in
                </button>
              </>
            )}
          </div>
        </header>
        {children}
      </div>
    </div>
  );
}
