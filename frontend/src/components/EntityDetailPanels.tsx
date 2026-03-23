// ─── Entity Detail Panels ───────────────────────────────────────────────────
// Rendered in the NewsFeed right sidebar when a corresponding entity is selected.
// Each panel reads from selectedEntity.extra (the GeoJSON feature properties).

import { motion } from "framer-motion";
import type { DashboardData, SelectedEntity } from "@/types/dashboard";

// ─── Shared helpers ─────────────────────────────────────────────────────────

interface PanelProps {
  entity: SelectedEntity;
  data: DashboardData;
}

/** Safely read a field from entity.extra, returning fallback when missing. */
function ex(entity: SelectedEntity, key: string, fallback: string = "\u2014"): string {
  const v = entity.extra?.[key];
  if (v == null || v === "") return fallback;
  return String(v);
}

/** Standard detail row used across all panels. */
function Row({ label, value, className }: { label: string; value: string; className?: string }) {
  return (
    <div className="flex justify-between items-center border-b border-[var(--border-primary)] pb-2">
      <span className="text-[var(--text-muted)] text-[10px]">{label}</span>
      <span className={className || "text-[var(--text-primary)] text-xs font-bold"}>{value}</span>
    </div>
  );
}

/** Wiki link row — renders a clickable link or nothing if no URL. */
function WikiRow({ url, label, accentClass }: { url: string | undefined | null; label: string; accentClass: string }) {
  if (!url) return null;
  const href = url.startsWith("http") ? url : `https://en.wikipedia.org/wiki/${encodeURIComponent(url)}`;
  return (
    <div className="flex justify-between items-center border-b border-[var(--border-primary)] pb-2">
      <span className="text-[var(--text-muted)] text-[10px]">REFERENCE</span>
      <a
        href={href}
        target="_blank"
        rel="noreferrer"
        className={`text-xs font-bold underline ${accentClass} hover:opacity-80 transition-opacity`}
      >
        {label}
      </a>
    </div>
  );
}

// ─── 1. Satellite ───────────────────────────────────────────────────────────

