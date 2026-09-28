import { Fragment, useEffect, useRef, useState, type FormEvent, type KeyboardEvent, type ReactNode } from "react";
import { api } from "../api";
import type { Action, ChatMessage, User } from "../types";
import { useSpeechToText } from "../useSpeechToText";
import { MacBroAvatar, UserAvatar } from "./Avatar";
import ProposalCard from "./ProposalCard";

const EXAMPLES = [
  "had 100g cooked chicken, 10ml olive oil and 50g onion",
  "two glasses of water",
  "had a sandwich for breakfast",
  "what did I eat yesterday?",
];

type Props = {
  user: User;
  onDataChanged: () => void;
  /** Text handed over from elsewhere (e.g. the dashboard's "Ask MacBro to edit"). */
  draft?: { text: string; nonce: number } | null;
};

function ProgressCard({ m }: { m: ChatMessage }) {
  const d = m.data!;
  const kcalPct = d.calories.pct ?? 0;
  return (
    <div className="progress-card">
      <div className="progress-head">
        <span className="progress-title">Day so far</span>
        <span className="muted small">{d.meals_logged} meal{d.meals_logged === 1 ? "" : "s"} logged</span>
      </div>
      <div className="progress-kcal">
        <b>{d.calories.consumed.toLocaleString()}</b>
        {d.calories.target != null && <span className="muted"> / {d.calories.target.toLocaleString()} kcal</span>}
        {d.calories.pct != null && (
          <span className={`progress-pct ${kcalPct > 110 ? "warn" : ""}`}>{d.calories.pct}% of daily budget</span>
        )}
      </div>
      <div className="progress-macros">
        {d.macros.map((x) => {
          const left = x.target != null ? Math.max(0, Math.round(x.target - x.consumed)) : null;
          return (
            <div key={x.key} className={`bar-row ${x.key.replace("_g", "")} progress-macro`}>
              <div className="bar-label">
                <span className="bar-name"><i className="swatch" aria-hidden="true" />{x.label}</span>
                <span className="num">{x.pct != null ? `${x.pct}%` : `${x.consumed} g`}</span>
              </div>
              <div className="bar"><div className="bar-fill" style={{ width: `${Math.min(100, x.pct ?? 0)}%` }} /></div>
              {left != null && <div className="muted tiny">{left > 0 ? `${left} g to go` : "done ✓"}</div>}
            </div>
          );
        })}
      </div>
      <p className="progress-headline">{d.headline}</p>
    </div>
  );
}

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

export default function Chat({ user, onDataChanged, draft }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [feedbackFor, setFeedbackFor] = useState<Action | null>(null);
  const [busyAction, setBusyAction] = useState<number | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const speechBaseRef = useRef("");
  // The in-flight request, so Stop can abort it (browser) and cancel it (server).
  const inflightRef = useRef<{ id: string; controller: AbortController; text: string; optimisticId: number } | null>(null);

  useEffect(() => {
    if (draft) {
      setInput(draft.text);
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [draft]);

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
    const requestId = `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
    const controller = new AbortController();
    inflightRef.current = { id: requestId, controller, text, optimisticId: optimistic.id };
    try {
      const newMsgs = await api.send(text, feedbackId, requestId, controller.signal);
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
      if (controller.signal.aborted) return;   // stop() already restored the draft
      setMessages((ms) => ms.filter((m) => m.id !== optimistic.id));
      setInput(text);
      setError((err as Error).message);
    } finally {
      if (inflightRef.current?.id === requestId) {
        inflightRef.current = null;
        setSending(false);
        inputRef.current?.focus();
      }
    }
  }

  /** Stop: abort the request, tell the server to drop the turn, and give the text back to edit. */
  async function stop() {
    const inflight = inflightRef.current;
    if (!inflight) return;
    inflightRef.current = null;
    inflight.controller.abort();
    setMessages((ms) => ms.filter((m) => m.id !== inflight.optimisticId));
    setInput(inflight.text);
    setSending(false);
    setError(null);
    inputRef.current?.focus();
    try {
      const { status } = await api.cancelChat(inflight.id);
      if (status === "finished") {
        // Too late to stop: the reply was saved, so show it rather than lose it.
        setInput("");
        setMessages(await api.history());
        setError("MacBro had already replied, so that message was kept.");
      }
    } catch {
      /* if the cancel call fails, the history reload on the next action catches up */
    }
  }

  async function resolve(action: Action, kind: "confirm" | "reject") {
    setBusyAction(action.id);
    setError(null);
    try {
      const res = kind === "confirm" ? await api.confirm(action.id) : await api.reject(action.id);
      updateAction(res.action);
      if (res.progress) setMessages((ms) => [...ms, res.progress!]);
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
        <MacBroAvatar size={36} />
        <div>
          <div className="chat-title">MacBro</div>
          <div className="muted small">Your macro bro. Tell me what you ate; I'll do the maths.</div>
        </div>
      </div>

      <div className="messages">
        {visible.length === 0 && (
          <div className="empty">
            <MacBroAvatar size={64} />
            <p className="empty-title">Hey{user.preferred_name ? ` ${user.preferred_name}` : ""}, I'm MacBro!</p>
            <p className="muted">Tell me what you ate, type or tap the mic, and I'll work out the macros.</p>
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
              ? <MacBroAvatar />
              : <UserAvatar name={user.preferred_name} email={user.email} />}
            <div className="msg">
              {m.kind === "progress" && m.data ? <ProgressCard m={m} /> : <div className="bubble">{renderText(m.content)}</div>}
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
            <MacBroAvatar />
            <div className="msg">
              <div className="bubble typing" aria-label="MacBro is thinking">
                <span /><span /><span />
              </div>
              <button type="button" className="ghost stop-inline" onClick={stop}>■ Stop</button>
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
            readOnly={sending}
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
          {sending ? (
            <button type="button" className="stop-btn" onClick={stop} title="Stop and edit your message">■ Stop</button>
          ) : (
            <button className="primary" disabled={!input.trim()}>Send</button>
          )}
        </div>
      </form>
    </section>
  );
}
