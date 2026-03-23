"use client";

import { motion } from "framer-motion";
import { X, MapPin, Loader2 } from "lucide-react";

interface NotableEntity {
  type: string;
  id: string | number;
  name: string;
  why: string;
}

interface BriefData {
  summary: string;
  notable_entities: NotableEntity[];
  suggested_layers: Record<string, boolean>;
  counts: Record<string, number>;
}

interface ViewportBriefPanelProps {
  data: BriefData | null;
  loading: boolean;
  onClose: () => void;
  onEntityClick: (entity: { type: string; id: string | number; name: string }) => void;
  onApplyLayers: (layers: Record<string, boolean>) => void;
}

export type { BriefData, NotableEntity };

export default function ViewportBriefPanel({
  data,
  loading,
  onClose,
  onEntityClick,
  onApplyLayers,
}: ViewportBriefPanelProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }}
      className="absolute bottom-24 left-1/2 -translate-x-1/2 z-[400] w-[500px] max-w-[90vw] pointer-events-auto"
    >
      <div className="bg-black/90 backdrop-blur-md border border-cyan-800/60 rounded-xl shadow-[0_4px_30px_rgba(0,0,0,0.5)] flex flex-col max-h-[400px]">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-cyan-800/40">
          <div className="flex items-center gap-2">
            <MapPin size={14} className="text-cyan-400" />
            <span className="text-[10px] text-cyan-400 font-mono tracking-[0.2em] font-bold">
              VIEWPORT BRIEFING
            </span>
          </div>
          <button type="button" onClick={onClose} className="text-[var(--text-muted)] hover:text-cyan-400 transition-colors">
            <X size={14} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto styled-scrollbar px-4 py-3 space-y-3 min-h-[100px] max-h-[300px]">
          {loading && (
            <div className="flex items-center gap-2 justify-center py-8">
              <Loader2 size={14} className="text-cyan-400 animate-spin" />
              <span className="text-[10px] text-cyan-400/60 font-mono">Analyzing viewport...</span>
            </div>
          )}

          {!loading && data && (
            <>
              {/* Summary */}
              <p className="text-[10px] text-[var(--text-primary)] font-mono leading-relaxed">
                {data.summary}
              </p>

              {/* Counts */}
              {Object.keys(data.counts).some(k => data.counts[k] > 0) && (
                <div className="flex flex-wrap gap-2 pt-1">
                  {Object.entries(data.counts)
                    .filter(([, v]) => v > 0)
                    .sort(([, a], [, b]) => b - a)
                    .map(([key, count]) => (
                      <span
                        key={key}
                        className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-cyan-950/40 border border-cyan-800/30 text-cyan-400/80"
                      >
                        {key.replace(/_/g, " ")}: {count}
                      </span>
                    ))}
                </div>
              )}

              {/* Notable entities */}
              {data.notable_entities.length > 0 && (
                <div className="pt-2 border-t border-cyan-800/30">
                  <div className="text-[9px] text-cyan-500/70 font-mono tracking-wider mb-1.5">
                    NOTABLE ({data.notable_entities.length})
                  </div>
                  <div className="space-y-1">
                    {data.notable_entities.map((entity, i) => (
                      <button
                        type="button"
                        key={`${entity.type}-${entity.id}-${i}`}
                        onClick={() => onEntityClick(entity)}
                        className="w-full text-left flex items-start gap-2 px-2 py-1.5 rounded hover:bg-cyan-950/30 transition-colors group"
                      >
                        <span className="text-[8px] font-mono text-cyan-600 bg-cyan-950/40 px-1 py-0.5 rounded flex-shrink-0 mt-0.5">
                          {entity.type.replace(/_/g, " ").toUpperCase()}
                        </span>
                        <div className="flex-1 min-w-0">
                          <div className="text-[10px] text-[var(--text-primary)] font-mono truncate group-hover:text-cyan-400 transition-colors">
                            {entity.name}
                          </div>
                          <div className="text-[9px] text-[var(--text-muted)] font-mono truncate">
                            {entity.why}
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Apply suggested layers */}
              {Object.keys(data.suggested_layers).length > 0 && (
                <div className="pt-2 border-t border-cyan-800/30">
                  <button
                    type="button"
                    onClick={() => onApplyLayers(data.suggested_layers)}
                    className="text-[9px] font-mono text-cyan-500 hover:text-cyan-300 transition-colors tracking-wider"
                  >
                    APPLY SUGGESTED LAYERS ({Object.keys(data.suggested_layers).length})
                  </button>
                </div>
              )}
            </>
          )}

          {!loading && !data && (
            <div className="text-[10px] text-[var(--text-muted)] font-mono text-center py-8">
              No briefing data available.
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
