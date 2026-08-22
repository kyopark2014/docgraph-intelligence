import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { api, type GraphStatus } from "../api";
import { CloseIcon } from "./SidebarIcons";

interface Props {
  userId: string;
  title: string;
  onClose: () => void;
}

export function KnowledgeGraphModal({ userId, title, onClose }: Props) {
  const [status, setStatus] = useState<GraphStatus | null>(null);
  const [frameSrc, setFrameSrc] = useState<string | null>(null);
  const [pollError, setPollError] = useState<string | null>(null);
  const [patternBusy, setPatternBusy] = useState(false);
  const patternBusyRef = useRef(false);

  const applyStatus = useCallback((next: GraphStatus) => {
    setStatus(next);
    if (next.exists) {
      setFrameSrc((prev) => {
        const bust = next.last_success_at
          ? encodeURIComponent(next.last_success_at)
          : String(Date.now());
        const nextSrc = `/api/graph?t=${bust}`;
        // Keep existing iframe if only polling and URL would be identical.
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
        const next = await api.getGraphStatus();
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
  }, [applyStatus, userId]);


  useEffect(() => {
    async function onMessage(e: MessageEvent) {
      const data = e.data;
      if (!data || data.type !== "graph-pattern") return;
      const pattern = String(data.pattern || "");
      if (pattern !== "pattern1" && pattern !== "pattern2" && pattern !== "pattern3") return;
      if (patternBusyRef.current) return;
      patternBusyRef.current = true;
      setPatternBusy(true);
      try {
        await api.patchSessionSettings({ graph_pattern: pattern });
        setFrameSrc(`/api/graph?t=${Date.now()}`);
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
            title={`${userId} knowledge graph`}
            src={frameSrc!}
            sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
          />
        ) : (
          <div className="knowledge-graph-placeholder">
            {busy ? (
              <>
                <p className="knowledge-graph-placeholder-title">
                  Building knowledge graph
                </p>
                <p className="knowledge-graph-placeholder-body">
                  Extracting in the background after login. Please wait
                  a moment.
                </p>
              </>
            ) : status?.status === "error" ? (
              <>
                <p className="knowledge-graph-placeholder-title">
                  Graph build failed
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
                <p className="knowledge-graph-placeholder-title">
                  No Knowledge Graph
                </p>
                <p className="knowledge-graph-placeholder-body">
                  No user graph yet. Try again shortly.
                </p>
              </>
            )}
          </div>
        )}
        {showFrame && (busy || patternBusy) ? (
          <div className="knowledge-graph-banner">
            {patternBusy ? "Switching pattern…" : "Refreshing graph…"}
          </div>
        ) : null}
      </div>
    </div>,
    document.body,
  );
}
