"use client";

import { useState, useMemo, useCallback } from "react";
import ArtifactShell from "@/artifacts/_shared/ArtifactShell";
import { useArtifactData } from "@/artifacts/_shared/useArtifactData";

export interface Entity {
  name: string;
  domain: string;
  type: string;
  risk_level: number;
  lat: number;
  lng: number;
  summary: string;
}

export interface EntityData {
  entities: Entity[];
}

const DOMAIN_COLORS: Record<string, string> = {
  aviation: "var(--sb-color-aviation)",
  military: "var(--sb-color-military)",
  maritime: "var(--sb-color-maritime)",
  infrastructure: "var(--sb-color-infrastructure)",
  intelligence: "var(--sb-color-intelligence)",
  seismic: "var(--sb-color-seismic)",
  markets: "var(--sb-color-markets)",
};

type SortKey = "name" | "domain" | "risk_level";
type SortDir = "asc" | "desc";

function riskBadgeClass(level: number): string {
  if (level >= 8) return "sb-badge sb-badge-critical";
  if (level >= 5) return "sb-badge sb-badge-elevated";
  if (level >= 3) return "sb-badge sb-badge-normal";
  return "sb-badge sb-badge-low";
}

interface Props {
  initialData?: EntityData;
}

export default function EntityRiskDashboard({ initialData }: Props) {
  const data = useArtifactData<EntityData>(initialData);
  const [sortKey, setSortKey] = useState<SortKey>("risk_level");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [search, setSearch] = useState("");
  const [domainFilter, setDomainFilter] = useState<string>("ALL");

  const domains = useMemo(() => {
    if (!data?.entities) return [];
    const unique = [...new Set(data.entities.map((e) => e.domain))];
    return unique.sort();
  }, [data]);

  const entities = useMemo(() => {
    if (!data?.entities) return [];
    let list = data.entities;
    if (domainFilter !== "ALL") {
      list = list.filter((e) => e.domain === domainFilter);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        (e) =>
          e.name.toLowerCase().includes(q) ||
          e.domain.toLowerCase().includes(q) ||
          e.type.toLowerCase().includes(q) ||
          e.summary.toLowerCase().includes(q),
      );
    }
    return [...list].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      const cmp = typeof av === "number" ? av - (bv as number) : String(av).localeCompare(String(bv));
      return sortDir === "desc" ? -cmp : cmp;
    });
  }, [data, domainFilter, search, sortKey, sortDir]);

  const handleFlyTo = useCallback((lat: number, lng: number) => {
    if (lat === 0 && lng === 0) return;
    window.open(`/?flyTo=${lat},${lng},10`, "_blank");
  }, []);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir(key === "risk_level" ? "desc" : "asc");
    }
  };

  if (!data?.entities?.length) {
    return (
      <ArtifactShell title="ENTITY RISK DASHBOARD">
        <p className="sb-label" style={{ padding: "24px 0", textAlign: "center" }}>
          NO ENTITIES IN SCOPE
        </p>
      </ArtifactShell>
    );
  }

  const sortIndicator = (key: SortKey) =>
    sortKey === key ? (sortDir === "asc" ? " \u25B2" : " \u25BC") : "";

  return (
    <ArtifactShell title="ENTITY RISK DASHBOARD">
      {/* Search */}
      <div style={{ marginBottom: "10px" }}>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by name, domain, type, or summary..."
          style={{
            width: "100%",
            background: "rgba(0,0,0,0.4)",
            border: "1px solid var(--sb-border-accent)",
            color: "var(--sb-text-primary)",
            fontFamily: "var(--sb-font-mono)",
            fontSize: "11px",
            padding: "6px 10px",
            letterSpacing: "0.05em",
            outline: "none",
          }}
        />
      </div>

      {/* Domain filter tabs */}
      <div style={{ display: "flex", gap: "4px", marginBottom: "12px", flexWrap: "wrap" }}>
        {["ALL", ...domains].map((d) => (
          <button
            key={d}
            onClick={() => setDomainFilter(d)}
            style={{
              background: domainFilter === d ? "rgba(34,211,238,0.15)" : "transparent",
              border: `1px solid ${domainFilter === d ? "var(--sb-color-aviation)" : "var(--sb-border-accent)"}`,
              color: domainFilter === d ? "var(--sb-color-aviation)" : "var(--sb-text-muted)",
              fontFamily: "var(--sb-font-mono)",
              fontSize: "10px",
              padding: "3px 10px",
              cursor: "pointer",
              letterSpacing: "0.05em",
            }}
          >
            {d.toUpperCase()}
          </button>
        ))}
      </div>

      <table className="sb-table">
        <thead>
          <tr>
            <th
              onClick={() => handleSort("name")}
              style={{ cursor: "pointer" }}
            >
              ENTITY{sortIndicator("name")}
            </th>
            <th
              onClick={() => handleSort("domain")}
              style={{ cursor: "pointer" }}
            >
              DOMAIN{sortIndicator("domain")}
            </th>
            <th
              onClick={() => handleSort("risk_level")}
              style={{ cursor: "pointer" }}
            >
              RISK{sortIndicator("risk_level")}
            </th>
            <th>SUMMARY</th>
          </tr>
        </thead>
        <tbody>
          {entities.map((e, i) => (
            <tr key={`${e.domain}-${e.name}-${i}`}>
              <td style={{ fontWeight: 600, whiteSpace: "nowrap" }}>
                {e.lat !== 0 || e.lng !== 0 ? (
                  <button
                    onClick={() => handleFlyTo(e.lat, e.lng)}
                    style={{
                      background: "none",
                      border: "none",
                      color: "var(--sb-text-secondary)",
                      fontFamily: "inherit",
                      fontSize: "inherit",
                      fontWeight: "inherit",
                      cursor: "pointer",
                      padding: 0,
                      textDecoration: "underline",
                      textDecorationStyle: "dotted",
                      textUnderlineOffset: "3px",
                    }}
                    title={`Fly to ${e.name} on map`}
                  >
                    {e.name}
                  </button>
                ) : (
                  e.name
                )}
              </td>
              <td>
                <span
                  className="sb-badge"
                  style={{
                    color: DOMAIN_COLORS[e.domain] || "var(--sb-text-secondary)",
                    borderColor: DOMAIN_COLORS[e.domain] || "var(--sb-border-accent)",
                    background: "rgba(0,0,0,0.3)",
                  }}
                >
                  {e.domain.toUpperCase()}
                </span>
              </td>
              <td>
                <span className={riskBadgeClass(e.risk_level)}>{e.risk_level}</span>
              </td>
              <td style={{ color: "var(--sb-text-muted)", maxWidth: 300 }}>{e.summary}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </ArtifactShell>
  );
}
