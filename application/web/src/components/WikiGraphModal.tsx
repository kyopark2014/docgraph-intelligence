import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { api, type WikiStatus } from "../api";
import { CloseIcon } from "./SidebarIcons";

interface Props {
  title?: string;
  onClose: () => void;
}

export function WikiGraphModal({ title = "DocGraph", onClose }: Props) {
  const [status, setStatus] = useState<WikiStatus | null>(null);
  const [frameSrc, setFrameSrc] = useState<string | null>(null);
  const [pollError, setPollError] = useState<string | null>(null);
  const [patternBusy, setPatternBusy] = useState(false);
  const patternBusyRef = useRef(false);

  const applyStatus = useCallback((next: WikiStatus) => {
    setStatus(next);
    if (next.exists) {
      setFrameSrc((prev) => {
        const bust = next.last_success_at
          ? encodeURIComponent(next.last_success_at)
          : String(Date.now());
        const nextSrc = `/api/docgraph/graph?t=${bust}`;
        return prev === nextSrc ? prev : nextSrc;
      });
    }
  }, []);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = prev;
    };
  }, [onClose]);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    async function poll() {
      try {
        const next = await api.getWikiStatus();
        if (cancelled) return;
        setPollError(null);
        applyStatus(next);
        const busy = next.status === "queued" || next.status === "running";
        if (busy || (!next.exists && next.status !== "error")) {
          timer = setTimeout(poll, 2500);
        }
      } catch (err) {
        if (cancelled) return;
        setPollError(err instanceof Error ? err.message : String(err));
        timer = setTimeout(poll, 4000);
      }
    }

    void poll();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [applyStatus]);

  useEffect(() => {
    async function onMessage(e: MessageEvent) {
      const data = e.data;
      if (!data || data.type !== "graph-pattern") return;
      const pattern = String(data.pattern || "");
      if (pattern !== "pattern1" && pattern !== "pattern2" && pattern !== "pattern3") {
        return;
      }
      if (patternBusyRef.current) return;
      patternBusyRef.current = true;
      setPatternBusy(true);
      try {
        await api.setWikiGraphPattern(pattern);
        setFrameSrc(`/api/docgraph/graph?t=${Date.now()}`);
      } catch (err) {
        setPollError(err instanceof Error ? err.message : String(err));
      } finally {
        patternBusyRef.current = false;
        setPatternBusy(false);
      }
    }
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, []);

  const busy = status?.status === "queued" || status?.status === "running";
  const showFrame = Boolean(frameSrc && status?.exists);

  return createPortal(
    <div
      className="modal-overlay knowledge-graph-modal"
      role="dialog"
      aria-modal="true"
      aria-label={title}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="knowledge-graph-panel">
        <button
          type="button"
          className="knowledge-graph-close"
          aria-label="Close"
          onClick={onClose}
        >
          <CloseIcon className="sidebar-icon" />
        </button>
        {showFrame ? (
          <iframe
            className="knowledge-graph-frame"
            title="DocGraph knowledge graph"
            src={frameSrc!}
            sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
          />
        ) : (
          <div className="knowledge-graph-placeholder">
            {busy ? (
              <>
                <p className="knowledge-graph-placeholder-title">
                  Syncing DocGraph
                </p>
                <p className="knowledge-graph-placeholder-body">
                  Extracting the DocGraph corpus with graphify.
                </p>
              </>
            ) : status?.status === "error" ? (
              <>
                <p className="knowledge-graph-placeholder-title">
                  DocGraph sync failed
                </p>
                <p className="knowledge-graph-placeholder-body">
                  {status.error || "Unknown error"}
                </p>
              </>
            ) : pollError ? (
              <>
                <p className="knowledge-graph-placeholder-title">Failed to load status</p>
                <p className="knowledge-graph-placeholder-body">{pollError}</p>
              </>
            ) : (
              <>
                <p className="knowledge-graph-placeholder-title">No DocGraph</p>
                <p className="knowledge-graph-placeholder-body">
                  Sync first via Settings → DocGraph → Sync
                  {status?.docgraph_dir ? ` (${status.docgraph_dir})` : ""}.
                </p>
              </>
            )}
          </div>
        )}
        {showFrame && (busy || patternBusy) ? (
          <div className="knowledge-graph-banner">
            {patternBusy ? "Switching pattern…" : "Syncing DocGraph…"}
          </div>
        ) : null}
      </div>
    </div>,
    document.body,
  );
}
