import { Fragment, useEffect, useRef, useState, type FormEvent, type KeyboardEvent, type ReactNode } from "react";
import { api, type AiAllowance } from "../api";
import type { Action, ChatMessage, MacroProgressData, ProgressData, User, WaterProgressData } from "../types";
import { dayLabel, litres, localTodayIso } from "../format";
import { haptic } from "../haptics";
import { useRevealFill } from "../motion";
import { useSpeechToText } from "../useSpeechToText";
import { MacBroAvatar, UserAvatar } from "./Avatar";
import { macroState } from "./Dashboard";
import ProposalCard from "./ProposalCard";
import { WaterDrop } from "./icons";

const EXAMPLES = [
  "had 100g cooked chicken, 10ml olive oil and 50g onion",
  "two glasses of water",
  "had a sandwich for breakfast",
  "what did I eat yesterday?",
];

type Props = {
  user: User;
  onDataChanged: () => void;
  /** Text (and optionally a day) handed over from elsewhere, e.g. the dashboard's "Edit in chat". */
  draft?: { text: string; nonce: number; date?: string } | null;
  /** True while the chat window is open; opening it jumps to the latest message. */
  active: boolean;
  /** The chat window's header buttons (ChatWidget). */
  onMinimize?: () => void;
  onClose?: () => void;
};

type DayBlock = { day: string; messages: ChatMessage[] };

/** After a water log: the day's water against the goal (no macros). */
function WaterProgressCard({ d, fresh }: { d: WaterProgressData; fresh?: boolean }) {
  const { consumed_ml: had, target_ml: target, pct } = d.water;
  const [barRef, shownPct] = useRevealFill<HTMLDivElement>(Math.min(100, pct ?? 0));
  return (
    <div className={`progress-card water ${fresh ? "spring-in" : ""}`}>
      <div className="progress-head">
        <span className="progress-title">
          <span className="water-icon"><WaterDrop /></span>
          {d.is_today === false && d.date ? `Water · ${dayLabel(d.date)}` : "Water today"}
        </span>
        {pct != null && <span className="progress-pct">{pct}% of goal</span>}
      </div>
      <div className="progress-kcal">
        <b>{litres(had)}</b>
        {target != null && <span className="muted"> / {litres(target)}</span>}
        {target != null && (
          <span className="muted small">{had >= target ? " · goal met ✓" : ` · ${litres(target - had)} to go`}</span>
        )}
      </div>
      <div className="bar water-bar" ref={barRef}>
        <div className={`bar-fill ${target != null && had >= target ? "reached" : ""}`} style={{ width: `${shownPct}%` }} />
      </div>
      <p className="progress-headline">{d.headline}</p>
    </div>
  );
}

/** One macro on the "Day so far" card. It fills from empty when the card appears (just after
 *  "Looks good"), and turns into the moving gradient once the target is reached. */
function ProgressMacro({ x }: { x: MacroProgressData["macros"][number] }) {
  const tone = x.key.replace("_g", "");
  const [ref, shownPct] = useRevealFill<HTMLDivElement>(Math.min(100, x.pct ?? 0));
  const left = x.target != null ? Math.max(0, Math.round(x.target - x.consumed)) : null;
  const state = x.target != null ? macroState(tone, x.consumed, x.target) : "under";
  return (
    <div className={`bar-row ${tone} progress-macro`}>
      <div className="bar-label">
        <span className="bar-name"><i className="swatch" aria-hidden="true" />{x.label}</span>
        <span className="num">{x.pct != null ? `${x.pct}%` : `${x.consumed} g`}</span>
      </div>
      <div className="bar" ref={ref}><div className={`bar-fill ${state === "under" ? "" : state}`} style={{ width: `${shownPct}%` }} /></div>
      {left != null && <div className="muted tiny">{left > 0 ? `${left} g to go` : state === "over" ? "over target" : "done ✓"}</div>}
    </div>
  );
}

const THINKING_LINES = [
  "Doing the maths…",
  "Weighing it up…",
  "Checking my food notes…",
  "Adding up the protein…",
];

