import { useState } from "react";

interface ConfirmButtonProps {
  children: React.ReactNode;
  confirmText: string;
  onConfirm: () => void | Promise<void>;
  className?: string;
  title?: string;
  detailText?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
}

export function ConfirmButton({
  children,
  confirmText,
  onConfirm,
  className = "button secondary",
  title = "Confirm action",
  detailText = "This action will be applied immediately after confirmation.",
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  danger = false,
}: ConfirmButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isWorking, setIsWorking] = useState(false);

  async function confirm() {
    setIsWorking(true);
    try {
      await onConfirm();
      setIsOpen(false);
    } finally {
      setIsWorking(false);
    }
  }

  return (
    <>
      <button type="button" className={className} onClick={() => setIsOpen(true)}>
        {children}
      </button>
      {isOpen && (
        <div className="modal-backdrop" role="presentation" onMouseDown={() => !isWorking && setIsOpen(false)}>
          <section
            className="confirmation-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="confirmation-dialog-title"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <p className="eyebrow">Review action</p>
            <h2 id="confirmation-dialog-title">{title}</h2>
            <p className="confirmation-question">{confirmText}</p>
            <p className="muted">{detailText}</p>
            <div className="dialog-actions">
              <button type="button" className="button secondary" onClick={() => setIsOpen(false)} disabled={isWorking}>
                {cancelLabel}
              </button>
              <button type="button" className={danger ? "button danger" : "button primary"} onClick={() => void confirm()} disabled={isWorking}>
                {isWorking ? "Working..." : confirmLabel}
              </button>
            </div>
          </section>
        </div>
      )}
    </>
  );
}
