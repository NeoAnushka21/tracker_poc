import { useEffect, useLayoutEffect, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { AppLogo } from "./Avatar";
import { APP_NAME, BOT_NAME } from "../brand";

// Keep these steps in sync with docs/user-guide.md whenever the UI changes.
export type GuideTab = "home" | "dashboard" | "foods" | "explore" | "body";

/** `targets`: CSS selectors of what the step talks about. Everything else is blurred; each visible
 *  match is cut out of the blur and outlined (the first one is scrolled into view). */
type Step = { tab: GuideTab; targets: string[]; title: string; body: ReactNode };

function steps(name: string | null): Step[] {
  return [
    {
      tab: "home",
      targets: [".guide-btn"],
      title: `Welcome to ${APP_NAME}${name ? `, ${name}` : ""}!`,
      body: <p>This quick tour shows you around in about a minute. You can reopen it any time from the <b>Guide</b> button at the top.</p>,
    },
    {
      tab: "home",
      targets: ["#tab-home", "#panel-home .home"],
      title: "Your Home page",
      body: (
        <ul>
          <li>A greeting and <b>today's summary</b>: calories eaten / target, your balance, and protein, fiber, carbs and fat.</li>
          <li>A separate <b>Water</b> tile with quick +250 ml / +500 ml buttons.</li>
          <li>Two <b>streaks</b>: days in a row you logged a meal, and days in a row you reached at least 85% of your protein target.</li>
        </ul>
      ),
    },
    {
      tab: "home",
      targets: ["#panel-home .macbro-invite"],
      title: `1. Tell ${BOT_NAME} what you ate`,
      body: (
        <>
          <p><b>{BOT_NAME}</b> is your nutrition assistant. On <b>Home</b>, tap {BOT_NAME} ("Want to log something? Talk to me") to open the chat window. Type, or tap the <b>mic</b> and speak. Plain language is fine:</p>
          <ul>
            <li>"2 eggs and a slice of toast for breakfast"</li>
            <li>"150g grilled chicken with a cup of rice"</li>
            <li>"two glasses of water"</li>
          </ul>
          <p className="muted small">The chat opens over the page: <b>–</b> minimizes it to a small {BOT_NAME} bubble (tap it to come back, even from another tab), <b>✕</b> closes it. Quantities help. If something is unclear, {BOT_NAME} asks before guessing. You get a daily number of AI messages (shown above the message box); quick replies like water and foods you've saved don't use them.</p>
        </>
      ),
    },
    {
      tab: "home",
      targets: ["#panel-home .macbro-invite"],
      title: "2. Nothing is saved until you confirm",
      body: (
        <>
          <p>{BOT_NAME} replies with a card that leads with the bottom line, <b>calories</b> and <b>protein</b>, and lists each item and amount so you can check it. <b>View details</b> shows the full carbs, fat and fiber breakdown. It says <b>Not saved yet</b> until you choose:</p>
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
      tab: "home",
      targets: ["#panel-home .macbro-invite"],
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
      targets: ["#tab-dashboard", ".day-summary", ".meals-head"],
      title: "4. Your day on Meals",
      body: (
        <ul>
          <li>A compact <b>summary tile</b>: small meters for calories, protein, fiber, carbs and fat (a bar glows once you hit its target), your <b>water</b> (tap +250 ml or +500 ml) and <b>micronutrients</b> (folded; tap to open).</li>
          <li>Below it, a colourful card per <b>meal</b> with its calories and share of your day. Tap the <b>pencil</b> on an item to move, copy, change the amount or delete it, or <b>+ Add food</b> to add one without the chat.</li>
          <li>Use <b>‹ ›</b> to look at earlier days.</li>
        </ul>
      ),
    },
    {
      tab: "dashboard",
      targets: ["#tab-dashboard", ".progress-toggle"],
      title: "5. Check your progress",
      body: <p>At the bottom of <b>Meals</b>, <b>Check your progress</b> opens your trends: switch between <b>7, 14 or 30 days</b> to see calories and protein against target, macro trends, calories by meal, and water. Your streaks are on <b>Home</b>. Hover or tab onto any chart for exact numbers.</p>,
    },
    {
      tab: "foods",
      targets: ["#tab-foods", "#panel-foods .foods-head", "#panel-foods .foods-tools"],
      title: "6. My Foods remembers for you",
      body: <p>Every food you confirm is saved here with its macros and micronutrients, so the next time you log it (e.g. "40g pineapple") the numbers are exactly the same, straight from your library, without using an AI message (small typos like "panner" are fine). About 300 common foods (fruit, dals, rice, milk, chicken…) are built in too, and for foods like rice or chicken MacBro asks whether the weight was raw or cooked instead of guessing. The list has three tabs: <b>Generic</b> foods, <b>Branded</b> products and <b>My Recipes</b>. It shows each name with its calories; tap <b>Additional info</b> for the other macros and micronutrients. You can search, correct or delete any of them. Packaged foods you log with their brand ("10 g Amul butter") are grouped by brand under <b>Branded</b>: press <b>Check label</b> to pick the real pack label from Open Food Facts, or type it in with the pencil. <b>+ Add</b> lets you add a branded product, a generic food or a recipe yourself.</p>,
    },
    {
      tab: "body",
      targets: ["#tab-body", "#panel-body .body-page > .card:first-child"],
      title: "7. Your Body Stats",
      body: (
        <ul>
          <li>Your <b>weight</b>, <b>height</b> and <b>BMI</b>, and an estimated <b>body fat</b> once you add your neck and waist (and hips for women).</li>
          <li>Tap a body part on the figure to see how to measure it and add a value. All measurements are optional and dated, so you can see them change.</li>
          <li>Update your weight or height here too.</li>
        </ul>
      ),
    },
    {
      tab: "explore",
      targets: ["#tab-explore", "#panel-explore .explore"],
      title: "8. Explore (coming soon)",
      body: <p>Two sections: <b>Recipes</b>, ready-made collections such as <b>high protein</b>, <b>non-veg quick &amp; easy</b> and <b>healthy desserts</b> with the macros already worked out, and <b>Workouts</b>, with strength basics, simple routines and tips. Tap a section to see what's planned.</p>,
    },
    {
      tab: "home",
      targets: [".settings-btn"],
      title: "9. Settings",
      body: (
        <>
          <p>Open <b>⚙ Settings</b> for <b>About you</b> (your details, and optional answers such as diet, allergies, pace, meal times and training), your calorie and macro <b>targets</b>, <b>light or dark</b> theme, your account and data, password, or deleting your account.</p>
          <p>That's it. Tap {BOT_NAME} on <b>Home</b> and tell {BOT_NAME} what you had today!</p>
        </>
      ),
    },
  ];
}

type Props = { name: string | null; onTab: (tab: GuideTab) => void; onClose: () => void };

type Hole = { x: number; y: number; w: number; h: number };
const PAD = 6;       // space between a highlighted element and its outline
const RADIUS = 14;

/** Rounded rectangle as an SVG path, for the evenodd clip-path that cuts holes in the blur. */
function roundedRect({ x, y, w, h }: Hole): string {
  const r = Math.min(RADIUS, w / 2, h / 2);
  return `M${x + r} ${y}H${x + w - r}A${r} ${r} 0 0 1 ${x + w} ${y + r}V${y + h - r}A${r} ${r} 0 0 1 ${x + w - r} ${y + h}` +
    `H${x + r}A${r} ${r} 0 0 1 ${x} ${y + h - r}V${y + r}A${r} ${r} 0 0 1 ${x + r} ${y}Z`;
}

/** The visible elements a step points at (hidden tab panels don't count). */
function findTargets(selectors: string[]): HTMLElement[] {
  return selectors.flatMap((sel) =>
    [...document.querySelectorAll<HTMLElement>(sel)].filter((el) => el.getClientRects().length > 0).slice(0, 1));
}

const overlaps = (a: Hole, b: Hole) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;

/** Holes for the targets as they show on screen. With evenodd, two overlapping holes cancel out
 *  (the overlap is blurred again), so: a target in the page is cut off at the sticky header's
 *  bottom edge (it's hidden behind it anyway, and the tab it belongs to has its own hole), and
 *  any holes that still overlap are merged into one. */
function visibleHoles(els: HTMLElement[]): Hole[] {
  const headerBottom = document.querySelector(".app-header")?.getBoundingClientRect().bottom ?? 0;
  const holes: Hole[] = [];
  for (const el of els) {
    const r = el.getBoundingClientRect();
    const top = el.closest(".app-header") ? r.top - PAD : Math.max(r.top - PAD, headerBottom + 2);
    const bottom = Math.min(r.bottom + PAD, window.innerHeight);
    if (bottom - top > 4) holes.push({ x: r.left - PAD, y: top, w: r.width + PAD * 2, h: bottom - top });
  }
  for (let merged = true; merged;) {
    merged = false;
    for (let a = 0; a < holes.length && !merged; a++) {
      for (let b = a + 1; b < holes.length && !merged; b++) {
        if (!overlaps(holes[a], holes[b])) continue;
        const [p, q] = [holes[a], holes[b]];
        const x = Math.min(p.x, q.x), y = Math.min(p.y, q.y);
        holes[a] = { x, y, w: Math.max(p.x + p.w, q.x + q.w) - x, h: Math.max(p.y + p.h, q.y + q.h) - y };
        holes.splice(b, 1);
        merged = true;
      }
    }
  }
  return holes;
}

/** Where the step's targets are on screen, kept up to date on scroll and resize. */
function useHoles(selectors: string[], stepKey: number): Hole[] {
  const [holes, setHoles] = useState<Hole[]>([]);
  useLayoutEffect(() => {
    let frame = 0;
    const measure = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => setHoles(visibleHoles(findTargets(selectors))));
    };
    // The step may have just switched tabs: give the panel a moment to lay out, then bring the
    // main target (the last one: a section rather than its tab) into view.
    const settle = window.setTimeout(() => {
      const els = findTargets(selectors);
      const main = els[els.length - 1];
      const calm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      main?.scrollIntoView({ block: "center", behavior: calm ? "auto" : "smooth" });
      measure();
    }, 60);
    const observer = new ResizeObserver(measure);
    observer.observe(document.body);
    window.addEventListener("scroll", measure, true);
    window.addEventListener("resize", measure);
    return () => {
      window.clearTimeout(settle);
      cancelAnimationFrame(frame);
      observer.disconnect();
      window.removeEventListener("scroll", measure, true);
      window.removeEventListener("resize", measure);
    };
  }, [stepKey]); // eslint-disable-line react-hooks/exhaustive-deps
  return holes;
}

