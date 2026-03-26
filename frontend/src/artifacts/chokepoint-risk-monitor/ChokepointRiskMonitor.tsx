"use client";

import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import * as d3 from "d3";
import { feature } from "topojson-client";
import type { Topology, GeometryCollection } from "topojson-specification";
import { useArtifactData } from "@/artifacts/_shared/useArtifactData";

/* ── Data interfaces ── */

interface Ship {
  name?: string;
  callsign?: string;
  type?: string;
  ship_type?: string;
  flag?: string;
  lat?: number;
  lng?: number;
  lon?: number;
  latitude?: number;
  longitude?: number;
}

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

interface OilPrice {
  price?: number;
  change_pct?: number;
}

interface ChokeData {
  ships?: Ship[];
  tracked_ships?: Ship[];
  military_flights?: MilitaryFlight[];
  gdelt_events?: GdeltEvent[];
  gps_jamming?: JammingZone[];
  fires?: FireDetection[];
  oil_prices?: { wti?: OilPrice; brent?: OilPrice };
}

/* ── Constants ── */

interface Chokepoint {
  id: string;
  name: string;
  lat: number;
  lng: number;
  significance: string;
}

const CHOKEPOINTS: Chokepoint[] = [
  { id: "hormuz", name: "Strait of Hormuz", lat: 26.57, lng: 56.25, significance: "21% global oil transit" },
  { id: "malacca", name: "Strait of Malacca", lat: 2.5, lng: 101.0, significance: "25% global trade volume" },
  { id: "suez", name: "Suez Canal", lat: 30.46, lng: 32.34, significance: "12% global trade" },
  { id: "bab", name: "Bab el-Mandeb", lat: 12.6, lng: 43.3, significance: "Red Sea gateway" },
  { id: "panama", name: "Panama Canal", lat: 9.08, lng: -79.68, significance: "5% global trade" },
  { id: "turkish", name: "Turkish Straits", lat: 41.1, lng: 29.05, significance: "3.3M bbl/day oil" },
];

const CONNECTIONS: [string, string][] = [
  ["hormuz", "bab"],
  ["bab", "suez"],
  ["malacca", "hormuz"],
  ["turkish", "suez"],
];

const BBOX_RADIUS = 2;

type RiskLevel = "LOW" | "NORMAL" | "ELEVATED" | "CRITICAL";

interface ChokepointStats {
  vessels: Ship[];
  vesselCount: number;
  military: (MilitaryFlight | Ship)[];
  militaryCount: number;
  conflicts: GdeltEvent[];
  conflictCount: number;
  jamming: JammingZone[];
  jammingCount: number;
  fires: FireDetection[];
  fireCount: number;
  riskScore: number;
  riskLevel: RiskLevel;
}

/* ── Utility functions ── */

function getLat(item: { lat?: number; latitude?: number }): number | null {
  return item.lat ?? item.latitude ?? null;
}

