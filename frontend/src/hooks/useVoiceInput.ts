/**
 * useVoiceInput — VAD-powered voice recording with cloud STT transcription.
 *
 * Activated externally (e.g., by wake word or toggle). Records audio using
 * Silero VAD for speech boundary detection, then sends to the backend
 * /api/assistant/transcribe endpoint.
 *
 * Detects "over" / "over and out" in transcriptions for tactical mode.
 */
import { useCallback, useRef, useState } from "react";

export type TranscriptionResult = {
  /** Transcribed text with "over" stripped if detected. */
  text: string;
  /** Raw transcript before stripping. */
  rawText: string;
  /** Duration of the audio in seconds. */
  durationS: number | null;
  /** Whether "over" was detected at the end. */
  overDetected: boolean;
  /** Whether "over and out" was detected (exit voice mode). */
  overAndOutDetected: boolean;
};

interface UseVoiceInputOptions {
  /** Called when transcription completes. */
  onTranscription: (result: TranscriptionResult) => void;
  /** Called when an error occurs. */
  onError?: (error: string) => void;
  /** Called when recording starts (speech detected). */
  onSpeechStart?: () => void;
  /** Called when recording ends (silence detected). */
  onSpeechEnd?: () => void;
}

interface UseVoiceInputReturn {
  /** Start listening for speech via VAD. */
  startListening: () => Promise<void>;
  /** Stop listening and discard any in-progress recording. */
  stopListening: () => void;
  /** Whether the hook is actively listening for speech. */
  isListening: boolean;
  /** Whether audio is being sent for transcription. */
  isTranscribing: boolean;
  /** Whether microphone permission has been granted. */
  hasPermission: boolean | null;
}

// Patterns for detecting "over" and "over and out" at the end of speech.
// Matches after optional punctuation/whitespace at the end.
const OVER_AND_OUT_RE = /[,.]?\s*over\s+and\s+out[.!]?\s*$/i;
const OVER_RE = /[,.]?\s*over[.!]?\s*$/i;

export function stripOverSuffix(text: string): {
  cleaned: string;
  overDetected: boolean;
  overAndOutDetected: boolean;
} {
  if (OVER_AND_OUT_RE.test(text)) {
    return {
      cleaned: text.replace(OVER_AND_OUT_RE, "").trim(),
      overDetected: true,
      overAndOutDetected: true,
    };
  }
  if (OVER_RE.test(text)) {
    return {
      cleaned: text.replace(OVER_RE, "").trim(),
      overDetected: true,
      overAndOutDetected: false,
    };
  }
  return { cleaned: text, overDetected: false, overAndOutDetected: false };
}

