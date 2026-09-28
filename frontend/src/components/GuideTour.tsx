import { useEffect, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { AppLogo } from "./Avatar";
import { APP_NAME, BOT_NAME } from "../brand";

// Keep these steps in sync with docs/user-guide.md whenever the UI changes.
export type GuideTab = "home" | "chat" | "dashboard" | "analysis" | "foods";

type Step = { tab: GuideTab; title: string; body: ReactNode };

function steps(name: string | null): Step[] {
  return [
    {
      tab: "home",
      title: `Welcome to ${APP_NAME}${name ? `, ${name}` : ""}!`,
      body: <p>This quick tour shows you around in about a minute. You can reopen it any time from the <b>Guide</b> button at the top.</p>,
    },
    {
      tab: "home",
      title: "Your Home page",
      body: (
        <ul>
          <li>A greeting and <b>today's summary</b>: calories eaten / target, your balance, and protein, fiber, carbs and fat.</li>
          <li>A separate <b>Water</b> tile with quick +250 ml / +500 ml buttons.</li>
          <li>Two <b>streaks</b>: days in a row you logged a meal, and days in a row you hit your target.</li>
        </ul>
      ),
    },
    {
      tab: "chat",
      title: `1. Tell ${BOT_NAME} what you ate`,
      body: (
        <>
          <p><b>{BOT_NAME}</b> is your nutrition assistant in the <b>Chat</b> tab. Type, or tap the <b>mic</b> and speak. Plain language is fine:</p>
          <ul>
            <li>"2 eggs and a slice of toast for breakfast"</li>
            <li>"150g grilled chicken with a cup of rice"</li>
            <li>"two glasses of water"</li>
          </ul>
          <p className="muted small">Quantities help. If something is unclear, {BOT_NAME} asks before guessing.</p>
        </>
      ),
    },
    {
      tab: "chat",
      title: "2. Nothing is saved until you confirm",
      body: (
        <>
          <p>{BOT_NAME} replies with a card showing each item and its calories, protein, carbs and fat. It says <b>Not saved yet</b> until you choose:</p>
          <ul>
            <li><b>Looks good</b> saves it.</li>
            <li><b>Needs changes</b> lets you type a correction, e.g. "the rice was 200g".</li>
            <li><b>Cancel</b> throws it away.</li>
          </ul>
          <p>After you confirm, a summary card shows your day so far: calories and macros after food, or water against your goal after water.</p>
          <p className="muted small">Changed your mind while I'm thinking? Press <b>■ Stop</b> to get your message back and edit it.</p>
        </>
      ),
    },
    {
      tab: "chat",
      title: "3. Ask, edit, move or delete",
      body: (
        <ul>
          <li>"What did I eat yesterday?" or "How much protein this week?"</li>
          <li>"Move the banana to morning snack" or "Copy yesterday's lunch to today"</li>
          <li>"Delete the cookie" or "Make the rice 150g"</li>
          <li>"Save my chapati as a recipe" to reuse a home-made dish</li>
          <li>Use <b>📅 Logging for</b> above the message box to add or fix food on any past day. Each day starts a fresh chat, and <b>Show earlier chat</b> brings back older ones.</li>
        </ul>
      ),
    },
    {
      tab: "dashboard",
      title: "4. Your day on the Dashboard",
      body: (
        <ul>
          <li>Tiles in order: <b>macros</b> (the ring shows <b>eaten / target</b> calories and your <b>balance</b>, with bars for protein, fiber, carbs and fat), then <b>micronutrients</b>, then <b>water</b> (tap +250 ml or +500 ml).</li>
          <li>Meals are split into breakfast, snacks, lunch and dinner. Tap the <b>pencil</b> on an item to move, copy, change the amount or delete it.</li>
          <li>Use <b>‹ ›</b> to look at earlier days.</li>
        </ul>
      ),
    },
    {
      tab: "analysis",
      title: "5. Trends in Analysis",
      body: <p>Switch between <b>7, 14 or 30 days</b> to see calories and protein against target, macro trends, calories by meal, and water. Your target streak is on <b>Home</b>. Hover or tab onto any chart for exact numbers.</p>,
    },
    {
      tab: "foods",
      title: "6. My foods remembers for you",
      body: <p>Every food you confirm is saved here, so the next time you log it the numbers are exactly the same. Recipes you save show up here too. You can search, correct or delete any of them.</p>,
    },
    {
      tab: "chat",
      title: "7. Settings",
      body: (
        <>
          <p>Open <b>⚙ Settings</b> to change your calorie and macro <b>targets</b>, update weight and height or add body measurements under <b>Body profile</b>, switch <b>light or dark</b> theme, change your password, or delete your account.</p>
          <p>That's it. Head to <b>Chat</b> and tell {BOT_NAME} what you had today!</p>
        </>
      ),
    },
  ];
}

type Props = { name: string | null; onTab: (tab: GuideTab) => void; onClose: () => void };

/** First-run walkthrough: a panel docked at the bottom that switches tabs as it goes. */
export default function GuideTour({ name, onTab, onClose }: Props) {
  const all = steps(name);
  const [i, setI] = useState(0);
  const panel = useRef<HTMLDivElement>(null);
  const step = all[i];
  const last = i === all.length - 1;

  useEffect(() => { onTab(step.tab); }, [i]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { panel.current?.focus(); }, [i]);

  function onKey(e: KeyboardEvent) {
    if (e.key === "Escape") onClose();
    else if (e.key === "ArrowRight" && !last) setI(i + 1);
    else if (e.key === "ArrowLeft" && i > 0) setI(i - 1);
  }

  return (
    <div className="guide card" role="dialog" aria-modal="false" aria-labelledby="guide-title"
         ref={panel} tabIndex={-1} onKeyDown={onKey}>
      <div className="guide-head">
        <AppLogo size={40} />
        <h2 id="guide-title">{step.title}</h2>
        <button className="ghost" onClick={onClose} aria-label="Close the guide">✕</button>
      </div>
      <div className="guide-body">{step.body}</div>
      <div className="guide-foot">
        <span className="guide-dots" aria-label={`Step ${i + 1} of ${all.length}`}>
          {all.map((_, k) => <span key={k} className={k === i ? "on" : ""} />)}
        </span>
        {!last && <button className="link" onClick={onClose}>Skip</button>}
        {i > 0 && <button onClick={() => setI(i - 1)}>Back</button>}
        {last
          ? <button className="primary" onClick={onClose}>Start logging</button>
          : <button className="primary" onClick={() => setI(i + 1)}>Next</button>}
      </div>
    </div>
  );
}
