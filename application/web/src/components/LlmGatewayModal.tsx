import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { api, type LlmGatewayVerifyResult } from "../api";

interface Props {
  enabled: boolean;
  isAdmin: boolean;
  gatewayConfigured: boolean;
  onConfirmEnable: (uiModels?: string[]) => Promise<void> | void;
  onDisable: () => Promise<void> | void;
  onClose: () => void;
}

export function LlmGatewayModal({
  enabled,
  isAdmin,
  gatewayConfigured,
  onConfirmEnable,
  onDisable,
  onClose,
}: Props) {
  const [url, setUrl] = useState("");
  const [key, setKey] = useState("");
  const [keyConfigured, setKeyConfigured] = useState(false);
  const [loading, setLoading] = useState(isAdmin);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (!isAdmin) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await api.getLlmGateway();
        if (!cancelled) {
          setUrl(data.url || "");
          setKeyConfigured(Boolean(data.key_configured || data.configured));
          // Never prefill the secret; empty means keep existing.
          setKey("");
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isAdmin]);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape" && !busy) onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [busy, onClose]);

  async function handleConfirm() {
    setError(null);
    setSuccess(null);

    if (!isAdmin) {
      setBusy(true);
      setError(null);
      try {
        const status = await api.getLlmGateway();
        if (!status.configured) {
          setError(
            gatewayConfigured
              ? "LLM Gateway is not configured, so it cannot be enabled. Ask an administrator to set it up."
              : "An administrator must configure LLM Gateway first.",
          );
          return;
        }
        await onConfirmEnable();
        onClose();
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setBusy(false);
      }
      return;
    }

    const nextUrl = url.trim();
    const nextKey = key.trim();
    if (!nextUrl) {
      setError("URL is required.");
      return;
    }
    if (!nextKey && !keyConfigured) {
      setError("A Key is required for the initial setup.");
      return;
    }

    setBusy(true);
    try {
      const result: LlmGatewayVerifyResult = await api.verifyLlmGateway({
        url: nextUrl,
        key: nextKey,
      });
      if (!result.ok) {
        setError(result.message || "Failed to verify LLM Gateway models.");
        return;
      }
      setSuccess(result.message || "Model verification succeeded");
      setKeyConfigured(true);
      setKey("");
      await onConfirmEnable(result.ui_models);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleDisable() {
    setBusy(true);
    setError(null);
    try {
      await onDisable();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  const description = isAdmin
    ? "Verify the URL. Enter a Key only when changing it (leave blank to keep the existing key). On successful model list lookup, it will be saved and enabled."
    : gatewayConfigured
      ? "Turn LLM Gateway on or off for this task. Shared API keys stay on the server only."
      : "LLM Gateway is not configured yet. Ask an administrator to set it up.";

  return createPortal(
    <div
      className="modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="llm-gateway-title"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget && !busy) onClose();
      }}
    >
      <div className="modal llm-gateway-modal">
        <h2 id="llm-gateway-title">LLM Gateway</h2>
        <p>
          {description}
          {enabled ? " (currently in use)" : ""}
        </p>

        {isAdmin &&
          (loading ? (
            <p className="llm-gateway-muted">Loading settings…</p>
          ) : (
            <form
              className="llm-gateway-fields"
              onSubmit={(e) => {
                e.preventDefault();
                if (!busy && !loading) void handleConfirm();
              }}
            >
              <label className="llm-gateway-field">
                <span>URL</span>
                <input
                  type="text"
                  value={url}
                  disabled={busy}
                  autoComplete="off"
                  placeholder="https://gateway.example.com"
                  onChange={(e) => setUrl(e.target.value)}
                />
              </label>
              <label className="llm-gateway-field">
                <span>
                  Key
                  {keyConfigured ? " (saved key on file — enter only to change)" : ""}
                </span>
                <input
                  type="password"
                  value={key}
                  disabled={busy}
                  autoComplete="new-password"
                  placeholder={
                    keyConfigured ? "Leave blank to keep the existing key" : "sk-..."
                  }
                  onChange={(e) => setKey(e.target.value)}
                />
              </label>
              <button type="submit" hidden aria-hidden="true" tabIndex={-1} />
            </form>
          ))}

        {!isAdmin && (
          <p className="llm-gateway-muted">
            {gatewayConfigured
              ? "Gateway is configured on the server."
              : "Gateway not configured — cannot enable."}
          </p>
        )}

        {error && (
          <p className="modal-error" role="alert">
            {error}
          </p>
        )}
        {success && <p className="llm-gateway-success">{success}</p>}

        <div className="modal-actions">
          <button
            type="button"
            className="modal-btn-secondary"
            disabled={busy}
            onClick={onClose}
          >
            Cancel
          </button>
          {enabled && (
            <button
              type="button"
              className="modal-btn-secondary"
              disabled={busy || loading}
              onClick={handleDisable}
            >
              Turn off
            </button>
          )}
          <button
            type="button"
            className="send-btn"
            disabled={
              busy || loading || (!isAdmin && !gatewayConfigured && !enabled)
            }
            onClick={handleConfirm}
          >
            {busy ? "Verifying…" : isAdmin ? "Verify" : "Turn on"}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
