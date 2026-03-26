"use client";

import { useState, useMemo, useEffect, useRef } from "react";
import { useArtifactData } from "@/artifacts/_shared/useArtifactData";

/* ── Data types ────────────────────────────────────────────── */

interface TickerData {
  gdelt_events?: Array<{
    lat?: number;
    lng?: number;
    event_type?: string;
    goldstein_scale?: number;
    source_url?: string;
  }>;
  military_flights?: Array<{
    callsign?: string;
    type?: string;
    lat?: number;
    lng?: number;
  }>;
  gps_jamming?: Array<{
    lat?: number;
    lng?: number;
    radius?: number;
  }>;
  fires?: Array<{
    lat?: number;
    lng?: number;
    brightness?: number;
    country?: string;
  }>;
  earthquakes?: Array<{
    magnitude?: number;
    lat?: number;
    lng?: number;
    place?: string;
  }>;
  news?: Array<{
    title?: string;
    source?: string;
    published?: string;
  }>;
}

/* ── Pulse item model ──────────────────────────────────────── */

type Severity = "critical" | "elevated" | "normal";
type Domain = "seismic" | "conflict" | "jamming" | "military" | "fire" | "news";

interface PulseItem {
  id: string;
  message: string;
  severity: Severity;
  domain: Domain;
}

const SEVERITY_ORDER: Record<Severity, number> = {
  critical: 0,
  elevated: 1,
  normal: 2,
};

const SEVERITY_COLORS: Record<Severity, string> = {
  critical: "#ef4444",
  elevated: "#f59e0b",
  normal: "#22d3ee",
};

const DOMAIN_COLORS: Record<Domain, string> = {
  seismic: "var(--sb-color-seismic)",
  conflict: "var(--sb-color-intelligence)",
  jamming: "var(--sb-color-maritime)",
  military: "var(--sb-color-military)",
  fire: "var(--sb-color-fire)",
  news: "var(--sb-text-secondary)",
};

const MAX_PULSES = 15;

/* ── Pulse generation ──────────────────────────────────────── */

function generatePulses(data: TickerData): PulseItem[] {
  const pulses: PulseItem[] = [];

  // Earthquakes (magnitude >= 4.0)
  if (data.earthquakes) {
    for (const eq of data.earthquakes) {
      if (eq.magnitude != null && eq.magnitude >= 4.0) {
        let severity: Severity = "normal";
        if (eq.magnitude >= 6) severity = "critical";
        else if (eq.magnitude >= 5) severity = "elevated";

        pulses.push({
          id: `eq-${eq.lat}-${eq.lng}-${eq.magnitude}`,
          message: `SEISMIC M${eq.magnitude.toFixed(1)} — ${eq.place || "Unknown location"}`,
          severity,
          domain: "seismic",
        });
      }
    }
  }

  // GDELT events (goldstein_scale < -5)
  if (data.gdelt_events) {
    for (const ev of data.gdelt_events) {
      if (ev.goldstein_scale != null && ev.goldstein_scale < -5) {
        let severity: Severity = "elevated";
        if (ev.goldstein_scale < -8) severity = "critical";

        pulses.push({
          id: `gdelt-${ev.lat}-${ev.lng}-${ev.event_type}`,
          message: `CONFLICT — ${ev.event_type || "Unknown event"}`,
          severity,
          domain: "conflict",
        });
      }
    }
  }

  // GPS jamming zones (always elevated)
  if (data.gps_jamming) {
    for (const jam of data.gps_jamming) {
      pulses.push({
        id: `jam-${jam.lat}-${jam.lng}`,
        message: `GPS JAMMING ZONE ACTIVE — ${jam.lat?.toFixed(1)}, ${jam.lng?.toFixed(1)}`,
        severity: "elevated",
        domain: "jamming",
      });
    }
  }

  // Military flights (surge detection)
  if (data.military_flights && data.military_flights.length > 20) {
    const count = data.military_flights.length;
    pulses.push({
      id: `mil-surge-${count}`,
      message: `MIL AVIATION SURGE — ${count} assets detected`,
      severity: count > 40 ? "critical" : "elevated",
      domain: "military",
    });
  }

  // Fires (brightness > 400 or count > 10, grouped by country)
  if (data.fires) {
    const highBrightness = data.fires.filter(
      (f) => f.brightness != null && f.brightness > 400,
    );
    const countries = new Map<string, number>();
    for (const f of data.fires) {
      const c = f.country || "Unknown";
      countries.set(c, (countries.get(c) || 0) + 1);
    }

    if (highBrightness.length > 0 || data.fires.length > 10) {
      for (const [country, count] of countries) {
        if (
          count > 10 ||
          highBrightness.some((f) => (f.country || "Unknown") === country)
        ) {
          pulses.push({
            id: `fire-${country}-${count}`,
            message: `THERMAL ANOMALY — ${count} detections ${country}`,
            severity: "elevated",
            domain: "fire",
          });
        }
      }
    }
  }

  // News (first 3 items, normal severity)
  if (data.news) {
    for (const item of data.news.slice(0, 3)) {
      if (item.title) {
        const truncated =
          item.title.length > 60
            ? item.title.slice(0, 57) + "..."
            : item.title;
        const source = item.source || "NEWS";
        pulses.push({
          id: `news-${item.title?.slice(0, 20)}-${item.published}`,
          message: `${source}: ${truncated}`,
          severity: "normal",
          domain: "news",
        });
      }
    }
  }

  // Sort: critical first, then elevated, then normal
  pulses.sort((a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity]);

  return pulses.slice(0, MAX_PULSES);
}

