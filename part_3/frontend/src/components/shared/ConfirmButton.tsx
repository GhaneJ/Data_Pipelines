export function ConfirmButton({
  children,
  confirmText,
  onConfirm,
  className = "button secondary",
}: {
  children: React.ReactNode;
  confirmText: string;
  onConfirm: () => void | Promise<void>;
  className?: string;
}) {
  return (
    <button
      type="button"
      className={className}
      onClick={() => {
        if (window.confirm(confirmText)) {
          void onConfirm();
        }
      }}
    >
      {children}
    </button>
  );
}
