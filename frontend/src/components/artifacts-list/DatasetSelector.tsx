"use client";

import { Database } from "lucide-react";
import type { DatasetEntry } from "@/artifacts/_shared/dummyData";

interface DatasetSelectorProps {
  artifactType: string | null;
  datasets: readonly DatasetEntry[];
  selected: string;
  onSelect: (key: string) => void;
}

export default function DatasetSelector({ artifactType, datasets, selected, onSelect }: DatasetSelectorProps) {
  if (datasets.length === 0 && artifactType === null) {
    return (
      <div className="flex items-center gap-2 h-6">
        <Database size={10} className="text-cyan-800" />
        <span className="text-[8px] font-mono tracking-[0.15em] text-cyan-800 uppercase">
          No artifact selected
        </span>
      </div>
    );
  }

  if (artifactType === "html") {
    return (
      <div className="flex items-center gap-2 h-6">
        <Database size={10} className="text-cyan-600" />
        <span className="text-[8px] font-mono tracking-[0.15em] text-cyan-600 uppercase">
          Dataset: Embedded in HTML
        </span>
      </div>
    );
  }

  if (datasets.length === 0) {
    return (
      <div className="flex items-center gap-2 h-6">
        <Database size={10} className="text-cyan-700" />
        <span className="text-[8px] font-mono tracking-[0.15em] text-cyan-700 uppercase animate-pulse">
          Loading datasets...
        </span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 h-6">
      <Database size={10} className="text-cyan-500" />
      <span className="text-[8px] font-mono tracking-[0.15em] text-cyan-600 uppercase shrink-0">
        Dataset:
      </span>
      <select
        value={selected}
        onChange={(e) => onSelect(e.target.value)}
        disabled={datasets.length <= 1}
        className="text-[8px] font-mono tracking-[0.1em] text-cyan-400 bg-black border border-cyan-800/40 rounded px-2 py-0.5 appearance-none cursor-pointer disabled:opacity-50 disabled:cursor-default hover:border-cyan-700/60 transition-colors focus:outline-none focus:border-cyan-600"
      >
        {datasets.map((ds) => (
          <option key={ds.key} value={ds.key}>
            {ds.label}
          </option>
        ))}
      </select>
    </div>
  );
}
