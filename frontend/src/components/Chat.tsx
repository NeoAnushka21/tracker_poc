import { Fragment, useEffect, useRef, useState, type FormEvent, type KeyboardEvent, type ReactNode } from "react";
import { api } from "../api";
import type { Action, ChatMessage, User } from "../types";
import { useSpeechToText } from "../useSpeechToText";
import { AssistantAvatar, UserAvatar } from "./Avatar";
import ProposalCard from "./ProposalCard";

const EXAMPLES = [
  "had 100g cooked chicken, 10ml olive oil and 50g onion",
  "two glasses of water",
  "had a sandwich for breakfast",
  "what did I eat yesterday?",
];

type Props = { user: User; onDataChanged: () => void };

/** Renders **bold** spans; everything else stays plain text (no HTML injection). */
function renderText(text: string): ReactNode {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith("**") && part.endsWith("**") && part.length > 4
      ? <strong key={i}>{part.slice(2, -2)}</strong>
      : <Fragment key={i}>{part}</Fragment>,
  );
}

function clock(iso: string): string {
  return new Date(iso).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

function MicIcon() {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
      <rect x="9" y="3" width="6" height="11" rx="3" fill="currentColor" />
      <path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21M8.5 21h7" stroke="currentColor" strokeWidth="1.8" fill="none" strokeLinecap="round" />
    </svg>
  );
}

export default function Chat({ user, onDataChanged }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [feedbackFor, setFeedbackFor] = useState<Action | null>(null);
  const [busyAction, setBusyAction] = useState<number | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const speechBaseRef = useRef("");

  const speech = useSpeechToText((spoken) => {
    const base = speechBaseRef.current;
    setInput(base ? `${base} ${spoken}` : spoken);
  });

  useEffect(() => {
    api.history().then(setMessages).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  function toggleMic() {
    if (speech.listening) {
      speech.stop();
    } else {
      speechBaseRef.current = input.trim();
      speech.start();
    }
  }

  function updateAction(updated: Action) {
    setMessages((ms) =>
      ms.map((m) => ({ ...m, actions: m.actions.map((a) => (a.id === updated.id ? updated : a)) })),
    );
  }

  async function send(e?: FormEvent) {
    e?.preventDefault();
    if (speech.listening) speech.stop();
    const text = input.trim();
    if (!text || sending) return;
    setError(null);
    speech.clearError();
    setSending(true);
    const optimistic: ChatMessage = {
      id: -Date.now(), role: "user", content: text, created_at: new Date().toISOString(), actions: [],
    };
    setMessages((ms) => [...ms, optimistic]);
    setInput("");
    const feedbackId = feedbackFor?.id ?? null;
    try {
      const newMsgs = await api.send(text, feedbackId);
      const newActionIds = new Set(newMsgs.flatMap((m) => m.actions.map((a) => a.id)));
      setMessages((ms) => [
        // The server supersedes older open proposals when a new one is made; mirror that.
        ...ms.map((m) => ({
          ...m,
          actions: m.actions.map((a) =>
            newActionIds.size > 0 && a.status === "pending" && !newActionIds.has(a.id)
              ? { ...a, status: "superseded" as const }
              : a,
          ),
        })),
        ...newMsgs,
      ]);
      setFeedbackFor(null);
    } catch (err) {
      setMessages((ms) => ms.filter((m) => m.id !== optimistic.id));
      setInput(text);
      setError((err as Error).message);
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  }

  async function resolve(action: Action, kind: "confirm" | "reject") {
    setBusyAction(action.id);
    setError(null);
    try {
      const res = kind === "confirm" ? await api.confirm(action.id) : await api.reject(action.id);
      updateAction(res.action);
      if (feedbackFor?.id === action.id) setFeedbackFor(null);
      if (kind === "confirm") onDataChanged();
    } catch (err) {
      setError((err as Error).message);
      api.history().then(setMessages).catch(() => {});
    } finally {
      setBusyAction(null);
    }
  }

  function needsChanges(action: Action) {
    setFeedbackFor(action);
    inputRef.current?.focus();
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  // App events (confirm/cancel notes) are context for the LLM; the card status shows them in the UI.
  const visible = messages.filter((m) => m.role !== "event");
  const shownError = error ?? speech.error;

  return (
    <section className="chat card">
      <div className="chat-head">
        <AssistantAvatar size={36} />
        <div>
          <div className="chat-title">Macro assistant</div>
          <div className="muted small">Tell me what you ate; I'll do the maths.</div>
        </div>
      </div>

      <div className="messages">
        {visible.length === 0 && (
          <div className="empty">
            <AssistantAvatar size={64} />
            <p>Hi{user.preferred_name ? ` ${user.preferred_name}` : ""}! Tell me what you ate and I'll work out the macros.</p>
            <div className="examples">
              {EXAMPLES.map((ex) => (
                <button key={ex} className="chip" onClick={() => { setInput(ex); inputRef.current?.focus(); }}>
                  {ex}
                </button>
              ))}
            </div>
          </div>
        )}
        {visible.map((m) => (
          <div key={m.id} className={`msg-row ${m.role}`}>
            {m.role === "assistant"
              ? <AssistantAvatar />
              : <UserAvatar name={user.preferred_name} email={user.email} />}
            <div className="msg">
              <div className="bubble">{renderText(m.content)}</div>
              {m.actions.map((a) => (
                <ProposalCard
                  key={a.id}
                  action={a}
                  busy={busyAction === a.id}
                  awaitingFeedback={feedbackFor?.id === a.id}
                  onConfirm={() => resolve(a, "confirm")}
                  onNeedsChanges={() => needsChanges(a)}
                  onCancel={() => resolve(a, "reject")}
                />
              ))}
              <span className="msg-time">{clock(m.created_at)}</span>
            </div>
          </div>
        ))}
        {sending && (
          <div className="msg-row assistant">
            <AssistantAvatar />
            <div className="msg">
              <div className="bubble typing" aria-label="Assistant is typing">
                <span /><span /><span />
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {shownError && <div className="error chat-error">{shownError}</div>}

      <form className="composer" onSubmit={send}>
        {feedbackFor && (
          <div className="feedback-chip">
            Changing: <b>{feedbackFor.payload.summary}</b>
            <button type="button" className="ghost" onClick={() => setFeedbackFor(null)} aria-label="Stop giving feedback">✕</button>
          </div>
        )}
        {speech.listening && <div className="listening-hint">Listening… tap the mic again when you're done.</div>}
        <div className="composer-row">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            rows={2}
            maxLength={4000}
            placeholder={
              speech.listening ? "Speak now…"
                : feedbackFor ? "What should I change? e.g. 'the chicken was 150g'"
                : "What did you eat? Type or tap the mic"
            }
          />
          {speech.supported && (
            <button
              type="button"
              className={`mic ${speech.listening ? "on" : ""}`}
              onClick={toggleMic}
              disabled={sending}
              aria-pressed={speech.listening}
              aria-label={speech.listening ? "Stop voice input" : "Start voice input"}
              title={speech.listening ? "Stop voice input" : "Speak instead of typing"}
            >
              <MicIcon />
            </button>
          )}
          <button className="primary" disabled={sending || !input.trim()}>Send</button>
        </div>
      </form>
    </section>
  );
}
