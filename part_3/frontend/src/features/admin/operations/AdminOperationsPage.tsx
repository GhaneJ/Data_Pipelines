import { useEffect, useMemo, useState } from "react";
import { downloadSourceFile, importSourceFile, listAdminNotifications, listRefreshRuns, listSourceFiles, markNotificationRead, resolveNotification, runSourceCheck, getSourceMonitorStatus } from "@/api/sourceOperations";
import type { AdminNotification, RefreshRun, SourceFile, SourceMonitorStatus } from "@/api/types";
import { ConfirmButton } from "@/components/shared/ConfirmButton";
import { EmptyState, ErrorPanel, LoadingState } from "@/components/shared/Feedback";

const PAGE_LIMIT = 25;

function formatDate(value: string | null | undefined) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("sv-SE", { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
}

function statusClass(status: string) {
  if (["success", "known", "imported", "resolved", "read"].includes(status)) return "status-pill ok";
  if (["failed", "changed", "error"].includes(status)) return "status-pill warning";
  return "status-pill neutral";
}

function statusText(status: string) {
  return status.replace(/_/g, " ");
}

function monitorMode(status: SourceMonitorStatus | null) {
  if (!status) return "Checking";
  if (!status.monitor_enabled) return "Manual checks only";
  return status.auto_import_enabled ? "Scheduled check and auto-import" : "Scheduled check and notify";
}

function SourceFileTable({ files, onDownload, onImport, onSelect }: { files: SourceFile[]; onDownload: (id: string) => Promise<void>; onImport: (id: string) => Promise<void>; onSelect: (file: SourceFile) => void }) {
  if (files.length === 0) return <EmptyState title="No MYH source files recorded" text="Run Check MYH now to discover official downloadable source files." />;
  return (
    <div className="table-scroll operations-table-wrap">
      <table className="data-table operations-table">
        <thead>
          <tr>
            <th>Source file</th>
            <th>Year</th>
            <th>Status</th>
            <th>Last seen</th>
            <th>SHA256</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {files.map((file) => (
            <tr key={file.id}>
              <td>
                <button className="table-link" type="button" onClick={() => onSelect(file)}>{file.file_name}</button>
                <small>{file.file_type.toUpperCase()} · {file.downloaded_path ?? "not downloaded"}</small>
              </td>
              <td>{file.source_year ?? "—"}</td>
              <td><span className={statusClass(file.status)}>{statusText(file.status)}</span></td>
              <td>{formatDate(file.last_seen_at)}</td>
              <td><code>{file.last_sha256 ? `${file.last_sha256.slice(0, 10)}…` : "—"}</code></td>
              <td>
                <div className="button-row compact-actions">
                  <button className="button secondary" type="button" onClick={() => void onDownload(file.id)}>Download</button>
                  <ConfirmButton
                    className="button primary"
                    title="Import official MYH source file"
                    confirmText={`Import ${file.file_name} into the official historical applications table?`}
                    detailText="The backend validates Tabell 3, replaces only affected official source years, and rolls back on failure. Provider submissions and admin workflows are not touched."
                    confirmLabel="Import official file"
                    onConfirm={() => onImport(file.id)}
                  >
                    Import
                  </ConfirmButton>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function NotificationList({ notifications, onRead, onResolve }: { notifications: AdminNotification[]; onRead: (id: string) => Promise<void>; onResolve: (id: string) => Promise<void> }) {
  if (notifications.length === 0) return <EmptyState title="No notifications" text="New source files, changed downloads, and refresh results will appear here." />;
  return (
    <div className="notification-stack">
      {notifications.map((notification) => (
        <article className={`notification-card ${notification.severity}`} key={notification.id}>
          <div>
            <p className="eyebrow">{notification.notification_type.replace(/_/g, " ")}</p>
            <h3>{notification.title}</h3>
            <p>{notification.message}</p>
            <small>{formatDate(notification.created_at)}</small>
          </div>
          <div className="notification-actions">
            <span className={statusClass(notification.status)}>{statusText(notification.status)}</span>
            {notification.status === "unread" && <button className="button secondary" type="button" onClick={() => void onRead(notification.id)}>Mark read</button>}
            {notification.status !== "resolved" && <button className="button ghost" type="button" onClick={() => void onResolve(notification.id)}>Resolve</button>}
          </div>
        </article>
      ))}
    </div>
  );
}

function RefreshRunTable({ runs, onSelect }: { runs: RefreshRun[]; onSelect: (run: RefreshRun) => void }) {
  if (runs.length === 0) return <EmptyState title="No refresh runs yet" text="Imports and compatibility refreshes will be listed here." />;
  return (
    <div className="table-scroll operations-table-wrap">
      <table className="data-table operations-table">
        <thead>
          <tr>
            <th>Run</th>
            <th>Status</th>
            <th>Mode</th>
            <th>Rows</th>
            <th>Affected years</th>
            <th>Finished</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.id}>
              <td><button className="table-link" type="button" onClick={() => onSelect(run)}>{run.id.slice(0, 8)}…</button></td>
              <td><span className={statusClass(run.status)}>{statusText(run.status)}</span></td>
              <td>{statusText(run.mode)}</td>
              <td>{run.rows_imported ?? "—"}</td>
              <td>{run.affected_years ?? "—"}</td>
              <td>{formatDate(run.finished_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function AdminOperationsPage() {
  const [status, setStatus] = useState<SourceMonitorStatus | null>(null);
  const [files, setFiles] = useState<SourceFile[]>([]);
  const [notifications, setNotifications] = useState<AdminNotification[]>([]);
  const [runs, setRuns] = useState<RefreshRun[]>([]);
  const [selectedFile, setSelectedFile] = useState<SourceFile | null>(null);
  const [selectedRun, setSelectedRun] = useState<RefreshRun | null>(null);
  const [loadState, setLoadState] = useState("loading");
  const [error, setError] = useState<unknown>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  async function load() {
    setLoadState("loading");
    setError(null);
    try {
      const [statusResult, sourceFiles, notificationResult, refreshRuns] = await Promise.all([
        getSourceMonitorStatus(),
        listSourceFiles({ limit: PAGE_LIMIT }),
        listAdminNotifications({ limit: PAGE_LIMIT }),
        listRefreshRuns({ limit: PAGE_LIMIT }),
      ]);
      setStatus(statusResult);
      setFiles(sourceFiles.items);
      setNotifications(notificationResult.items);
      setRuns(refreshRuns.items);
      setLoadState("success");
    } catch (err) {
      setError(err);
      setLoadState("error");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function handleCheckNow() {
    setActionMessage(null);
    setError(null);
    try {
      const result = await runSourceCheck();
      setActionMessage(result.message);
      await load();
    } catch (err) {
      setError(err);
    }
  }

  async function handleDownload(sourceFileId: string) {
    setActionMessage(null);
    setError(null);
    try {
      const result = await downloadSourceFile(sourceFileId);
      setActionMessage(`${result.file_name} downloaded (${result.sha256.slice(0, 12)}…).`);
      await load();
    } catch (err) {
      setError(err);
    }
  }

  async function handleImport(sourceFileId: string) {
    setActionMessage(null);
    setError(null);
    try {
      const result = await importSourceFile(sourceFileId);
      setActionMessage(`Refresh ${result.status}: ${result.rows_imported ?? 0} row(s) imported for ${result.affected_years ?? "selected years"}.`);
      await load();
    } catch (err) {
      setError(err);
    }
  }

  async function handleRead(notificationId: string) {
    await markNotificationRead(notificationId);
    await load();
  }

  async function handleResolve(notificationId: string) {
    await resolveNotification(notificationId);
    await load();
  }

  const latestCheck = useMemo(() => status?.last_check ?? null, [status]);
  const latestRun = useMemo(() => status?.latest_refresh_run ?? null, [status]);

  return (
    <div className="page-stack admin-operations-page">
      <section className="hero-panel operations-hero">
        <div>
          <p className="eyebrow">Admin operations</p>
          <h2>MYH source monitoring and safe refresh pipeline</h2>
          <p className="muted">Discover official MYH result files, notify admins, download/hash source workbooks, validate Tabell 3, and import only affected official source years.</p>
          <div className="button-row">
            <button className="button primary" type="button" onClick={() => void handleCheckNow()}>Check MYH now</button>
            <button className="button secondary" type="button" onClick={() => void load()}>Refresh page</button>
          </div>
        </div>
        <div className="system-status-card refined-status-card">
          <span>Monitor mode</span>
          <strong>{monitorMode(status)}</strong>
          <small>{status?.source_url ?? "Configured by backend"}</small>
        </div>
      </section>

      {loadState === "loading" && <LoadingState text="Loading source operations..." />}
      {error !== null && <ErrorPanel error={error} />}
      {actionMessage && <div className="alert alert-success"><strong>{actionMessage}</strong></div>}

      {loadState === "success" && status && (
        <>
          <section className="admin-insight-grid refined-insight-grid operations-summary-grid">
            <article className="insight-card static-card">
              <span>Known source files</span>
              <strong>{status.known_source_files}</strong>
              <small>{status.source_url}</small>
            </article>
            <article className="insight-card static-card">
              <span>Unread notifications</span>
              <strong>{status.unread_notifications}</strong>
              <small>Admin-only operational messages</small>
            </article>
            <article className="insight-card static-card">
              <span>Last source check</span>
              <strong>{latestCheck ? String(latestCheck.status ?? "recorded") : "None"}</strong>
              <small>{latestCheck ? formatDate(String(latestCheck.finished_at ?? latestCheck.started_at ?? "")) : "Run Check MYH now"}</small>
            </article>
            <article className="insight-card static-card">
              <span>Latest refresh</span>
              <strong>{latestRun ? String(latestRun.status ?? "recorded") : "None"}</strong>
              <small>{latestRun ? String(latestRun.mode ?? "refresh run") : "No import yet"}</small>
            </article>
          </section>

          <section className="operations-grid">
            <article className="panel operations-panel wide-panel">
              <div className="section-heading compact">
                <div>
                  <p className="eyebrow">Official source files</p>
                  <h3>Detected MYH workbooks</h3>
                </div>
                <span className="muted">Runtime downloads stay outside Git.</span>
              </div>
              <SourceFileTable files={files} onDownload={handleDownload} onImport={handleImport} onSelect={setSelectedFile} />
            </article>

            <article className="panel operations-panel">
              <div className="section-heading compact">
                <div>
                  <p className="eyebrow">Admin notifications</p>
                  <h3>Operational messages</h3>
                </div>
              </div>
              <NotificationList notifications={notifications} onRead={handleRead} onResolve={handleResolve} />
            </article>
          </section>

          <section className="operations-grid">
            <article className="panel operations-panel wide-panel">
              <div className="section-heading compact">
                <div>
                  <p className="eyebrow">Refresh history</p>
                  <h3>Validation and import runs</h3>
                </div>
              </div>
              <RefreshRunTable runs={runs} onSelect={setSelectedRun} />
            </article>
            <article className="panel operations-panel detail-panel">
              <p className="eyebrow">Inspector</p>
              {selectedFile ? (
                <div className="detail-stack">
                  <h3>{selectedFile.file_name}</h3>
                  <p>{selectedFile.file_url}</p>
                  <dl className="system-check-list">
                    <div><dt>Status</dt><dd>{selectedFile.status}</dd></div>
                    <div><dt>Year</dt><dd>{selectedFile.source_year ?? "—"}</dd></div>
                    <div><dt>Downloaded</dt><dd>{formatDate(selectedFile.last_downloaded_at)}</dd></div>
                    <div><dt>Last error</dt><dd>{selectedFile.last_error ?? "—"}</dd></div>
                  </dl>
                </div>
              ) : selectedRun ? (
                <div className="detail-stack">
                  <h3>Refresh {selectedRun.id.slice(0, 8)}…</h3>
                  <p>{selectedRun.validation_summary ?? selectedRun.error_message ?? "No details recorded."}</p>
                  <dl className="system-check-list">
                    <div><dt>Status</dt><dd>{selectedRun.status}</dd></div>
                    <div><dt>Mode</dt><dd>{selectedRun.mode}</dd></div>
                    <div><dt>Rows</dt><dd>{selectedRun.rows_imported ?? "—"}</dd></div>
                    <div><dt>Processed file</dt><dd>{selectedRun.processed_path ?? "—"}</dd></div>
                  </dl>
                </div>
              ) : (
                <EmptyState title="Nothing selected" text="Open a source file or refresh run detail to inspect it here." />
              )}
            </article>
          </section>
        </>
      )}
    </div>
  );
}
