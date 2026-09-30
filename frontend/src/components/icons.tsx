/** Small line icons (decorative: the buttons that use them carry aria-label + title). */
import type { ReactNode } from "react";

function Icon({ children, size = 18 }: { children: ReactNode; size?: number }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} aria-hidden="true" fill="none" stroke="currentColor"
         strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      {children}
    </svg>
  );
}

export const PencilIcon = () => <Icon><path d="M4 20h4L19 9a2.8 2.8 0 0 0-4-4L4 16v4z" /><path d="M13.5 6.5l4 4" /></Icon>;
export const TrashIcon = () => <Icon><path d="M4 7h16M9 7V4.5h6V7M6.5 7l1 12.5h9l1-12.5M10 11v5M14 11v5" /></Icon>;
export const CloseIcon = () => <Icon><path d="M6 6l12 12M18 6L6 18" /></Icon>;
export const CheckIcon = () => <Icon><path d="M5 12.5l4.5 4.5L19 7.5" /></Icon>;
export const ArrowRightIcon = () => <Icon><path d="M5 12h14M13 6l6 6-6 6" /></Icon>;
/** Speech bubble: "edit this in the chat". */
export const ChatIcon = () => (
  <Icon><path d="M20 12a7.5 7.5 0 0 1-11 6.6L4 20l1.4-4.6A7.5 7.5 0 1 1 20 12z" /><path d="M9 11h6M9 14h4" /></Icon>
);

/** Filled water drop (water tracker, water chat card). */
export function WaterDrop() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path d="M12 3c3.5 4.4 6 7.9 6 11a6 6 0 0 1-12 0c0-3.1 2.5-6.6 6-11z" fill="currentColor" />
    </svg>
  );
}

/** Meal icons (Dashboard meal cards): sunrise, apple, bowl, cup, moon. */
export const SunriseIcon = () => (
  <Icon size={20}><path d="M3 18h18M6 18a6 6 0 0 1 12 0" /><path d="M12 5v3M4.9 9.9l2.1 2.1M19.1 9.9L17 12M3 14h1.5M19.5 14H21" /></Icon>
);
export const AppleIcon = () => (
  <Icon size={20}><path d="M12 7.5c-1.5-1.3-6-1.8-6.5 3.2-.4 4 2 8.8 4.5 8.8 1 0 1.3-.5 2-.5s1 .5 2 .5c2.5 0 4.9-4.8 4.5-8.8-.5-5-5-4.5-6.5-3.2z" /><path d="M12 7.5c0-2 1-3.5 3-4" /></Icon>
);
export const BowlIcon = () => (
  <Icon size={20}><path d="M3.5 11h17a8.5 8.5 0 0 1-17 0z" /><path d="M9 20h6M8 8c0-1.5 1-2 1-3.5M12 8c0-1.5 1-2 1-3.5M16 8c0-1.5 1-2 1-3.5" /></Icon>
);
export const CupIcon = () => (
  <Icon size={20}><path d="M5 9h11v5a5 5 0 0 1-5 5h-1a5 5 0 0 1-5-5V9z" /><path d="M16 10.5h1.5a2.5 2.5 0 0 1 0 5H16M8 3.5c0 1.5-1 1.5-1 3M11.5 3.5c0 1.5-1 1.5-1 3" /></Icon>
);
export const MoonIcon = () => (
  <Icon size={20}><path d="M19.5 14.5A7.5 7.5 0 0 1 9.5 4.5a7.5 7.5 0 1 0 10 10z" /><path d="M16 4.5v3M14.5 6h3" /></Icon>
);
/** Down chevron for fold/unfold toggles (rotates to point up when open, styles.css .chevron). */
export const ChevronDownIcon = () => <Icon size={18}><path d="M6 9l6 6 6-6" /></Icon>;
/** Rising line: "Check your progress" (Meals tab). */
export const TrendIcon = () => <Icon size={20}><path d="M4 18l5-6 4 3 7-9" /><path d="M15 6h5v5" /></Icon>;
