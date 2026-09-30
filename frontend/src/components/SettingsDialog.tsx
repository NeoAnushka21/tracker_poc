import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { api } from "../api";
import type { User } from "../types";
import { ACTIVITY, GOALS } from "../format";
import TargetsEditor from "./TargetsEditor";
import ThemeToggle from "./ThemeToggle";
import { UserAvatar } from "./Avatar";
import { APP_NAME } from "../brand";
import { LocationFields } from "./LocationFields";
import { AboutYouForm, SuggestedTargets } from "./AboutYou";

type Section = "about" | "targets" | "appearance" | "account" | "security" | "delete";

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

/** A titled card of label / value rows (optionally with an action on the right). */
function Group({ title, note, children }: { title: string; note?: string; children: ReactNode }) {
  return (
    <section className="settings-group">
      <h3>{title}</h3>
      {note && <p className="muted small">{note}</p>}
      <dl className="settings-rows">{children}</dl>
    </section>
  );
}

function Row({ label, children, action }: { label: string; children: ReactNode; action?: ReactNode }) {
  return (
    <div className="settings-row">
      <dt>{label}</dt>
      <dd>{children}</dd>
      {action && <div className="settings-row-action">{action}</div>}
    </div>
  );
}

function PanelHead({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="settings-panel-head">
      <h3>{title}</h3>
      {children && <p className="muted small">{children}</p>}
    </div>
  );
}

/** Country (required) and region (optional): shown as a row, with Change opening the dropdowns. */
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

  const shown = [user.country_name, user.region].filter(Boolean).join(" · ") || "–";
  if (!editing) {
    return (
      <Row label="Country / state" action={<button type="button" className="ghost small-btn" onClick={() => setEditing(true)}>Change</button>}>
        {shown}
      </Row>
    );
  }
  return (
    <Row label="Country / state">
      <form className="settings-location" onSubmit={save}>
        <LocationFields country={country} region={region} onChange={(c, r) => { setCountry(c); setRegion(r); }} />
        {error && <p className="error small">{error}</p>}
        <div className="proposal-actions">
          <button className="primary" disabled={!country || busy}>{busy ? "Saving…" : "Save"}</button>
          <button type="button" className="ghost" onClick={() => { setEditing(false); setCountry(user.country ?? ""); setRegion(user.region ?? ""); }}>
            Cancel
          </button>
        </div>
      </form>
    </Row>
  );
}

/** About you: the basics from onboarding, then the optional answers. */
function AboutSection({ user, onSaved }: { user: User; onSaved: (u: User) => void }) {
  const [note, setNote] = useState<string | null>(null);
  const [suggested, setSuggested] = useState<{ daily_calorie_target: number } | null>(null);
  const height = user.height_cm == null ? "–"
    : user.unit_system === "imperial"
      ? `${Math.floor(user.height_cm / 30.48)} ft ${Math.round((user.height_cm % 30.48) / 2.54)} in`
      : `${Math.round(user.height_cm)} cm`;
  return (
    <>
      <PanelHead title="About you">What {APP_NAME} knows about you, and what it's used for.</PanelHead>
      <Group title="Basics" note="From your sign-up. Height and weight are updated on the Body Profile tab.">
        <Row label="Name">{user.preferred_name ?? "–"}</Row>
        <Row label="Age">{user.age ?? "–"} <span className="muted small">from your date of birth</span></Row>
        <Row label="Sex">{user.sex ? user.sex[0].toUpperCase() + user.sex.slice(1) : "–"}</Row>
        <Row label="Height">{height}</Row>
        <WhereYouLive user={user} onSaved={onSaved} />
        <Row label="Time zone">{user.timezone}</Row>
        <Row label="Goal">{user.goal_type ? GOALS[user.goal_type] ?? user.goal_type : "–"}</Row>
        <Row label="Activity">{user.activity_level ? ACTIVITY[user.activity_level] ?? user.activity_level : "–"}</Row>
      </Group>
      <section className="settings-group">
        <h3>More about you <span className="muted small">(optional)</span></h3>
        <p className="muted small">Used for your targets (pace, pregnancy), picking the right meal in the chat, and MacBro's suggestions.</p>
        {suggested && (
          <SuggestedTargets suggested={suggested} user={user}
                            onDone={(u) => { if (u) onSaved(u); setSuggested(null); setNote(u ? "Targets updated." : null); }} />
        )}
        <div className="settings-card">
          <AboutYouForm user={user} saveLabel="Save"
                        onSaved={(u, s) => { onSaved(u); setSuggested(s); setNote(s ? null : "Saved."); }} />
          {note && <p className="ok small" role="status">{note}</p>}
        </div>
      </section>
    </>
  );
}

