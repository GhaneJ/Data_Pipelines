import { ApiError } from "@/api/client";

function userFriendlyMessage(error: unknown): string {
  if (!(error instanceof Error)) return "The request could not be completed.";
  if (error.message.includes("Request validation failed")) return "Please check the form fields and try again.";
  if (error.message.includes("not enough values to unpack")) return "The request could not be processed. Please check the selected record and try again.";
  return error.message;
}

export function ErrorPanel({ error }: { error: unknown }) {
  const message = userFriendlyMessage(error);
  const requestId = error instanceof ApiError ? error.requestId : null;
  return (
    <div className="alert alert-error" role="alert">
      <strong>{message}</strong>
      {requestId && (
        <details className="technical-details">
          <summary>Technical reference</summary>
          <span>Request ID: {requestId}</span>
        </details>
      )}
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
