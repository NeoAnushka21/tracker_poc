/**
 * Small vibrations for key moments. Only phones whose browser supports the Vibration API
 * (Android Chrome and friends; not iOS Safari) feel anything; elsewhere these do nothing.
 * Skipped when the user asks for reduced motion.
 */
const PATTERNS: Record<"tap" | "success" | "celebrate", number | number[]> = {
  tap: 10,                        // a light tick: quick-add buttons
  success: [14, 70, 14],          // double pulse: "Looks good" saved
  celebrate: [18, 60, 18, 60, 40], // streak completed today
};

export function haptic(kind: keyof typeof PATTERNS): void {
  try {
    if (typeof navigator === "undefined" || typeof navigator.vibrate !== "function") return;
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;
    navigator.vibrate(PATTERNS[kind]);
  } catch {
    /* some browsers throw when vibration is blocked; it's only a nicety */
  }
}