function AppearanceSection() {
  return (
    <>
      <PanelHead title="Appearance">Light, dark, or follow your device.</PanelHead>
      <div className="settings-card"><ThemeToggle /></div>
    </>
  );
}

function AccountSection({ user }: { user: User }) {
  return (
    <>
      <div className="account-card">
        <UserAvatar name={user.preferred_name} email={user.email} size={48} />
        <div>
          <div className="account-name">{user.preferred_name ?? (user.is_admin ? "Administrator" : "No preferred name")}</div>
          <div className="muted">{user.email}</div>
        </div>
      </div>
      <Group title="Sign-in">
        <Row label="Email">{user.email}</Row>
        {!user.is_admin && (
          <Row label="Signs in with">{[user.has_password && "Email and password", user.google_linked && "Google"].filter(Boolean).join(" · ") || "–"}</Row>
        )}
        <Row label="Registered">{when(user.created_at)}</Row>
        <Row label="Last login">{when(user.last_login_at)}</Row>
      </Group>
      <YourData user={user} />
    </>
  );
}

/** Download my data (everything stored about the account) and the privacy notice. */
function YourData({ user }: { user: User }) {
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
    <Group title="Your data">
      <Row label="Consent given">{when(user.consented_at)}</Row>
      <Row label="Download"
           action={<button type="button" className="ghost small-btn" onClick={download} disabled={busy}>{busy ? "Preparing…" : "Download my data"}</button>}>
        <span className="muted small">Everything {APP_NAME} stores about you, as a file.</span>
        {error && <span className="error small"> {error}</span>}
      </Row>
      <Row label="Policies">
        <a href="/privacy" target="_blank" rel="noopener">How we use your data</a> · <a href="/terms" target="_blank" rel="noopener">Terms</a>
      </Row>
    </Group>
  );
}

function TargetsSection({ user, onSaved }: { user: User; onSaved: (u: User) => void }) {
  const [msg, setMsg] = useState<string | null>(null);
  return (
    <>
      <PanelHead title="Daily calorie & macro targets">
        Calculated from your profile; adjust any number. Changing weight or height on the Body Profile tab can recalculate these.
      </PanelHead>
      <div className="settings-card">
        <TargetsEditor
          key={`${user.targets?.effective_date}-${user.targets?.calories}-${user.targets?.protein_g}`}
          user={user}
          saveLabel="Save targets"
          onSaved={(u) => { onSaved(u); setMsg("Targets saved."); }}
        />
        {msg && <p className="ok small">{msg}</p>}
      </div>
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
  // Personal things first, then the account; Delete account is set apart at the end.
  const sections: { id: Section; label: string }[] = [
    ...(!user.is_admin ? [
      { id: "about" as const, label: "About you" },
      { id: "targets" as const, label: "Targets" },
    ] : []),
    { id: "appearance", label: "Appearance" },
    { id: "account", label: "Account & privacy" },
    { id: "security", label: "Security" },
    ...(!user.is_admin ? [{ id: "delete" as const, label: "Delete account" }] : []),
  ];
  const [section, setSection] = useState<Section>(user.is_admin ? "account" : "about");

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
            {section === "about" && <AboutSection user={user} onSaved={onSaved} />}
            {section === "targets" && <TargetsSection user={user} onSaved={onSaved} />}
            {section === "appearance" && <AppearanceSection />}
            {section === "account" && <AccountSection user={user} />}
            {section === "security" && (
              <>
                <PanelHead title="Security">Your password, and signing out of other devices.</PanelHead>
                <div className="settings-card"><SecuritySection user={user} onSaved={onSaved} /></div>
                <div className="settings-card"><SignOutEverywhere onSignedOut={onSignedOut} /></div>
              </>
            )}
            {section === "delete" && <DeleteSection user={user} onDeleted={onSignedOut} />}
          </div>
        </div>
      </div>
    </div>
  );
}
