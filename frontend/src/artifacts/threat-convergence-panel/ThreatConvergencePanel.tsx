"use client";

import type { CSSProperties } from "react";
import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import * as d3 from "d3";
import { useArtifactData } from "@/artifacts/_shared/useArtifactData";

/* ── Data interfaces ── */

interface MilitaryFlight {
  callsign?: string;
  registration?: string;
  type?: string;
  aircraft_type?: string;
  lat?: number;
  lng?: number;
  lon?: number;
  latitude?: number;
  longitude?: number;
}

interface GdeltEvent {
  event_type?: string;
  EventCode?: string;
  goldstein_scale?: number;
  GoldsteinScale?: number;
  lat?: number;
  lng?: number;
  lon?: number;
  latitude?: number;
  longitude?: number;
}

interface JammingZone {
  lat?: number;
  lng?: number;
  lon?: number;
  latitude?: number;
  longitude?: number;
  radius?: number;
}

interface FireDetection {
  lat?: number;
  lng?: number;
  lon?: number;
  latitude?: number;
  longitude?: number;
  brightness?: number;
  bright_ti4?: number;
}

interface Ship {
  name?: string;
  shipName?: string;
  type?: string;
  shipType?: string;
  lat?: number;
  lng?: number;
  lon?: number;
  latitude?: number;
  longitude?: number;
}

interface ConvergenceData {
  military_flights?: MilitaryFlight[];
  gdelt_events?: GdeltEvent[];
  gps_jamming?: JammingZone[];
  fires?: FireDetection[];
  ships?: Ship[];
}

/* ── Domain definitions ── */

interface DomainDef {
  label: string;
  color: string;
}

const DOMAINS: Record<string, DomainDef> = {
  military: { label: "Military", color: "#facc15" },
  conflict: { label: "Conflict", color: "#f87171" },
  fire:     { label: "Fire",     color: "#ff6b35" },
  jamming:  { label: "Jamming",  color: "#a78bfa" },
  maritime: { label: "Maritime", color: "#60a5fa" },
};

const DOMAIN_KEYS = Object.keys(DOMAINS);

/* ── Named regions for reverse geocoding ── */

const NAMED_REGIONS = [
  { name: "Strait of Hormuz",      lat: 26.5,  lng: 56.5,  r: 4 },
  { name: "Eastern Mediterranean", lat: 34.5,  lng: 33.0,  r: 5 },
  { name: "South China Sea",       lat: 14.0,  lng: 114.0, r: 8 },
  { name: "Taiwan Strait",         lat: 24.5,  lng: 119.0, r: 3 },
  { name: "Baltic Sea",            lat: 58.0,  lng: 20.0,  r: 5 },
  { name: "Black Sea",             lat: 43.5,  lng: 34.0,  r: 5 },
  { name: "Red Sea",               lat: 20.0,  lng: 38.5,  r: 5 },
  { name: "Suez Canal",            lat: 30.5,  lng: 32.3,  r: 2 },
  { name: "Bab el-Mandeb",         lat: 12.5,  lng: 43.3,  r: 3 },
  { name: "Gulf of Aden",          lat: 12.0,  lng: 47.0,  r: 4 },
  { name: "Persian Gulf",          lat: 27.0,  lng: 51.0,  r: 4 },
  { name: "Arabian Sea",           lat: 18.0,  lng: 63.0,  r: 6 },
  { name: "East China Sea",        lat: 30.0,  lng: 126.0, r: 5 },
  { name: "Sea of Japan",          lat: 40.0,  lng: 135.0, r: 5 },
  { name: "Malacca Strait",        lat: 3.0,   lng: 100.5, r: 3 },
  { name: "Bay of Bengal",         lat: 15.0,  lng: 87.0,  r: 6 },
  { name: "North Sea",             lat: 56.0,  lng: 3.0,   r: 5 },
  { name: "Norwegian Sea",         lat: 66.0,  lng: 2.0,   r: 5 },
  { name: "Barents Sea",           lat: 73.0,  lng: 35.0,  r: 6 },
  { name: "Panama Canal",          lat: 9.0,   lng: -79.5, r: 2 },
  { name: "Caribbean Sea",         lat: 15.0,  lng: -73.0, r: 8 },
  { name: "Gulf of Mexico",        lat: 25.0,  lng: -90.0, r: 6 },
  { name: "Western Pacific",       lat: 20.0,  lng: 140.0, r: 8 },
  { name: "Indian Ocean",          lat: -5.0,  lng: 72.0,  r: 10 },
  { name: "Central Africa",        lat: 2.0,   lng: 22.0,  r: 8 },
  { name: "Horn of Africa",        lat: 8.0,   lng: 45.0,  r: 5 },
  { name: "Sahel Region",          lat: 15.0,  lng: 5.0,   r: 8 },
  { name: "Eastern Ukraine",       lat: 48.5,  lng: 37.5,  r: 4 },
  { name: "Caucasus Region",       lat: 42.0,  lng: 44.0,  r: 4 },
  { name: "Korean Peninsula",      lat: 37.5,  lng: 127.0, r: 4 },
  { name: "Philippine Sea",        lat: 18.0,  lng: 130.0, r: 6 },
  { name: "Mozambique Channel",    lat: -18.0, lng: 42.0,  r: 5 },
  { name: "Gulf of Guinea",        lat: 3.0,   lng: 3.0,   r: 5 },
  { name: "South Atlantic",        lat: -30.0, lng: -15.0, r: 10 },
  { name: "North Atlantic",        lat: 45.0,  lng: -30.0, r: 10 },
  { name: "Arctic Ocean",          lat: 80.0,  lng: 0.0,   r: 12 },
];