function getLng(item: { lng?: number; lon?: number; longitude?: number }): number | null {
  return item.lng ?? item.lon ?? item.longitude ?? null;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function filterByBbox<T extends Record<string, any>>(
  items: T[],
  bbox: { south: number; north: number; west: number; east: number },
): T[] {
  return items.filter((item) => {
    const lat = getLat(item);
    const lng = getLng(item);
    if (lat == null || lng == null) return false;
    return lat >= bbox.south && lat <= bbox.north && lng >= bbox.west && lng <= bbox.east;
  });
}

function calcStats(cp: Chokepoint, data: ChokeData): ChokepointStats {
  const bbox = {
    south: cp.lat - BBOX_RADIUS,
    north: cp.lat + BBOX_RADIUS,
    west: cp.lng - BBOX_RADIUS,
    east: cp.lng + BBOX_RADIUS,
  };

  const ships = filterByBbox(data.ships || [], bbox);
  const tracked = filterByBbox(data.tracked_ships || [], bbox);
  const military = filterByBbox(data.military_flights || [], bbox);
  const gdelt = filterByBbox(data.gdelt_events || [], bbox);
  const jamming = filterByBbox(data.gps_jamming || [], bbox);
  const fires = filterByBbox(data.fires || [], bbox);

  const trackedMilitary = tracked.filter((s) => {
    const t = (s.type || "").toLowerCase();
    return t.includes("navy") || t.includes("military") || t.includes("coast guard");
  });

  const allMilitary: (MilitaryFlight | Ship)[] = [...military, ...trackedMilitary];

  const milPts = Math.min(allMilitary.length * 2, 10);
  const conflictPts = Math.min(gdelt.length * 3, 15);
  const jamPts = jamming.length * 5;
  const firePts = Math.min(fires.length, 5);
  const totalRisk = milPts + conflictPts + jamPts + firePts;

  let riskLevel: RiskLevel = "LOW";
  if (totalRisk >= 20) riskLevel = "CRITICAL";
  else if (totalRisk >= 10) riskLevel = "ELEVATED";
  else if (totalRisk >= 5) riskLevel = "NORMAL";

  return {
    vessels: [...ships, ...tracked],
    vesselCount: ships.length + tracked.length,
    military: allMilitary,
    militaryCount: allMilitary.length,
    conflicts: gdelt,
    conflictCount: gdelt.length,
    jamming,
    jammingCount: jamming.length,
    fires,
    fireCount: fires.length,
    riskScore: totalRisk,
    riskLevel,
  };
}

function getBadgeColors(level: RiskLevel) {
  switch (level) {
    case "CRITICAL":
      return { bg: "rgba(248,113,113,0.2)", stroke: "rgba(248,113,113,0.4)", text: "#f87171" };
    case "ELEVATED":
      return { bg: "rgba(250,204,21,0.15)", stroke: "rgba(250,204,21,0.3)", text: "#facc15" };
    case "NORMAL":
      return { bg: "rgba(34,211,238,0.1)", stroke: "rgba(34,211,238,0.3)", text: "#22d3ee" };
    default:
      return { bg: "rgba(74,222,128,0.1)", stroke: "rgba(74,222,128,0.3)", text: "#4ade80" };
  }
}

function hexPoints(r: number): string {
  const pts: string[] = [];
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 3) * i - Math.PI / 2;
    pts.push(`${Math.cos(angle) * r},${Math.sin(angle) * r}`);
  }
  return pts.join(" ");
}

function badgeClass(level: RiskLevel): string {
  return `sb-badge-${level.toLowerCase()}`;
}

/* ── Component ── */

interface Props {
  initialData?: ChokeData;
}

