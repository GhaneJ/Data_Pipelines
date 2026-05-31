import { useEffect, useState } from "react";
import { listProviderSubmissions } from "@/api/providerSubmissions";
import { useAuth } from "@/auth/AuthContext";
import { ErrorPanel, LoadingState } from "@/components/shared/Feedback";

export function ProviderDashboardPage({ onNavigate }: { onNavigate: (path: string) => void }) {
  const { user } = useAuth();
  const [cards, setCards] = useState({ total: 0, draft: 0, needsChanges: 0, final: 0 });
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    async function load() {
      try {
        const result = await listProviderSubmissions({ limit: 100 });
        setCards({
          total: result.items.length,
          draft: result.items.filter((item) => item.status === "draft").length,
          needsChanges: result.items.filter((item) => item.status === "needs_changes").length,
          final: result.items.filter((item) => item.status === "approved" || item.status === "rejected").length,
        });
        setStatus("success");
      } catch (err) {
        setError(err);
        setStatus("error");
      }
    }
    void load();
  }, []);

  return (
    <div className="page-stack">
      <section className="hero compact"><p className="eyebrow">Provider workspace</p><h2>Welcome, {user?.display_name}</h2><p>Your provider account is approved and tied to provider ID {user?.provider_id}. The backend owns all provider data boundaries.</p></section>
      {status === "loading" && <LoadingState text="Loading provider workspace..." />}
      {error !== null && <ErrorPanel error={error} />}
      {status === "success" && <section className="summary-grid"><button className="summary-tile" onClick={() => onNavigate("/provider/submissions")}><span>Total submissions</span><strong>{cards.total}</strong><small>owned by your provider</small></button><button className="summary-tile" onClick={() => onNavigate("/provider/submissions")}><span>Editable drafts</span><strong>{cards.draft}</strong><small>drafts can be changed</small></button><button className="summary-tile" onClick={() => onNavigate("/provider/submissions")}><span>Needs changes</span><strong>{cards.needsChanges}</strong><small>admin feedback available</small></button><button className="summary-tile" onClick={() => onNavigate("/provider/submissions")}><span>Final decisions</span><strong>{cards.final}</strong><small>approved/rejected are locked</small></button></section>}
    </div>
  );
}
