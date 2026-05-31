import { useEffect, useMemo, useState } from "react";
import { AuthProvider, useAuth } from "@/auth/AuthContext";
import { AppShell } from "@/layouts/AppShell";
import { AdminDashboardPage } from "@/features/admin/AdminDashboardPage";
import { AdminApiAccessPage } from "@/features/admin/apiAccess/AdminApiAccessPage";
import { AdminReviewsPage } from "@/features/admin/reviews/AdminReviewsPage";
import { AdminSignupRequestsPage } from "@/features/admin/signupRequests/AdminSignupRequestsPage";
import { AdminUsersPage } from "@/features/admin/users/AdminUsersPage";
import { DataExplorerPage } from "@/features/dataExplorer/DataExplorerPage";
import { ProviderDashboardPage } from "@/features/provider/ProviderDashboardPage";
import { ProviderWorkspacePage } from "@/features/provider/ProviderWorkspacePage";
import { ForbiddenPage, LoginPage, SignupPage } from "@/pages";
import { LoadingState } from "@/components/shared/Feedback";
import "@/styles.css";

function normalizePath(path: string) {
  return path === "/" ? "/" : path.replace(/\/$/, "");
}

function useRoute() {
  const [path, setPath] = useState(normalizePath(window.location.pathname));

  useEffect(() => {
    const onPopState = () => setPath(normalizePath(window.location.pathname));
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  function navigate(nextPath: string) {
    const normalized = normalizePath(nextPath);
    window.history.pushState({}, "", normalized);
    setPath(normalized);
  }

  return { path, navigate };
}

function ProtectedRoute({ role, children, onNavigate }: { role: "admin" | "provider"; children: React.ReactNode; onNavigate: (path: string) => void }) {
  const { user, status } = useAuth();
  if (status === "checking") return <LoadingState text="Checking session..." />;
  if (!user) return <LoginPage onNavigate={onNavigate} />;
  if (user.role !== role) return <ForbiddenPage onNavigate={onNavigate} />;
  return <>{children}</>;
}

function HomeRedirect({ onNavigate }: { onNavigate: (path: string) => void }) {
  const { user, status } = useAuth();
  useEffect(() => {
    if (status === "authenticated" && user?.role === "admin") onNavigate("/admin");
    else if (status === "authenticated" && user?.role === "provider") onNavigate("/provider");
    else if (status === "anonymous") onNavigate("/login");
  }, [status, user, onNavigate]);
  return <LoadingState text="Opening workspace..." />;
}

function RoutedWorkspace() {
  const { path, navigate } = useRoute();
  const main = useMemo(() => {
    if (path === "/" ) return <HomeRedirect onNavigate={navigate} />;
    if (path === "/login") return <LoginPage onNavigate={navigate} />;
    if (path === "/signup") return <SignupPage onNavigate={navigate} />;
    if (path === "/data" || path === "/data/applications" || path === "/data/stats") return <DataExplorerPage />;
    if (path === "/admin") return <ProtectedRoute role="admin" onNavigate={navigate}><AdminDashboardPage onNavigate={navigate} /></ProtectedRoute>;
    if (path.startsWith("/admin/users")) return <ProtectedRoute role="admin" onNavigate={navigate}><AdminUsersPage /></ProtectedRoute>;
    if (path.startsWith("/admin/signup-requests")) return <ProtectedRoute role="admin" onNavigate={navigate}><AdminSignupRequestsPage /></ProtectedRoute>;
    if (path.startsWith("/admin/provider-submissions")) return <ProtectedRoute role="admin" onNavigate={navigate}><AdminReviewsPage /></ProtectedRoute>;
    if (path === "/admin/api-access") return <ProtectedRoute role="admin" onNavigate={navigate}><AdminApiAccessPage /></ProtectedRoute>;
    if (path === "/provider") return <ProtectedRoute role="provider" onNavigate={navigate}><ProviderDashboardPage onNavigate={navigate} /></ProtectedRoute>;
    if (path.startsWith("/provider/submissions")) return <ProtectedRoute role="provider" onNavigate={navigate}><ProviderWorkspacePage /></ProtectedRoute>;
    return <section className="auth-card"><p className="eyebrow">Not found</p><h2>Page not found</h2><button className="button primary" onClick={() => navigate("/")}>Return home</button></section>;
  }, [path, navigate]);

  return <AppShell currentPath={path} onNavigate={navigate}>{main}</AppShell>;
}

function App() {
  return <AuthProvider><RoutedWorkspace /></AuthProvider>;
}

export default App;
