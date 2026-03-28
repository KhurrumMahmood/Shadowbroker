/**
 * useVoiceMode — Orchestrates the full voice conversation loop.
 *
 * Supports two modes:
 *   - Tactical: wake word ("Jarvis") → record → "Over" terminates → agent → TTS → follow-up window
 *   - Casual:   toggle on → continuous listening → silence terminates → agent → TTS → auto-resume
 *
 * This hook composes useWakeWord, useVoiceInput, and useVoiceOutput.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useWakeWord } from "./useWakeWord";
import { useVoiceInput, type TranscriptionResult } from "./useVoiceInput";
import { useVoiceOutput } from "./useVoiceOutput";

export type VoiceMode = "tactical" | "casual";

export type VoiceState =
  | "off"
  | "standby"      // Tactical: listening for wake word only
  | "listening"     // Recording user speech
  | "transcribing"  // Sending audio to STT
  | "analyzing"     // Agent is processing the query
  | "generating"    // TTS is being generated (before first audio)
  | "speaking"      // TTS audio is playing
  | "follow_up";    // Tactical: brief window accepting speech without wake word

export interface VoiceModeSettings {
  mode: VoiceMode;
  voice: string;
  followUpWindowMs: number;
  audioCues: boolean;
  picovoiceAccessKey: string;
}

const DEFAULT_SETTINGS: VoiceModeSettings = {
  mode: "tactical",
  voice: "onyx",
  followUpWindowMs: 6000,
  audioCues: true,
  picovoiceAccessKey: "",
};

interface UseVoiceModeOptions {
  settings: VoiceModeSettings;
  /** Called when voice mode submits a transcribed query. */
  onSubmitQuery: (text: string) => void;
  /** Called when "over and out" is detected or voice mode is deactivated. */
  onDeactivate?: () => void;
  /** Called on errors. */
  onError?: (error: string) => void;
}

interface UseVoiceModeReturn {
  /** Current voice state. */
  state: VoiceState;
  /** Activate voice mode. */
  activate: () => void;
  /** Deactivate voice mode. */
  deactivate: () => void;
  /** Whether voice mode is active (not "off"). */
  isActive: boolean;
  /** Signal that the agent has started processing. Call this after submitting the query. */
  notifyAnalyzing: () => void;
  /** Signal that the agent has responded. Triggers TTS. */
  notifyResponse: (text: string) => void;
  /** Speak a short progress narration during analysis. */
  narrateProgress: (text: string) => void;
  /** Current settings. */
  settings: VoiceModeSettings;
  /** Update settings. */
  updateSettings: (patch: Partial<VoiceModeSettings>) => void;
}

// Persist settings to localStorage
const SETTINGS_KEY = "shadowbroker_voice_settings";

function loadSettings(): VoiceModeSettings {
  try {
    const stored = localStorage.getItem(SETTINGS_KEY);
    if (stored) return { ...DEFAULT_SETTINGS, ...JSON.parse(stored) };
  } catch {}
  return { ...DEFAULT_SETTINGS };
}

function saveSettings(settings: VoiceModeSettings) {
  try {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
  } catch {}
}

