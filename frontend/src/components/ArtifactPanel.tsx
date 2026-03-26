"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import artifactTokensCSS from "@/design/artifact-tokens.css?raw";

interface ArtifactPanelProps {
  artifactId: string | null;
  artifactTitle?: string;
  onClose: () => void;
  data?: unknown;
}

/**
 * Sandboxed iframe renderer for agent-generated HTML artifacts.
 *
 * Loads artifact HTML from /api/artifacts/{id}, injects design tokens,
 * and renders in a sandboxed iframe. Supports expand/collapse and
 * data injection via postMessage.
 */
export default function ArtifactPanel({ artifactId, artifactTitle, onClose, data }: ArtifactPanelProps) {
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [iframeReady, setIframeReady] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const pendingDataRef = useRef<unknown>(undefined);

  const loadArtifact = useCallback(async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`/api/artifacts/${id}`);
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
          // Send any pending data after iframe loads
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
    if (artifactId) {
      loadArtifact(artifactId);
    }
  }, [artifactId, loadArtifact]);

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
    : "w-full mt-2";

  return (
    <AnimatePresence>
      <motion.div
        className={panelClass}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 10 }}
        transition={{ duration: 0.2 }}
      >
        <div className="h-full flex flex-col bg-black/95 backdrop-blur-xl border border-cyan-800/60 rounded-xl shadow-[0_4px_30px_rgba(0,0,0,0.5)] overflow-hidden">
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
            <iframe
              ref={iframeRef}
              className="w-full h-full border-0"
              sandbox="allow-scripts"
              title={artifactTitle || "Agent artifact"}
              style={{ minHeight: expanded ? "100%" : "280px", background: "#000" }}
            />
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