export default function ChokepointRiskMonitor({ initialData }: Props) {
  const data = useArtifactData<ChokeData>(initialData);
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [copyLabel, setCopyLabel] = useState("COPY STATUS");
  const [containerSize, setContainerSize] = useState<{ w: number; h: number }>({ w: 0, h: 0 });

  // Track container size so D3 re-renders when the panel animation settles
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        const { width, height } = entry.contentRect;
        if (width > 50 && height > 50) {
          setContainerSize((prev) => (prev.w === Math.round(width) && prev.h === Math.round(height) ? prev : { w: Math.round(width), h: Math.round(height) }));
        }
      }
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const allStats = useMemo(() => {
    if (!data) return {} as Record<string, ChokepointStats>;
    const result: Record<string, ChokepointStats> = {};
    for (const cp of CHOKEPOINTS) {
      result[cp.id] = calcStats(cp, data);
    }
    return result;
  }, [data]);

  const selectedCp = selectedId ? CHOKEPOINTS.find((c) => c.id === selectedId) : null;
  const selectedStats = selectedId ? allStats[selectedId] : null;

  // D3 rendering — re-runs when container gets real dimensions
  useEffect(() => {
    const svg = svgRef.current;
    const container = containerRef.current;
    if (!svg || !container || containerSize.w === 0) return;

    const width = containerSize.w;
    const height = containerSize.h;

    const svgSel = d3.select(svg)
      .attr("width", width)
      .attr("height", height)
      .attr("viewBox", `0 0 ${width} ${height}`);

    svgSel.selectAll("*").remove();

    const projection = d3.geoNaturalEarth1()
      .scale(width / 5.8)
      .translate([width / 2, height / 2]);

    const path = d3.geoPath().projection(projection);
    const mapGroup = svgSel.append("g");

    // Load world outline
    d3.json<Topology<{ land: GeometryCollection }>>("https://cdn.jsdelivr.net/npm/world-atlas@2/land-110m.json")
      .then((world) => {
        if (!world) return;
        const land = feature(world, world.objects.land);
        mapGroup.append("path")
          .datum(land)
          .attr("d", path as never)
          .attr("fill", "rgba(255,255,255,0.015)")
          .attr("stroke", "rgba(34,211,238,0.08)")
          .attr("stroke-width", 0.5);
      })
      .catch(() => { /* render without world outline */ })
      .finally(() => {
        drawConnections(mapGroup, projection);
        drawChokepoints(mapGroup, projection);
      });

    function drawConnections(
      group: d3.Selection<SVGGElement, unknown, null, undefined>,
      proj: d3.GeoProjection,
    ) {
      const cpMap: Record<string, Chokepoint> = {};
      CHOKEPOINTS.forEach((cp) => { cpMap[cp.id] = cp; });

      for (const [fromId, toId] of CONNECTIONS) {
        const from = cpMap[fromId];
        const to = cpMap[toId];
        if (!from || !to) continue;
        const p1 = proj([from.lng, from.lat]);
        const p2 = proj([to.lng, to.lat]);
        if (!p1 || !p2) continue;

        group.append("line")
          .attr("x1", p1[0]).attr("y1", p1[1])
          .attr("x2", p2[0]).attr("y2", p2[1])
          .attr("stroke", "rgba(34,211,238,0.12)")
          .attr("stroke-width", 1)
          .attr("stroke-dasharray", "4 4")
          .attr("fill", "none");
      }
    }

    function drawChokepoints(
      group: d3.Selection<SVGGElement, unknown, null, undefined>,
      proj: d3.GeoProjection,
    ) {
      const nodeGroups = group.selectAll<SVGGElement, Chokepoint>(".chokepoint-node")
        .data(CHOKEPOINTS, (d) => d.id)
        .enter()
        .append("g")
        .attr("class", "chokepoint-node")
        .attr("data-id", (d) => d.id)
        .style("cursor", "pointer")
        .attr("transform", (d) => {
          const p = proj([d.lng, d.lat]);
          return p ? `translate(${p[0]},${p[1]})` : "translate(0,0)";
        })
        .on("click", (_event, d) => {
          setSelectedId((prev) => (prev === d.id ? null : d.id));
        });

      // Outer ring
      nodeGroups.append("circle")
        .attr("class", "node-ring")
        .attr("r", 28)
        .attr("fill", "none")
        .attr("stroke", "#22d3ee")
        .attr("stroke-width", 1.5)
        .attr("stroke-opacity", 0.5);

      // Inner fill
      nodeGroups.append("circle")
        .attr("r", 26)
        .attr("fill", "rgba(5,5,8,0.85)");

      // Hexagon accent
      nodeGroups.append("polygon")
        .attr("points", hexPoints(18))
        .attr("fill", "none")
        .attr("stroke", "#22d3ee")
        .attr("stroke-width", 0.5)
        .attr("stroke-opacity", 0.2);

      // Center vessel count
      nodeGroups.append("text")
        .attr("class", "node-count")
        .attr("text-anchor", "middle")
        .attr("dy", "0.35em")
        .attr("fill", "rgb(243,244,246)")
        .attr("font-family", "'Courier New', monospace")
        .attr("font-size", "16px")
        .text("--");

      // Name label
      nodeGroups.append("text")
        .attr("text-anchor", "middle")
        .attr("dy", 44)
        .attr("fill", "#22d3ee")
        .attr("font-family", "'Courier New', monospace")
        .attr("font-size", "8px")
        .attr("letter-spacing", "0.12em")
        .text((d) => d.name.toUpperCase());

      // Risk badge background
      nodeGroups.append("rect")
        .attr("class", "node-badge-bg")
        .attr("x", -18)
        .attr("y", 48)
        .attr("width", 36)
        .attr("height", 12)
        .attr("rx", 1)
        .attr("fill", "rgba(74,222,128,0.1)")
        .attr("stroke", "rgba(74,222,128,0.3)")
        .attr("stroke-width", 0.5);

      // Risk badge text
      nodeGroups.append("text")
        .attr("class", "node-badge-text")
        .attr("text-anchor", "middle")
        .attr("dy", 57)
        .attr("fill", "#4ade80")
        .attr("font-family", "'Courier New', monospace")
        .attr("font-size", "7px")
        .attr("letter-spacing", "0.1em")
        .text("LOW");
    }
  }, [containerSize]); // Re-render when container resizes (e.g., animation settles)

  // Update nodes when stats change
  useEffect(() => {
    const svg = d3.select(svgRef.current);
    if (!svg.node()) return;

    for (const cp of CHOKEPOINTS) {
      const stats = allStats[cp.id];
      if (!stats) continue;

      const node = svg.select(`.chokepoint-node[data-id="${cp.id}"]`);
      if (node.empty()) continue;

      // Update vessel count
      node.select(".node-count")
        .transition().duration(400)
        .tween("text", function () {
          const el = this as SVGTextElement;
          const prev = parseInt(el.textContent || "0") || 0;
          const interp = d3.interpolateRound(prev, stats.vesselCount);
          return (t: number) => { el.textContent = String(interp(t)); };
        });

      // Update badge
      const colors = getBadgeColors(stats.riskLevel);
      node.select(".node-badge-bg")
        .transition().duration(400)
        .attr("fill", colors.bg)
        .attr("stroke", colors.stroke);

      node.select(".node-badge-text")
        .text(stats.riskLevel)
        .transition().duration(400)
        .attr("fill", colors.text);

      const badgeW = Math.max(stats.riskLevel.length * 6 + 8, 36);
      node.select(".node-badge-bg")
        .attr("x", -badgeW / 2)
        .attr("width", badgeW);

      // Ring color
      node.select(".node-ring")
        .transition().duration(400)
        .attr("stroke", colors.text)
        .attr("stroke-opacity", stats.riskLevel === "CRITICAL" ? 0.9 : 0.5)
        .attr("stroke-width", selectedId === cp.id ? 2.5 : 1.5);

      // Remove old indicators
      node.selectAll(".indicator-dot").remove();

      // Military indicator dots
      const milCount = Math.min(stats.militaryCount, 8);
      for (let m = 0; m < milCount; m++) {
        const angle = (Math.PI * 2 / Math.max(milCount, 1)) * m - Math.PI / 2;
        node.append("circle")
          .attr("class", "indicator-dot")
          .attr("cx", Math.cos(angle) * 32)
          .attr("cy", Math.sin(angle) * 32)
          .attr("r", 2.5)
          .attr("fill", "#facc15")
          .attr("opacity", 0)
          .transition().duration(300).delay(m * 40)
          .attr("opacity", 0.9);
      }

      // Conflict pip
      if (stats.conflictCount > 0) {
        node.append("circle")
          .attr("class", "indicator-dot")
          .attr("cx", 22).attr("cy", -22)
          .attr("r", 4)
          .attr("fill", "#f87171")
          .attr("stroke", "rgba(248,113,113,0.4)")
          .attr("stroke-width", 2)
          .attr("opacity", 0)
          .transition().duration(300).attr("opacity", 0.9);
      }

      // GPS jamming indicator
      if (stats.jammingCount > 0) {
        node.append("circle")
          .attr("class", "indicator-dot")
          .attr("cx", -22).attr("cy", -22)
          .attr("r", 4)
          .attr("fill", "#c084fc")
          .attr("stroke", "rgba(192,132,252,0.4)")
          .attr("stroke-width", 2)
          .attr("opacity", 0)
          .transition().duration(300).attr("opacity", 0.9);
      }

      // Fire indicator
      if (stats.fireCount > 0) {
        node.append("circle")
          .attr("class", "indicator-dot")
          .attr("cx", 22).attr("cy", 18)
          .attr("r", 3.5)
          .attr("fill", "#fb923c")
          .attr("stroke", "rgba(251,146,60,0.4)")
          .attr("stroke-width", 1.5)
          .attr("opacity", 0)
          .transition().duration(300).attr("opacity", 0.9);
      }
    }
  }, [allStats, selectedId]);

  const handleCopy = useCallback(() => {
    const now = new Date();
    const ts = now.toUTCString().replace("GMT", "UTC");
    const lines: string[] = [];
    lines.push(`CHOKEPOINT STATUS \u2014 ${ts}`);
    lines.push("\u2501".repeat(16));

    for (const cp of CHOKEPOINTS) {
      const stats = allStats[cp.id] || { vesselCount: 0, militaryCount: 0, conflictCount: 0, riskLevel: "LOW" as RiskLevel };
      const shortName = cp.name.replace("Strait of ", "").replace("Canal", "").replace("Straits", "").trim().toUpperCase();
      lines.push(
        `\u25A0 ${shortName} [${stats.riskLevel}] \u2014 ${stats.vesselCount} vessels, ${stats.militaryCount} military, ${stats.conflictCount} conflicts`,
      );
    }

    if (data?.oil_prices) {
      const wti = data.oil_prices.wti;
      const brent = data.oil_prices.brent;
      const wtiStr = wti ? `$${(wti.price || 0).toFixed(2)} (${(wti.change_pct || 0) >= 0 ? "+" : ""}${(wti.change_pct || 0).toFixed(1)}%)` : "--";
      const brentStr = brent ? `$${(brent.price || 0).toFixed(2)} (${(brent.change_pct || 0) >= 0 ? "+" : ""}${(brent.change_pct || 0).toFixed(1)}%)` : "--";
      lines.push(`OIL: WTI ${wtiStr} | BRENT ${brentStr}`);
    }

    navigator.clipboard.writeText(lines.join("\n")).then(() => {
      setCopyLabel("COPIED");
      setTimeout(() => setCopyLabel("COPY STATUS"), 2000);
    });
  }, [allStats, data]);

  const oilPrices = data?.oil_prices;
  const wti = oilPrices?.wti;
  const brent = oilPrices?.brent;
  const hasData = !!data;

  const S: Record<string, React.CSSProperties> = useMemo(() => ({
    container: {
      fontFamily: "var(--sb-font-mono, 'Courier New', monospace)",
      fontSize: "11px",
      letterSpacing: "0.05em",
      color: "var(--sb-text-primary, rgb(243,244,246))",
      display: "flex",
      flexDirection: "column",
      height: "100%",
      minHeight: 0,
    },
    header: {
      display: "flex",
      justifyContent: "space-between",
      alignItems: "flex-start",
      borderBottom: "1px solid var(--sb-border-accent, rgba(34,211,238,0.4))",
      paddingBottom: 10,
      marginBottom: 12,
      flexWrap: "wrap",
      gap: 8,
    },
    heading: {
      fontSize: 14,
      letterSpacing: "0.2em",
      textTransform: "uppercase" as const,
      color: "var(--sb-text-secondary, #22d3ee)",
      fontWeight: "normal",
      textShadow: "0 0 8px rgba(34,211,238,0.3)",
    },
    subheading: {
      fontSize: 10,
      letterSpacing: "0.1em",
      color: "var(--sb-text-primary, rgb(243,244,246))",
      opacity: 0.5,
    },
    oilPrices: { display: "flex", gap: 14 },
    oilItem: { display: "flex", flexDirection: "column" as const, alignItems: "flex-end" as const, gap: 1 },
    oilLabel: { fontSize: 8, letterSpacing: "0.15em", opacity: 0.5 },
    oilPrice: { fontSize: 12 },
    oilUp: { fontSize: 9, color: "#4ade80" },
    oilDown: { fontSize: 9, color: "#f87171" },
    timestamp: { fontSize: 8, letterSpacing: "0.1em", color: "rgba(34,211,238,0.5)", textAlign: "right" as const },
    main: { display: "flex", flex: 1, gap: 12, minHeight: 0 },
    mapArea: { flex: 1, position: "relative" as const, minHeight: 300 },
    detailPanel: {
      width: 260,
      background: "var(--sb-bg-secondary, rgb(5,5,8))",
      border: "1px solid var(--sb-border-accent, rgba(34,211,238,0.4))",
      padding: 12,
      display: "flex",
      flexDirection: "column" as const,
      gap: 10,
      overflowY: "auto" as const,
      maxHeight: 450,
    },
    footer: {
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      borderTop: "1px solid rgba(255,255,255,0.08)",
      paddingTop: 8,
      marginTop: 12,
    },
    legend: { display: "flex", gap: 12, fontSize: 8, opacity: 0.6 },
    legendItem: { display: "flex", alignItems: "center", gap: 4 },
    legendDot: { width: 6, height: 6, borderRadius: "50%" },
    copyBtn: {
      background: "none",
      border: "1px solid var(--sb-border-accent, rgba(34,211,238,0.4))",
      color: copyLabel === "COPIED" ? "#4ade80" : "var(--sb-text-secondary, #22d3ee)",
      fontFamily: "var(--sb-font-mono, 'Courier New', monospace)",
      fontSize: 9,
      letterSpacing: "0.15em",
      padding: "6px 14px",
      cursor: "pointer",
      textTransform: "uppercase" as const,
      borderColor: copyLabel === "COPIED" ? "#4ade80" : undefined,
    },
  }), [copyLabel]);

  return (
    <div style={S.container}>
      {/* Header */}
      <div style={S.header}>
        <div>
          <h1 style={S.heading}>CHOKEPOINT RISK MONITOR</h1>
          <p style={S.subheading}>MARITIME STRATEGIC CHOKEPOINT STATUS</p>
        </div>
        <div style={{ display: "flex", alignItems: "flex-start", gap: 16, flexWrap: "wrap" }}>
          <div style={S.oilPrices}>
            <div style={S.oilItem}>
              <span style={S.oilLabel}>WTI</span>
              <span style={S.oilPrice}>{wti ? `$${(wti.price || 0).toFixed(2)}` : "--"}</span>
              {wti && (
                <span style={(wti.change_pct || 0) >= 0 ? S.oilUp : S.oilDown}>
                  {(wti.change_pct || 0) >= 0 ? "+" : ""}{(wti.change_pct || 0).toFixed(1)}%
                </span>
              )}
            </div>
            <div style={S.oilItem}>
              <span style={S.oilLabel}>BRENT</span>
              <span style={S.oilPrice}>{brent ? `$${(brent.price || 0).toFixed(2)}` : "--"}</span>
              {brent && (
                <span style={(brent.change_pct || 0) >= 0 ? S.oilUp : S.oilDown}>
                  {(brent.change_pct || 0) >= 0 ? "+" : ""}{(brent.change_pct || 0).toFixed(1)}%
                </span>
              )}
            </div>
          </div>
          <div style={S.timestamp}>
            {hasData ? `DATA AS OF ${new Date().toUTCString().replace("GMT", "UTC")}` : "DATA AS OF -- (NO FEED)"}
          </div>
        </div>
      </div>

      {/* Main area */}
      <div style={S.main}>
        <div ref={containerRef} style={S.mapArea}>
          <svg ref={svgRef} style={{ width: "100%", height: "100%" }} />
          {!hasData && (
            <div style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%,-50%)", textAlign: "center" }}>
              <span style={{ fontSize: 12, letterSpacing: "0.2em", color: "#22d3ee", animation: "sb-pulse 1.8s ease-in-out infinite" }}>
                AWAITING FEED DATA...
              </span>
            </div>
          )}
        </div>

        {/* Detail panel */}
        {selectedCp && selectedStats && (
          <div style={S.detailPanel}>
            <button
              onClick={() => setSelectedId(null)}
              style={{
                background: "none",
                border: "1px solid var(--sb-border-accent, rgba(34,211,238,0.4))",
                color: "#22d3ee",
                fontFamily: "inherit",
                fontSize: 9,
                letterSpacing: "0.1em",
                padding: "4px 8px",
                cursor: "pointer",
                alignSelf: "flex-end",
              }}
            >
              [X] CLOSE
            </button>

            <div style={{ fontSize: 12, color: "#22d3ee", letterSpacing: "0.15em", borderBottom: "1px solid rgba(34,211,238,0.4)", paddingBottom: 6 }}>
              {selectedCp.name.toUpperCase()}
            </div>
            <div style={{ fontSize: 9, opacity: 0.6, marginTop: -6 }}>{selectedCp.significance}</div>

            <div>
              <div style={{ fontSize: 9, color: "rgba(34,211,238,0.5)", letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 4 }}>
                RISK BREAKDOWN
              </div>
              {[
                { label: "Risk Score", value: String(selectedStats.riskScore) },
                { label: "Risk Level", value: selectedStats.riskLevel, isBadge: true },
                { label: "Vessels", value: String(selectedStats.vesselCount) },
                { label: "Military Assets", value: String(selectedStats.militaryCount) },
                { label: "Conflict Events", value: String(selectedStats.conflictCount) },
                { label: "GPS Jamming Zones", value: String(selectedStats.jammingCount) },
                { label: "Fire Detections", value: String(selectedStats.fireCount) },
              ].map((row) => (
                <div key={row.label} style={{ display: "flex", justifyContent: "space-between", fontSize: 10, padding: "2px 0", borderBottom: "1px dashed rgba(255,255,255,0.08)" }}>
                  <span style={{ opacity: 0.6 }}>{row.label}</span>
                  {row.isBadge ? (
                    <span className={badgeClass(row.value as RiskLevel)}>{row.value}</span>
                  ) : (
                    <span>{row.value}</span>
                  )}
                </div>
              ))}
            </div>

            <div>
              <div style={{ fontSize: 9, color: "rgba(34,211,238,0.5)", letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 4 }}>
                VESSELS IN AREA
              </div>
              <div style={{ maxHeight: 120, overflowY: "auto", fontSize: 9 }}>
                {selectedStats.vessels.length === 0 ? (
                  <div style={{ opacity: 0.4, padding: "2px 0" }}>No vessels detected</div>
                ) : (
                  selectedStats.vessels.slice(0, 30).map((v, i) => (
                    <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "2px 0", borderBottom: "1px dashed rgba(255,255,255,0.08)" }}>
                      <span>{v.name || v.callsign || "UNKNOWN"}</span>
                      <span style={{ opacity: 0.5 }}>{v.type || v.ship_type || "--"}</span>
                    </div>
                  ))
                )}
                {selectedStats.vessels.length > 30 && (
                  <div style={{ opacity: 0.4, padding: "2px 0" }}>+{selectedStats.vessels.length - 30} more</div>
                )}
              </div>
            </div>

            <div>
              <div style={{ fontSize: 9, color: "rgba(34,211,238,0.5)", letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 4 }}>
                MILITARY ASSETS
              </div>
              <div style={{ maxHeight: 120, overflowY: "auto", fontSize: 9 }}>
                {selectedStats.military.length === 0 ? (
                  <div style={{ opacity: 0.4, padding: "2px 0" }}>No military assets detected</div>
                ) : (
                  selectedStats.military.slice(0, 20).map((m, i) => (
                    <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "2px 0", borderBottom: "1px dashed rgba(255,255,255,0.08)" }}>
                      <span>{"callsign" in m ? (m as MilitaryFlight).callsign || "UNKNOWN" : (m as Ship).name || "UNKNOWN"}</span>
                      <span style={{ opacity: 0.5 }}>{"aircraft_type" in m ? (m as MilitaryFlight).aircraft_type || "--" : (m as Ship).type || "--"}</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div style={S.footer}>
        <div style={S.legend}>
          {[
            { color: "#60a5fa", label: "VESSELS" },
            { color: "#facc15", label: "MILITARY" },
            { color: "#f87171", label: "CONFLICT" },
            { color: "#c084fc", label: "GPS JAM" },
            { color: "#fb923c", label: "FIRES" },
          ].map(({ color, label }) => (
            <div key={label} style={S.legendItem}>
              <div style={{ ...S.legendDot, background: color }} />
              <span>{label}</span>
            </div>
          ))}
        </div>
        <button type="button" onClick={handleCopy} style={S.copyBtn}>{copyLabel}</button>
      </div>
    </div>
  );
}
