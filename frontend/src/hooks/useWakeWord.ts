/**
 * useWakeWord — Picovoice Porcupine WASM wake word detection.
 *
 * Listens continuously for "Jarvis" using a lightweight WASM model (~1MB, <4% CPU).
 * Runs detection in a Web Worker; audio is captured via AudioContext.
 *
 * Requires:
 *   - @picovoice/porcupine-web installed
 *   - Porcupine model file at /porcupine_params.pv in public/
 *     (download from https://github.com/Picovoice/porcupine/tree/master/lib/common)
 *   - NEXT_PUBLIC_PICOVOICE_ACCESS_KEY set in .env.local
 *
 * Usage:
 *   const { start, stop, isActive, isLoaded, error } = useWakeWord({
 *     onWakeWord: () => { ... },
 *     accessKey: process.env.NEXT_PUBLIC_PICOVOICE_ACCESS_KEY ?? "",
 *   });
 */
import { useCallback, useEffect, useRef, useState } from "react";

interface UseWakeWordOptions {
  /** Called when the wake word is detected. */
  onWakeWord: () => void;
  /** Picovoice access key (free tier: picovoice.ai/console). */
  accessKey: string;
  /** Auto-start listening on mount. Default: false. */
  autoStart?: boolean;
}

interface UseWakeWordReturn {
  /** Start wake word detection. */
  start: () => Promise<void>;
  /** Stop wake word detection. */
  stop: () => Promise<void>;
  /** Whether the engine is currently listening. */
  isActive: boolean;
  /** Whether the WASM model has loaded. */
  isLoaded: boolean;
  /** Error message if initialization failed. */
  error: string | null;
}

export function useWakeWord({
  onWakeWord,
  accessKey,
  autoStart = false,
}: UseWakeWordOptions): UseWakeWordReturn {
  const [isActive, setIsActive] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Use `any` for Porcupine types — avoids coupling to the exact d.ts shape
  // while still dynamically importing to keep the bundle small.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const workerRef = useRef<any>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const onWakeWordRef = useRef(onWakeWord);
  onWakeWordRef.current = onWakeWord;

  const initEngine = useCallback(async () => {
    if (workerRef.current) return;
    if (!accessKey) {
      setError("Picovoice access key is required");
      return;
    }

    try {
      // Dynamic import to keep bundle small (~1MB loaded on demand)
      const { PorcupineWorker, BuiltInKeyword } = await import(
        "@picovoice/porcupine-web"
      );

      const worker = await PorcupineWorker.create(
        accessKey,
        // "Jarvis" is a built-in keyword — no custom model file needed
        [{ builtin: BuiltInKeyword.Jarvis, sensitivity: 0.65 }],
        (detection: { label: string; index: number }) => {
          if (detection.label === "Jarvis" || detection.index === 0) {
            onWakeWordRef.current();
          }
        },
        // Porcupine parameter model — must be placed in public/
        { publicPath: "/porcupine_params.pv" }
      );

      workerRef.current = worker;
      setIsLoaded(true);
      setError(null);
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Failed to load wake word engine";
      setError(msg);
      console.error("[useWakeWord] Init failed:", err);
    }
  }, [accessKey]);

  const start = useCallback(async () => {
    if (!workerRef.current) {
      await initEngine();
    }
    const worker = workerRef.current;
    if (!worker) return;

    try {
      // Capture microphone audio
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { sampleRate: worker.sampleRate, channelCount: 1 },
      });
      streamRef.current = stream;

      const audioContext = new AudioContext({ sampleRate: worker.sampleRate });
      audioContextRef.current = audioContext;
      const source = audioContext.createMediaStreamSource(stream);

      // Feed PCM frames to Porcupine worker
      const bufferSize = worker.frameLength;
      const processor = audioContext.createScriptProcessor(bufferSize, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (event: AudioProcessingEvent) => {
        const inputData = event.inputBuffer.getChannelData(0);
        // Convert Float32 [-1, 1] to Int16
        const pcm = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
          pcm[i] = Math.max(
            -32768,
            Math.min(32767, Math.round(inputData[i] * 32767))
          );
        }
        worker.process(pcm);
      };

      source.connect(processor);
      processor.connect(audioContext.destination);
      setIsActive(true);
    } catch (err) {
      console.error("[useWakeWord] Start failed:", err);
      setError(
        err instanceof Error ? err.message : "Failed to start microphone"
      );
    }
  }, [initEngine]);

  const stop = useCallback(async () => {
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (audioContextRef.current) {
      await audioContextRef.current.close();
      audioContextRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    setIsActive(false);
  }, []);

  // Auto-start if requested
  useEffect(() => {
    if (autoStart && accessKey) {
      start();
    }
  }, [autoStart, accessKey, start]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (processorRef.current) processorRef.current.disconnect();
      if (audioContextRef.current)
        audioContextRef.current.close().catch(() => {});
      if (streamRef.current)
        streamRef.current.getTracks().forEach((t) => t.stop());
      if (workerRef.current) {
        workerRef.current.release().catch(() => {});
        workerRef.current = null;
      }
    };
  }, []);

  return { start, stop, isActive, isLoaded, error };
}
