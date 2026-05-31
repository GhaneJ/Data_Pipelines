import { useAuth } from "@/auth/AuthContext";

export interface NavTarget {
  path: string;
  label: string;
  eyebrow?: string;
  roles?: string[];
}

const NAV_TARGETS: NavTarget[] = [
  { path: "/data", label: "Open data", eyebrow: "Public" },
  { path: "/data/stats", label: "Insights", eyebrow: "Public" },
  { path: "/data/applications", label: "Archive", eyebrow: "Public" },
  { path: "/admin", label: "Dashboard", eyebrow: "Admin", roles: ["admin"] },
  { path: "/admin/users", label: "Users", eyebrow: "Access", roles: ["admin"] },
  { path: "/admin/signup-requests", label: "Access requests", eyebrow: "Approval", roles: ["admin"] },
  { path: "/admin/provider-submissions", label: "Review queue", eyebrow: "Workflow", roles: ["admin"] },
  { path: "/admin/api-access", label: "Machine access", eyebrow: "API", roles: ["admin"] },
  { path: "/admin/operations", label: "Operations", eyebrow: "Refresh", roles: ["admin"] },
  { path: "/provider", label: "Workspace", eyebrow: "Provider", roles: ["provider"] },
  { path: "/provider/submissions", label: "My submissions", eyebrow: "Register", roles: ["provider"] },
];

function roleLabel(role: string | undefined) {
  if (role === "admin") return "Administrator";
  if (role === "provider") return "Provider";
  return "Public visitor";
}

export function AppShell({ currentPath, onNavigate, children }: { currentPath: string; onNavigate: (path: string) => void; children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const targets = NAV_TARGETS.filter((target) => !target.roles || (user && target.roles.includes(user.role)));

  return (
    <div className="portal-shell">
      <aside className="sidebar">
        <button className="brand-card" type="button" onClick={() => onNavigate(user?.role === "admin" ? "/admin" : user?.role === "provider" ? "/provider" : "/data")}>
          <span className="brand-mark">MYH</span>
          <div>
            <strong>Applications Portal</strong>
            <span>Data service workspace</span>
          </div>
        </button>
        <nav aria-label="Workspace navigation">
          {targets.map((target) => (
            <button
              key={target.path}
              type="button"
              className={currentPath === target.path || (target.path !== "/data" && currentPath.startsWith(`${target.path}/`)) ? "nav-link active" : "nav-link"}
              onClick={() => onNavigate(target.path)}
            >
              {target.eyebrow && <small>{target.eyebrow}</small>}
              <span>{target.label}</span>
            </button>
          ))}
        </nav>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">Data Pipeline Project — Part 3</p>
            <h1>MYH Applications Portal</h1>
          </div>
          <div className="user-card">
            {user ? (
              <>
                <div className="user-card-copy">
                  <strong>{user.display_name || user.username}</strong>
                  <span>{user.username} · {roleLabel(user.role)}</span>
                </div>
                <button type="button" className="button ghost" onClick={() => void logout().then(() => onNavigate("/login"))}>
                  Log out
                </button>
              </>
            ) : (
              <>
                <div className="user-card-copy">
                  <strong>Public visitor</strong>
                  <span>Read-only explorer</span>
                </div>
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
