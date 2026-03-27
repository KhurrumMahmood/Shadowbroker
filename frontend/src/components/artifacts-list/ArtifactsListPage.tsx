"use client";

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, Crosshair, MessageSquare } from "lucide-react";
import Link from "next/link";
import ArtifactPanel from "@/components/ArtifactPanel";
import ArtifactSidebar from "./ArtifactSidebar";
import DatasetSelector from "./DatasetSelector";
import FakeChatPanel from "./FakeChatPanel";
import { getDummyData, getDatasets, type DatasetEntry } from "@/artifacts/_shared/dummyData";

export interface SelectedArtifact {
  name: string;
  title: string;
  version: number;
  type: "html" | "react";
}

export default function ArtifactsListPage() {
  const [selected, setSelected] = useState<SelectedArtifact | null>(null);
  const [artifactData, setArtifactData] = useState<unknown>(null);
  const [datasetKey, setDatasetKey] = useState("default");
  const [loading, setLoading] = useState(false);
  const [datasets, setDatasets] = useState<readonly DatasetEntry[]>([]);
  const [chatVisible, setChatVisible] = useState(true);

  const loadData = useCallback(async (artifactName: string, dsKey: string) => {
    setLoading(true);
    try {
      const ds = await getDatasets(artifactName);
      setDatasets(ds);
      const data = await getDummyData(artifactName, dsKey);
      setArtifactData(data ?? null);
    } catch {
      setDatasets([]);
      setArtifactData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleSelect = useCallback((artifact: SelectedArtifact) => {
    if (selected?.name === artifact.name) return;
    setSelected(artifact);
    setDatasetKey("default");
    if (artifact.type === "react") {
      loadData(artifact.name, "default");
    } else {
      setDatasets([]);
      setArtifactData(null);
    }
  }, [selected, loadData]);

  const handleDatasetChange = useCallback((key: string) => {
    setDatasetKey(key);
    if (selected?.type === "react") {
      loadData(selected.name, key);
    }
  }, [selected, loadData]);

  const handleClose = useCallback(() => {
    setSelected(null);
    setArtifactData(null);
  }, []);

  return (
    <div className="h-screen bg-black text-[var(--text-primary)] flex flex-col hud-zone">
      {/* Header */}
      <motion.header
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="h-12 flex items-center justify-between px-6 border-b border-cyan-800/40 shrink-0"
      >
        <div className="flex items-center gap-3">
          <Crosshair size={16} className="text-cyan-400" />
          <h1 className="text-sm font-bold tracking-[0.3em] font-mono text-[var(--text-primary)]">
            ARTIFACTS <span className="text-cyan-400">{"// "}</span>SHOWCASE
          </h1>
        </div>
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={() => setChatVisible((v) => !v)}
            className={`flex items-center gap-1.5 text-[8px] font-mono tracking-[0.15em] uppercase transition-colors ${
              chatVisible ? "text-cyan-400" : "text-cyan-700 hover:text-cyan-500"
            }`}
          >
            <MessageSquare size={10} />
            Chat
          </button>
          <Link
            href="/"
            className="flex items-center gap-1.5 text-[8px] font-mono tracking-[0.15em] text-cyan-500 hover:text-cyan-300 transition-colors uppercase"
          >
            <ArrowLeft size={10} />
            Dashboard
          </Link>
        </div>
      </motion.header>

      {/* Three-column layout */}
      <div
        className="flex-1 min-h-0 grid transition-[grid-template-columns] duration-300"
        style={{
          gridTemplateColumns: chatVisible ? "280px 1fr 320px" : "280px 1fr",
        }}
      >
        {/* Left: Artifact sidebar */}
        <motion.div
          initial={{ opacity: 0, x: -12 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3, delay: 0.1 }}
        >
          <ArtifactSidebar selected={selected} onSelect={handleSelect} />
        </motion.div>

        {/* Center: Dataset selector + artifact preview */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3, delay: 0.15 }}
          className={`flex flex-col min-h-0 ${chatVisible ? "border-r border-cyan-800/40" : ""}`}
        >
          {/* Dataset selector bar */}
          <div className="px-4 py-2 border-b border-cyan-800/40 shrink-0">
            <DatasetSelector
              artifactType={selected?.type ?? null}
              datasets={datasets}
              selected={datasetKey}
              onSelect={handleDatasetChange}
            />
          </div>

          {/* Artifact preview area */}
          <div className="flex-1 min-h-0 relative">
            <AnimatePresence mode="wait">
              {selected ? (
                <motion.div
                  key={selected.name}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="h-full"
                >
                  <ArtifactPanel
                    artifactId={selected.name}
                    artifactTitle={selected.title}
                    artifactVersion={selected.version}
                    artifactType={selected.type}
                    registryName={selected.name}
                    onClose={handleClose}
                    data={artifactData}
                    sidePaneMode
                  />
                </motion.div>
              ) : (
                <motion.div
                  key="empty"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="h-full"
                >
                  <EmptyState />
                </motion.div>
              )}
            </AnimatePresence>
            {loading && (
              <div className="absolute inset-0 flex items-center justify-center bg-black/60">
                <span className="text-[9px] font-mono tracking-[0.2em] text-cyan-600 animate-pulse">
                  LOADING FIXTURE DATA...
                </span>
              </div>
            )}
          </div>
        </motion.div>

        {/* Right: Fake chat panel (toggleable) */}
        <AnimatePresence>
          {chatVisible && (
            <motion.div
              initial={{ opacity: 0, x: 12 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 12 }}
              transition={{ duration: 0.2 }}
              className="min-h-0 overflow-hidden"
            >
              <FakeChatPanel selectedArtifact={selected?.name ?? null} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="h-full flex flex-col items-center justify-center gap-3 text-center px-8">
      <Crosshair size={24} className="text-cyan-800" />
      <p className="text-[10px] font-mono tracking-[0.2em] text-cyan-600 uppercase">
        Select an Artifact
      </p>
      <p className="text-[8px] font-mono text-cyan-800 max-w-xs leading-relaxed">
        Choose an artifact from the registry to preview it with sample data.
        React artifacts load bundled fixtures. HTML artifacts require the backend.
      </p>
    </div>
  );
}