export function SatelliteDetailPanel({ entity }: PanelProps) {
  return (
    <motion.div
      initial={{ y: 50, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="w-full bg-black/60 backdrop-blur-md border border-cyan-800 rounded-xl flex flex-col z-10 font-mono shadow-[0_4px_30px_rgba(0,255,255,0.15)] pointer-events-auto overflow-hidden flex-shrink-0"
    >
      <div className="p-3 border-b border-cyan-500/30 bg-cyan-950/40 flex justify-between items-center">
        <h2 className="text-xs tracking-widest font-bold text-cyan-400">ORBITAL ASSET</h2>
        <span className="text-[10px] text-[var(--text-muted)] font-mono">NORAD: {ex(entity, "id", "N/A")}</span>
      </div>
      <div className="p-4 flex flex-col gap-3">
        <Row label="DESIGNATION" value={ex(entity, "name")} className="text-cyan-400 text-xs font-bold" />
        <Row label="NORAD ID" value={ex(entity, "id")} />
        <Row label="MISSION" value={ex(entity, "mission", "GENERAL").toUpperCase()} className="text-cyan-400 text-xs font-bold" />
        <Row label="TYPE" value={ex(entity, "sat_type")} />
        <Row label="COUNTRY" value={ex(entity, "country")} />
        <Row label="ALTITUDE" value={entity.extra?.alt_km != null ? `${Number(entity.extra.alt_km).toLocaleString()} km` : "\u2014"} />
        <WikiRow url={entity.extra?.wiki} label="Wikipedia" accentClass="text-cyan-400" />
      </div>
    </motion.div>
  );
}

// ─── 2. UAV ─────────────────────────────────────────────────────────────────

export function UavDetailPanel({ entity }: PanelProps) {
  return (
    <motion.div
      initial={{ y: 50, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="w-full bg-black/60 backdrop-blur-md border border-red-800 rounded-xl flex flex-col z-10 font-mono shadow-[0_4px_30px_rgba(255,50,50,0.15)] pointer-events-auto overflow-hidden flex-shrink-0"
    >
      <div className="p-3 border-b border-red-500/30 bg-red-950/40 flex justify-between items-center">
        <h2 className="text-xs tracking-widest font-bold text-red-400">UAV TRANSPONDER</h2>
        <span className="text-[10px] text-[var(--text-muted)] font-mono">ICAO: {ex(entity, "icao24", "N/A")}</span>
      </div>
      <div className="p-4 flex flex-col gap-3">
        <Row label="CALLSIGN" value={ex(entity, "callsign")} className="text-red-400 text-xs font-bold" />
        <Row label="AIRCRAFT" value={ex(entity, "name")} />
        <Row label="UAV TYPE" value={ex(entity, "uav_type")} />
        <Row label="COUNTRY" value={ex(entity, "country")} />
        <Row label="ALTITUDE" value={entity.extra?.alt != null ? `${(Math.round(Number(entity.extra.alt) / 0.3048)).toLocaleString()} ft` : "\u2014"} />
        <Row label="SPEED" value={entity.extra?.speed_knots != null ? `${entity.extra.speed_knots} kts` : "\u2014"} />
        {entity.extra?.registration && <Row label="REGISTRATION" value={ex(entity, "registration")} />}
        {entity.extra?.squawk && <Row label="SQUAWK" value={ex(entity, "squawk")} />}
        <WikiRow url={entity.extra?.wiki} label="Wikipedia" accentClass="text-red-400" />
      </div>
    </motion.div>
  );
}

// ─── 3. Earthquake ──────────────────────────────────────────────────────────

export function EarthquakeDetailPanel({ entity }: PanelProps) {
  const title = entity.extra?.title || entity.name || "Unknown Event";
  const mag = entity.extra?.name?.match(/\[M([\d.]+)\]/)?.[1] || "\u2014";

  return (
    <motion.div
      initial={{ y: 50, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="w-full bg-black/60 backdrop-blur-md border border-yellow-800 rounded-xl flex flex-col z-10 font-mono shadow-[0_4px_30px_rgba(255,200,0,0.15)] pointer-events-auto overflow-hidden flex-shrink-0"
    >
      <div className="p-3 border-b border-yellow-500/30 bg-yellow-950/40 flex justify-between items-center">
        <h2 className="text-xs tracking-widest font-bold text-yellow-400">SEISMIC EVENT</h2>
        <span className="text-[10px] text-[var(--text-muted)] font-mono">ID: {ex(entity, "id", "N/A")}</span>
      </div>
      <div className="p-4 flex flex-col gap-3">
        <Row label="MAGNITUDE" value={`M ${mag}`} className="text-yellow-400 text-xs font-bold" />
        <Row label="LOCATION" value={title} className="text-[var(--text-primary)] text-xs font-bold text-right ml-4 max-w-[200px]" />
        {entity.extra?.name && (
          <Row label="PLACE" value={entity.extra.name.replace(/\[M[\d.]+\]\n?/, "").trim() || "\u2014"} className="text-[var(--text-primary)] text-xs font-bold text-right ml-4 max-w-[200px]" />
        )}
      </div>
    </motion.div>
  );
}

// ─── 4. KiwiSDR ─────────────────────────────────────────────────────────────

export function KiwisdrDetailPanel({ entity }: PanelProps) {
  const users = entity.extra?.users ?? 0;
  const usersMax = entity.extra?.users_max ?? 0;

  return (
    <motion.div
      initial={{ y: 50, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="w-full bg-black/60 backdrop-blur-md border border-amber-800 rounded-xl flex flex-col z-10 font-mono shadow-[0_4px_30px_rgba(245,158,11,0.15)] pointer-events-auto overflow-hidden flex-shrink-0"
    >
      <div className="p-3 border-b border-amber-500/30 bg-amber-950/40 flex justify-between items-center">
        <h2 className="text-xs tracking-widest font-bold text-amber-400">SDR RECEIVER</h2>
        <span className="text-[10px] text-[var(--text-muted)] font-mono">ID: {ex(entity, "id", "N/A")}</span>
      </div>
      <div className="p-4 flex flex-col gap-3">
        <Row label="NAME" value={ex(entity, "name")} className="text-amber-400 text-xs font-bold" />
        <Row label="LOCATION" value={ex(entity, "location")} className="text-[var(--text-primary)] text-xs font-bold text-right ml-4 max-w-[200px]" />
        <Row label="USERS" value={`${users} / ${usersMax}`} />
        <Row label="ANTENNA" value={ex(entity, "antenna")} className="text-[var(--text-primary)] text-xs font-bold text-right ml-4 max-w-[180px]" />
        <Row label="BANDS" value={ex(entity, "bands")} className="text-[var(--text-primary)] text-xs font-bold text-right ml-4 max-w-[180px]" />
        {entity.extra?.url && (
          <div className="flex justify-between items-center border-b border-[var(--border-primary)] pb-2">
            <span className="text-[var(--text-muted)] text-[10px]">STREAM</span>
            <a
              href={entity.extra.url}
              target="_blank"
              rel="noreferrer"
              className="text-xs font-bold underline text-amber-400 hover:opacity-80 transition-opacity"
            >
              TUNE IN
            </a>
          </div>
        )}
      </div>
    </motion.div>
  );
}

// ─── 5. Fire (FIRMS) ────────────────────────────────────────────────────────

export function FireDetailPanel({ entity }: PanelProps) {
  const frp = entity.extra?.frp;

  return (
    <motion.div
      initial={{ y: 50, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="w-full bg-black/60 backdrop-blur-md border border-red-800 rounded-xl flex flex-col z-10 font-mono shadow-[0_4px_30px_rgba(239,68,68,0.2)] pointer-events-auto overflow-hidden flex-shrink-0"
    >
      <div className="p-3 border-b border-red-500/30 bg-red-950/40 flex justify-between items-center">
        <h2 className="text-xs tracking-widest font-bold text-red-500">THERMAL HOTSPOT</h2>
        <span className="text-[10px] text-[var(--text-muted)] font-mono">FIRMS</span>
      </div>
      <div className="p-4 flex flex-col gap-3">
        <Row
          label="FIRE RADIATIVE POWER"
          value={frp != null ? `${Number(frp).toFixed(1)} MW` : "\u2014"}
          className="text-red-500 text-xs font-bold"
        />
        <Row label="BRIGHTNESS" value={entity.extra?.brightness != null ? `${Number(entity.extra.brightness).toFixed(1)} K` : "\u2014"} />
        <Row label="CONFIDENCE" value={ex(entity, "confidence", "N/A")} />
        <Row label="DAY / NIGHT" value={ex(entity, "daynight", "N/A")} />
        <Row label="ACQ DATE" value={ex(entity, "acq_date")} />
        <Row label="ACQ TIME" value={entity.extra?.acq_time ? String(entity.extra.acq_time).replace(/^(\d{2})(\d{2})$/, "$1:$2 UTC") : "\u2014"} />
      </div>
    </motion.div>
  );
}

// ─── 6. Internet Outage ─────────────────────────────────────────────────────

export function InternetOutageDetailPanel({ entity }: PanelProps) {
  const severity = entity.extra?.severity;

  return (
    <motion.div
      initial={{ y: 50, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="w-full bg-black/60 backdrop-blur-md border border-red-800 rounded-xl flex flex-col z-10 font-mono shadow-[0_4px_30px_rgba(248,113,113,0.15)] pointer-events-auto overflow-hidden flex-shrink-0"
    >
      <div className="p-3 border-b border-red-500/30 bg-red-950/40 flex justify-between items-center">
        <h2 className="text-xs tracking-widest font-bold text-red-400">NETWORK OUTAGE</h2>
        <span className="text-[10px] text-[var(--text-muted)] font-mono">IODA</span>
      </div>
      <div className="p-4 flex flex-col gap-3">
        <Row label="REGION" value={ex(entity, "region")} className="text-red-400 text-xs font-bold" />
        <Row label="COUNTRY" value={ex(entity, "country")} />
        <Row label="SEVERITY" value={severity != null ? `${severity}% drop` : "\u2014"} className="text-red-400 text-xs font-bold" />
        <Row label="LEVEL" value={ex(entity, "level")} />
        <Row label="DATASOURCE" value={ex(entity, "datasource", "IODA")} />
      </div>
    </motion.div>
  );
}

// ─── 7. Data Center ─────────────────────────────────────────────────────────

export function DatacenterDetailPanel({ entity }: PanelProps) {
  const parts = [
    entity.extra?.street,
    entity.extra?.city,
    entity.extra?.zip,
    entity.extra?.country,
  ].filter(Boolean);
  const address = parts.length > 0 ? parts.join(", ") : "\u2014";

  return (
    <motion.div
      initial={{ y: 50, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="w-full bg-black/60 backdrop-blur-md border border-violet-800 rounded-xl flex flex-col z-10 font-mono shadow-[0_4px_30px_rgba(167,139,250,0.15)] pointer-events-auto overflow-hidden flex-shrink-0"
    >
      <div className="p-3 border-b border-violet-500/30 bg-violet-950/40 flex justify-between items-center">
        <h2 className="text-xs tracking-widest font-bold text-violet-400">DATA CENTER</h2>
        <span className="text-[10px] text-[var(--text-muted)] font-mono">ID: {ex(entity, "id", "N/A")}</span>
      </div>
      <div className="p-4 flex flex-col gap-3">
        <Row label="NAME" value={ex(entity, "name")} className="text-violet-400 text-xs font-bold" />
        <Row label="COMPANY" value={ex(entity, "company")} />
        <Row label="ADDRESS" value={address} className="text-[var(--text-primary)] text-xs font-bold text-right ml-4 max-w-[200px]" />
      </div>
    </motion.div>
  );
}

// ─── 8. Military Base ───────────────────────────────────────────────────────

const SIDE_ACCENT: Record<string, { text: string; border: string; bg: string; shadow: string }> = {
  red:   { text: "text-red-400",  border: "border-red-800",  bg: "bg-red-950/40",  shadow: "rgba(248,113,113,0.15)" },
  blue:  { text: "text-cyan-400", border: "border-cyan-800", bg: "bg-cyan-950/40", shadow: "rgba(0,255,255,0.15)" },
  green: { text: "text-green-400", border: "border-green-800", bg: "bg-green-950/40", shadow: "rgba(74,222,128,0.15)" },
};

export function MilitaryBaseDetailPanel({ entity }: PanelProps) {
  const side = (entity.extra?.side as string) || "blue";
  const accent = SIDE_ACCENT[side] || SIDE_ACCENT.blue;

  return (
    <motion.div
      initial={{ y: 50, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.4 }}
      className={`w-full bg-black/60 backdrop-blur-md border ${accent.border} rounded-xl flex flex-col z-10 font-mono pointer-events-auto overflow-hidden flex-shrink-0`}
      style={{ boxShadow: `0 4px 30px ${accent.shadow}` }}
    >
      <div className={`p-3 border-b ${accent.border}/30 ${accent.bg} flex justify-between items-center`}>
        <h2 className={`text-xs tracking-widest font-bold ${accent.text}`}>MILITARY INSTALLATION</h2>
        <span className="text-[10px] text-[var(--text-muted)] font-mono">{side.toUpperCase()} FORCE</span>
      </div>
      <div className="p-4 flex flex-col gap-3">
        <Row label="NAME" value={ex(entity, "name")} className={`${accent.text} text-xs font-bold`} />
        <Row label="COUNTRY" value={ex(entity, "country")} />
        <Row label="OPERATOR" value={ex(entity, "operator")} />
        <Row label="BRANCH" value={ex(entity, "branch")} />
      </div>
    </motion.div>
  );
}

// ─── 9. Power Plant ─────────────────────────────────────────────────────────

export function PowerPlantDetailPanel({ entity }: PanelProps) {
  return (
    <motion.div
      initial={{ y: 50, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="w-full bg-black/60 backdrop-blur-md border border-amber-800 rounded-xl flex flex-col z-10 font-mono shadow-[0_4px_30px_rgba(245,158,11,0.15)] pointer-events-auto overflow-hidden flex-shrink-0"
    >
      <div className="p-3 border-b border-amber-500/30 bg-amber-950/40 flex justify-between items-center">
        <h2 className="text-xs tracking-widest font-bold text-amber-400">POWER PLANT</h2>
        <span className="text-[10px] text-[var(--text-muted)] font-mono">ID: {ex(entity, "id", "N/A")}</span>
      </div>
      <div className="p-4 flex flex-col gap-3">
        <Row label="NAME" value={ex(entity, "name")} className="text-amber-400 text-xs font-bold" />
        <Row label="FUEL TYPE" value={ex(entity, "fuel_type")} />
        <Row label="CAPACITY" value={entity.extra?.capacity_mw != null ? `${Number(entity.extra.capacity_mw).toLocaleString()} MW` : "\u2014"} />
        <Row label="OPERATOR" value={ex(entity, "owner")} />
        <Row label="COUNTRY" value={ex(entity, "country")} />
      </div>
    </motion.div>
  );
}