export function useVoiceMode({
  settings: initialSettings,
  onSubmitQuery,
  onDeactivate,
  onError,
}: UseVoiceModeOptions): UseVoiceModeReturn {
  const [settings, setSettings] = useState<VoiceModeSettings>(() => ({
    ...loadSettings(),
    ...initialSettings,
  }));
  const [state, setState] = useState<VoiceState>("off");

  const stateRef = useRef<VoiceState>("off");
  stateRef.current = state;

  const followUpTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onSubmitRef = useRef(onSubmitQuery);
  onSubmitRef.current = onSubmitQuery;
  const onDeactivateRef = useRef(onDeactivate);
  onDeactivateRef.current = onDeactivate;
  const onErrorRef = useRef(onError);
  onErrorRef.current = onError;
  const settingsRef = useRef(settings);
  settingsRef.current = settings;

  const setVoiceState = useCallback((s: VoiceState) => {
    stateRef.current = s;
    setState(s);
  }, []);

  const clearFollowUpTimer = useCallback(() => {
    if (followUpTimerRef.current) {
      clearTimeout(followUpTimerRef.current);
      followUpTimerRef.current = null;
    }
  }, []);

  // --- Wake Word ---
  const handleWakeWord = useCallback(() => {
    if (stateRef.current === "standby" || stateRef.current === "follow_up") {
      clearFollowUpTimer();
      setVoiceState("listening");
      voiceInput.startListening();
    }
  }, [clearFollowUpTimer, setVoiceState]);

  const wakeWord = useWakeWord({
    onWakeWord: handleWakeWord,
    accessKey: settings.picovoiceAccessKey,
  });

  // --- Voice Input ---
  const handleTranscription = useCallback(
    (result: TranscriptionResult) => {
      if (result.overAndOutDetected) {
        // "Over and out" — deactivate voice mode
        deactivateInternal();
        // Still submit the query if there's text before "over and out"
        if (result.text.trim()) {
          onSubmitRef.current(result.text);
        }
        return;
      }

      if (result.text.trim()) {
        setVoiceState("analyzing");
        onSubmitRef.current(result.text);
      } else {
        // Empty transcription — resume listening
        if (settingsRef.current.mode === "tactical") {
          setVoiceState("standby");
        } else {
          voiceInput.startListening();
          setVoiceState("listening");
        }
      }
    },
    [setVoiceState],
  );

  const voiceInput = useVoiceInput({
    onTranscription: handleTranscription,
    onError: (msg) => onErrorRef.current?.(msg),
    onSpeechStart: () => {
      // If in follow-up window and user speaks, transition to listening
      if (stateRef.current === "follow_up") {
        clearFollowUpTimer();
        setVoiceState("listening");
      }
    },
    onSpeechEnd: () => {
      if (stateRef.current === "listening") {
        setVoiceState("transcribing");
      }
    },
  });

  // --- Voice Output ---
  const voiceOutput = useVoiceOutput({
    voice: settings.voice,
    onPlaybackStart: () => {
      setVoiceState("speaking");
    },
    onFinished: () => {
      if (stateRef.current !== "speaking") return;

      if (settingsRef.current.mode === "tactical") {
        // Start follow-up window
        setVoiceState("follow_up");
        voiceInput.startListening();
        followUpTimerRef.current = setTimeout(() => {
          if (stateRef.current === "follow_up") {
            voiceInput.stopListening();
            setVoiceState("standby");
          }
        }, settingsRef.current.followUpWindowMs);
      } else {
        // Casual: auto-resume listening
        setVoiceState("listening");
        voiceInput.startListening();
      }
    },
  });

  // --- Public API ---

  const activate = useCallback(() => {
    if (stateRef.current !== "off") return;

    if (settings.mode === "tactical" && settings.picovoiceAccessKey) {
      // Full tactical: wake word → record → "over" terminates
      setVoiceState("standby");
      wakeWord.start();
    } else {
      // Casual mode, or tactical fallback when Picovoice key is missing
      setVoiceState("listening");
      voiceInput.startListening();
    }
  }, [settings.mode, settings.picovoiceAccessKey, setVoiceState, wakeWord, voiceInput]);

  const deactivateInternal = useCallback(() => {
    clearFollowUpTimer();
    wakeWord.stop();
    voiceInput.stopListening();
    voiceOutput.stop();
    setVoiceState("off");
    onDeactivateRef.current?.();
  }, [clearFollowUpTimer, wakeWord, voiceInput, voiceOutput, setVoiceState]);

  const deactivate = useCallback(() => {
    deactivateInternal();
  }, [deactivateInternal]);

  const notifyAnalyzing = useCallback(() => {
    if (stateRef.current === "transcribing" || stateRef.current === "listening") {
      voiceInput.stopListening();
      setVoiceState("analyzing");
    }
  }, [voiceInput, setVoiceState]);

  const notifyResponse = useCallback(
    (text: string) => {
      if (stateRef.current !== "off") {
        setVoiceState("generating");
        voiceOutput.speak(text);
      }
    },
    [setVoiceState, voiceOutput],
  );

  const narrateProgress = useCallback(
    (text: string) => {
      if (stateRef.current === "analyzing") {
        voiceOutput.speakShort(text);
      }
    },
    [voiceOutput],
  );

  const updateSettings = useCallback(
    (patch: Partial<VoiceModeSettings>) => {
      setSettings((prev) => {
        const next = { ...prev, ...patch };
        saveSettings(next);
        return next;
      });
    },
    [],
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clearFollowUpTimer();
      wakeWord.stop();
      voiceInput.stopListening();
      voiceOutput.stop();
    };
  }, [clearFollowUpTimer, wakeWord, voiceInput, voiceOutput]);

  return {
    state,
    activate,
    deactivate,
    isActive: state !== "off",
    notifyAnalyzing,
    notifyResponse,
    narrateProgress,
    settings,
    updateSettings,
  };
}
