"use client";

import { useState, useRef, useCallback, useEffect, Suspense, lazy, type ComponentType } from "react";
import { motion, AnimatePresence } from "framer-motion";
import artifactTokensCSS from "@/design/artifact-tokens.css?raw";

/** Static map of React artifact components. Each new React artifact needs a one-line addition. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const REACT_ARTIFACTS: Record<string, () => Promise<{ default: ComponentType<any> }>> = {
  "entity-risk-dashboard": () => import("@/artifacts/entity-risk-dashboard/EntityRiskDashboard"),
  "sitrep-region-brief": () => import("@/artifacts/sitrep-region-brief/SitrepRegionBrief"),
  "tracked-entity-dashboard": () => import("@/artifacts/tracked-entity-dashboard/TrackedEntityDashboard"),
  "risk-pulse-ticker": () => import("@/artifacts/risk-pulse-ticker/RiskPulseTicker"),
};

interface ArtifactPanelProps {
  artifactId: string | null;
  artifactTitle?: string;
  artifactVersion?: number;
  artifactType?: "html" | "react";
  registryName?: string;
  onClose: () => void;
  data?: unknown;
  /** When true, renders as a side pane (h-full, no border/shadow) instead of a standalone card. */
  sidePaneMode?: boolean;
}

/**
 * Renders agent-generated artifacts — either as a sandboxed iframe (HTML)
 * or as a directly-imported React component.
 */