/* ── Utility functions ── */

function safeNum(v: unknown): number {
  return typeof v === "number" && isFinite(v) ? v : 0;
}

function safeLat(obj: { lat?: number; latitude?: number }): number {
  return safeNum(obj.lat ?? obj.latitude);
}

function safeLng(obj: { lng?: number; lon?: number; longitude?: number }): number {
  return safeNum(obj.lng ?? obj.longitude ?? obj.lon);
}

function getRegionName(lat: number, lng: number): string {
  let best: string | null = null;
  let bestDist = Infinity;
  for (const r of NAMED_REGIONS) {
    const d = Math.sqrt((lat - r.lat) ** 2 + (lng - r.lng) ** 2);
    if (d < r.r && d < bestDist) {
      bestDist = d;
      best = r.name;
    }
  }
  if (best) return best;
  const ns = lat >= 0 ? "N" : "S";
  const ew = lng >= 0 ? "E" : "W";
  return `${Math.abs(Math.round(lat))}${ns} ${Math.abs(Math.round(lng))}${ew}`;
}

/* ── Spatial clustering ── */

const CELL_SIZE = 2;

function cellKey(lat: number, lng: number): string {
  const cLat = Math.floor(lat / CELL_SIZE) * CELL_SIZE;
  const cLng = Math.floor(lng / CELL_SIZE) * CELL_SIZE;
  return `${cLat},${cLng}`;
}

function parseCellKey(key: string): { lat: number; lng: number } {
  const [lat, lng] = key.split(",").map(Number);
  return { lat: lat + CELL_SIZE / 2, lng: lng + CELL_SIZE / 2 };
}

type Severity = "critical" | "elevated" | "normal";

interface EntityInfo {
  name: string;
  type: string;
}

interface ConvergenceZone {
  key: string;
  lat: number;
  lng: number;
  regionName: string;
  domainCount: number;
  totalCount: number;
  score: number;
  domains: Record<string, boolean>;
  events: Record<string, EntityInfo[]>;
  severity: Severity;
}

