import { useEffect, useState } from "react";
import { api } from "../api";
import type { User } from "../types";
import { MacBroAvatar } from "./Avatar";

/** Shown once to accounts created before the consent notice (or after its wording changes). */
export default function ConsentGate({ onAccepted, onLogout }: { onAccepted: (u: User) => void; onLogout: () => void }) {
  const [text, setText] = useState<string | null>(null);
  const [checked, setChecked] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.consentText().then((c) => setText(c.text)).catch((e) => setError(e.message));
  }, []);

  async function accept() {
    setBusy(true);
    setError(null);
    try {
      onAccepted(await api.giveConsent());
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="center">
      <div className="card auth-card">
        <div className="auth-brand">
          <MacBroAvatar size={56} />
          <div>
            <h1>Before we continue</h1>
            <p className="muted">We've added a data consent notice.</p>
          </div>
        </div>
        <label className="consent-box">
          <input type="checkbox" checked={checked} onChange={(e) => setChecked(e.target.checked)} />
          <span>{text ?? "Loading…"}</span>
        </label>
        {error && <p className="error">{error}</p>}
        <button className="primary" onClick={accept} disabled={!checked || busy}>{busy ? "…" : "Agree and continue"}</button>
        <button type="button" className="link" onClick={onLogout}>Log out instead</button>
      </div>
    </div>
  );
}