export default function ArtifactPanel({
  artifactId, artifactTitle, artifactVersion, artifactType, registryName, onClose, data,
  sidePaneMode = false,
}: ArtifactPanelProps) {
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [iframeReady, setIframeReady] = useState(false);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [ReactComponent, setReactComponent] = useState<ComponentType<any> | null>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const pendingDataRef = useRef<unknown>(undefined);

  const isReact = artifactType === "react" && registryName && registryName in REACT_ARTIFACTS;

  // Load React component
  useEffect(() => {
    if (!isReact || !registryName) return;
    setLoading(true);
    setError(null);
    REACT_ARTIFACTS[registryName]()
      .then((mod) => {
        setReactComponent(() => mod.default);
        setLoading(false);
      })
      .catch(() => {
        setError("Failed to load React artifact");
        setLoading(false);
      });
  }, [isReact, registryName]);

  const loadArtifact = useCallback(async (id: string, regName?: string, version?: number) => {
    setLoading(true);
    setError(null);
    try {
      // Registry artifacts use /api/artifacts/registry/{name}/v/{version}
      // Ephemeral artifacts use /api/artifacts/{id}
      const url = regName
        ? `/api/artifacts/registry/${regName}/v/${version || 1}`
        : `/api/artifacts/${id}`;
      const resp = await fetch(url);
      if (!resp.ok) {
        setError(`Artifact not found (${resp.status})`);
        setLoading(false);
        return;
      }
      const html = await resp.text();

      // Inject design tokens into the artifact HTML
      const tokenStyle = `<style>${artifactTokensCSS}</style>`;
      const injectedHtml = html.includes("<head>")
        ? html.replace("<head>", `<head>${tokenStyle}`)
        : `<!DOCTYPE html><html><head>${tokenStyle}</head><body>${html}</body></html>`;

      // Write to iframe via srcdoc
      const iframe = iframeRef.current;
      if (iframe) {
        setIframeReady(false);
        iframe.onload = () => {
          setIframeReady(true);
          if (pendingDataRef.current !== undefined) {
            iframe.contentWindow?.postMessage(
              { type: "shadowbroker:data", payload: pendingDataRef.current },
              "*"
            );
          }
        };
        iframe.srcdoc = injectedHtml;
      }
      setLoading(false);
    } catch (e) {
      setError("Failed to load artifact");
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (artifactId && !isReact) {
      loadArtifact(artifactId, registryName, artifactVersion);
    }
    return () => {
      if (iframeRef.current) {
        iframeRef.current.onload = null;
      }
    };
  }, [artifactId, isReact, registryName, artifactVersion, loadArtifact]);

  /** Send data to the artifact iframe via postMessage */
  const sendData = useCallback((payload: unknown) => {
    iframeRef.current?.contentWindow?.postMessage(
      { type: "shadowbroker:data", payload },
      "*"
    );
  }, []);

  // Track pending data and send when iframe is ready
  useEffect(() => {
    pendingDataRef.current = data;
    if (iframeReady && data !== undefined) {
      sendData(data);
    }
  }, [data, iframeReady, sendData]);

  if (!artifactId) return null;

  const panelClass = expanded
    ? "fixed inset-4 z-[9999]"
    : sidePaneMode
      ? "h-full w-full"
      : "w-full mt-2";

  const containerClass = expanded || !sidePaneMode
    ? "h-full flex flex-col bg-black/95 backdrop-blur-xl border border-cyan-800/60 rounded-xl shadow-[0_4px_30px_rgba(0,0,0,0.5)] overflow-hidden"
    : "h-full flex flex-col bg-transparent overflow-hidden";

  return (
    <AnimatePresence>
      <motion.div
        className={panelClass}
        initial={sidePaneMode ? undefined : { opacity: 0, y: 10 }}
        animate={sidePaneMode ? undefined : { opacity: 1, y: 0 }}
        exit={sidePaneMode ? undefined : { opacity: 0, y: 10 }}
        transition={{ duration: 0.2 }}
      >
        <div className={containerClass}>
          {/* Header */}
          <div className="flex items-center justify-between px-3 py-1.5 border-b border-cyan-800/40 bg-[var(--bg-secondary)]/60">
            <div className="flex items-center gap-2">
              <span className="text-[8px] font-mono tracking-[0.2em] text-cyan-500 uppercase">
                ARTIFACT
              </span>
              {artifactTitle && (
                <span className="text-[9px] font-mono text-[var(--text-primary)] truncate max-w-[200px]">
                  {artifactTitle}
                </span>
              )}
              {artifactVersion != null && (
                <span className="text-[7px] font-mono tracking-[0.15em] text-cyan-400 bg-cyan-900/40 px-1.5 py-0.5 rounded border border-cyan-800/40">
                  V{artifactVersion}
                </span>
              )}
            </div>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => setExpanded(!expanded)}
                className="text-[8px] font-mono tracking-[0.15em] text-cyan-600 hover:text-cyan-400 px-2 py-0.5 rounded border border-cyan-800/30 hover:border-cyan-700/50 transition-colors"
              >
                {expanded ? "COLLAPSE" : "EXPAND"}
              </button>
              <button
                type="button"
                onClick={onClose}
                className="text-[8px] font-mono tracking-[0.15em] text-cyan-600 hover:text-cyan-400 px-2 py-0.5 rounded border border-cyan-800/30 hover:border-cyan-700/50 transition-colors"
              >
                CLOSE
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 relative min-h-0">
            {loading && (
              <div className="absolute inset-0 flex items-center justify-center bg-black/80 z-10">
                <span className="text-[9px] font-mono tracking-[0.2em] text-cyan-600 animate-pulse">
                  LOADING ARTIFACT...
                </span>
              </div>
            )}
            {error && (
              <div className="absolute inset-0 flex items-center justify-center bg-black/80 z-10">
                <span className="text-[9px] font-mono tracking-[0.15em] text-red-400">
                  {error}
                </span>
              </div>
            )}
            {isReact && ReactComponent ? (
              <div style={{ minHeight: (expanded || sidePaneMode) ? "100%" : "280px", padding: 12, background: "#000" }}>
                <Suspense fallback={null}>
                  <ReactComponent initialData={data} />
                </Suspense>
              </div>
            ) : (
              <iframe
                ref={iframeRef}
                className="w-full h-full border-0"
                sandbox="allow-scripts"
                title={artifactTitle || "Agent artifact"}
                style={{ minHeight: (expanded || sidePaneMode) ? "100%" : "280px", background: "#000" }}
              />
            )}
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
