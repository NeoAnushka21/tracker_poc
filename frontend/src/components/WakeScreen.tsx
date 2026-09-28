import { useEffect, useState } from "react";
import { APP_NAME, BOT_NAME } from "../brand";
import { MacBroAvatar } from "./Avatar";

/** Rotating lines while the free server wakes (~30–60 s). The last one stays. */
const LINES = [
  `${BOT_NAME} is warming up the kitchen…`,
  "Stretching before the macro maths…",
  "Sharpening the calorie pencils…",
  `${APP_NAME} will be ready in about a minute…`,
];
const LINE_EVERY_S = 5;
const SLOW_AFTER_S = 90;

/**
 * Full-screen loader with a dancing MacBro: shown while the app starts, when the sleeping free
 * server wakes up (wake.ts), and on the always-on launcher page (launcher.tsx).
 * The dance respects "reduce motion" (styles.css, "wake screen").
 */
export function WakeScreen({ overlay = false, stalled = false, onRetry }: {
  overlay?: boolean; stalled?: boolean; onRetry?: () => void;
}) {
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, []);

  const line = LINES[Math.min(Math.floor(seconds / LINE_EVERY_S), LINES.length - 1)];
  return (
    <div className={`wake-screen${overlay ? " overlay" : ""}`} role="status" aria-live="polite">
      <div className="wake-dancer" aria-hidden="true">
        <span className="wake-note n1">♪</span>
        <span className="wake-note n2">♫</span>
        <div className="wake-bounce"><MacBroAvatar size={120} /></div>
        <span className="wake-floor" />
      </div>
      {stalled ? (
        <>
          <p className="wake-line">This is taking longer than usual.</p>
          {onRetry && <button className="primary" onClick={onRetry}>Try again</button>}
        </>
      ) : (
        <>
          <p className="wake-line" key={line}>{line}</p>
          <p className="muted small wake-sub">
            {seconds >= SLOW_AFTER_S
              ? "Still waking up. Almost there."
              : `The free server naps when nobody's around. It's waking up now.`}
          </p>
          <span className="wake-dots" aria-hidden="true"><i /><i /><i /></span>
        </>
      )}
    </div>
  );
}

/** Shows the WakeScreen only if loading lasts longer than a blink, so fast loads don't flash it. */
export function DelayedWakeScreen({ delayMs = 600 }: { delayMs?: number }) {
  const [show, setShow] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setShow(true), delayMs);
    return () => clearTimeout(t);
  }, [delayMs]);
  return show ? <WakeScreen /> : null;
}
