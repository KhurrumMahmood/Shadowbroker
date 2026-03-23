"use client";

import { motion } from "framer-motion";
import { X } from "lucide-react";
import type { BoxSelectResult } from "@/components/map/hooks/useBoxSelect";

const TYPE_LABELS: Record<string, { label: string; color: string }> = {
  flight: { label: "Commercial Flights", color: "#67e8f9" },
  private_flight: { label: "Private Flights", color: "#94a3b8" },
  private_jet: { label: "Private Jets", color: "#c084fc" },
  military_flight: { label: "Military Flights", color: "#f87171" },
  tracked_flight: { label: "Tracked Aircraft", color: "#fbbf24" },
  uav: { label: "UAVs", color: "#f87171" },
  ship: { label: "Ships", color: "#94a3b8" },
  carrier: { label: "Carriers", color: "#f87171" },
  satellite: { label: "Satellites", color: "#67e8f9" },
  earthquake: { label: "Earthquakes", color: "#facc15" },
  gdelt: { label: "Incidents", color: "#fb923c" },
  liveuamap: { label: "Conflict Events", color: "#ef4444" },
  cctv: { label: "CCTV Cameras", color: "#a3e635" },
  kiwisdr: { label: "SDR Receivers", color: "#fbbf24" },
  firms_fire: { label: "Fire Hotspots", color: "#ef4444" },
  internet_outage: { label: "Internet Outages", color: "#ef4444" },
  datacenter: { label: "Data Centers", color: "#a78bfa" },
  power_plant: { label: "Power Plants", color: "#fbbf24" },
  military_base: { label: "Military Bases", color: "#f87171" },
};

export default function BoxSelectSummary({
  result,
  onClose,
}: {
  result: BoxSelectResult;
  onClose: () => void;
}) {
  const totalEntities = result.features.length;
  const sortedTypes = Object.entries(result.counts).sort((a, b) => b[1] - a[1]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 10 }}
      className="absolute bottom-24 left-1/2 -translate-x-1/2 z-[300] pointer-events-auto"
    >
      <div className="bg-black/90 backdrop-blur-md border border-cyan-800/60 rounded-xl px-5 py-4 shadow-[0_4px_30px_rgba(0,0,0,0.4)] min-w-[280px] max-w-[400px]">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-cyan-400 font-mono tracking-[0.2em] font-bold">
              AREA SCAN
            </span>
            <span className="text-[9px] text-cyan-400/60 font-mono">
              {totalEntities} {totalEntities === 1 ? "entity" : "entities"}
            </span>
          </div>
          <button
            onClick={onClose}
            className="text-[var(--text-muted)] hover:text-cyan-400 transition-colors"
          >
            <X size={14} />
          </button>
        </div>

        {sortedTypes.length === 0 ? (
          <div className="text-[10px] text-[var(--text-muted)] font-mono">
            No entities found in selection area.
          </div>
        ) : (
          <div className="flex flex-col gap-1.5">
            {sortedTypes.map(([type, count]) => {
              const meta = TYPE_LABELS[type] || { label: type, color: "#94a3b8" };
              return (
                <div key={type} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: meta.color }}
                    />
                    <span className="text-[10px] font-mono text-[var(--text-secondary)]">
                      {meta.label}
                    </span>
                  </div>
                  <span
                    className="text-[10px] font-mono font-bold"
                    style={{ color: meta.color }}
                  >
                    {count.toLocaleString()}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </motion.div>
  );
}
