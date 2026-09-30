import { useEffect, useState, type FormEvent } from "react";
import { api } from "../api";
import type { User } from "../types";
import { GOALS } from "../format";
import TargetsEditor from "./TargetsEditor";
import ThemeToggle from "./ThemeToggle";
import { UserAvatar } from "./Avatar";
import { APP_NAME } from "../brand";
import { LocationFields } from "./LocationFields";
import { AboutYouForm, SuggestedTargets } from "./AboutYou";

/** Settings → About you: the optional answers, with the new-target offer when they change it. */
function AboutSection({ user, onSaved }: { user: User; onSaved: (u: User) => void }) {
  const [note, setNote] = useState<string | null>(null);
  const [suggested, setSuggested] = useState<{ daily_calorie_target: number } | null>(null);
  return (
    <div className="settings-form">
      <p className="muted small">All optional. Used for your targets (pace, pregnancy), meal times in the chat, and MacBro's suggestions.</p>
      {suggested && (
        <SuggestedTargets suggested={suggested} user={user}
                          onDone={(u) => { if (u) onSaved(u); setSuggested(null); setNote(u ? "Targets updated." : null); }} />
      )}
      <AboutYouForm user={user} saveLabel="Save"
                    onSaved={(u, s) => { onSaved(u); setSuggested(s); setNote(s ? null : "Saved."); }} />
      {note && <p className="muted small" role="status">{note}</p>}
    </div>
  );
}

type Section = "account" | "about" | "targets" | "security" | "delete";

type Props = {
  user: User;
  onClose: () => void;
  onSaved: (u: User) => void;
  /** Account deleted or logged out everywhere: back to the login screen. */
  onSignedOut: () => void;
};

