"use client";

/**
 * VoiceIndicator — HUD-styled visual indicator for voice mode state.
 *
 * Shows the current state of the voice conversation loop with
 * military-aesthetic animations and labels.
 */
import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Mic, Radio, AudioLines, Volume2, Loader2 } from "lucide-react";
import type { VoiceState } from "@/hooks/useVoiceMode";

interface VoiceIndicatorProps {
  state: VoiceState;
  /** Optional: progress text from the agent's SSE events. */
  progressText?: string | null;
}

const STATE_CONFIG: Record<
  Exclude<VoiceState, "off">,
  { label: string; icon: typeof Mic; color: string; animate: boolean }
> = {
  standby: {
    label: "COMMS STANDBY",
    icon: Radio,
    color: "rgb(8, 145, 178)",     // cyan-600 (muted)
    animate: false,
  },
  listening: {
    label: "RECEIVING",
    icon: Mic,
    color: "rgb(34, 211, 238)",    // cyan-400 (bright)
    animate: true,
  },
  transcribing: {
    label: "PROCESSING VOICE",
    icon: Loader2,
    color: "rgb(34, 211, 238)",
    animate: true,
  },
  analyzing: {
    label: "ANALYZING",
    icon: Loader2,
    color: "rgb(6, 182, 212)",     // cyan-500
    animate: true,
  },
  generating: {
    label: "GENERATING AUDIO",
    icon: AudioLines,
    color: "rgb(6, 182, 212)",
    animate: true,
  },
  speaking: {
    label: "TRANSMITTING",
    icon: Volume2,
    color: "rgb(34, 211, 238)",
    animate: true,
  },
  follow_up: {
    label: "CHANNEL OPEN",
    icon: Radio,
    color: "rgba(34, 211, 238, 0.6)",
    animate: true,
  },
};

export function VoiceIndicator({ state, progressText }: VoiceIndicatorProps) {
  if (state === "off") return null;

  const config = STATE_CONFIG[state];
  const Icon = config.icon;

  return (
    <div className="flex flex-col items-center gap-2 py-3 px-4">
      {/* Pulsing ring + icon */}
      <div className="relative flex items-center justify-center">
        {/* Outer pulse ring */}
        {config.animate && (
          <motion.div
            className="absolute rounded-full"
            style={{
              width: 56,
              height: 56,
              border: `1px solid ${config.color}`,
              boxShadow: `0 0 12px ${config.color}40`,
            }}
            animate={{
              scale: [1, 1.3, 1],
              opacity: [0.6, 0, 0.6],
            }}
            transition={{
              duration: state === "listening" ? 1.5 : 2,
              repeat: Infinity,
              ease: "easeInOut",
            }}
          />
        )}

        {/* Icon circle */}
        <motion.div
          className="flex items-center justify-center rounded-full"
          style={{
            width: 44,
            height: 44,
            backgroundColor: `${config.color}15`,
            border: `1px solid ${config.color}60`,
          }}
          animate={
            config.animate
              ? { boxShadow: [`0 0 8px ${config.color}20`, `0 0 16px ${config.color}40`, `0 0 8px ${config.color}20`] }
              : {}
          }
          transition={{ duration: 2, repeat: Infinity }}
        >
          <Icon
            size={20}
            style={{ color: config.color }}
            className={
              config.icon === Loader2 ? "animate-spin" : ""
            }
          />
        </motion.div>
      </div>

      {/* State label */}
      <AnimatePresence mode="wait">
        <motion.div
          key={config.label}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -4 }}
          transition={{ duration: 0.15 }}
          className="text-center"
        >
          <div
            className="font-mono text-[9px] tracking-[0.2em] uppercase"
            style={{ color: config.color }}
          >
            {config.label}
          </div>

          {/* Progress text (during analysis) */}
          {progressText && (state === "analyzing" || state === "generating") && (
            <div
              className="font-mono text-[8px] tracking-[0.1em] mt-1 max-w-[240px] truncate"
              style={{ color: "rgb(8, 145, 178)" }}
            >
              {progressText}
            </div>
          )}

          {/* "Say Jarvis to begin" hint in standby */}
          {state === "standby" && (
            <div
              className="font-mono text-[8px] tracking-[0.1em] mt-1"
              style={{ color: "rgba(8, 145, 178, 0.5)" }}
            >
              SAY &quot;JARVIS&quot; TO BEGIN
            </div>
          )}

          {/* Follow-up hint */}
          {state === "follow_up" && (
            <div
              className="font-mono text-[8px] tracking-[0.1em] mt-1"
              style={{ color: "rgba(34, 211, 238, 0.5)" }}
            >
              SPEAK NOW OR WAIT...
            </div>
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
