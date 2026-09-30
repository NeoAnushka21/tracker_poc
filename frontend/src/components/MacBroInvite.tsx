import type { ReactNode } from "react";
import { BOT_NAME } from "../brand";
import { MacBroAvatar } from "./Avatar";

/** MacBro with a speech bubble that opens the chat window (Home, Meals). */
export default function MacBroInvite({ children, label, onClick, size = 56 }: {
  children: ReactNode; label: string; onClick: () => void; size?: number;
}) {
  return (
    <button type="button" className="macbro-invite" onClick={onClick} aria-label={`${label}: chat with ${BOT_NAME}`}>
      <span className="macbro-invite-bubble">{children}</span>
      <MacBroAvatar size={size} />
    </button>
  );
}
