import { useEffect, useState, type ComponentProps } from "react";
import { BOT_NAME } from "../brand";
import { MacBroAvatar } from "./Avatar";
import Chat from "./Chat";

export type ChatWindow = "closed" | "open" | "minimized";

type Props = Omit<ComponentProps<typeof Chat>, "active" | "onMinimize" | "onClose"> & {
  state: ChatWindow;
  onState: (s: ChatWindow) => void;
};

/** MacBro's chat as a floating window, the way websites show a chat assistant: opened from
 *  Home ("Want to log something?") or the Dashboard, minimized to a bubble, or closed.
 *  It stays mounted once opened, so the draft, scroll position and a reply on its way survive
 *  minimizing and switching tabs. On a phone it fills the screen. */
export default function ChatWidget({ state, onState, ...chat }: Props) {
  const [opened, setOpened] = useState(state === "open");   // mount the chat on first open only
  if (state === "open" && !opened) setOpened(true);

  useEffect(() => {
    if (state !== "open") return;
    const onKey = (e: globalThis.KeyboardEvent) => { if (e.key === "Escape") onState("minimized"); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [state, onState]);

  return (
    <>
      {opened && (
        <div className="chat-widget" role="dialog" aria-modal="false" aria-labelledby="chat-title" hidden={state !== "open"}>
          <Chat {...chat} active={state === "open"}
                onMinimize={() => onState("minimized")} onClose={() => onState("closed")} />
        </div>
      )}
      {state === "minimized" && (
        <button type="button" className="chat-launcher" onClick={() => onState("open")} aria-label={`Open chat with ${BOT_NAME}`}>
          <MacBroAvatar size={40} />
          <span>{BOT_NAME}</span>
        </button>
      )}
    </>
  );
}
