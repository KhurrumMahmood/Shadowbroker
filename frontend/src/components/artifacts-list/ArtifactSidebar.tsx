"use client";

import { useMemo } from "react";
import { Layers } from "lucide-react";
import registry from "@/artifacts/registry.json";
import type { RegistryEntry } from "@/artifacts/_shared/types";
import type { SelectedArtifact } from "./ArtifactsListPage";

interface ArtifactSidebarProps {
  selected: SelectedArtifact | null;
  onSelect: (artifact: SelectedArtifact) => void;
}

const categoryLabels: Record<string, string> = registry.categories;

export default function ArtifactSidebar({ selected, onSelect }: ArtifactSidebarProps) {
  const grouped = useMemo(() => {
    const groups: Record<string, RegistryEntry[]> = {};
    for (const entry of registry.artifacts as RegistryEntry[]) {
      const cat = entry.category ?? "uncategorized";
      (groups[cat] ??= []).push(entry);
    }
    return groups;
  }, []);

  const categoryOrder = Object.keys(registry.categories);

  return (
    <div className="flex flex-col h-full border-r border-cyan-800/40 bg-black/90">
      {/* Header */}
      <div className="px-4 py-3 border-b border-cyan-800/40 flex items-center gap-2">
        <Layers size={12} className="text-cyan-400" />
        <span className="text-[8px] font-mono tracking-[0.2em] text-cyan-500 uppercase">
          Artifact Registry
        </span>
        <span className="text-[7px] font-mono text-cyan-700 ml-auto">
          {registry.artifacts.length}
        </span>
      </div>

      {/* Scrollable list grouped by category */}
      <div className="flex-1 overflow-y-auto styled-scrollbar p-2 space-y-3">
        {categoryOrder.map((catKey) => {
          const entries = grouped[catKey];
          if (!entries?.length) return null;
          return (
            <Section
              key={catKey}
              label={categoryLabels[catKey] ?? catKey}
              count={entries.length}
            >
              {entries.map((entry) => (
                <ArtifactRow
                  key={entry.name}
                  entry={entry}
                  isSelected={selected?.name === entry.name}
                  onSelect={onSelect}
                />
              ))}
            </Section>
          );
        })}
      </div>
    </div>
  );
}

function Section({ label, count, children }: {
  label: string;
  count: number;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="flex items-center gap-1.5 px-2 py-1.5">
        <span className="text-[7px] font-mono tracking-[0.15em] text-cyan-600 uppercase">
          {label}
        </span>
        <span className="text-[7px] font-mono text-cyan-800 ml-auto">{count}</span>
      </div>
      <div className="flex flex-col gap-1">{children}</div>
    </div>
  );
}

function ArtifactRow({ entry, isSelected, onSelect }: {
  entry: RegistryEntry;
  isSelected: boolean;
  onSelect: (artifact: SelectedArtifact) => void;
}) {
  const isHtml = entry.type === "html";
  return (
    <button
      type="button"
      onClick={() => onSelect({
        name: entry.name,
        title: entry.title,
        version: entry.current_version,
        type: entry.type,
      })}
      className={`text-left w-full p-2 rounded-lg border transition-colors ${
        isSelected
          ? "bg-cyan-950/30 border-cyan-700/50"
          : "border-cyan-800/20 hover:border-cyan-700/40 hover:bg-cyan-950/15"
      }`}
    >
      <div className="flex items-center justify-between mb-1">
        <span className={`text-[9px] font-mono font-semibold truncate ${
          isSelected ? "text-cyan-300" : "text-[var(--text-primary)]"
        }`}>
          {entry.title}
        </span>
        <span className="text-[7px] font-mono text-cyan-600 ml-2 shrink-0">
          V{entry.current_version}
        </span>
      </div>
      <div className="flex items-center gap-1 flex-wrap">
        {entry.tags.slice(0, 3).map((tag) => (
          <span
            key={tag}
            className="text-[7px] font-mono tracking-[0.1em] text-cyan-500 bg-cyan-900/30 px-1.5 py-0.5 rounded"
          >
            {tag}
          </span>
        ))}
        {isHtml && (
          <span className="text-[6px] font-mono tracking-[0.1em] text-yellow-600 ml-auto">
            REQUIRES BACKEND
          </span>
        )}
      </div>
    </button>
  );
}