function computeConvergence(data: ConvergenceData, activeFilters: Record<string, boolean>): ConvergenceZone[] {
  const cells: Record<string, {
    domains: Record<string, boolean>;
    events: Record<string, EntityInfo[]>;
    totalCount: number;
    lat: number;
    lng: number;
  }> = {};

  function ensureCell(lat: number, lng: number) {
    const key = cellKey(lat, lng);
    if (!cells[key]) {
      const center = parseCellKey(key);
      cells[key] = { domains: {}, events: {}, totalCount: 0, lat: center.lat, lng: center.lng };
    }
    return cells[key];
  }

  function addEvent(domain: string, lat: number, lng: number, entity: EntityInfo) {
    if (!activeFilters[domain]) return;
    if (lat === 0 && lng === 0) return;
    if (lat < -90 || lat > 90 || lng < -180 || lng > 180) return;
    const cell = ensureCell(lat, lng);
    cell.domains[domain] = true;
    if (!cell.events[domain]) cell.events[domain] = [];
    cell.events[domain].push(entity);
    cell.totalCount++;
  }

  // Military flights
  for (const f of data.military_flights || []) {
    addEvent("military", safeLat(f), safeLng(f), {
      name: f.callsign || f.registration || "UNKNOWN",
      type: f.type || f.aircraft_type || "MIL",
    });
  }

  // GDELT conflict events
  for (const g of data.gdelt_events || []) {
    addEvent("conflict", safeLat(g), safeLng(g), {
      name: g.event_type || g.EventCode || "CONFLICT",
      type: `GOLDSTEIN:${g.goldstein_scale ?? g.GoldsteinScale ?? "?"}`,
    });
  }

  // GPS jamming
  for (const j of data.gps_jamming || []) {
    addEvent("jamming", safeLat(j), safeLng(j), {
      name: "JAMMING ZONE",
      type: `R:${j.radius ?? "?"}km`,
    });
  }

  // Fires
  for (const fi of data.fires || []) {
    addEvent("fire", safeLat(fi), safeLng(fi), {
      name: "FIRE",
      type: `BRT:${fi.brightness ?? fi.bright_ti4 ?? "?"}`,
    });
  }

  // Ships — military always count, commercial only if >10 in cell (congestion)
  const shipCells: Record<string, Ship[]> = {};
  for (const s of data.ships || []) {
    const sLat = safeLat(s);
    const sLng = safeLng(s);
    if (sLat === 0 && sLng === 0) continue;
    const ck = cellKey(sLat, sLng);
    if (!shipCells[ck]) shipCells[ck] = [];
    shipCells[ck].push(s);
  }

  for (const ck of Object.keys(shipCells)) {
    const cellShips = shipCells[ck];
    for (const ms of cellShips) {
      const st = (ms.type || ms.shipType || "").toString().toLowerCase();
      if (st.includes("military") || st.includes("navy") || st.includes("war") || st === "35" || st === "55") {
        addEvent("military", safeLat(ms), safeLng(ms), {
          name: ms.name || ms.shipName || "WARSHIP",
          type: "NAVAL",
        });
      }
    }
    if (cellShips.length > 10 && activeFilters.maritime) {
      const center = parseCellKey(ck);
      addEvent("maritime", center.lat, center.lng, {
        name: `${cellShips.length} VESSELS`,
        type: "CONGESTION",
      });
    }
  }

  // Build convergence zones: cells with 3+ domains
  const zones: ConvergenceZone[] = [];
  for (const key of Object.keys(cells)) {
    const cell = cells[key];
    const domainCount = Object.keys(cell.domains).length;
    if (domainCount >= 3) {
      const score = domainCount * cell.totalCount;
      zones.push({
        key,
        lat: cell.lat,
        lng: cell.lng,
        regionName: getRegionName(cell.lat, cell.lng),
        domainCount,
        totalCount: cell.totalCount,
        score,
        domains: cell.domains,
        events: cell.events,
        severity: domainCount >= 5 ? "critical" : domainCount >= 4 ? "elevated" : "normal",
      });
    }
  }

  zones.sort((a, b) => b.score - a.score);
  return zones.slice(0, 8);
}

