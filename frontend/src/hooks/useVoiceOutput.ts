/**
 * useVoiceOutput — Progressive sentence-pipelined TTS playback.
 *
 * Splits text into sentences, requests TTS for each, and plays them
 * sequentially. First sentence starts playing immediately while the rest
 * are generated in parallel.
 *
 * Usage:
 *   const { speak, speakShort, stop, isSpeaking, isGenerating } = useVoiceOutput({
 *     voice: "onyx",
 *     onFinished: () => { ... },
 *   });
 */
import { useCallback, useRef, useState } from "react";

interface UseVoiceOutputOptions {
  /** TTS voice name. Default: "onyx". */
  voice?: string;
  /** Called when all audio has finished playing. */
  onFinished?: () => void;
  /** Called when first audio chunk starts playing. */
  onPlaybackStart?: () => void;
}

interface UseVoiceOutputReturn {
  /** Speak a full response — splits into sentences and pipelines TTS. */
  speak: (text: string) => void;
  /** Speak a short phrase immediately (for progress narration). */
  speakShort: (text: string) => void;
  /** Stop all playback and clear the queue. */
  stop: () => void;
  /** Whether audio is currently playing. */
  isSpeaking: boolean;
  /** Whether TTS is being generated (before first audio plays). */
  isGenerating: boolean;
}

// Split text into sentences. Handles common abbreviations to avoid false splits.
const SENTENCE_RE = /(?<=[.!?])\s+(?=[A-Z])/;

export function splitSentences(text: string): string[] {
  const raw = text.split(SENTENCE_RE).filter((s) => s.trim().length > 0);
  // Merge very short fragments with the previous sentence
  const merged: string[] = [];
  for (const s of raw) {
    if (merged.length > 0 && s.length < 20) {
      merged[merged.length - 1] += " " + s;
    } else {
      merged.push(s);
    }
  }
  return merged;
}

async function fetchTTSAudio(
  text: string,
  voice: string,
  signal?: AbortSignal,
): Promise<Blob> {
  const resp = await fetch("/api/assistant/tts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, voice }),
    signal,
  });

  if (!resp.ok) {
    throw new Error(`TTS failed: HTTP ${resp.status}`);
  }

  return resp.blob();
}

