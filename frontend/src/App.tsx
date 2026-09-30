import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { api, ApiError } from "./api";
import type { User } from "./types";
import AuthScreen from "./components/AuthScreen";
import Onboarding from "./components/Onboarding";
import { LocationGate } from "./components/LocationFields";
import { AboutYouGate } from "./components/AboutYou";
import ChatWidget, { type ChatWindow } from "./components/ChatWidget";
import Dashboard from "./components/Dashboard";
import SettingsDialog from "./components/SettingsDialog";
import HomePage from "./components/HomePage";
import FoodsPage from "./components/FoodsPage";
import BodyPage from "./components/BodyPage";
import ExplorePage from "./components/ExplorePage";
import AnalysisPage from "./components/AnalysisPage";
import AdminPage from "./components/AdminPage";
import ConsentGate from "./components/ConsentGate";
import GuideTour from "./components/GuideTour";
import { AppLogo, UserAvatar } from "./components/Avatar";
import { APP_NAME } from "./brand";
import { DelayedWakeScreen, WakeScreen } from "./components/WakeScreen";
import { useServerWaking } from "./wake";

const TABS = [
  { id: "home", label: "Home" },
  { id: "dashboard", label: "Dashboard" },
  { id: "analysis", label: "Analysis" },
  { id: "foods", label: "Saved Food" },
  { id: "explore", label: "Explore" },
  { id: "body", label: "Body Profile" },
] as const;
type TabId = (typeof TABS)[number]["id"];

function tabFromHash(): TabId {
  const h = window.location.hash.replace("#", "");
  return (TABS.find((t) => t.id === h)?.id ?? "home") as TabId;
}

