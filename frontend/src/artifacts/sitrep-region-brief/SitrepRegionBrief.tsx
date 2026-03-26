"use client";

import { useState, useMemo, useCallback } from "react";
import ArtifactShell from "@/artifacts/_shared/ArtifactShell";
import { useArtifactData } from "@/artifacts/_shared/useArtifactData";

/* ── Data Interfaces ── */

interface Ship {
  name?: string;
  mmsi?: string;
  type?: string;
  flag?: string;
  tracked?: boolean;
  [key: string]: unknown;
}

interface MilitaryFlight {
  callsign?: string;
  type?: string;
  aircraft_type?: string;
  [key: string]: unknown;
}

interface GdeltEvent {
  type?: string;
  event_type?: string;
  [key: string]: unknown;
}

interface FireDetection {
  [key: string]: unknown;
}

interface GpsJammingZone {
  [key: string]: unknown;
}

interface NewsItem {
  [key: string]: unknown;
}

interface SitrepData {
  region?: string;
  bbox?: { south: number; west: number; north: number; east: number };
  timeframe?: number;
  ships?: Ship[];
  military_flights?: MilitaryFlight[];
  gdelt_events?: GdeltEvent[];
  fires?: FireDetection[];
  gps_jamming?: GpsJammingZone[];
  news?: NewsItem[];
  assessment?: string;
}

/* ── Helpers ── */

type ThreatLevel = "CRITICAL" | "ELEVATED" | "NORMAL" | "LOW";

function computeThreatLevel(data: SitrepData): ThreatLevel {
  const militaryCount = data.military_flights?.length ?? 0;
  const conflictCount = data.gdelt_events?.length ?? 0;
  const jammingCount = data.gps_jamming?.length ?? 0;
  const fireCount = data.fires?.length ?? 0;

  const score = militaryCount * 2 + conflictCount * 3 + jammingCount * 5 + fireCount;

  if (score >= 30) return "CRITICAL";
  if (score >= 15) return "ELEVATED";
  if (score >= 5) return "NORMAL";
  return "LOW";
}

function threatBadgeClass(level: ThreatLevel): string {
  const map: Record<ThreatLevel, string> = {
    CRITICAL: "sb-badge sb-badge-critical",
    ELEVATED: "sb-badge sb-badge-elevated",
    NORMAL: "sb-badge sb-badge-normal",
    LOW: "sb-badge sb-badge-low",
  };
  return map[level];
}

function shipTypeBreakdown(ships: Ship[]): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const s of ships) {
    const t = (s.type ?? "unknown").toLowerCase();
    counts[t] = (counts[t] ?? 0) + 1;
  }
  return counts;
}

function formatBreakdown(counts: Record<string, number>): string {
  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .map(([type, count]) => `${count} ${type}`)
    .join(", ");
}

/* ── Styles ── */

const sectionStyle: React.CSSProperties = {
  marginBottom: 20,
};

const sectionTitleStyle: React.CSSProperties = {
  fontFamily: "var(--sb-font-mono)",
  fontSize: 13,
  fontWeight: 700,
  color: "var(--sb-text-secondary)",
  textTransform: "uppercase" as const,
  letterSpacing: "0.08em",
  marginBottom: 8,
};

const sectionBodyStyle: React.CSSProperties = {
  fontFamily: "var(--sb-font-mono)",
  fontSize: 13,
  color: "var(--sb-text-primary)",
  lineHeight: 1.6,
};

const bannerStyle: React.CSSProperties = {
  textAlign: "center" as const,
  fontFamily: "var(--sb-font-mono)",
  fontSize: 11,
  fontWeight: 600,
  color: "var(--sb-text-secondary)",
  letterSpacing: "0.15em",
  padding: "6px 0",
  borderTop: "1px solid var(--sb-border-accent)",
  borderBottom: "1px solid var(--sb-border-accent)",
  marginBottom: 16,
};

const regionStyle: React.CSSProperties = {
  fontFamily: "var(--sb-font-mono)",
  fontSize: 22,
  fontWeight: 700,
  color: "var(--sb-text-primary)",
  textTransform: "uppercase" as const,
  letterSpacing: "0.05em",
  margin: "8px 0 4px",
};

const metaStyle: React.CSSProperties = {
  fontFamily: "var(--sb-font-mono)",
  fontSize: 11,
  color: "var(--sb-text-muted)",
  marginBottom: 4,
};

const dividerStyle: React.CSSProperties = {
  border: "none",
  borderTop: "1px solid var(--sb-border-accent)",
  margin: "16px 0",
};

const copyBtnStyle: React.CSSProperties = {
  fontFamily: "var(--sb-font-mono)",
  fontSize: 12,
  fontWeight: 600,
  color: "var(--sb-text-secondary)",
  background: "var(--sb-bg-tertiary)",
  border: "1px solid var(--sb-border-accent)",
  padding: "8px 20px",
  cursor: "pointer",
  letterSpacing: "0.1em",
  textTransform: "uppercase" as const,
  marginTop: 8,
};