export function useVoiceOutput({
  voice = "onyx",
  onFinished,
  onPlaybackStart,
}: UseVoiceOutputOptions = {}): UseVoiceOutputReturn {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

  const abortRef = useRef<AbortController | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const currentUrlRef = useRef<string | null>(null);
  const queueRef = useRef<Blob[]>([]);
  const playingRef = useRef(false);
  const stoppedRef = useRef(false);
  // Track whether all TTS fetches are done so playNext knows when to fire onFinished
  const allFetchedRef = useRef(false);

  const onFinishedRef = useRef(onFinished);
  onFinishedRef.current = onFinished;
  const onPlaybackStartRef = useRef(onPlaybackStart);
  onPlaybackStartRef.current = onPlaybackStart;

  // Play the next audio blob in the queue
  const playNext = useCallback(() => {
    if (stoppedRef.current) return;

    if (queueRef.current.length === 0) {
      // Queue is empty — only finish if all fetches are done
      if (allFetchedRef.current) {
        playingRef.current = false;
        setIsSpeaking(false);
        onFinishedRef.current?.();
      }
      // Otherwise, playback will resume when the next blob arrives
      return;
    }

    const blob = queueRef.current.shift()!;
    const url = URL.createObjectURL(blob);
    currentUrlRef.current = url;
    const audio = new Audio(url);
    audioRef.current = audio;

    audio.onplay = () => {
      if (!playingRef.current) {
        playingRef.current = true;
        onPlaybackStartRef.current?.();
      }
    };

    audio.onended = () => {
      URL.revokeObjectURL(url);
      currentUrlRef.current = null;
      audioRef.current = null;
      playNext();
    };

    audio.onerror = () => {
      URL.revokeObjectURL(url);
      currentUrlRef.current = null;
      audioRef.current = null;
      playNext();
    };

    audio.play().catch(() => {
      // Autoplay blocked — user interaction required
      URL.revokeObjectURL(url);
      currentUrlRef.current = null;
      audioRef.current = null;
      playingRef.current = false;
      setIsSpeaking(false);
    });
  }, []);

  const speak = useCallback(
    (text: string) => {
      // Cancel any in-progress generation/playback
      stop();
      stoppedRef.current = false;
      allFetchedRef.current = false;

      const controller = new AbortController();
      abortRef.current = controller;

      const sentences = splitSentences(text);
      if (sentences.length === 0) return;

      setIsGenerating(true);
      setIsSpeaking(true);

      // Indexed results array to preserve sentence order
      const results: (Blob | null)[] = new Array(sentences.length).fill(null);
      let nextToQueue = 0;
      let playbackStarted = false;

      // Flush contiguous completed sentences to the queue in order
      const flushQueue = () => {
        if (stoppedRef.current) return;
        while (nextToQueue < results.length && results[nextToQueue]) {
          queueRef.current.push(results[nextToQueue]!);
          nextToQueue++;
        }
        // Start playback once the first sentence is queued
        if (!playbackStarted && queueRef.current.length > 0) {
          playbackStarted = true;
          setIsGenerating(false);
          playNext();
        } else if (playbackStarted && !audioRef.current && queueRef.current.length > 0) {
          // Playback stalled (queue was empty, now has items) — resume
          playNext();
        }
      };

      const promises = sentences.map(async (sentence, i) => {
        try {
          const blob = await fetchTTSAudio(
            sentence,
            voice,
            controller.signal,
          );
          if (stoppedRef.current) return;
          results[i] = blob;
          flushQueue();
        } catch (err) {
          if (err instanceof DOMException && err.name === "AbortError") return;
          console.error(`[useVoiceOutput] TTS failed for sentence ${i}:`, err);
          // Mark as a zero-length blob so ordering isn't stuck
          results[i] = new Blob();
          flushQueue();
        }
      });

      // When all fetches complete, mark as done so playNext can fire onFinished
      Promise.all(promises).then(() => {
        allFetchedRef.current = true;
        if (!playbackStarted && !stoppedRef.current) {
          // All requests failed
          setIsGenerating(false);
          setIsSpeaking(false);
          onFinishedRef.current?.();
        } else if (!audioRef.current && queueRef.current.length === 0 && !stoppedRef.current) {
          // All done and nothing playing — fire finished
          playingRef.current = false;
          setIsSpeaking(false);
          onFinishedRef.current?.();
        }
      });
    },
    [voice, playNext],
  );

  // Speak a short phrase immediately — used for progress narration.
  // Does NOT clear the queue — narration plays before the main response.
  const speakShort = useCallback(
    (text: string) => {
      if (stoppedRef.current) return;

      const controller = new AbortController();
      fetchTTSAudio(text, voice, controller.signal)
        .then((blob) => {
          if (stoppedRef.current) return;
          // Insert at the front of the queue if not already playing
          if (!playingRef.current) {
            queueRef.current.unshift(blob);
            setIsSpeaking(true);
            playNext();
          } else {
            // If already playing, queue after current
            queueRef.current.unshift(blob);
          }
        })
        .catch(() => {});
    },
    [voice, playNext],
  );

  const stop = useCallback(() => {
    stoppedRef.current = true;
    allFetchedRef.current = false;
    abortRef.current?.abort();
    abortRef.current = null;

    // Revoke current blob URL to prevent leak
    if (currentUrlRef.current) {
      URL.revokeObjectURL(currentUrlRef.current);
      currentUrlRef.current = null;
    }

    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }

    queueRef.current = [];
    playingRef.current = false;
    setIsSpeaking(false);
    setIsGenerating(false);
  }, []);

  return { speak, speakShort, stop, isSpeaking, isGenerating };
}