/* ── Pulsing dot keyframes (injected once) ─────────────────── */

const PULSE_STYLE_ID = "sb-risk-pulse-keyframes";

function ensurePulseKeyframes() {
  if (typeof document === "undefined") return;
  if (document.getElementById(PULSE_STYLE_ID)) return;
  const style = document.createElement("style");
  style.id = PULSE_STYLE_ID;
  style.textContent = `
    @keyframes sb-pulse-dot {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.3; }
    }
  `;
  document.head.appendChild(style);
}

/* ── Component ─────────────────────────────────────────────── */

interface Props {
  initialData?: TickerData;
}

export default function RiskPulseTicker({ initialData }: Props) {
  const data = useArtifactData<TickerData>(initialData);
  const [collapsed, setCollapsed] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const bodyRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    ensurePulseKeyframes();
  }, []);

  const pulses = useMemo(() => {
    if (!data) return [];
    return generatePulses(data);
  }, [data]);

  const hasCritical = pulses.some((p) => p.severity === "critical");
  const alertCount = pulses.length;

  return (
    <div
      style={{
        width: "100%",
        maxWidth: 380,
        fontFamily: "var(--sb-font-mono), ui-monospace, monospace",
        fontSize: 9,
        color: "var(--sb-text-primary)",
        background: "var(--sb-bg-primary)",
        border: "1px solid var(--sb-border-accent)",
        borderRadius: 4,
        overflow: "hidden",
        userSelect: "none",
      }}
    >
      {/* Header */}
      <div
        onClick={() => setCollapsed((c) => !c)}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          padding: "5px 8px",
          background: "var(--sb-bg-secondary)",
          borderBottom: collapsed
            ? "none"
            : "1px solid var(--sb-border-accent)",
          cursor: "pointer",
        }}
      >
        {/* Pulsing dot */}
        <span
          style={{
            display: "inline-block",
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: hasCritical ? "#ef4444" : "#22d3ee",
            animation: hasCritical ? "sb-pulse-dot 1.2s ease-in-out infinite" : "none",
            flexShrink: 0,
          }}
        />
        <span
          style={{
            fontWeight: 700,
            letterSpacing: "0.05em",
            color: "var(--sb-text-primary)",
            flex: 1,
          }}
        >
          RISK PULSE
        </span>
        {alertCount > 0 && (
          <span
            style={{
              fontSize: 8,
              padding: "1px 5px",
              borderRadius: 3,
              background: "rgba(255,255,255,0.08)",
              color: "var(--sb-text-secondary)",
              border: "1px solid var(--sb-border-accent)",
            }}
          >
            {alertCount} alert{alertCount !== 1 ? "s" : ""}
          </span>
        )}
        <span
          style={{
            fontSize: 8,
            color: "var(--sb-text-muted)",
            flexShrink: 0,
          }}
        >
          {collapsed ? "\u25BC" : "\u25B2"}
        </span>
      </div>

      {/* Body */}
      {!collapsed && (
        <div style={{ position: "relative" }}>
          <div
            ref={bodyRef}
            style={{
              maxHeight: 200,
              overflowY: "auto",
              overflowX: "hidden",
            }}
          >
            {pulses.length === 0 ? (
              <div
                style={{
                  padding: "12px 8px",
                  textAlign: "center",
                  color: "var(--sb-text-muted)",
                  letterSpacing: "0.04em",
                }}
              >
                NO ACTIVE ALERTS
              </div>
            ) : (
              pulses.map((pulse) => (
                <div
                  key={pulse.id}
                  onClick={() =>
                    setSelectedId(
                      selectedId === pulse.id ? null : pulse.id,
                    )
                  }
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    padding: "3px 8px",
                    height: 24,
                    cursor: "pointer",
                    borderLeft: `2px solid ${DOMAIN_COLORS[pulse.domain]}`,
                    background:
                      selectedId === pulse.id
                        ? "rgba(255,255,255,0.04)"
                        : "transparent",
                    transition: "background 0.15s",
                  }}
                >
                  {/* Severity pip */}
                  <span
                    style={{
                      display: "inline-block",
                      width: 5,
                      height: 5,
                      borderRadius: "50%",
                      background: SEVERITY_COLORS[pulse.severity],
                      flexShrink: 0,
                      animation:
                        pulse.severity === "critical"
                          ? "sb-pulse-dot 1.2s ease-in-out infinite"
                          : "none",
                    }}
                  />
                  {/* Message */}
                  <span
                    style={{
                      flex: 1,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                      color:
                        pulse.severity === "critical"
                          ? "#ef4444"
                          : pulse.severity === "elevated"
                            ? "#f59e0b"
                            : "var(--sb-text-secondary)",
                    }}
                  >
                    {pulse.message}
                  </span>
                </div>
              ))
            )}
          </div>
          {/* Bottom fade gradient */}
          {pulses.length > 6 && (
            <div
              style={{
                position: "absolute",
                bottom: 0,
                left: 0,
                right: 0,
                height: 20,
                background:
                  "linear-gradient(transparent, var(--sb-bg-primary))",
                pointerEvents: "none",
              }}
            />
          )}
        </div>
      )}
    </div>
  );
}
