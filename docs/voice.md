# Voice Communication

Military radio-style voice interface for the AI assistant. User says a wake word, speaks a query ending with "over", and hears the response via TTS.

## Conversation Flow

```
Standby (wake word listening)
  → Listening (VAD-driven recording)
  → Transcribing (cloud STT)
  → Analyzing (agent pipeline)
  → Speaking (TTS playback)
  → Follow-up window (5-7s, no wake word needed)
  → Standby
```

- **"Over"** at the end of speech signals the user is done (like releasing a transmit key)
- **"Over and out"** exits voice mode entirely
- **Barge-in**: speaking during TTS playback stops playback and starts recording

## Architecture

### Frontend Hooks (`frontend/src/hooks/`)

| Hook | Purpose |
|------|---------|
| `useWakeWord.ts` | Picovoice Porcupine WASM wake word detection ("Jarvis"). Manual `AudioContext` + `ScriptProcessorNode` pipeline feeds PCM frames to `PorcupineWorker`. |
| `useVoiceInput.ts` | VAD-powered recording with energy-based silence detection (2s threshold). Sends audio blobs to `/api/assistant/transcribe`. Detects "over" / "over and out" suffixes via regex (`stripOverSuffix()`). |
| `useVoiceOutput.ts` | Sentence-pipelined TTS. Splits text via `splitSentences()`, fetches TTS for all sentences in parallel, plays back in order via indexed results array and `flushQueue()`. |
| `useVoiceMode.ts` | State machine orchestrating the above three hooks. Manages transitions between standby/listening/transcribing/analyzing/speaking/follow-up states. |

### Frontend Components (`frontend/src/components/`)

| Component | Purpose |
|-----------|---------|
| `VoiceIndicator.tsx` | HUD-style visual state indicator (pulsing rings, waveforms, status labels like `COMMS STANDBY`, `RECEIVING...`) |
| `VoiceSettings.tsx` | Voice configuration panel (voice selection, wake word toggle, follow-up window) |

### Backend (`backend/services/voice.py`)

- **`transcribe(audio_bytes, content_type)`** — Async. Forwards audio to OpenAI `gpt-4o-mini-transcribe` ($0.003/min), returns `{text, duration_s}`. Validates content-type against `ALLOWED_AUDIO_TYPES`.
- **`tts_stream(text, voice)`** — Async generator. Streams audio chunks from OpenAI `tts-1` ($0.015/1K chars). Default voice: "onyx" (deep, authoritative).
- **`AVAILABLE_VOICES`** — `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`.

### API Endpoints (`backend/main.py`)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/assistant/transcribe` | POST | Multipart audio upload (max 25 MB). Content-type validated. Rate-limited 15/min. |
| `/api/assistant/tts` | POST | JSON `{text, voice}`. Text max 4096 chars. Returns streaming `audio/mpeg`. Rate-limited 15/min. |
| `/api/assistant/voices` | GET | Lists available TTS voices. |

## Environment Variables

| Variable | Location | Required | Notes |
|----------|----------|----------|-------|
| `TTS_OPENAI_API_KEY` | Backend `.env` | Yes (for voice) | OpenAI key for STT + TTS. Falls back to `OPENAI_API_KEY`. |
| `NEXT_PUBLIC_PICOVOICE_ACCESS_KEY` | Frontend `.env.local` | Yes (for wake word) | Free tier: 1 MAU. Get from picovoice.ai/console. |

## Key Design Decisions

- **"Over" detection** uses STT transcript inspection (regex on final word), not a separate keyword model. Only matches "over" as the last word — "flew over Syria" won't trigger.
- **Ordered playback**: TTS sentences are fetched in parallel but played in order via an indexed results array. `flushQueue()` pushes contiguous completed sentences to the playback queue.
- **Failed sentences** produce zero-length blobs so the ordering queue isn't stuck waiting.
- **Blob URL lifecycle**: `currentUrlRef` tracks the active blob URL, revoked in `stop()` to prevent memory leaks.
- **Eager API key validation**: TTS endpoint validates the key before creating `StreamingResponse` — errors during async generator iteration would produce truncated 200 responses.
- **Stale closure prevention**: `handleSendVoice` in `AIAssistantPanel.tsx` uses `handleSendInternalRef` (a ref) to always call the latest version of the send function.
- **Async STT**: `transcribe()` uses `httpx.AsyncClient` to avoid blocking FastAPI's event loop.

## Tests

```bash
# Backend (13 tests)
cd backend && source venv/bin/activate
python -m pytest tests/test_voice.py -v

# Frontend (17 tests)
cd frontend
npx vitest run src/__tests__/hooks/useVoiceInput.test.ts src/__tests__/hooks/useVoiceOutput.test.ts
```

## Cost Per Voice Exchange

| Component | Cost |
|-----------|------|
| Wake word (Porcupine WASM) | Free (client-side) |
| STT (~10s speech) | ~$0.0005 |
| TTS (~800 chars response) | ~$0.012 |
| **Total voice overhead** | **~$0.013** |

## Porcupine Licensing

Free tier allows 1 monthly active user (sufficient for dev/personal use). For multi-user deployment: commercial license ($6k/year), or swap to openWakeWord/Hey Buddy! (free, Apache 2.0), or fall back to toggle-based activation.
