"use client";

import { useState, useMemo } from "react";
import ArtifactShell from "@/artifacts/_shared/ArtifactShell";
import { useArtifactData } from "@/artifacts/_shared/useArtifactData";

interface TrackedShip {
  name: string;
  type?: string;
  lat?: number;
  lng?: number;
  flag?: string;
  owner?: string;
  mmsi?: string;
}

interface MilitaryFlight {
  callsign?: string;
  type?: string;
  lat?: number;
  lng?: number;
  altitude?: number;
  squawk?: string;
  hex?: string;
}

interface Carrier {
  name: string;
  location?: string;
  status?: string;
  lat?: number;
  lng?: number;
}

interface TrackedData {
  tracked_ships?: TrackedShip[];
  military_flights?: MilitaryFlight[];
  carriers?: Carrier[];
}

type Category = "ALL" | "VESSELS" | "AIRCRAFT" | "CARRIERS";
type SortKey = "name" | "category" | "ownerFlag";
type SortDir = "asc" | "desc";

interface UnifiedEntity {
  category: Category;
  name: string;
  subtype: string;
  ownerFlag: string;
  lat?: number;
  lng?: number;
  status: string;
}

function normalizeEntities(data: TrackedData): UnifiedEntity[] {
  const entities: UnifiedEntity[] = [];

  if (data.tracked_ships) {
    for (const s of data.tracked_ships) {
      entities.push({
        category: "VESSELS",
        name: s.name,
        subtype: s.type || "unknown",
        ownerFlag: s.owner || s.flag || "\u2014",
        lat: s.lat,
        lng: s.lng,
        status: "TRACKING",
      });
    }
  }

  if (data.military_flights) {
    for (const f of data.military_flights) {
      const parts: string[] = [];
      if (f.altitude != null) parts.push(`ALT ${f.altitude}`);
      if (f.squawk) parts.push(`SQK ${f.squawk}`);
      entities.push({
        category: "AIRCRAFT",
        name: f.callsign || f.hex || "UNKNOWN",
        subtype: f.type || "unknown",
        ownerFlag: "\u2014",
        lat: f.lat,
        lng: f.lng,
        status: parts.length ? parts.join(" / ") : "TRACKING",
      });
    }
  }

  if (data.carriers) {
    for (const c of data.carriers) {
      entities.push({
        category: "CARRIERS",
        name: c.name,
        subtype: "carrier",
        ownerFlag: "US NAVY",
        lat: c.lat,
        lng: c.lng,
        status: c.status || c.location || "\u2014",
      });
    }
  }

  return entities;
}

function formatPosition(lat?: number, lng?: number): string {
  if (lat == null || lng == null) return "\u2014";
  return `${lat.toFixed(2)}, ${lng.toFixed(2)}`;
}

function categoryColor(cat: Category): string {
  switch (cat) {
    case "VESSELS":
      return "var(--sb-color-maritime)";
    case "AIRCRAFT":
      return "var(--sb-color-aviation)";
    case "CARRIERS":
      return "var(--sb-color-military)";
    default:
      return "var(--sb-text-secondary)";
  }
}

function buildExportText(data: TrackedData): string {
  const ts = new Date().toISOString().replace("T", " ").slice(0, 19) + "Z";
  const lines: string[] = [];
  lines.push(`TRACKED ENTITIES \u2014 ${ts}`);
  lines.push("\u2501".repeat(16));

  const ships = data.tracked_ships || [];
  lines.push(`VESSELS (${ships.length}):`);
  for (const s of ships) {
    const pos = s.lat != null && s.lng != null ? `${s.lat.toFixed(2)}, ${s.lng.toFixed(2)}` : "unknown";
    lines.push(`  \u2022 ${s.name} \u2014 ${s.type || "unknown"} \u2014 ${s.flag || "\u2014"} \u2014 ${pos}`);
  }

  const flights = data.military_flights || [];
  lines.push(`AIRCRAFT (${flights.length}):`);
  for (const f of flights) {
    const pos = f.lat != null && f.lng != null ? `${f.lat.toFixed(2)}, ${f.lng.toFixed(2)}` : "unknown";
    lines.push(`  \u2022 ${f.callsign || f.hex || "UNKNOWN"} \u2014 ${f.type || "unknown"} \u2014 ALT ${f.altitude ?? "\u2014"} \u2014 ${pos}`);
  }

  const carriers = data.carriers || [];
  lines.push(`CARRIERS (${carriers.length}):`);
  for (const c of carriers) {
    lines.push(`  \u2022 ${c.name} \u2014 ${c.status || "\u2014"} \u2014 ${c.location || "\u2014"}`);
  }

  return lines.join("\n");
}

interface Props {
  initialData?: TrackedData;
}