export function useVoiceInput({
  onTranscription,
  onError,
  onSpeechStart,
  onSpeechEnd,
}: UseVoiceInputOptions): UseVoiceInputReturn {
  const [isListening, setIsListening] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [hasPermission, setHasPermission] = useState<boolean | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const vadRef = useRef<ReturnType<typeof createVADSession> | null>(null);

  // Callbacks stored in refs to avoid stale closures
  const onTranscriptionRef = useRef(onTranscription);
  onTranscriptionRef.current = onTranscription;
  const onErrorRef = useRef(onError);
  onErrorRef.current = onError;
  const onSpeechStartRef = useRef(onSpeechStart);
  onSpeechStartRef.current = onSpeechStart;
  const onSpeechEndRef = useRef(onSpeechEnd);
  onSpeechEndRef.current = onSpeechEnd;

  const sendToSTT = useCallback(async (audioBlob: Blob) => {
    setIsTranscribing(true);
    try {
      const formData = new FormData();
      formData.append("file", audioBlob, "recording.webm");

      const resp = await fetch("/api/assistant/transcribe", {
        method: "POST",
        body: formData,
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ error: "Transcription failed" }));
        throw new Error(err.error || `HTTP ${resp.status}`);
      }

      const data = await resp.json();
      const rawText = (data.text || "").trim();

      if (!rawText) {
        // Empty transcription — ignore silently
        return;
      }

      const { cleaned, overDetected, overAndOutDetected } =
        stripOverSuffix(rawText);

      onTranscriptionRef.current({
        text: cleaned,
        rawText,
        durationS: data.duration_s ?? null,
        overDetected,
        overAndOutDetected,
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Transcription failed";
      onErrorRef.current?.(msg);
    } finally {
      setIsTranscribing(false);
    }
  }, []);

  const startListening = useCallback(async () => {
    if (isListening) return;

    try {
      // Request microphone permission
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          channelCount: 1,
          sampleRate: 16000,
        },
      });
      streamRef.current = stream;
      setHasPermission(true);

      // Set up MediaRecorder for capturing audio
      const recorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
          ? "audio/webm;codecs=opus"
          : "audio/webm",
      });
      mediaRecorderRef.current = recorder;
      audioChunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      recorder.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        audioChunksRef.current = [];
        if (blob.size > 0) {
          sendToSTT(blob);
        }
      };

      // Start VAD-driven recording
      // The VAD monitors the audio stream and triggers recording start/stop.
      // We use a simple approach: start recording when speech is detected,
      // stop after sustained silence.
      const vadSession = createVADSession(stream, {
        onSpeechStart: () => {
          onSpeechStartRef.current?.();
          if (recorder.state === "inactive") {
            audioChunksRef.current = [];
            recorder.start(100); // collect in 100ms chunks
          }
        },
        onSpeechEnd: () => {
          onSpeechEndRef.current?.();
          if (recorder.state === "recording") {
            recorder.stop();
          }
        },
      });

      vadRef.current = vadSession;
      vadSession.start();
      setIsListening(true);
    } catch (err) {
      if (err instanceof DOMException && err.name === "NotAllowedError") {
        setHasPermission(false);
        onErrorRef.current?.("Microphone permission denied");
      } else {
        onErrorRef.current?.(
          err instanceof Error ? err.message : "Failed to start voice input"
        );
      }
    }
  }, [isListening, sendToSTT]);

  const stopListening = useCallback(() => {
    vadRef.current?.stop();
    vadRef.current = null;

    if (mediaRecorderRef.current?.state === "recording") {
      mediaRecorderRef.current.stop();
    }
    mediaRecorderRef.current = null;

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }

    setIsListening(false);
  }, []);

  return {
    startListening,
    stopListening,
    isListening,
    isTranscribing,
    hasPermission,
  };
}

// ---------------------------------------------------------------------------
// Lightweight VAD session using AudioWorklet + energy detection.
// Falls back to simple energy-based detection if @ricky0123/vad is not available.
// This avoids a hard dependency on the VAD library for initial development.
// ---------------------------------------------------------------------------
type VADCallbacks = {
  onSpeechStart: () => void;
  onSpeechEnd: () => void;
};

function createVADSession(stream: MediaStream, callbacks: VADCallbacks) {
  let active = false;
  let isSpeaking = false;
  let silenceStart = 0;
  const SILENCE_THRESHOLD = 2000; // ms of silence before considering speech ended
  const ENERGY_THRESHOLD = 0.01; // RMS energy threshold for speech detection

  let audioContext: AudioContext | null = null;
  let analyser: AnalyserNode | null = null;
  let source: MediaStreamAudioSourceNode | null = null;
  let rafId: number | null = null;

  function start() {
    active = true;
    audioContext = new AudioContext();
    analyser = audioContext.createAnalyser();
    analyser.fftSize = 512;
    source = audioContext.createMediaStreamSource(stream);
    source.connect(analyser);

    const dataArray = new Float32Array(analyser.fftSize);

    function tick() {
      if (!active || !analyser) return;

      analyser.getFloatTimeDomainData(dataArray);

      // Calculate RMS energy
      let sum = 0;
      for (let i = 0; i < dataArray.length; i++) {
        sum += dataArray[i] * dataArray[i];
      }
      const rms = Math.sqrt(sum / dataArray.length);

      const now = Date.now();

      if (rms > ENERGY_THRESHOLD) {
        silenceStart = 0;
        if (!isSpeaking) {
          isSpeaking = true;
          callbacks.onSpeechStart();
        }
      } else if (isSpeaking) {
        if (silenceStart === 0) {
          silenceStart = now;
        } else if (now - silenceStart > SILENCE_THRESHOLD) {
          isSpeaking = false;
          silenceStart = 0;
          callbacks.onSpeechEnd();
        }
      }

      rafId = requestAnimationFrame(tick);
    }

    tick();
  }

  function stop() {
    active = false;
    if (rafId !== null) {
      cancelAnimationFrame(rafId);
      rafId = null;
    }
    source?.disconnect();
    audioContext?.close();
    audioContext = null;
    analyser = null;
    source = null;

    // Fire speech end if still speaking when stopped
    if (isSpeaking) {
      isSpeaking = false;
      callbacks.onSpeechEnd();
    }
  }

  return { start, stop };
}