/** While a reply is on its way: MacBro nodding along with maths symbols floating up, and a
 *  rotating line. Screen readers hear one steady "MacBro is thinking". */
function MacBroThinking({ onStop }: { onStop: () => void }) {
  const [line, setLine] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setLine((n) => (n + 1) % THINKING_LINES.length), 2400);
    return () => clearInterval(t);
  }, []);
  return (
    <div className="msg-row assistant">
      <span className="thinking-avatar">
        <MacBroAvatar />
        <span className="math-glyphs" aria-hidden="true"><i>+</i><i>×</i><i>=</i><i>÷</i></span>
      </span>
      <div className="msg">
        <div className="bubble thinking" role="status">
          <span className="sr-only">MacBro is thinking</span>
          <span key={line} className="thinking-line" aria-hidden="true">{THINKING_LINES[line]}</span>
          <span className="typing" aria-hidden="true"><span /><span /><span /></span>
        </div>
        <button type="button" className="ghost stop-inline" onClick={onStop}>■ Stop</button>
      </div>
    </div>
  );
}

function ProgressCard({ m, fresh }: { m: ChatMessage; fresh?: boolean }) {
  const data = m.data as ProgressData;
  if (data.focus === "water") return <WaterProgressCard d={data} fresh={fresh} />;
  const d = data;
  const kcalPct = d.calories.pct ?? 0;
  return (
    <div className={`progress-card ${fresh ? "spring-in" : ""}`}>
      <div className="progress-head">
        <span className="progress-title">{d.is_today === false && d.date ? `${dayLabel(d.date)} total` : "Day so far"}</span>
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
        {d.macros.map((x) => <ProgressMacro key={x.key} x={x} />)}
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

export default function Chat({ user, onDataChanged, draft, active, onMinimize, onClose }: Props) {
  // Today's chat (a fresh one each day); earlier days load on request, oldest first.
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [earlier, setEarlier] = useState<DayBlock[]>([]);
  const [prevDay, setPrevDay] = useState<string | null>(null);
  const [loadingEarlier, setLoadingEarlier] = useState(false);
  // Day new messages are about (null = today). Set with the date picker or from the dashboard.
  const [logDate, setLogDate] = useState<string | null>(null);
  const messagesRef = useRef<HTMLDivElement>(null);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ai, setAi] = useState<AiAllowance | null>(null);   // today's AI allowance
  const [feedbackFor, setFeedbackFor] = useState<Action | null>(null);
  const [busyAction, setBusyAction] = useState<number | null>(null);
  // Messages that arrived in this session (not loaded from history): only these spring in.
  const [freshIds, setFreshIds] = useState<Set<number>>(() => new Set());
  const markFresh = (ids: number[]) => setFreshIds((f) => new Set([...f, ...ids]));
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const speechBaseRef = useRef("");
  // The in-flight request, so Stop can abort it (browser) and cancel it (server).
  const inflightRef = useRef<{ id: string; controller: AbortController; text: string; optimisticId: number } | null>(null);

  useEffect(() => {
    if (draft) {
      setInput(draft.text);
      setLogDate(draft.date && draft.date !== localTodayIso() ? draft.date : null);
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [draft]);

  const speech = useSpeechToText((spoken) => {
    const base = speechBaseRef.current;
    setInput(base ? `${base} ${spoken}` : spoken);
  });

  function refreshAllowance() {
    api.aiAllowance().then(setAi).catch(() => setAi(null));
  }

  async function loadToday() {
    refreshAllowance();
    const d = await api.chatDay();
    setMessages(d.messages);
    // Earlier days already on screen stay; otherwise offer the most recent one.
    setPrevDay((p) => (earlierRef.current.length ? p : d.prev_day));
  }
  const earlierRef = useRef<DayBlock[]>([]);
  earlierRef.current = earlier;

  useEffect(() => {
    loadToday().catch((e) => setError(e.message));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  function scrollToLatest(smooth: boolean) {
    bottomRef.current?.scrollIntoView({ behavior: smooth ? "smooth" : "auto", block: "end" });
  }

  // New messages scroll smoothly; opening the tab (or first load) jumps straight to the latest.
  const firstScroll = useRef(true);
  useEffect(() => {
    if (!active) return;
    scrollToLatest(!firstScroll.current);
    if (messages.length) firstScroll.current = false;
  }, [messages, sending]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (active) requestAnimationFrame(() => { scrollToLatest(false); inputRef.current?.focus(); });
  }, [active, draft]);

  async function showEarlier() {
    if (!prevDay) return;
    const box = messagesRef.current;
    const fromBottom = box ? box.scrollHeight - box.scrollTop : 0;
    setLoadingEarlier(true);
    try {
      const d = await api.chatDay(prevDay);
      setEarlier((e) => [{ day: d.day, messages: d.messages }, ...e]);
      setPrevDay(d.prev_day);
      // Keep the reader where they were instead of jumping.
      requestAnimationFrame(() => { if (box) box.scrollTop = box.scrollHeight - fromBottom; });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoadingEarlier(false);
    }
  }

  function toggleMic() {
    if (speech.listening) {
      speech.stop();
    } else {
      speechBaseRef.current = input.trim();
      speech.start();
    }
  }

  function updateAction(updated: Action) {
    const patch = (ms: ChatMessage[]) =>
      ms.map((m) => ({ ...m, actions: m.actions.map((a) => (a.id === updated.id ? updated : a)) }));
    setMessages(patch);
    setEarlier((blocks) => blocks.map((b) => ({ ...b, messages: patch(b.messages) })));
  }

  /** `preset`: a quick-reply button's text (e.g. "cooked"), sent without touching the draft. */
  async function send(e?: FormEvent, preset?: string) {
    e?.preventDefault();
    if (speech.listening) speech.stop();
    const text = (preset ?? input).trim();
    if (!text || sending) return;
    setError(null);
    speech.clearError();
    setSending(true);
    const optimistic: ChatMessage = {
      id: -Date.now(), role: "user", content: text, created_at: new Date().toISOString(), actions: [],
      data: logDate ? { log_date: logDate } : null,
    };
    setMessages((ms) => [...ms, optimistic]);
    if (preset === undefined) setInput("");
    const feedbackId = feedbackFor?.id ?? null;
    const requestId = `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
    const controller = new AbortController();
    inflightRef.current = { id: requestId, controller, text, optimisticId: optimistic.id };
    try {
      const newMsgs = await api.send(text, feedbackId, requestId, controller.signal, logDate);
      const newActionIds = new Set(newMsgs.flatMap((m) => m.actions.map((a) => a.id)));
      markFresh(newMsgs.filter((m) => m.role === "assistant").map((m) => m.id));
      // The reply includes the saved copy of the user's message, which replaces the optimistic one.
      setMessages((ms) => [
        // The server supersedes older open proposals when a new one is made; mirror that.
        ...ms.filter((m) => m.id !== optimistic.id).map((m) => ({
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
        refreshAllowance();
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
        await loadToday();
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
      if (res.progress) {
        markFresh([res.progress.id]);
        setMessages((ms) => [...ms, res.progress!]);
      }
      if (kind === "confirm") haptic("success");
      if (feedbackFor?.id === action.id) setFeedbackFor(null);
      if (kind === "confirm") onDataChanged();
    } catch (err) {
      setError((err as Error).message);
      loadToday().catch(() => {});
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
  const shown = (ms: ChatMessage[]) => ms.filter((m) => m.role !== "event");
  const visible = shown(messages);
  const shownError = error ?? speech.error;
  const today = localTodayIso();

  function renderMessage(m: ChatMessage) {
    const picked = m.role === "user" && m.data && "log_date" in m.data ? m.data.log_date : undefined;
    const fresh = freshIds.has(m.id);
    return (
      <div key={m.id} className={`msg-row ${m.role}`}>
        {m.role === "assistant"
          ? <MacBroAvatar />
          : <UserAvatar name={user.preferred_name} email={user.email} />}
        <div className="msg">
          {picked && <span className="msg-date-tag">📅 for {dayLabel(picked, today)}</span>}
          {m.kind === "progress" && m.data
            ? <ProgressCard m={m} fresh={fresh} />
            : <div className={`bubble ${fresh ? "fade-in" : ""}`}>{renderText(m.content)}</div>}
          {m.data && "ask_state" in m.data && m.id === visible[visible.length - 1]?.id && (
            <div className="quick-replies" role="group" aria-label="Raw or cooked">
              {["raw", "cooked"].map((s) => (
                <button key={s} type="button" className="chip" disabled={sending} onClick={() => void send(undefined, s)}>
                  {s === "raw" ? "Raw" : "Cooked"}{m.data && "ask_state" in m.data && m.data.ask_state.items.length > 1 ? " (all)" : ""}
                </button>
              ))}
            </div>
          )}
          {m.actions.map((a) => (
            <ProposalCard
              key={a.id}
              action={a}
              fresh={fresh}
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
    );
  }

  return (
    <section className="chat card">
      <div className="chat-head">
        <MacBroAvatar size={36} />
        <div className="chat-head-text">
          <div className="chat-title" id="chat-title">MacBro</div>
          <div className="muted small">Your macro bro. Tell me what you ate; I'll do the maths.</div>
        </div>
        {(onMinimize || onClose) && (
          <div className="chat-window-actions">
            {onMinimize && (
              <button type="button" className="ghost icon-btn" onClick={onMinimize} aria-label="Minimize chat" title="Minimize">
                <span aria-hidden="true" className="minimize-glyph" />
              </button>
            )}
            {onClose && (
              <button type="button" className="ghost icon-btn" onClick={onClose} aria-label="Close chat" title="Close">
                <span aria-hidden="true">✕</span>
              </button>
            )}
          </div>
        )}
      </div>

      <div className="messages" ref={messagesRef}>
        {prevDay && (
          <button type="button" className="ghost show-earlier" onClick={showEarlier} disabled={loadingEarlier}>
            {loadingEarlier ? "Loading…" : `Show earlier chat (${dayLabel(prevDay, today)})`}
          </button>
        )}
        {earlier.map((b) => (
          <section key={b.day} className="chat-day" aria-label={`Chat on ${dayLabel(b.day, today)}`}>
            <div className="day-divider"><span>{dayLabel(b.day, today)}</span></div>
            {shown(b.messages).map(renderMessage)}
          </section>
        ))}
        {earlier.length > 0 && <div className="day-divider"><span>Today</span></div>}
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
        {visible.map(renderMessage)}
        {sending && <MacBroThinking onStop={stop} />}
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
        <div className={`log-date ${logDate ? "past" : ""}`}>
          <label htmlFor="log-date-input">
            <span aria-hidden="true">📅</span> Logging for{" "}
            <b>{logDate ? dayLabel(logDate, today) : "Today"}</b>
          </label>
          <input id="log-date-input" type="date" max={today} value={logDate ?? today}
                 onChange={(e) => setLogDate(e.target.value && e.target.value < today ? e.target.value : null)}
                 title="Pick a day to add or change food for" />
          {logDate && (
            <button type="button" className="link" onClick={() => setLogDate(null)}>Back to today</button>
          )}
          {ai?.limit != null && ai.remaining != null && (
            <span className={`ai-left ${ai.remaining === 0 ? "out" : ai.remaining <= 3 ? "low" : ""}`}
                  title="AI messages reset at midnight. Instant replies (water, today's summary, saved foods) and buttons don't count.">
              {ai.remaining === 0 ? "No AI messages left today · resets at midnight"
                : `${ai.remaining} of ${ai.limit} AI messages left today`}
            </span>
          )}
        </div>
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
                : logDate ? `What did you eat ${dayLabel(logDate, today) === "Yesterday" ? "yesterday" : `on ${dayLabel(logDate, today)}`}? Or what should change?`
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