const SEVERITY_COLORS: Record<Severity, { solid: string; dim: string }> = {
  critical: { solid: "#f87171", dim: "rgba(248,113,113,0.15)" },
  elevated: { solid: "#fbbf24", dim: "rgba(251,191,36,0.12)" },
  normal:   { solid: "#22d3ee", dim: "rgba(34,211,238,0.10)" },
};

function severityColor(s: Severity): string {
  return SEVERITY_COLORS[s].solid;
}

function severityColorDim(s: Severity): string {
  return SEVERITY_COLORS[s].dim;
}

function badgeClass(severity: Severity): string {
  return `sb-badge-${severity}`;
}

const SECTION_LABEL: CSSProperties = {
  fontSize: 8,
  letterSpacing: "0.15em",
  textTransform: "uppercase",
  color: "rgba(243,244,246,0.5)",
  marginBottom: 3,
};

/* ── Component ── */

interface Props {
  initialData?: ConvergenceData;
}

export default function ThreatConvergencePanel({ initialData }: Props) {
  const data = useArtifactData<ConvergenceData>(initialData);
  const vizRef = useRef<HTMLDivElement>(null);
  const simulationRef = useRef<d3.Simulation<d3.SimulationNodeDatum, undefined> | null>(null);
  const [activeFilters, setActiveFilters] = useState<Record<string, boolean>>(() => {
    const f: Record<string, boolean> = {};
    DOMAIN_KEYS.forEach((k) => { f[k] = true; });
    return f;
  });
  const [selectedZone, setSelectedZone] = useState<ConvergenceZone | null>(null);
  const [exportLabel, setExportLabel] = useState("EXPORT BRIEF");

  const zones = useMemo(() => {
    if (!data) return [];
    return computeConvergence(data, activeFilters);
  }, [data, activeFilters]);

  // Sync selectedZone when zones recompute (data refresh or filter change)
  useEffect(() => {
    if (selectedZone) {
      const updated = zones.find((z) => z.key === selectedZone.key);
      setSelectedZone(updated ?? (zones.length > 0 ? zones[0] : null));
    } else if (zones.length > 0) {
      setSelectedZone(zones[0]);
    }
  }, [zones]); // eslint-disable-line react-hooks/exhaustive-deps

  const toggleFilter = useCallback((key: string) => {
    setActiveFilters((prev) => ({ ...prev, [key]: !prev[key] }));
  }, []);

  // Re-trigger D3 when container gets real dimensions after animation
  const [vizSize, setVizSize] = useState<{ w: number; h: number }>({ w: 0, h: 0 });
  useEffect(() => {
    const el = vizRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        const { width, height } = entry.contentRect;
        if (width > 50 && height > 50) {
          setVizSize((prev) => (prev.w === Math.round(width) && prev.h === Math.round(height) ? prev : { w: Math.round(width), h: Math.round(height) }));
        }
      }
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // D3 bubble visualization
  useEffect(() => {
    const panel = vizRef.current;
    if (!panel || vizSize.w === 0) return;

    // Clean up
    const oldSvg = panel.querySelector("svg");
    if (oldSvg) oldSvg.remove();
    if (simulationRef.current) simulationRef.current.stop();

    if (zones.length === 0) return;

    const width = vizSize.w;
    const height = vizSize.h;

    const svg = d3.select(panel)
      .append("svg")
      .attr("width", width)
      .attr("height", height)
      .style("width", "100%")
      .style("height", "100%");

    const maxCount = d3.max(zones, (d) => d.totalCount) || 1;
    const rScale = d3.scaleSqrt()
      .domain([1, Math.max(maxCount, 2)])
      .range([30, Math.min(100, Math.min(width, height) / 4)]);

    interface BubbleNode extends d3.SimulationNodeDatum {
      idx: number;
      zone: ConvergenceZone;
      r: number;
    }

    const nodes: BubbleNode[] = zones.map((z, i) => ({
      idx: i,
      zone: z,
      r: rScale(z.totalCount),
      x: width / 2 + (Math.random() - 0.5) * width * 0.4,
      y: height / 2 + (Math.random() - 0.5) * height * 0.4,
    }));

    // Defs for glow filter
    const defs = svg.append("defs");
    const filter = defs.append("filter").attr("id", "glow");
    filter.append("feGaussianBlur").attr("stdDeviation", "3").attr("result", "blur");
    const feMerge = filter.append("feMerge");
    feMerge.append("feMergeNode").attr("in", "blur");
    feMerge.append("feMergeNode").attr("in", "SourceGraphic");

    const nodeG = svg.selectAll<SVGGElement, BubbleNode>(".zone-group")
      .data(nodes)
      .enter()
      .append("g")
      .attr("class", "zone-group");

    // Main circle
    nodeG.append("circle")
      .attr("class", "zone-circle")
      .attr("r", (d) => d.r)
      .attr("fill", (d) => severityColorDim(d.zone.severity))
      .attr("stroke", (d) => severityColor(d.zone.severity))
      .attr("stroke-width", 1.5)
      .attr("filter", "url(#glow)")
      .style("cursor", "pointer")
      .on("click", (_event, d) => {
        setSelectedZone(d.zone);
        svg.selectAll(".zone-circle")
          .attr("stroke-width", 1.5);
        d3.select(_event.currentTarget as SVGCircleElement)
          .attr("stroke-width", 3);
      });

    // Region name label
    nodeG.append("text")
      .attr("text-anchor", "middle")
      .attr("dy", "-0.3em")
      .attr("fill", "rgb(243,244,246)")
      .attr("font-family", "'Courier New', monospace")
      .attr("font-size", "9px")
      .attr("letter-spacing", "0.08em")
      .style("pointer-events", "none")
      .text((d) => {
        const name = d.zone.regionName;
        return name.length > 18 ? name.substring(0, 16) + ".." : name;
      });

    // Count label
    nodeG.append("text")
      .attr("text-anchor", "middle")
      .attr("dy", "1.1em")
      .attr("fill", "rgba(243,244,246,0.6)")
      .attr("font-family", "'Courier New', monospace")
      .attr("font-size", "8px")
      .style("pointer-events", "none")
      .text((d) => `${d.zone.domainCount}D / ${d.zone.totalCount} EVT`);

    // Domain pips around circle edge
    nodeG.each(function (d) {
      const g = d3.select(this);
      const activeDomains = Object.keys(d.zone.domains);
      const pipR = 4;
      const angleStep = (2 * Math.PI) / Math.max(activeDomains.length, 1);
      const startAngle = -Math.PI / 2;
      activeDomains.forEach((dk, i) => {
        const angle = startAngle + i * angleStep;
        const px = Math.cos(angle) * (d.r + pipR + 3);
        const py = Math.sin(angle) * (d.r + pipR + 3);
        g.append("circle")
          .attr("cx", px)
          .attr("cy", py)
          .attr("r", pipR)
          .attr("fill", DOMAINS[dk]?.color || "#888")
          .style("pointer-events", "none");
      });
    });

    // Force simulation
    const sim = d3.forceSimulation<BubbleNode>(nodes)
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("charge", d3.forceManyBody().strength(-30))
      .force("collision", d3.forceCollide<BubbleNode>().radius((d) => d.r + 16).strength(0.8))
      .force("x", d3.forceX(width / 2).strength(0.05))
      .force("y", d3.forceY(height / 2).strength(0.05))
      .on("tick", () => {
        nodeG.attr("transform", (d) => {
          d.x = Math.max(d.r + 10, Math.min(width - d.r - 10, d.x!));
          d.y = Math.max(d.r + 10, Math.min(height - d.r - 10, d.y!));
          return `translate(${d.x},${d.y})`;
        });
      });

    simulationRef.current = sim as unknown as d3.Simulation<d3.SimulationNodeDatum, undefined>;

    return () => {
      sim.stop();
    };
  }, [zones, vizSize]);

  const handleExport = useCallback(() => {
    if (zones.length === 0) return;
    const lines: string[] = [];
    lines.push("SHADOWBROKER THREAT CONVERGENCE BRIEF");
    lines.push(`Generated: ${new Date().toISOString()}`);
    lines.push(`Convergence Zones: ${zones.length}`);
    lines.push("===================================");
    zones.forEach((z, i) => {
      lines.push("");
      lines.push(`${i + 1}. ${z.regionName.toUpperCase()}`);
      lines.push(`   Severity: ${z.severity.toUpperCase()}`);
      lines.push(`   Domains: ${Object.keys(z.domains).join(", ")}`);
      lines.push(`   Total Events: ${z.totalCount}`);
      lines.push(`   Score: ${z.score}`);
      lines.push(`   Coordinates: ${z.lat.toFixed(2)}, ${z.lng.toFixed(2)}`);
      const sigParts = Object.keys(z.domains).map((dk) => dk.toUpperCase().substring(0, 3));
      lines.push(`   Signature: ${sigParts.join("+")}`);
    });

    navigator.clipboard.writeText(lines.join("\n")).then(() => {
      setExportLabel("COPIED");
      setTimeout(() => setExportLabel("EXPORT BRIEF"), 2000);
    });
  }, [zones]);

  const timestamp = useMemo(() => {
    const now = new Date();
    return now.toISOString().replace("T", " ").substring(0, 19) + " UTC";
  }, [data]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div style={{
      fontFamily: "var(--sb-font-mono, 'Courier New', monospace)",
      fontSize: 11,
      letterSpacing: "0.05em",
      color: "var(--sb-text-primary, rgb(243,244,246))",
      display: "flex",
      flexDirection: "column",
      height: "100%",
      minHeight: 0,
    }}>
      {/* Header */}
      <div style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "10px 0 12px",
        borderBottom: "1px solid rgba(8,145,178,0.4)",
        marginBottom: 10,
      }}>
        <div>
          <div style={{
            fontSize: 16,
            letterSpacing: "0.2em",
            textTransform: "uppercase",
            color: "#22d3ee",
            textShadow: "0 0 10px rgba(34,211,238,0.4)",
          }}>
            THREAT CONVERGENCE PANEL
          </div>
          <div style={{ fontSize: 9, letterSpacing: "0.15em", color: "rgba(243,244,246,0.5)", textTransform: "uppercase" }}>
            CROSS-DOMAIN CORRELATION ENGINE
          </div>
        </div>
        <div style={{ fontSize: 9, color: "rgba(243,244,246,0.5)", letterSpacing: "0.08em" }}>
          {timestamp}
        </div>
      </div>

      {/* Domain filters */}
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 10, alignItems: "center" }}>
        <span style={{ fontSize: 9, color: "rgba(243,244,246,0.5)", letterSpacing: "0.12em", textTransform: "uppercase", marginRight: 4 }}>
          Domains:
        </span>
        {DOMAIN_KEYS.map((k) => (
          <button
            key={k}
            type="button"
            onClick={() => toggleFilter(k)}
            style={{
              background: activeFilters[k] ? "rgba(34,211,238,0.08)" : "rgba(255,255,255,0.05)",
              border: `1px solid ${activeFilters[k] ? "rgba(34,211,238,0.6)" : "rgba(255,255,255,0.15)"}`,
              color: "var(--sb-text-primary, rgb(243,244,246))",
              fontFamily: "inherit",
              fontSize: 8,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              padding: "3px 8px",
              cursor: "pointer",
              borderRadius: 2,
              display: "flex",
              alignItems: "center",
              gap: 4,
              opacity: activeFilters[k] ? 1 : 0.35,
            }}
          >
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: DOMAINS[k].color, display: "inline-block" }} />
            {DOMAINS[k].label}
          </button>
        ))}
        <button
          type="button"
          onClick={handleExport}
          style={{
            marginLeft: "auto",
            background: exportLabel === "COPIED" ? "rgba(74,222,128,0.15)" : "rgba(34,211,238,0.1)",
            border: `1px solid ${exportLabel === "COPIED" ? "#4ade80" : "rgba(34,211,238,0.6)"}`,
            color: exportLabel === "COPIED" ? "#4ade80" : "#22d3ee",
            fontFamily: "inherit",
            fontSize: 8,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            padding: "3px 10px",
            cursor: "pointer",
            borderRadius: 2,
          }}
        >
          {exportLabel}
        </button>
      </div>

      {/* Main area */}
      <div style={{ display: "flex", gap: 12, flex: 1, minHeight: 0 }}>
        {/* Viz panel */}
        <div
          ref={vizRef}
          style={{
            flex: "0 0 60%",
            background: "var(--sb-bg-secondary, rgb(5,5,8))",
            border: "1px solid rgba(8,145,178,0.4)",
            borderRadius: 4,
            position: "relative",
            overflow: "hidden",
            minHeight: 400,
          }}
        >
          {/* Top accent line */}
          <div style={{
            position: "absolute",
            top: 0, left: 0, right: 0,
            height: 1,
            background: "linear-gradient(90deg, transparent, #22d3ee, transparent)",
            zIndex: 1,
          }} />
          {zones.length === 0 && (
            <div style={{
              position: "absolute",
              top: 0, left: 0, right: 0, bottom: 0,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: 12,
              zIndex: 10,
            }}>
              <span style={{
                fontSize: 12,
                letterSpacing: "0.2em",
                textTransform: "uppercase",
                color: "#22d3ee",
              }}>
                {data ? "NO CONVERGENCE ZONES DETECTED" : "CORRELATING FEEDS..."}
              </span>
            </div>
          )}
        </div>

        {/* Detail panel */}
        <div style={{
          flex: "0 0 calc(40% - 12px)",
          background: "var(--sb-bg-secondary, rgb(5,5,8))",
          border: "1px solid rgba(8,145,178,0.4)",
          borderRadius: 4,
          position: "relative",
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
        }}>
          {/* Top accent line */}
          <div style={{
            position: "absolute",
            top: 0, left: 0, right: 0,
            height: 1,
            background: "linear-gradient(90deg, transparent, #22d3ee, transparent)",
          }} />

          {/* Detail header */}
          <div style={{ padding: "14px 16px 10px", borderBottom: "1px solid rgba(8,145,178,0.4)" }}>
            <div style={{ fontSize: 9, letterSpacing: "0.15em", textTransform: "uppercase", color: "rgba(243,244,246,0.5)", marginBottom: 4 }}>
              Selected Zone
            </div>
            <div style={{ fontSize: 14, letterSpacing: "0.12em", color: "#22d3ee", textTransform: "uppercase", textShadow: "0 0 8px rgba(34,211,238,0.3)" }}>
              {selectedZone?.regionName || "---"}
            </div>
          </div>

          {/* Detail body */}
          <div style={{ flex: 1, overflowY: "auto", padding: "12px 16px" }}>
            {!selectedZone ? (
              <div style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                height: "100%",
                color: "rgba(243,244,246,0.5)",
                fontSize: 10,
                letterSpacing: "0.15em",
                textTransform: "uppercase",
              }}>
                SELECT A CONVERGENCE ZONE
              </div>
            ) : (
              <>
                {/* Convergence Score */}
                <div style={{ marginBottom: 14 }}>
                  <div style={SECTION_LABEL}>
                    Convergence Score
                  </div>
                  <div style={{ fontSize: 20, fontWeight: "bold", letterSpacing: "0.08em" }}>
                    {selectedZone.score}
                  </div>
                  <span className={badgeClass(selectedZone.severity)} style={{ display: "inline-block", marginTop: 4 }}>
                    {selectedZone.severity.toUpperCase()}
                  </span>
                </div>

                {/* Active Domains */}
                <div style={{ marginBottom: 14 }}>
                  <div style={SECTION_LABEL}>
                    Active Domains
                  </div>
                  <div style={{ fontSize: 11 }}>{selectedZone.domainCount} / {DOMAIN_KEYS.length}</div>
                </div>

                {/* Convergence Signature */}
                <div style={{ marginBottom: 14 }}>
                  <div style={SECTION_LABEL}>
                    Convergence Signature
                  </div>
                  <span style={{
                    display: "inline-block",
                    padding: "4px 8px",
                    borderRadius: 2,
                    fontSize: 8,
                    letterSpacing: "0.1em",
                    textTransform: "uppercase",
                    fontWeight: "bold",
                    background: "rgba(34,211,238,0.1)",
                    border: "1px solid rgba(34,211,238,0.6)",
                    color: "#22d3ee",
                  }}>
                    {Object.keys(selectedZone.domains).map((dk) => dk.toUpperCase().substring(0, 3)).join(" + ")}
                  </span>
                </div>

                {/* Coordinates */}
                <div style={{ marginBottom: 14 }}>
                  <div style={SECTION_LABEL}>
                    Coordinates
                  </div>
                  <div style={{ fontSize: 11 }}>{selectedZone.lat.toFixed(2)}, {selectedZone.lng.toFixed(2)} (cell {CELL_SIZE}&deg;)</div>
                </div>

                {/* Total Events */}
                <div style={{ marginBottom: 14 }}>
                  <div style={SECTION_LABEL}>
                    Total Events
                  </div>
                  <div style={{ fontSize: 11 }}>{selectedZone.totalCount}</div>
                </div>

                {/* Domain Breakdown */}
                <div style={{ marginBottom: 14 }}>
                  <div style={SECTION_LABEL}>
                    DOMAIN BREAKDOWN
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 4 }}>
                    {Object.keys(selectedZone.events).map((dk) => {
                      const items = selectedZone.events[dk];
                      const dInfo = DOMAINS[dk] || { label: dk, color: "#888" };
                      return (
                        <div key={dk}>
                          <div style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 6,
                            padding: "4px 8px",
                            background: "rgba(255,255,255,0.02)",
                            borderRadius: 2,
                            borderLeft: `2px solid ${dInfo.color}`,
                          }}>
                            <span style={{ width: 6, height: 6, borderRadius: "50%", background: dInfo.color, flexShrink: 0 }} />
                            <span style={{ fontSize: 9, letterSpacing: "0.1em", textTransform: "uppercase", flex: 1 }}>
                              {dInfo.label}
                            </span>
                            <span style={{ fontSize: 12, fontWeight: "bold", color: "#22d3ee" }}>
                              {items.length}
                            </span>
                          </div>
                          <div style={{ marginTop: 4, paddingLeft: 14 }}>
                            {items.slice(0, 5).map((ent, ei) => (
                              <div key={ei} style={{ fontSize: 8, color: "rgba(243,244,246,0.5)", lineHeight: 1.6 }}>
                                &bull; {ent.name} [{ent.type}]
                              </div>
                            ))}
                            {items.length > 5 && (
                              <div style={{ fontSize: 8, color: "rgba(243,244,246,0.5)", opacity: 0.5 }}>
                                + {items.length - 5} more
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Detail footer */}
          <div style={{
            padding: "8px 16px",
            borderTop: "1px solid rgba(8,145,178,0.4)",
            fontSize: 8,
            color: "rgba(243,244,246,0.5)",
            letterSpacing: "0.1em",
            textAlign: "center",
            textTransform: "uppercase",
          }}>
            THREAT CONVERGENCE PANEL v1
          </div>
        </div>
      </div>
    </div>
  );
}
