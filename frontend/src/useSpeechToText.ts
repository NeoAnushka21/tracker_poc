import { useCallback, useEffect, useRef, useState } from "react";

// Minimal typings for the Web Speech API (Chrome/Edge expose it as webkitSpeechRecognition).
type SpeechRecognitionResultLike = { isFinal: boolean; 0: { transcript: string } };
type SpeechRecognitionEventLike = { resultIndex: number; results: ArrayLike<SpeechRecognitionResultLike> };
type SpeechRecognitionLike = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((e: SpeechRecognitionEventLike) => void) | null;
  onerror: ((e: { error: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
};
type SpeechRecognitionCtor = new () => SpeechRecognitionLike;

function getRecognitionCtor(): SpeechRecognitionCtor | null {
  const w = window as unknown as { SpeechRecognition?: SpeechRecognitionCtor; webkitSpeechRecognition?: SpeechRecognitionCtor };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

const ERRORS: Record<string, string> = {
  "not-allowed": "Microphone access was blocked. Allow it in the browser's address bar and try again.",
  "service-not-allowed": "Microphone access was blocked. Allow it in the browser's address bar and try again.",
  "audio-capture": "No microphone was found.",
  network: "Voice input needs an internet connection.",
};

/**
 * Browser speech-to-text. `onText(spoken)` is called with everything recognised so far in
 * this listening session (final + in-progress words), so the caller can show live text.
 */
export function useSpeechToText(onText: (spoken: string) => void) {
  const ctor = getRecognitionCtor();
  const [listening, setListening] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const recRef = useRef<SpeechRecognitionLike | null>(null);
  const onTextRef = useRef(onText);
  onTextRef.current = onText;

  const stop = useCallback(() => recRef.current?.stop(), []);

  const start = useCallback(() => {
    if (!ctor) return;
    setError(null);
    const rec = new ctor();
    rec.lang = navigator.language || "en-US";
    rec.continuous = true;          // keep listening through short pauses
    rec.interimResults = true;      // show words as they're recognised
    let finalText = "";
    rec.onresult = (e) => {
      let interim = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const r = e.results[i];
        if (r.isFinal) finalText += r[0].transcript;
        else interim += r[0].transcript;
      }
      onTextRef.current((finalText + interim).trim());
    };
    rec.onerror = (e) => {
      if (e.error !== "no-speech" && e.error !== "aborted") {
        setError(ERRORS[e.error] ?? `Voice input error: ${e.error}`);
      }
    };
    rec.onend = () => {
      setListening(false);
      recRef.current = null;
    };
    recRef.current = rec;
    rec.start();
    setListening(true);
  }, [ctor]);

  useEffect(() => () => recRef.current?.abort(), []);

  return { supported: ctor !== null, listening, error, start, stop, clearError: () => setError(null) };
}
