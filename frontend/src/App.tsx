import { useEffect, useState } from "react";
import { api, ApiError } from "./api";
import type { User } from "./types";
import AuthScreen from "./components/AuthScreen";
import Onboarding from "./components/Onboarding";
import Chat from "./components/Chat";
import Dashboard from "./components/Dashboard";
import SettingsDialog from "./components/SettingsDialog";
import SummaryStrip from "./components/SummaryStrip";
import FoodsPage from "./components/FoodsPage";
import { AssistantAvatar, UserAvatar } from "./components/Avatar";

const TABS = [
  { id: "chat", label: "Chat" },
  { id: "dashboard", label: "Dashboard" },
  { id: "foods", label: "My foods" },
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
  if (!user.onboarded) return <Onboarding onDone={setUser} />;

  return (
    <div className="app">
      <header className="topbar">
        <span className="brand"><AssistantAvatar size={30} />Macro Tracker</span>
        <div className="topbar-actions">
          <button className="ghost" onClick={() => setShowSettings(true)}>Targets &amp; weight</button>
          <button className="ghost" onClick={logout}>Log out</button>
          <span className="topbar-user">
            <span className="greeting">{greeting()}{user.preferred_name ? `, ${user.preferred_name}` : ""}</span>
            <UserAvatar name={user.preferred_name} email={user.email} size={34} />
          </span>
        </div>
      </header>
      <nav className="tabs" role="tablist" aria-label="Sections">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            id={`tab-${t.id}`}
            aria-selected={tab === t.id}
            aria-controls={`panel-${t.id}`}
            className={tab === t.id ? "on" : ""}
            onClick={() => openTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>
      {/* Panels stay mounted so the chat keeps its scroll position and draft text. */}
      <main className="page page-chat" id="panel-chat" role="tabpanel" aria-labelledby="tab-chat" hidden={tab !== "chat"}>
        <SummaryStrip dataVersion={dataVersion} onOpen={() => openTab("dashboard")} />
        <Chat user={user} onDataChanged={() => setDataVersion((v) => v + 1)} />
      </main>
      <main className="page" id="panel-dashboard" role="tabpanel" aria-labelledby="tab-dashboard" hidden={tab !== "dashboard"}>
        <Dashboard dataVersion={dataVersion} onDataChanged={() => setDataVersion((v) => v + 1)} />
      </main>
      <main className="page" id="panel-foods" role="tabpanel" aria-labelledby="tab-foods" hidden={tab !== "foods"}>
        <FoodsPage dataVersion={dataVersion} />
      </main>
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
