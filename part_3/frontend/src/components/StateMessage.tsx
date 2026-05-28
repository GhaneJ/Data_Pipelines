import type { ApiStatus } from "@/services/api";

interface StateMessageProps {
  status: ApiStatus;
  loadingText?: string;
  errorText?: string | null;
  emptyText?: string;
  isEmpty?: boolean;
}

export function StateMessage({
  status,
  loadingText = "Loading data...",
  errorText = "Data could not be loaded.",
  emptyText = "No data matched this view.",
  isEmpty = false,
}: StateMessageProps) {
  if (status === "loading" || status === "idle") {
    return <p className="state-message">{loadingText}</p>;
  }

  if (status === "error") {
    return (
      <p className="state-message error" role="alert">
        {errorText}
      </p>
    );
  }

  if (isEmpty) {
    return <p className="state-message">{emptyText}</p>;
  }

  return null;
}