const listStyle: React.CSSProperties = {
  fontFamily: "var(--sb-font-mono)",
  fontSize: 12,
  color: "var(--sb-text-muted)",
  margin: "4px 0 0 16px",
  padding: 0,
  listStyle: "none",
};

const listItemStyle: React.CSSProperties = {
  padding: "1px 0",
};

/* ── Component ── */

interface Props {
  initialData?: SitrepData;
}

export default function SitrepRegionBrief({ initialData }: Props) {
  const data = useArtifactData<SitrepData>(initialData);
  const [copied, setCopied] = useState(false);

  const threatLevel = useMemo(() => (data ? computeThreatLevel(data) : "LOW" as ThreatLevel), [data]);

  const shipCounts = useMemo(() => shipTypeBreakdown(data?.ships ?? []), [data]);

  const notableShips = useMemo(() => {
    if (!data?.ships) return [];
    return data.ships.filter((s) => s.tracked);
  }, [data]);

  const callsigns = useMemo(() => {
    if (!data?.military_flights) return [];
    return data.military_flights
      .map((f) => f.callsign)
      .filter((c): c is string => Boolean(c));
  }, [data]);

  const eventTypes = useMemo(() => {
    if (!data?.gdelt_events) return [];
    const types = new Set<string>();
    for (const e of data.gdelt_events) {
      const t = e.type ?? e.event_type;
      if (t) types.add(String(t));
    }
    return Array.from(types);
  }, [data]);

  const timestamp = useMemo(() => new Date().toISOString(), []);

  const regionName = data?.region ?? "UNKNOWN REGION";
  const timeframe = data?.timeframe ?? 24;
  const shipCount = data?.ships?.length ?? 0;
  const milCount = data?.military_flights?.length ?? 0;
  const conflictCount = data?.gdelt_events?.length ?? 0;
  const fireCount = data?.fires?.length ?? 0;
  const jammingCount = data?.gps_jamming?.length ?? 0;

  const buildPlaintext = useCallback((): string => {
    const sep = "\u2550".repeat(39);
    const callsignList = callsigns.slice(0, 10).join(", ");
    const callsignSuffix = callsigns.length > 10 ? ` + ${callsigns.length - 10} more` : "";
    const breakdownStr = formatBreakdown(shipCounts);

    return [
      sep,
      `SITUATION REPORT \u2014 ${regionName}`,
      "UNCLASSIFIED // OSINT",
      sep,
      `PERIOD: LAST ${timeframe} HOURS`,
      `GENERATED: ${timestamp}`,
      `THREAT LEVEL: ${threatLevel}`,
      "",
      "1. SITUATION OVERVIEW",
      `${shipCount} vessels, ${milCount} military assets, ${conflictCount} conflict events, ${fireCount} fire detections`,
      "",
      `2. MARITIME: ${shipCount} vessels (${breakdownStr || "none"})`,
      `3. MILITARY: ${milCount} assets (${callsignList || "none"}${callsignSuffix})`,
      `4. CONFLICT: ${conflictCount} events, ${jammingCount} jamming zones`,
      `5. ENVIRONMENTAL: ${fireCount} fire detections`,
      "",
      "ASSESSMENT:",
      data?.assessment ?? "ASSESSMENT PENDING",
      sep,
    ].join("\n");
  }, [regionName, timeframe, timestamp, threatLevel, shipCount, milCount, conflictCount, fireCount, jammingCount, callsigns, shipCounts, data?.assessment]);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(buildPlaintext());
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API not available
    }
  }, [buildPlaintext]);

  /* ── Empty State ── */

  if (!data) {
    return (
      <ArtifactShell title="SITREP">
        <p className="sb-label" style={{ padding: "24px 0", textAlign: "center" }}>
          AWAITING REGION DATA
        </p>
      </ArtifactShell>
    );
  }

  /* ── Render ── */

  return (
    <ArtifactShell title="SITREP">
      {/* Classification Banner */}
      <div style={bannerStyle}>UNCLASSIFIED // OSINT</div>

      {/* Header */}
      <div style={regionStyle}>{regionName}</div>
      <div style={metaStyle}>LAST {timeframe} HOURS</div>
      <div style={metaStyle}>GENERATED {timestamp}</div>
      <div style={{ marginTop: 8, marginBottom: 4 }}>
        <span className={threatBadgeClass(threatLevel)}>{threatLevel}</span>
      </div>

      <hr style={dividerStyle} />

      {/* a. SITUATION OVERVIEW */}
      <div style={sectionStyle}>
        <div style={sectionTitleStyle}>A. SITUATION OVERVIEW</div>
        <div style={sectionBodyStyle}>
          Threat posture assessed as{" "}
          <span style={{ color: "var(--sb-text-secondary)", fontWeight: 700 }}>{threatLevel}</span>{" "}
          based on current data density across monitored feeds.
        </div>
        <div style={{ ...sectionBodyStyle, marginTop: 6 }}>
          {shipCount} vessels, {milCount} military assets, {conflictCount} conflict events, {fireCount} fire detections
        </div>
      </div>

      {/* b. MARITIME ACTIVITY */}
      <div style={sectionStyle}>
        <div style={sectionTitleStyle}>
          <span style={{ color: "var(--sb-color-maritime)" }}>B. MARITIME ACTIVITY</span>
        </div>
        <div style={sectionBodyStyle}>
          {shipCount} vessel{shipCount !== 1 ? "s" : ""} in region
        </div>
        {shipCount > 0 && (
          <div style={{ ...sectionBodyStyle, color: "var(--sb-text-muted)", marginTop: 4 }}>
            Breakdown: {formatBreakdown(shipCounts)}
          </div>
        )}
        {notableShips.length > 0 && (
          <div style={{ marginTop: 6 }}>
            <span style={{ ...sectionBodyStyle, color: "var(--sb-text-secondary)", fontWeight: 600 }}>
              TRACKED VESSELS:
            </span>
            <ul style={listStyle}>
              {notableShips.map((s, i) => (
                <li key={s.mmsi ?? i} style={listItemStyle}>
                  {s.name ?? s.mmsi ?? "UNKNOWN"}{s.flag ? ` [${s.flag}]` : ""}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* c. MILITARY POSTURE */}
      <div style={sectionStyle}>
        <div style={sectionTitleStyle}>
          <span style={{ color: "var(--sb-color-military)" }}>C. MILITARY POSTURE</span>
        </div>
        <div style={sectionBodyStyle}>
          {milCount} military aircraft detected
        </div>
        {callsigns.length > 0 && (
          <div style={{ ...sectionBodyStyle, color: "var(--sb-text-muted)", marginTop: 4 }}>
            Callsigns: {callsigns.slice(0, 10).join(", ")}
            {callsigns.length > 10 && ` + ${callsigns.length - 10} more`}
          </div>
        )}
        {data.military_flights && data.military_flights.length > 0 && (
          <>
            {(() => {
              const types = new Set<string>();
              for (const f of data.military_flights!) {
                const t = f.aircraft_type ?? f.type;
                if (t) types.add(String(t));
              }
              if (types.size === 0) return null;
              return (
                <div style={{ ...sectionBodyStyle, color: "var(--sb-text-muted)", marginTop: 4 }}>
                  Aircraft types: {Array.from(types).join(", ")}
                </div>
              );
            })()}
          </>
        )}
      </div>

      {/* d. CONFLICT & INSTABILITY */}
      <div style={sectionStyle}>
        <div style={sectionTitleStyle}>
          <span style={{ color: "var(--sb-color-intelligence)" }}>D. CONFLICT &amp; INSTABILITY</span>
        </div>
        <div style={sectionBodyStyle}>
          {conflictCount} conflict/instability event{conflictCount !== 1 ? "s" : ""} recorded
        </div>
        {eventTypes.length > 0 && (
          <div style={{ ...sectionBodyStyle, color: "var(--sb-text-muted)", marginTop: 4 }}>
            Event types: {eventTypes.join(", ")}
          </div>
        )}
        <div style={{ ...sectionBodyStyle, marginTop: 6 }}>
          GPS jamming: {jammingCount} zone{jammingCount !== 1 ? "s" : ""} detected
          {jammingCount > 0 && (
            <span className="sb-badge sb-badge-elevated" style={{ marginLeft: 8 }}>ACTIVE</span>
          )}
        </div>
      </div>

      {/* e. ENVIRONMENTAL */}
      <div style={sectionStyle}>
        <div style={sectionTitleStyle}>
          <span style={{ color: "var(--sb-color-fire)" }}>E. ENVIRONMENTAL</span>
        </div>
        <div style={sectionBodyStyle}>
          {fireCount} fire detection{fireCount !== 1 ? "s" : ""}
          {fireCount > 5 && (
            <span className="sb-badge sb-badge-elevated" style={{ marginLeft: 8 }}>SIGNIFICANT</span>
          )}
        </div>
      </div>

      {/* f. ASSESSMENT */}
      <div style={sectionStyle}>
        <div style={sectionTitleStyle}>F. ASSESSMENT</div>
        <div style={{
          ...sectionBodyStyle,
          background: "var(--sb-bg-tertiary)",
          padding: 12,
          borderLeft: "3px solid var(--sb-border-accent)",
          lineHeight: 1.7,
        }}>
          {data.assessment
            ? data.assessment
            : "ASSESSMENT PENDING \u2014 REQUEST VIA ANALYST"}
        </div>
      </div>

      <hr style={dividerStyle} />

      {/* Copy Action */}
      <div style={{ textAlign: "center" as const }}>
        <button type="button" style={copyBtnStyle} onClick={handleCopy}>
          {copied ? "COPIED" : "COPY SITREP"}
        </button>
      </div>
    </ArtifactShell>
  );
}
