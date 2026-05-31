import { ApiError } from "@/api/client";

export function ErrorPanel({ error }: { error: unknown }) {
  const message = error instanceof Error ? error.message : "The request could not be completed.";
  const requestId = error instanceof ApiError ? error.requestId : null;
  return (
    <div className="alert alert-error" role="alert">
      <strong>{message}</strong>
      {requestId && <span>Request ID: {requestId}</span>}
    </div>
  );
}

export function EmptyState({ title, text }: { title: string; text: string }) {
  return (
    <div className="empty-state">
      <strong>{title}</strong>
      <span>{text}</span>
    </div>
  );
}

export function LoadingState({ text = "Loading..." }: { text?: string }) {
  return <div className="loading-state">{text}</div>;
}
