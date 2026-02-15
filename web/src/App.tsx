import { useState } from "react";
import Chat from "./Chat";
import Dashboard from "./Dashboard";
import Settings from "./Settings";

type Page = "chat" | "dashboard" | "settings";

export default function App() {
  const [page, setPage] = useState<Page>("chat");

  return (
    <div className="flex h-screen bg-gray-950 text-gray-100">
      {/* Sidebar */}
      <nav className="w-16 bg-gray-900 border-r border-gray-800 flex flex-col items-center py-4 gap-4">
        <div className="w-10 h-10 bg-gulama-600 rounded-lg flex items-center justify-center text-white font-bold text-lg">
          G
        </div>

        <div className="flex-1 flex flex-col gap-2 mt-4">
          <NavButton
            active={page === "chat"}
            onClick={() => setPage("chat")}
            title="Chat"
          >
            <ChatIcon />
          </NavButton>
          <NavButton
            active={page === "dashboard"}
            onClick={() => setPage("dashboard")}
            title="Dashboard"
          >
            <DashIcon />
          </NavButton>
          <NavButton
            active={page === "settings"}
            onClick={() => setPage("settings")}
            title="Settings"
          >
            <GearIcon />
          </NavButton>
        </div>

        <div className="text-xs text-gray-600">v0.1</div>
      </nav>

      {/* Main content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {page === "chat" && <Chat />}
        {page === "dashboard" && <Dashboard />}
        {page === "settings" && <Settings />}
      </main>
    </div>
  );
}

function NavButton({
  active,
  onClick,
  title,
  children,
}: {
  active: boolean;
  onClick: () => void;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      className={`w-10 h-10 rounded-lg flex items-center justify-center transition-colors ${
        active
          ? "bg-gulama-600 text-white"
          : "text-gray-500 hover:text-gray-300 hover:bg-gray-800"
      }`}
    >
      {children}
    </button>
  );
}

function ChatIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
    </svg>
  );
}

function DashIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
    </svg>
  );
}

function GearIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  );
}