/** Chat was a tab until 2026-09-30; an old #chat link opens the chat window on Home. */
const chatFromHash = () => window.location.hash === "#chat";

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const waking = useServerWaking();   // the overlay (main.tsx) is already showing the loader
  // Bumped whenever confirmed data changes, so the dashboard refetches.
  const [dataVersion, setDataVersion] = useState(0);
  const [showSettings, setShowSettings] = useState(false);
  const [tab, setTab] = useState<TabId>(tabFromHash);
  const [chatDraft, setChatDraft] = useState<{ text: string; nonce: number; date?: string } | null>(null);
  const [chatWindow, setChatWindow] = useState<ChatWindow>(() => (chatFromHash() ? "open" : "closed"));
  const [guideOpen, setGuideOpen] = useState(false);
  // Sliding underline under the active tab: measured from the button itself.
  const tabsRef = useRef<HTMLDivElement>(null);
  const [indicator, setIndicator] = useState<{ left: number; width: number } | null>(null);

  useEffect(() => {
    const onHash = () => {
      setTab(tabFromHash());
      if (chatFromHash()) setChatWindow("open");
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  function openTab(id: TabId) {
    window.location.hash = id;   // remembered across refreshes; hashchange updates state
    setTab(id);
  }

  useEffect(() => {
    api.me()
      .then(setUser)
      .catch((e) => {
        if (!(e instanceof ApiError && e.status === 401)) setError(e.message);
      })
      .finally(() => setLoading(false));
  }, []);

  async function logout() {
    await api.logout();
    setUser(null);
  }

  // First-run guide: opens once for a new user after onboarding; the Guide button reopens it.
  useEffect(() => {
    if (user && !user.is_admin && user.consented && user.onboarded && !user.guide_seen) setGuideOpen(true);
  }, [user?.id, user?.onboarded, user?.consented]); // eslint-disable-line react-hooks/exhaustive-deps

  function closeGuide() {
    setGuideOpen(false);
    openTab("home");
    if (user && !user.guide_seen) api.guideSeen().then(setUser).catch(() => {});
  }

  useLayoutEffect(() => {
    const measure = () => {
      const el = tabsRef.current?.querySelector<HTMLElement>("button.on");
      setIndicator(el ? { left: el.offsetLeft, width: el.offsetWidth } : null);
    };
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, [tab, user?.id, user?.onboarded, user?.consented]);

  if (loading) return waking ? null : <DelayedWakeScreen />;
  if (error) return <WakeScreen stalled onRetry={() => window.location.reload()} />;
  if (!user) return <AuthScreen onAuthed={setUser} />;

  const settingsButton = (
    <button className="ghost settings-btn" onClick={() => setShowSettings(true)} aria-label="Settings" title="Settings">
      <span aria-hidden="true">⚙</span><span className="settings-label">Settings</span>
    </button>
  );
  const settings = showSettings && (
    <SettingsDialog
      user={user}
      onClose={() => setShowSettings(false)}
      onSaved={(u) => { setUser(u); setDataVersion((v) => v + 1); }}
      onSignedOut={() => { setShowSettings(false); setUser(null); window.location.hash = ""; }}
    />
  );

  // The admin account gets only the admin console: no onboarding or food tracking.
  if (user.is_admin) {
    return (
      <div className="app">
        <div className="app-header"><div className="app-header-glass">
        <header className="topbar">
          <span className="brand"><AppLogo size={34} />{APP_NAME}<span className="admin-badge">Admin</span></span>
          <div className="topbar-actions">
            {settingsButton}
            <button className="ghost" onClick={logout}>Log out</button>
            <span className="topbar-user"><UserAvatar name={user.preferred_name} email={user.email} size={34} /></span>
          </div>
        </header>
        </div></div>
        <main className="page page-wide"><AdminPage /></main>
        {settings}
      </div>
    );
  }

  if (!user.consented) return <ConsentGate onAccepted={setUser} onLogout={logout} />;
  if (!user.onboarded) return <Onboarding onDone={setUser} initialName={user.preferred_name} />;
  if (user.needs_location) return <LocationGate user={user} onSaved={setUser} onLogout={logout} />;
  if (user.needs_preferences) return <AboutYouGate user={user} onDone={setUser} onLogout={logout} />;

  const tabs = TABS;
  const current = tabs.some((t) => t.id === tab) ? tab : "home";

  return (
    <div className="app">
      {/* One mesh image behind one frosted-glass layer, shared by the top bar and the tabs (styles.css, "header"). */}
      <div className="app-header"><div className="app-header-glass">
      <header className="topbar">
        <span className="brand"><AppLogo size={34} />{APP_NAME}</span>
        <div className="topbar-actions">
          <button className="ghost guide-btn" onClick={() => setGuideOpen(true)} aria-label="Guide" title={`How to use ${APP_NAME}`}>
            <span aria-hidden="true">?</span><span className="settings-label">Guide</span>
          </button>
          {settingsButton}
          <button className="ghost" onClick={logout}>Log out</button>
          <span className="topbar-user" title={user.email}>
            <UserAvatar name={user.preferred_name} email={user.email} size={34} />
          </span>
        </div>
      </header>
      <div className="tabs" role="tablist" aria-label="Sections" ref={tabsRef}>
        {tabs.map((t) => (
          <button
            key={t.id}
            role="tab"
            id={`tab-${t.id}`}
            aria-selected={current === t.id}
            aria-controls={`panel-${t.id}`}
            className={current === t.id ? "on" : ""}
            onClick={() => openTab(t.id)}
          >
            {t.label}
          </button>
        ))}
        {indicator && <span className="tab-indicator" aria-hidden="true"
                            style={{ transform: `translateX(${indicator.left}px)`, width: indicator.width }} />}
      </div>
      </div></div>
      {/* Panels stay mounted so each keeps its state when you switch tabs. */}
      <main className="page" id="panel-home" role="tabpanel" aria-labelledby="tab-home" hidden={current !== "home"}>
        <HomePage user={user} dataVersion={dataVersion} onDataChanged={() => setDataVersion((v) => v + 1)}
                  onOpenChat={() => setChatWindow("open")} onOpenDashboard={() => openTab("dashboard")} />
      </main>
      <main className="page" id="panel-dashboard" role="tabpanel" aria-labelledby="tab-dashboard" hidden={current !== "dashboard"}>
        <Dashboard
          dataVersion={dataVersion}
          onDataChanged={() => setDataVersion((v) => v + 1)}
          onAskMacBro={(text, date) => { setChatDraft({ text, nonce: Date.now(), date }); setChatWindow("open"); }}
        />
      </main>
      {/* Analysis and Admin load only when opened (admin views are audited). */}
      {current === "analysis" && (
        <main className="page" id="panel-analysis" role="tabpanel" aria-labelledby="tab-analysis">
          <AnalysisPage dataVersion={dataVersion} />
        </main>
      )}
      <main className="page" id="panel-foods" role="tabpanel" aria-labelledby="tab-foods" hidden={current !== "foods"}>
        <FoodsPage dataVersion={dataVersion} />
      </main>
      <main className="page" id="panel-explore" role="tabpanel" aria-labelledby="tab-explore" hidden={current !== "explore"}>
        <ExplorePage />
      </main>
      <main className="page" id="panel-body" role="tabpanel" aria-labelledby="tab-body" hidden={current !== "body"}>
        <BodyPage user={user} onUserChanged={(u) => { setUser(u); setDataVersion((v) => v + 1); }} />
      </main>
      <ChatWidget state={chatWindow} onState={setChatWindow} user={user}
                  onDataChanged={() => setDataVersion((v) => v + 1)} draft={chatDraft} />
      {settings}
      {guideOpen && <GuideTour name={user.preferred_name} onTab={openTab} onClose={closeGuide} />}
    </div>
  );
}
