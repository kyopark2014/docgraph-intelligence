import { useEffect } from "react";
import { createPortal } from "react-dom";

interface Props {
  title: string;
  busy: boolean;
  message: string | null;
  onClose: () => void;
}

export function SyncProgressModal({ title, busy, message, onClose }: Props) {
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape" && !busy) onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = prev;
    };
  }, [busy, onClose]);

  useEffect(() => {
    if (busy) return;
    const timer = window.setTimeout(() => onClose(), 4000);
    return () => window.clearTimeout(timer);
  }, [busy, message, onClose]);

  const display =
    message?.trim() ||
    (busy ? "Sync in progress…" : "Sync completed.");

  return createPortal(
    <div
      className="modal-overlay sync-progress-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="sync-progress-title"
      aria-busy={busy}
      onMouseDown={(e) => {
        if (e.target === e.currentTarget && !busy) onClose();
      }}
    >
      <div className="sync-progress-modal">
        <div className="sync-progress-header">
          <h2 id="sync-progress-title">{title}</h2>
          {!busy && (
            <button
              type="button"
              className="sync-progress-close"
              aria-label="Close"
              onClick={onClose}
            >
              ×
            </button>
          )}
        </div>

        <div className="sync-progress-body">
          {busy ? (
            <div className="sync-progress-spinner" aria-hidden="true" />
          ) : (
            <div className="sync-progress-done" aria-hidden="true">
              ✓
            </div>
          )}
          <p className="sync-progress-message">{display}</p>
          {busy && (
            <p className="sync-progress-hint">
              Keep this window open until finished, or check the Syncing
              indicator in the sidebar.
            </p>
          )}
        </div>

        <div className="sync-progress-actions">
          {busy ? (
            <button
              type="button"
              className="sync-progress-btn is-secondary"
              onClick={onClose}
            >
              Continue in background
            </button>
          ) : (
            <button
              type="button"
              className="sync-progress-btn"
              onClick={onClose}
            >
              OK
            </button>
          )}
        </div>
      </div>
    </div>,
    document.body,
  );
}
