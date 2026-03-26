"use client";

import { useState, useMemo } from "react";
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

  const entities = useMemo(() => {
    if (!data?.entities) return [];
    return [...data.entities].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      const cmp = typeof av === "number" ? av - (bv as number) : String(av).localeCompare(String(bv));
      return sortDir === "desc" ? -cmp : cmp;
    });
  }, [data, sortKey, sortDir]);

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
          {entities.map((e) => (
            <tr key={e.name}>
              <td style={{ fontWeight: 600, whiteSpace: "nowrap" }}>{e.name}</td>
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