function when(iso: string | null): string {
  if (!iso) return "–";
  return new Date(iso).toLocaleString(undefined, { day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

/** Country (required) and region (optional): shown as text, with Change opening the dropdowns. */
function WhereYouLive({ user, onSaved }: { user: User; onSaved: (u: User) => void }) {
  const [editing, setEditing] = useState(false);
  const [country, setCountry] = useState(user.country ?? "");
  const [region, setRegion] = useState(user.region ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      onSaved(await api.setLocation(country, region || null));
      setEditing(false);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (!editing) {
    return (
      <div>
        <dt>Country / region</dt>
        <dd>
          {[user.country_name, user.region].filter(Boolean).join(" · ") || "–"}{" "}
          <button type="button" className="link" onClick={() => setEditing(true)}>Change</button>
        </dd>
      </div>
    );
  }
  return (
    <div>
      <dt>Country / region</dt>
      <dd>
        <form className="settings-location" onSubmit={save}>
          <LocationFields country={country} region={region} onChange={(c, r) => { setCountry(c); setRegion(r); }} />
          {error && <p className="error small">{error}</p>}
          <div className="proposal-actions">
            <button className="primary" disabled={!country || busy}>{busy ? "Saving…" : "Save"}</button>
            <button type="button" onClick={() => { setEditing(false); setCountry(user.country ?? ""); setRegion(user.region ?? ""); }}>
              Cancel
            </button>
          </div>
        </form>
      </dd>
    </div>
  );
}

function AccountSection({ user, onSaved }: { user: User; onSaved: (u: User) => void }) {
  return (
    <>
      <div className="account-card">
        <UserAvatar name={user.preferred_name} email={user.email} size={48} />
        <div>
          <div className="account-name">{user.preferred_name ?? (user.is_admin ? "Administrator" : "No preferred name")}</div>
          <div className="muted">{user.email}</div>
        </div>
      </div>
      <dl className="settings-facts">
        <div><dt>Email</dt><dd>{user.email}</dd></div>
        {!user.is_admin && (
          <div><dt>Sign-in</dt><dd>{[user.has_password && "Email and password", user.google_linked && "Google"].filter(Boolean).join(" · ") || "–"}</dd></div>
        )}
        <div><dt>Registered</dt><dd>{when(user.created_at)}</dd></div>
        <div><dt>Last login</dt><dd>{when(user.last_login_at)}</dd></div>
        <div><dt>Data consent given</dt><dd>{when(user.consented_at)}</dd></div>
        {!user.is_admin && (
          <>
            <div><dt>Age</dt><dd>{user.age ?? "–"} <span className="muted small">(from your date of birth)</span></dd></div>
            <WhereYouLive user={user} onSaved={onSaved} />
            <div><dt>Goal</dt><dd>{user.goal_type ? GOALS[user.goal_type] ?? user.goal_type : "–"}</dd></div>
            <div><dt>Time zone</dt><dd>{user.timezone}</dd></div>
          </>
        )}
      </dl>
      <h3>Appearance</h3>
      <ThemeToggle />
      <YourData />
    </>
  );
}

/** Download my data (everything stored about the account) and the privacy notice. */
function YourData() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function download() {
    setBusy(true);
    setError(null);
    try {
      const data = await api.exportData();
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = `${APP_NAME.toLowerCase()}-my-data-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <h3>Your data</h3>
      <p className="muted small">
        A copy of everything {APP_NAME} stores about your account: profile, logs, foods, chat and more, as a file.{" "}
        <a href="/privacy" target="_blank" rel="noopener">How we use your data</a> · <a href="/terms" target="_blank" rel="noopener">Terms</a>
      </p>
      <button type="button" onClick={download} disabled={busy}>{busy ? "Preparing…" : "Download my data"}</button>
      {error && <p className="error small">{error}</p>}
    </>
  );
}

function TargetsSection({ user, onSaved }: { user: User; onSaved: (u: User) => void }) {
  const [msg, setMsg] = useState<string | null>(null);
  return (
    <>
      <h3 className="first">Daily calorie &amp; macro targets</h3>
      <p className="muted small">Calculated from your profile; adjust any number. Changing weight or height on the
        Body Profile tab can recalculate these.</p>
      <TargetsEditor
        key={`${user.targets?.effective_date}-${user.targets?.calories}-${user.targets?.protein_g}`}
        user={user}
        saveLabel="Save targets"
        onSaved={(u) => { onSaved(u); setMsg("Targets saved."); }}
      />
      {msg && <p className="ok small">{msg}</p>}
    </>
  );
}

function SecuritySection({ user, onSaved }: { user: User; onSaved: (u: User) => void }) {
  const setting = !user.has_password;   // Google-only account: this sets its first password
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMsg(null);
    if (next !== confirm) return setError("The new passwords don't match.");
    setBusy(true);
    try {
      await api.changePassword(setting ? "" : current, next);
      setMsg(setting ? "Password set. You can now also log in with your email and password. Any other devices were signed out."
        : "Password changed. Any other devices were signed out.");
      setCurrent(""); setNext(""); setConfirm("");
      if (setting) onSaved(await api.me());
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="settings-form">
      <h3 className="first">{setting ? "Set a password" : "Change password"}</h3>
      {setting ? (
        <p className="muted small">You sign in with Google. Set a password if you'd also like to log in with your email.</p>
      ) : (
        <label>Current password<input type="password" value={current} onChange={(e) => setCurrent(e.target.value)} required autoComplete="current-password" /></label>
      )}
      <label>New password <span className="muted">(at least 8 characters)</span>
        <input type="password" value={next} onChange={(e) => setNext(e.target.value)} minLength={8} required autoComplete="new-password" /></label>
      <label>Confirm new password<input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} minLength={8} required autoComplete="new-password" /></label>
      {error && <p className="error">{error}</p>}
      {msg && <p className="ok small">{msg}</p>}
      <button className="primary" disabled={busy}>{busy ? "Saving…" : setting ? "Set password" : "Change password"}</button>
    </form>
  );
}

/** Ends every session of the account, e.g. after using a shared computer or losing a phone. */
function SignOutEverywhere({ onSignedOut }: { onSignedOut: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    if (!window.confirm("Log out on every device, including this one?")) return;
    setBusy(true);
    setError(null);
    try {
      await api.logoutEverywhere();
      onSignedOut();
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <div className="settings-form">
      <h3>Signed-in devices</h3>
      <p className="muted small">Lost a phone or used a shared computer? This signs your account out everywhere.</p>
      <button type="button" onClick={run} disabled={busy}>{busy ? "Logging out…" : "Log out of all devices"}</button>
      {error && <p className="error small">{error}</p>}
    </div>
  );
}

function DeleteSection({ user, onDeleted }: { user: User; onDeleted: () => void }) {
  const [password, setPassword] = useState("");
  const [typed, setTyped] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await api.deleteAccount(password, user.has_password ? "" : password);
      onDeleted();
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="settings-form danger-zone">
      <h3 className="first">Delete account</h3>
      <p>
        This permanently deletes your account and everything in it: food logs, saved foods and recipes, water logs,
        weight history, targets and your chat history. <b>This can't be undone.</b>
      </p>
      <label>Type <b>DELETE</b> to confirm<input value={typed} onChange={(e) => setTyped(e.target.value)} autoComplete="off" /></label>
      {user.has_password ? (
        <label>Your password<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" /></label>
      ) : (
        <label>Type your email <b>{user.email}</b><input type="email" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="off" /></label>
      )}
      {error && <p className="error">{error}</p>}
      <button className="danger-button" disabled={busy || typed !== "DELETE" || !password}>
        {busy ? "Deleting…" : `Permanently delete ${user.email}`}
      </button>
    </form>
  );
}

export default function SettingsDialog({ user, onClose, onSaved, onSignedOut }: Props) {
  const sections: { id: Section; label: string }[] = [
    { id: "account", label: "Account" },
    ...(!user.is_admin ? [
      { id: "about" as const, label: "About you" },
      { id: "targets" as const, label: "Targets" },
    ] : []),
    { id: "security", label: user.has_password ? "Password" : "Set password" },
    ...(!user.is_admin ? [{ id: "delete" as const, label: "Delete account" }] : []),
  ];
  const [section, setSection] = useState<Section>("account");

  useEffect(() => {   // Escape closes the dialog (keyboard users)
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    // A click on the dimmed area outside closes it too; keyboards use Escape or the close button.
    <div className="backdrop" role="presentation" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="card dialog settings-dialog" role="dialog" aria-modal="true" aria-labelledby="settings-title">
        <div className="dialog-head">
          <h2 id="settings-title">Settings</h2>
          <button className="ghost" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <div className="settings-body">
          <div className="settings-nav" role="tablist" aria-label="Settings sections">
            {sections.map((s) => (
              <button key={s.id} role="tab" aria-selected={section === s.id}
                      className={`${section === s.id ? "on" : ""} ${s.id === "delete" ? "danger" : ""}`}
                      onClick={() => setSection(s.id)}>
                {s.label}
              </button>
            ))}
          </div>
          <div className="settings-panel" role="tabpanel">
            {section === "account" && <AccountSection user={user} onSaved={onSaved} />}
            {section === "about" && <AboutSection user={user} onSaved={onSaved} />}
            {section === "targets" && <TargetsSection user={user} onSaved={onSaved} />}
            {section === "security" && (
              <>
                <SecuritySection user={user} onSaved={onSaved} />
                <SignOutEverywhere onSignedOut={onSignedOut} />
              </>
            )}
            {section === "delete" && <DeleteSection user={user} onDeleted={onSignedOut} />}
          </div>
        </div>
      </div>
    </div>
  );
}