/** First-run walkthrough: a panel docked at the bottom that switches tabs as it goes. The page
 *  behind is blurred, except the parts the step talks about (tabs, tiles, buttons), which stay
 *  sharp and outlined. */
export default function GuideTour({ name, onTab, onClose }: Props) {
  const all = steps(name);
  const [i, setI] = useState(0);
  const panel = useRef<HTMLDivElement>(null);
  const step = all[i];
  const last = i === all.length - 1;
  const holes = useHoles(step.targets, i);

  useEffect(() => { onTab(step.tab); }, [i]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { panel.current?.focus(); }, [i]);

  // Keep the panel off what it's pointing at: bottom centre by default, else the first of top
  // centre and the four corners that covers no highlight (or covers the least).
  const [pos, setPos] = useState<{ left: number; top: number } | null>(null);
  useLayoutEffect(() => {
    const el = panel.current;
    if (!el) return;
    const { width: w, height: h } = el.getBoundingClientRect();
    const M = 16;
    const vw2 = window.innerWidth, vh2 = window.innerHeight;
    const xs = { centre: (vw2 - w) / 2, left: M, right: vw2 - w - M };
    const ys = { bottom: vh2 - h - M, top: M };
    const spots = [[xs.centre, ys.bottom], [xs.centre, ys.top], [xs.left, ys.bottom], [xs.right, ys.bottom],
      [xs.left, ys.top], [xs.right, ys.top]];
    const covered = ([x, y]: number[]) => holes.reduce((sum, o) => {
      const dx = Math.min(x + w, o.x + o.w) - Math.max(x, o.x);
      const dy = Math.min(y + h, o.y + o.h) - Math.max(y, o.y);
      return sum + (dx > 0 && dy > 0 ? dx * dy : 0);
    }, 0);
    let best = spots[0], bestArea = covered(best);
    for (const s of spots.slice(1)) {
      if (bestArea === 0) break;
      const area = covered(s);
      if (area < bestArea) { best = s; bestArea = area; }
    }
    const next = { left: Math.round(Math.max(M, best[0])), top: Math.round(Math.max(M, best[1])) };
    setPos((p) => (p && p.left === next.left && p.top === next.top ? p : next));
  }, [holes, i]);

  // One path: the whole screen, minus a rounded hole per target (evenodd).
  const vw = typeof window === "undefined" ? 0 : window.innerWidth;
  const vh = typeof window === "undefined" ? 0 : window.innerHeight;
  const clip = `path(evenodd, "M0 0H${vw}V${vh}H0Z${holes.map(roundedRect).join("")}")`;

  function onKey(e: KeyboardEvent) {
    if (e.key === "Escape") onClose();
    else if (e.key === "ArrowRight" && !last) setI(i + 1);
    else if (e.key === "ArrowLeft" && i > 0) setI(i - 1);
  }

  return (
    <>
    <div className="guide-spotlight" aria-hidden="true" style={{ clipPath: clip }} />
    {holes.map((h, k) => (
      <div key={k} className="guide-ring" aria-hidden="true" style={{ left: h.x, top: h.y, width: h.w, height: h.h }} />
    ))}
    {/* The tour panel is a dialog that handles its own keys (← → to step, Escape to close). */}
    {/* oxlint-disable-next-line jsx-a11y/no-noninteractive-element-interactions */}
    <div className="guide card" role="dialog" aria-modal="false" aria-labelledby="guide-title"
         ref={panel} tabIndex={-1} onKeyDown={onKey}
         style={pos ? { left: pos.left, top: pos.top, bottom: "auto", transform: "none" } : undefined}>
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
    </>
  );
}