export default function TrackedEntityDashboard({ initialData }: Props) {
  const data = useArtifactData<TrackedData>(initialData);
  const [filter, setFilter] = useState<Category>("ALL");
  const [sortKey, setSortKey] = useState<SortKey>("name");
  const [sortDir, setSortDir] = useState<SortDir>("asc");
  const [exportLabel, setExportLabel] = useState("EXPORT LIST");

  const allEntities = useMemo(() => {
    if (!data) return [];
    return normalizeEntities(data);
  }, [data]);

  const vesselCount = useMemo(() => allEntities.filter((e) => e.category === "VESSELS").length, [allEntities]);
  const aircraftCount = useMemo(() => allEntities.filter((e) => e.category === "AIRCRAFT").length, [allEntities]);
  const carrierCount = useMemo(() => allEntities.filter((e) => e.category === "CARRIERS").length, [allEntities]);

  const filtered = useMemo(() => {
    const list = filter === "ALL" ? allEntities : allEntities.filter((e) => e.category === filter);
    return [...list].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      const cmp = String(av).localeCompare(String(bv));
      return sortDir === "desc" ? -cmp : cmp;
    });
  }, [allEntities, filter, sortKey, sortDir]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  const handleExport = () => {
    if (!data) return;
    const text = buildExportText(data);
    navigator.clipboard.writeText(text).then(() => {
      setExportLabel("COPIED");
      setTimeout(() => setExportLabel("EXPORT LIST"), 2000);
    });
  };

  if (!allEntities.length) {
    return (
      <ArtifactShell title="TRACKED ENTITY DASHBOARD">
        <p className="sb-label" style={{ padding: "24px 0", textAlign: "center" }}>
          NO TRACKED ENTITIES IN SCOPE
        </p>
      </ArtifactShell>
    );
  }

  const sortIndicator = (key: SortKey) =>
    sortKey === key ? (sortDir === "asc" ? " \u25B2" : " \u25BC") : "";

  const categories: Category[] = ["ALL", "VESSELS", "AIRCRAFT", "CARRIERS"];

  return (
    <ArtifactShell title="TRACKED ENTITY DASHBOARD">
      {/* Header area */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "8px",
          marginBottom: "12px",
        }}
      >
        <span
          className="sb-label"
          style={{ fontFamily: "var(--sb-font-mono)", fontSize: "11px" }}
        >
          VESSELS: {vesselCount} | AIRCRAFT: {aircraftCount} | CARRIERS: {carrierCount} | TOTAL: {allEntities.length}
        </span>

        <button
          onClick={handleExport}
          style={{
            background: "transparent",
            border: "1px solid var(--sb-border-accent)",
            color: "var(--sb-text-secondary)",
            fontFamily: "var(--sb-font-mono)",
            fontSize: "10px",
            padding: "4px 10px",
            cursor: "pointer",
            letterSpacing: "0.05em",
          }}
        >
          {exportLabel}
        </button>
      </div>

      {/* Filter tabs */}
      <div style={{ display: "flex", gap: "4px", marginBottom: "12px" }}>
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setFilter(cat)}
            style={{
              background: filter === cat ? "rgba(34,211,238,0.15)" : "transparent",
              border: `1px solid ${filter === cat ? "var(--sb-color-aviation)" : "var(--sb-border-accent)"}`,
              color: filter === cat ? "var(--sb-color-aviation)" : "var(--sb-text-muted)",
              fontFamily: "var(--sb-font-mono)",
              fontSize: "10px",
              padding: "3px 10px",
              cursor: "pointer",
              letterSpacing: "0.05em",
            }}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Entity table */}
      <table className="sb-table">
        <thead>
          <tr>
            <th
              onClick={() => handleSort("category")}
              style={{ cursor: "pointer" }}
            >
              TYPE{sortIndicator("category")}
            </th>
            <th
              onClick={() => handleSort("name")}
              style={{ cursor: "pointer" }}
            >
              NAME{sortIndicator("name")}
            </th>
            <th>SUBTYPE</th>
            <th
              onClick={() => handleSort("ownerFlag")}
              style={{ cursor: "pointer" }}
            >
              OWNER/FLAG{sortIndicator("ownerFlag")}
            </th>
            <th>POSITION</th>
            <th>STATUS</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((e, i) => (
            <tr key={`${e.category}-${e.name}-${i}`}>
              <td>
                <span
                  className="sb-badge"
                  style={{
                    color: categoryColor(e.category),
                    borderColor: categoryColor(e.category),
                    background: "rgba(0,0,0,0.3)",
                    fontSize: "10px",
                  }}
                >
                  {e.category === "VESSELS" ? "VESSEL" : e.category === "AIRCRAFT" ? "AIRCRAFT" : "CARRIER"}
                </span>
              </td>
              <td style={{ fontWeight: 600, whiteSpace: "nowrap" }}>{e.name}</td>
              <td style={{ color: "var(--sb-text-muted)" }}>{e.subtype}</td>
              <td style={{ color: "var(--sb-text-secondary)" }}>{e.ownerFlag}</td>
              <td style={{ fontFamily: "var(--sb-font-mono)", fontSize: "11px", color: "var(--sb-text-muted)" }}>
                {formatPosition(e.lat, e.lng)}
              </td>
              <td style={{ fontFamily: "var(--sb-font-mono)", fontSize: "11px", color: "var(--sb-text-secondary)" }}>
                {e.status}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </ArtifactShell>
  );
}
