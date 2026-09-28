import { useEffect, useState } from "react";
import { api, ApiError } from "./api";
import type { User } from "./types";
import AuthScreen from "./components/AuthScreen";
import Onboarding from "./components/Onboarding";
import Chat from "./components/Chat";
import Dashboard from "./components/Dashboard";
import SettingsDialog from "./components/SettingsDialog";
import SummaryStrip from "./components/SummaryStrip";
import ThemeToggle from "./components/ThemeToggle";
import FoodsPage from "./components/FoodsPage";
import AnalysisPage from "./components/AnalysisPage";
import AdminPage from "./components/AdminPage";
import ConsentGate from "./components/ConsentGate";
import { MacBroAvatar, UserAvatar } from "./components/Avatar";

const TABS = [
  { id: "chat", label: "Chat", admin: false },
  { id: "dashboard", label: "Dashboard", admin: false },
  { id: "analysis", label: "Analysis", admin: false },
  { id: "foods", label: "My foods", admin: false },
  { id: "admin", label: "Admin", admin: true },
] as const;
type TabId = (typeof TABS)[number]["id"];

function tabFromHash(): TabId {
  const h = window.location.hash.replace("#", "");
  return (TABS.find((t) => t.id === h)?.id ?? "chat") as TabId;
}

function greeting(): string {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
}

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Bumped whenever confirmed data changes, so the dashboard refetches.
  const [dataVersion, setDataVersion] = useState(0);
  const [showSettings, setShowSettings] = useState(false);
  const [tab, setTab] = useState<TabId>(tabFromHash);

  useEffect(() => {
    const onHash = () => setTab(tabFromHash());
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

  if (loading) return <div className="center muted">Loading…</div>;
  if (error) return <div className="center error">Couldn't reach the server: {error}</div>;
  if (!user) return <AuthScreen onAuthed={setUser} />;
  if (!user.consented) return <ConsentGate onAccepted={setUser} onLogout={logout} />;
  if (!user.onboarded) return <Onboarding onDone={setUser} />;

  const tabs = TABS.filter((t) => !t.admin || user.is_admin);
  const current = tabs.some((t) => t.id === tab) ? tab : "chat";

  return (
    <div className="app">
      <header className="topbar">
        <span className="brand"><MacBroAvatar size={34} />MacBro</span>
        <div className="topbar-actions">
          <ThemeToggle />
          <button className="ghost" onClick={() => setShowSettings(true)}>Targets &amp; weight</button>
          <button className="ghost" onClick={logout}>Log out</button>
          <span className="topbar-user">
            <span className="greeting">{greeting()}{user.preferred_name ? `, ${user.preferred_name}` : ""}</span>
            <UserAvatar name={user.preferred_name} email={user.email} size={34} />
          </span>
        </div>
      </header>
      <nav className="tabs" role="tablist" aria-label="Sections">
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
      </nav>
      {/* Panels stay mounted so the chat keeps its scroll position and draft text. */}
      <main className="page page-chat" id="panel-chat" role="tabpanel" aria-labelledby="tab-chat" hidden={current !== "chat"}>
        <SummaryStrip dataVersion={dataVersion} onOpen={() => openTab("dashboard")} />
        <Chat user={user} onDataChanged={() => setDataVersion((v) => v + 1)} />
      </main>
      <main className="page" id="panel-dashboard" role="tabpanel" aria-labelledby="tab-dashboard" hidden={current !== "dashboard"}>
        <Dashboard dataVersion={dataVersion} onDataChanged={() => setDataVersion((v) => v + 1)} />
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
      {current === "admin" && user.is_admin && (
        <main className="page page-wide" id="panel-admin" role="tabpanel" aria-labelledby="tab-admin">
          <AdminPage />
        </main>
      )}
      {showSettings && (
        <SettingsDialog
          user={user}
          onClose={() => setShowSettings(false)}
          onSaved={(u) => {
            setUser(u);
            setDataVersion((v) => v + 1);
          }}
        />
      )}
    </div>
  );
}
