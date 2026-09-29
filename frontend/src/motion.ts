import { useEffect, useRef, useState, type RefObject } from "react";

/**
 * The value a meter should draw, held back until the meter is on screen. It starts at 0, so the
 * first view fills from empty; later changes animate from the old value. Tabs that are hidden
 * (e.g. the dashboard while you confirm a meal in chat) keep the old value until you open them,
 * so the fill plays where you can see it. The ease-out transition itself lives in styles.css.
 */
export function useRevealFill<T extends Element>(value: number): [RefObject<T | null>, number] {
  const ref = useRef<T>(null);
  const [shown, setShown] = useState(0);
  const latest = useRef(value);
  latest.current = value;
  const visible = useRef(false);

  useEffect(() => {
    const el = ref.current;
    if (!el || typeof IntersectionObserver === "undefined") {
      setShown(latest.current);
      return;
    }
    const io = new IntersectionObserver(([entry]) => {
      visible.current = entry.isIntersecting;
      // One frame later, so the browser has painted the old width and the transition runs.
      if (entry.isIntersecting) requestAnimationFrame(() => setShown(latest.current));
    });
    io.observe(el);
    return () => io.disconnect();
  }, []);

  useEffect(() => {
    if (visible.current) setShown(value);
  }, [value]);

  return [ref, shown];
}
