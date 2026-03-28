"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Shield, AlertTriangle, Bell, MapPin } from "lucide-react";

interface AlertItem {
  id: string;
  alert_type: string;
  severity: "critical" | "elevated" | "normal";
  title: string;
  description: string;
  lat: number | null;
  lng: number | null;
  created_at: number;
  significance: number | null;
}

interface IntelFeedPanelProps {
  isOpen: boolean;
  onClose: () => void;
  onFlyTo?: (lat: number, lng: number, zoom: number) => void;
  alertCount: number;
  onAlertCountChange: (count: number) => void;
}

const SEVERITY_STYLES = {
  critical: {
    border: "border-red-500/60",
    bg: "bg-red-950/30",
    badge: "bg-red-500/20 text-red-400 border-red-500/40",
    icon: "text-red-400",
    glow: "shadow-[0_0_8px_rgba(239,68,68,0.2)]",
  },
  elevated: {
    border: "border-yellow-500/60",
    bg: "bg-yellow-950/20",
    badge: "bg-yellow-500/20 text-yellow-400 border-yellow-500/40",
    icon: "text-yellow-400",
    glow: "",
  },
  normal: {
    border: "border-cyan-800/40",
    bg: "bg-cyan-950/10",
    badge: "bg-cyan-500/20 text-cyan-400 border-cyan-500/40",
    icon: "text-cyan-400",
    glow: "",
  },
};

const ALERT_TYPE_LABELS: Record<string, string> = {
  military_convergence: "MIL CONVERGENCE",
  chokepoint_disruption: "CHOKEPOINT",
  infrastructure_cascade: "INFRA CASCADE",
  sanctions_evasion: "SANCTIONS",
  airlift_surge: "AIRLIFT SURGE",
  under_reported_crisis: "UNREPORTED",
  ew_detection: "EW DETECTED",
  vip_movement: "VIP MOVEMENT",
  correlation_rf_anomaly: "RF ANOMALY",
  correlation_military_buildup: "MIL BUILDUP",
  correlation_infra_cascade: "CORR INFRA CASCADE",
  prediction_market_signal: "MARKET SIGNAL",
  black_sea_escalation: "BLACK SEA",
  disinformation_divergence: "DISINFO DIVERGENCE",
  supply_chain_cascade: "SUPPLY CASCADE",
  correlation_conflict_escalation: "CONFLICT ESCALATION",
  correlation_fimi_amplification: "FIMI AMPLIFICATION",
};

