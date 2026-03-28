"use client";

import registry from "@/artifacts/registry.json";

interface ArtifactBrowserProps {
  onSelect: (artifact: { name: string; title: string; version: number; type: string }) => void;
}

export default function ArtifactBrowser({ onSelect }: ArtifactBrowserProps) {
  const entries = registry.artifacts;

  if (entries.length === 0) {
    return (
      <div className="p-6 text-center">
        <p className="text-[9px] font-mono tracking-[0.15em] text-[var(--text-muted)]">
          NO ARTIFACTS IN REGISTRY
        </p>
        <p className="text-[8px] font-mono text-cyan-800 mt-2">
          Artifacts are created when you query the AI analyst
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1 p-2 overflow-y-auto">
      {entries.map((entry) => (
        <button
          key={entry.name}
          type="button"
          onClick={() => onSelect({ name: entry.name, title: entry.title, version: entry.current_version, type: entry.type || "html" })}
          className="text-left p-2 rounded-lg border border-cyan-800/30 hover:border-cyan-700/50 hover:bg-cyan-950/20 transition-colors"
        >
          <div className="flex items-center justify-between mb-1">
            <span className="text-[9px] font-mono text-[var(--text-primary)] font-semibold truncate">
              {entry.title}
            </span>
            <span className="text-[7px] font-mono text-cyan-600 ml-2 shrink-0">
              V{entry.current_version}
            </span>
          </div>
          <div className="flex items-center gap-1 flex-wrap">
            {entry.tags.slice(0, 4).map((tag) => (
              <span
                key={tag}
                className="text-[7px] font-mono tracking-[0.1em] text-cyan-500 bg-cyan-900/30 px-1.5 py-0.5 rounded"
              >
                {tag}
              </span>
            ))}
            <span className="text-[7px] font-mono text-cyan-700 ml-auto">
              {(entry.type || "html").toUpperCase()}
            </span>
          </div>
        </button>
      ))}
    </div>
  );
}
