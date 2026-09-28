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
