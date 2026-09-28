import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { api } from "../api";
import type { Action, ChatMessage, User } from "../types";
import ProposalCard from "./ProposalCard";

const EXAMPLES = [
  "had 100g cooked chicken, 10ml olive oil and 50g onion",
  "two glasses of water",
  "had a sandwich for breakfast",
  "what did I eat yesterday?",
];

type Props = { user: User; onDataChanged: () => void };

export default function Chat({ user, onDataChanged }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [feedbackFor, setFeedbackFor] = useState<Action | null>(null);
  const [busyAction, setBusyAction] = useState<number | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    api.history().then(setMessages).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  function updateAction(updated: Action) {
    setMessages((ms) =>
      ms.map((m) => ({ ...m, actions: m.actions.map((a) => (a.id === updated.id ? updated : a)) })),
    );
  }

  async function send(e?: FormEvent) {
    e?.preventDefault();
    const text = input.trim();
    if (!text || sending) return;
    setError(null);
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

  return (
    <section className="chat card">
      <div className="messages">
        {visible.length === 0 && (
          <div className="empty">
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
          <div key={m.id} className={`msg ${m.role}`}>
            <div className="bubble">{m.content}</div>
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
          </div>
        ))}
        {sending && (
          <div className="msg assistant">
            <div className="bubble typing">Thinking…</div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {error && <div className="error chat-error">{error}</div>}

      <form className="composer" onSubmit={send}>
        {feedbackFor && (
          <div className="feedback-chip">
            Changing: <b>{feedbackFor.payload.summary}</b>
            <button type="button" className="ghost" onClick={() => setFeedbackFor(null)} aria-label="Stop giving feedback">✕</button>
          </div>
        )}
        <div className="composer-row">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            rows={2}
            maxLength={4000}
            placeholder={feedbackFor ? "What should I change? e.g. 'the chicken was 150g'" : "What did you eat?"}
          />
          <button className="primary" disabled={sending || !input.trim()}>Send</button>
        </div>
      </form>
    </section>
  );
}
