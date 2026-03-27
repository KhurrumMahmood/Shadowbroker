"use client";

/**
 * VoiceSettings — Configuration panel for voice mode.
 *
 * Allows the user to choose between Tactical/Casual mode, pick a TTS voice,
 * adjust follow-up window duration, and toggle audio cues.
 */
import { Radio, Volume2, Timer, Bell } from "lucide-react";
import type { VoiceModeSettings, VoiceMode } from "@/hooks/useVoiceMode";

interface VoiceSettingsProps {
  settings: VoiceModeSettings;
  onUpdate: (patch: Partial<VoiceModeSettings>) => void;
  onClose: () => void;
}

const VOICES = [
  { id: "onyx", label: "Onyx", desc: "Deep, authoritative" },
  { id: "nova", label: "Nova", desc: "Clear, professional" },
  { id: "alloy", label: "Alloy", desc: "Balanced, neutral" },
  { id: "echo", label: "Echo", desc: "Warm, conversational" },
  { id: "shimmer", label: "Shimmer", desc: "Bright, energetic" },
  { id: "fable", label: "Fable", desc: "Calm, narrative" },
];

export function VoiceSettings({ settings, onUpdate, onClose }: VoiceSettingsProps) {
  return (
    <div
      className="absolute bottom-full left-0 right-0 mb-1 rounded border p-3 text-[10px] font-mono tracking-wider"
      style={{
        backgroundColor: "rgba(0, 0, 0, 0.95)",
        borderColor: "rgba(8, 145, 178, 0.4)",
        backdropFilter: "blur(12px)",
        zIndex: 50,
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <span
          className="text-[9px] tracking-[0.2em] uppercase"
          style={{ color: "rgb(34, 211, 238)" }}
        >
          VOICE CONFIG
        </span>
        <button
          onClick={onClose}
          className="text-[9px] tracking-wider uppercase hover:opacity-80"
          style={{ color: "rgb(8, 145, 178)" }}
        >
          CLOSE
        </button>
      </div>

      {/* Mode selector */}
      <div className="mb-3">
        <div className="flex items-center gap-1 mb-1.5" style={{ color: "rgb(8, 145, 178)" }}>
          <Radio size={10} />
          <span className="text-[8px] tracking-[0.15em] uppercase">MODE</span>
        </div>
        <div className="flex gap-1.5">
          {(["tactical", "casual"] as VoiceMode[]).map((mode) => (
            <button
              key={mode}
              onClick={() => onUpdate({ mode })}
              className="flex-1 py-1.5 px-2 rounded text-[9px] tracking-wider uppercase transition-colors"
              style={{
                backgroundColor:
                  settings.mode === mode
                    ? "rgba(8, 145, 178, 0.2)"
                    : "rgba(255, 255, 255, 0.03)",
                borderWidth: 1,
                borderColor:
                  settings.mode === mode
                    ? "rgba(34, 211, 238, 0.5)"
                    : "rgba(255, 255, 255, 0.08)",
                color:
                  settings.mode === mode
                    ? "rgb(34, 211, 238)"
                    : "rgb(156, 163, 175)",
              }}
            >
              {mode}
            </button>
          ))}
        </div>
        <div
          className="text-[7px] tracking-wider mt-1"
          style={{ color: "rgba(8, 145, 178, 0.6)" }}
        >
          {settings.mode === "tactical"
            ? 'WAKE WORD "JARVIS" + "OVER" TO SEND'
            : "CONTINUOUS LISTENING, SILENCE TO SEND"}
        </div>
      </div>

      {/* Voice selector */}
      <div className="mb-3">
        <div className="flex items-center gap-1 mb-1.5" style={{ color: "rgb(8, 145, 178)" }}>
          <Volume2 size={10} />
          <span className="text-[8px] tracking-[0.15em] uppercase">VOICE</span>
        </div>
        <div className="grid grid-cols-3 gap-1">
          {VOICES.map((v) => (
            <button
              key={v.id}
              onClick={() => onUpdate({ voice: v.id })}
              className="py-1 px-1.5 rounded text-[8px] tracking-wider transition-colors text-left"
              style={{
                backgroundColor:
                  settings.voice === v.id
                    ? "rgba(8, 145, 178, 0.2)"
                    : "rgba(255, 255, 255, 0.03)",
                borderWidth: 1,
                borderColor:
                  settings.voice === v.id
                    ? "rgba(34, 211, 238, 0.5)"
                    : "rgba(255, 255, 255, 0.05)",
                color:
                  settings.voice === v.id
                    ? "rgb(34, 211, 238)"
                    : "rgb(156, 163, 175)",
              }}
            >
              <div className="uppercase">{v.label}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Follow-up window (tactical only) */}
      {settings.mode === "tactical" && (
        <div className="mb-3">
          <div className="flex items-center gap-1 mb-1.5" style={{ color: "rgb(8, 145, 178)" }}>
            <Timer size={10} />
            <span className="text-[8px] tracking-[0.15em] uppercase">
              FOLLOW-UP WINDOW: {(settings.followUpWindowMs / 1000).toFixed(0)}S
            </span>
          </div>
          <input
            type="range"
            min={3000}
            max={10000}
            step={1000}
            value={settings.followUpWindowMs}
            onChange={(e) =>
              onUpdate({ followUpWindowMs: Number(e.target.value) })
            }
            className="w-full h-1 appearance-none rounded cursor-pointer"
            style={{
              background: `linear-gradient(to right, rgb(8, 145, 178) ${((settings.followUpWindowMs - 3000) / 7000) * 100}%, rgba(255,255,255,0.1) 0%)`,
            }}
          />
        </div>
      )}

      {/* Audio cues toggle */}
      <div>
        <button
          onClick={() => onUpdate({ audioCues: !settings.audioCues })}
          className="flex items-center gap-1.5 py-1"
        >
          <Bell size={10} style={{ color: "rgb(8, 145, 178)" }} />
          <span
            className="text-[8px] tracking-[0.15em] uppercase"
            style={{ color: "rgb(8, 145, 178)" }}
          >
            AUDIO CUES
          </span>
          <span
            className="text-[8px] tracking-wider uppercase ml-1"
            style={{
              color: settings.audioCues
                ? "rgb(34, 211, 238)"
                : "rgb(107, 114, 128)",
            }}
          >
            {settings.audioCues ? "ON" : "OFF"}
          </span>
        </button>
      </div>
    </div>
  );
}