function timeAgo(ts: number): string {
  const seconds = Math.floor(Date.now() / 1000 - ts);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export default function IntelFeedPanel({
  isOpen,
  onClose,
  onFlyTo,
  alertCount,
  onAlertCountChange,
}: IntelFeedPanelProps) {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const dismissedRef = useRef(dismissed);
  dismissedRef.current = dismissed;

  const fetchAlerts = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetch("/api/alerts?limit=50");
      if (!res.ok) return;
      const data: AlertItem[] = await res.json();
      setAlerts(data);
      const visibleCount = data.filter((a) => !dismissedRef.current.has(a.id)).length;
      onAlertCountChange(visibleCount);
    } catch {
      // Silent fail — backend may not be running
    } finally {
      setLoading(false);
    }
  }, [onAlertCountChange]);

  // Poll every 30s when open, 60s when closed
  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, isOpen ? 30000 : 60000);
    return () => clearInterval(interval);
  }, [isOpen, fetchAlerts]);

  const handleDismiss = (id: string) => {
    setDismissed((prev) => {
      const next = new Set(prev).add(id);
      onAlertCountChange(alerts.filter((a) => !next.has(a.id)).length);
      return next;
    });
  };

  const visibleAlerts = alerts.filter((a) => !dismissed.has(a.id));

  if (!isOpen) return null;

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      className="absolute top-20 right-4 z-[500] w-[380px] max-w-[90vw] pointer-events-auto"
    >
      <div className="bg-black/95 backdrop-blur-md border border-cyan-800/60 rounded-xl shadow-[0_4px_30px_rgba(0,0,0,0.6)] flex flex-col max-h-[70vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-cyan-800/40">
          <div className="flex items-center gap-2">
            <Shield size={14} className="text-cyan-400" />
            <span className="text-[10px] text-cyan-400 font-mono tracking-[0.2em] font-bold">
              INTELLIGENCE FEED
            </span>
            {visibleAlerts.length > 0 && (
              <span className="text-[9px] bg-red-500/20 text-red-400 border border-red-500/40 rounded px-1.5 py-0.5 font-mono">
                {visibleAlerts.length}
              </span>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-[var(--text-muted)] hover:text-cyan-400 transition-colors"
          >
            <X size={14} />
          </button>
        </div>

        {/* Alert list */}
        <div className="flex-1 overflow-y-auto styled-scrollbar px-2 py-2 space-y-2 min-h-[80px] max-h-[calc(70vh-60px)]">
          {loading && visibleAlerts.length === 0 && (
            <div className="text-center py-8 text-[var(--text-muted)] text-[10px] font-mono">
              SCANNING...
            </div>
          )}

          {!loading && visibleAlerts.length === 0 && (
            <div className="text-center py-8 text-[var(--text-muted)] text-[10px] font-mono tracking-wider">
              NO ACTIVE ALERTS
            </div>
          )}

          <AnimatePresence>
            {visibleAlerts.map((alert) => {
              const style = SEVERITY_STYLES[alert.severity] || SEVERITY_STYLES.normal;
              return (
                <motion.div
                  key={alert.id}
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  className={`rounded-lg border ${style.border} ${style.bg} ${style.glow} p-3`}
                >
                  {/* Alert header */}
                  <div className="flex items-start justify-between gap-2 mb-1.5">
                    <div className="flex items-center gap-2 min-w-0">
                      {alert.severity === "critical" ? (
                        <AlertTriangle size={12} className={style.icon} />
                      ) : (
                        <Bell size={12} className={style.icon} />
                      )}
                      <span
                        className={`text-[8px] font-mono tracking-[0.15em] border rounded px-1.5 py-0.5 ${style.badge}`}
                      >
                        {ALERT_TYPE_LABELS[alert.alert_type] || alert.alert_type.toUpperCase()}
                      </span>
                      {alert.significance != null && (
                        <span
                          className={`text-[8px] font-mono tracking-wider border rounded px-1 py-0.5 ${
                            alert.significance >= 70
                              ? "border-red-500/40 text-red-400"
                              : alert.significance >= 40
                                ? "border-yellow-500/40 text-yellow-400"
                                : "border-cyan-500/40 text-cyan-400"
                          }`}
                        >
                          {alert.significance}
                        </span>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={() => handleDismiss(alert.id)}
                      className="text-[var(--text-muted)] hover:text-red-400 transition-colors flex-shrink-0"
                      title="Dismiss"
                    >
                      <X size={10} />
                    </button>
                  </div>

                  {/* Title */}
                  <div className="text-[11px] font-mono text-gray-200 font-medium mb-1">
                    {alert.title}
                  </div>

                  {/* Description */}
                  <div className="text-[9px] font-mono text-[var(--text-muted)] leading-relaxed mb-2">
                    {alert.description}
                  </div>

                  {/* Footer */}
                  <div className="flex items-center justify-between">
                    <span className="text-[8px] font-mono text-[var(--text-muted)]">
                      {timeAgo(alert.created_at)}
                    </span>
                    {alert.lat != null && alert.lng != null && onFlyTo && (
                      <button
                        type="button"
                        onClick={() => onFlyTo(alert.lat!, alert.lng!, 8)}
                        className="flex items-center gap-1 text-[8px] font-mono text-cyan-400 hover:text-cyan-300 transition-colors"
                      >
                        <MapPin size={8} />
                        VIEW
                      </button>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>
      </div>
    </motion.div>
  );
}
