"use client";

import React, { useState, useMemo, useCallback, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, X, ChevronLeft, ChevronRight, Minimize2, Maximize2 } from "lucide-react";
import type { DashboardData, SelectedEntity } from "@/types/dashboard";
import { getEntities, toSelectedEntity, entityDisplayName } from "@/hooks/useCategoryCycler";
import { buildSearchIndex, searchWithIndex } from "@/utils/layerSearch";

interface LayerSearchPaneProps {
  layerId: string;
  layerName: string;
  data: DashboardData;
  onFlyTo: (lat: number, lng: number) => void;
  onEntityClick: (entity: SelectedEntity) => void;
  onClose: () => void;
}

export default function LayerSearchPane({
  layerId,
  layerName,
  data,
  onFlyTo,
  onEntityClick,
  onClose,
}: LayerSearchPaneProps) {
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [minimized, setMinimized] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Dragging state
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const dragRef = useRef<{ startX: number; startY: number; origX: number; origY: number } | null>(null);

  const { items: allItems, entityType } = useMemo(
    () => getEntities(layerId, data),
    [layerId, data],
  );

  // Pre-compute search index once when items change (not on every keystroke)
  const searchIndex = useMemo(
    () => buildSearchIndex(allItems),
    [allItems],
  );

  const results = useMemo(
    () => searchWithIndex(allItems, searchIndex, query),
    [allItems, searchIndex, query],
  );

  // Reset selection when results change
  useEffect(() => {
    setSelectedIndex(0);
  }, [results.length, query]);

  // Focus input on mount
  useEffect(() => {
    if (!minimized) inputRef.current?.focus();
  }, [minimized]);

  const flyToEntity = useCallback(
    (item: any) => {
      const lat = item.lat ?? item.geometry?.coordinates?.[1];
      const lng = item.lng ?? item.lon ?? item.geometry?.coordinates?.[0];
      if (lat != null && lng != null) onFlyTo(lat, lng);
      onEntityClick(toSelectedEntity(item, entityType));
    },
    [onFlyTo, onEntityClick, entityType],
  );

  const selectAndFly = useCallback(
    (idx: number) => {
      if (idx < 0 || idx >= results.length) return;
      setSelectedIndex(idx);
      flyToEntity(results[idx]);
    },
    [results, flyToEntity],
  );

  const goPrev = useCallback(() => {
    if (results.length === 0) return;
    const idx = (selectedIndex - 1 + results.length) % results.length;
    selectAndFly(idx);
  }, [selectedIndex, results.length, selectAndFly]);

  const goNext = useCallback(() => {
    if (results.length === 0) return;
    const idx = (selectedIndex + 1) % results.length;
    selectAndFly(idx);
  }, [selectedIndex, results.length, selectAndFly]);

  // Keyboard navigation
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "ArrowDown") { e.preventDefault(); goNext(); }
      else if (e.key === "ArrowUp") { e.preventDefault(); goPrev(); }
      else if (e.key === "Enter" && results.length > 0) {
        e.preventDefault();
        selectAndFly(selectedIndex);
      }
      else if (e.key === "Escape") { onClose(); }
    },
    [goNext, goPrev, selectAndFly, selectedIndex, results.length, onClose],
  );

  // Scroll selected item into view
  useEffect(() => {
    if (!listRef.current) return;
    const el = listRef.current.children[selectedIndex] as HTMLElement | undefined;
    el?.scrollIntoView({ block: "nearest" });
  }, [selectedIndex]);

  // Drag handlers (with cleanup ref to prevent listener leaks on unmount)
  const dragCleanupRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    return () => { dragCleanupRef.current?.(); };
  }, []);

  const onDragStart = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      dragRef.current = { startX: e.clientX, startY: e.clientY, origX: offset.x, origY: offset.y };
      const onMove = (ev: MouseEvent) => {
        if (!dragRef.current) return;
        setOffset({
          x: dragRef.current.origX + (ev.clientX - dragRef.current.startX),
          y: dragRef.current.origY + (ev.clientY - dragRef.current.startY),
        });
      };
      const onUp = () => {
        dragRef.current = null;
        dragCleanupRef.current = null;
        window.removeEventListener("mousemove", onMove);
        window.removeEventListener("mouseup", onUp);
      };
      window.addEventListener("mousemove", onMove);
      window.addEventListener("mouseup", onUp);
      dragCleanupRef.current = onUp;
    },
    [offset],
  );

  /** Produce a display label for an entity */
  const entityLabel = (item: any): string =>
    entityDisplayName(item) || `${item.lat?.toFixed(2)},${item.lng?.toFixed(2)}`;

  const entitySub = (item: any): string => {
    const parts: string[] = [];
    if (item.country) parts.push(item.country);
    if (item.type) parts.push(item.type);
    if (item.model) parts.push(item.model);
    if (item.airline) parts.push(item.airline);
    if (item.registration) parts.push(item.registration);
    return parts.slice(0, 3).join(" · ");
  };

  // ── Minimized bar ──
  if (minimized) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1, x: offset.x, y: offset.y }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="absolute left-[344px] top-24 z-[300] pointer-events-auto hud-zone"
      >
        <div className="flex items-center gap-2 bg-black/90 border border-cyan-800/50 rounded-lg px-3 py-2 backdrop-blur-md shadow-lg">
          <div
            className="cursor-grab active:cursor-grabbing text-[var(--text-muted)] hover:text-cyan-400 transition-colors"
            onMouseDown={onDragStart}
            title="Drag to reposition"
          >
            <Search size={12} />
          </div>
          <button type="button" onClick={goPrev} className="w-5 h-5 flex items-center justify-center rounded border border-cyan-500/30 text-cyan-400 hover:bg-cyan-950/30 transition-colors">
            <ChevronLeft size={10} />
          </button>
          <span className="text-[9px] text-cyan-400 font-mono tracking-wider min-w-[60px] text-center">
            {results.length > 0 ? `${selectedIndex + 1} / ${results.length.toLocaleString()}` : "0 / 0"}
          </span>
          <button type="button" onClick={goNext} className="w-5 h-5 flex items-center justify-center rounded border border-cyan-500/30 text-cyan-400 hover:bg-cyan-950/30 transition-colors">
            <ChevronRight size={10} />
          </button>
          {query && (
            <span className="text-[8px] text-[var(--text-muted)] font-mono truncate max-w-[80px]">"{query}"</span>
          )}
          <button type="button" onClick={() => setMinimized(false)} className="text-[var(--text-muted)] hover:text-cyan-400 transition-colors" title="Expand">
            <Maximize2 size={10} />
          </button>
          <button type="button" onClick={onClose} className="text-[var(--text-muted)] hover:text-red-400 transition-colors" title="Close">
            <X size={10} />
          </button>
        </div>
      </motion.div>
    );
  }

  // ── Full pane ──
  return (
    <motion.div
      initial={{ opacity: 0, x: offset.x - 20 }}
      animate={{ opacity: 1, x: offset.x, y: offset.y }}
      exit={{ opacity: 0, x: offset.x - 20 }}
      transition={{ duration: 0.2 }}
      className="absolute left-[344px] top-24 z-[300] w-72 pointer-events-auto hud-zone"
    >
      <div className="bg-black/90 border border-cyan-800/50 rounded-xl backdrop-blur-md shadow-[0_4px_30px_rgba(0,0,0,0.4)] flex flex-col max-h-[60vh] overflow-hidden">
        {/* Header — draggable */}
        <div
          className="flex items-center justify-between px-3 py-2.5 border-b border-[var(--border-primary)]/50 cursor-grab active:cursor-grabbing"
          onMouseDown={onDragStart}
        >
          <div className="flex items-center gap-2">
            <Search size={12} className="text-cyan-400" />
            <span className="text-[10px] text-cyan-400 font-mono tracking-widest font-bold truncate">{layerName.toUpperCase()}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <button type="button" onClick={() => setMinimized(true)} className="text-[var(--text-muted)] hover:text-cyan-400 transition-colors" title="Minimize">
              <Minimize2 size={12} />
            </button>
            <button type="button" onClick={onClose} className="text-[var(--text-muted)] hover:text-red-400 transition-colors" title="Close">
              <X size={12} />
            </button>
          </div>
        </div>

        {/* Search input */}
        <div className="px-3 py-2 border-b border-[var(--border-primary)]/30">
          <div className="flex items-center gap-2 bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-primary)] px-2 py-1.5 focus-within:border-cyan-500/40 transition-colors">
            <Search size={11} className="text-[var(--text-muted)] shrink-0" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Search by name, callsign, MMSI..."
              className="bg-transparent text-[11px] text-[var(--text-primary)] font-mono w-full outline-none placeholder:text-[var(--text-muted)]/50"
            />
            {query && (
              <button type="button" onClick={() => setQuery("")} className="text-[var(--text-muted)] hover:text-cyan-400 transition-colors shrink-0">
                <X size={10} />
              </button>
            )}
          </div>
          <div className="flex items-center justify-between mt-1.5">
            <span className="text-[8px] text-[var(--text-muted)] font-mono">
              {results.length.toLocaleString()} {query ? "matches" : "entities"}
            </span>
            {results.length > 0 && (
              <div className="flex items-center gap-1.5">
                <button type="button" onClick={goPrev} className="w-5 h-5 flex items-center justify-center rounded border border-cyan-500/30 text-cyan-400 hover:bg-cyan-950/30 transition-colors">
                  <ChevronLeft size={10} />
                </button>
                <span className="text-[8px] text-cyan-400 font-mono min-w-[40px] text-center">{selectedIndex + 1}/{results.length.toLocaleString()}</span>
                <button type="button" onClick={goNext} className="w-5 h-5 flex items-center justify-center rounded border border-cyan-500/30 text-cyan-400 hover:bg-cyan-950/30 transition-colors">
                  <ChevronRight size={10} />
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Results list */}
        <div ref={listRef} className="overflow-y-auto styled-scrollbar flex-1">
          {results.length === 0 && query && (
            <div className="px-3 py-6 text-center text-[10px] text-[var(--text-muted)] font-mono">
              No matches for "{query}"
            </div>
          )}
          {results.slice(0, 200).map((item, i) => {
            const isSelected = i === selectedIndex;
            return (
              <div
                key={item.icao24 || item.mmsi || item.id || item.name || `${item.lat}-${item.lng}-${i}`}
                className={`px-3 py-2 cursor-pointer border-b border-[var(--border-primary)]/20 transition-colors ${
                  isSelected
                    ? "bg-cyan-950/40 border-l-2 border-l-cyan-500"
                    : "hover:bg-[var(--bg-secondary)]/60 border-l-2 border-l-transparent"
                }`}
                onClick={() => selectAndFly(i)}
              >
                <div className={`text-[10px] font-mono font-medium truncate ${isSelected ? "text-cyan-300" : "text-[var(--text-primary)]"}`}>
                  {entityLabel(item)}
                </div>
                <div className="text-[8px] text-[var(--text-muted)] font-mono truncate mt-0.5">
                  {entitySub(item)}
                </div>
              </div>
            );
          })}
          {results.length > 200 && (
            <div className="px-3 py-2 text-[8px] text-[var(--text-muted)] font-mono text-center">
              Showing 200 of {results.length.toLocaleString()} — refine your search
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
