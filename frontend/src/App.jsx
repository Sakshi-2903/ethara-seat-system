import { Routes, Route, NavLink, Navigate } from "react-router-dom";
import Dashboard from "./pages/Dashboard.jsx";
import Directory from "./pages/Directory.jsx";
import Seats from "./pages/Seats.jsx";
import NewJoiner from "./pages/NewJoiner.jsx";
import Assistant from "./pages/Assistant.jsx";
import Login from "./pages/Login.jsx";
import MySeat from "./pages/MySeat.jsx";
import BackgroundWatermark from "./components/BackgroundWatermark.jsx";
import { useAuth } from "./auth.jsx";

const ROLE_LABEL = { admin: "Admin", employee: "Employee" };

export default function App() {
  const { auth } = useAuth();

  if (!auth) {
    return <Login />;
  }

  const NAV_ITEMS = [
    { to: "/", label: "Dashboard", icon: GridIcon, end: true },
    { to: "/my-seat", label: "My Seat", icon: BookmarkIcon },
    { to: "/directory", label: "Directory", icon: PeopleIcon },
    { to: "/seats", label: "Seat Map", icon: SeatIcon },
    ...(auth.role !== "employee"
      ? [{ to: "/new-joiner", label: "New Joiner", icon: PlusIcon }]
      : []),
    { to: "/assistant", label: "Ask Ethara", icon: SparkIcon },
  ];

  return (
    <div className="flex min-h-screen">
      <aside className="hidden md:flex w-64 shrink-0 flex-col bg-ink text-paper sticky top-0 h-screen overflow-y-auto">
        <div className="px-6 py-6 border-b border-white/10">
          <div className="flex items-center gap-2">
            <img src="/logo.png" alt="Ethara.AI" className="h-8 w-8 rounded-md object-contain bg-white" />
            <div>
              <p className="font-display font-semibold text-[15px] leading-none">Ethara</p>
              <p className="text-[11px] text-slate-light mt-1 tracking-wide uppercase">Seat Directory</p>
            </div>
          </div>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-white/10 text-white"
                    : "text-paper/70 hover:bg-white/5 hover:text-white"
                }`
              }
            >
              <item.icon className="h-4 w-4 shrink-0" />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <UserFooter />
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="md:hidden flex items-center justify-between px-4 py-3 bg-ink text-paper">
          <div className="flex items-center gap-2">
            <img src="/logo.png" alt="Ethara.AI" className="h-7 w-7 rounded-md object-contain bg-white" />
            <span className="font-display font-semibold text-sm">Ethara</span>
          </div>
          <MobileUserBadge />
        </header>
        <nav className="md:hidden flex overflow-x-auto gap-1 px-3 py-2 bg-ink-soft text-paper scrollbar-thin">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `whitespace-nowrap px-3 py-1.5 rounded-full text-xs font-medium ${
                  isActive ? "bg-signal text-ink" : "text-paper/70"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <main className="flex-1 bg-paper relative">
          <BackgroundWatermark opacity={0.035} />
          <div className="relative">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/my-seat" element={<MySeat />} />
              <Route path="/directory" element={<Directory />} />
              <Route path="/seats" element={<Seats />} />
              <Route
                path="/new-joiner"
                element={auth.role === "employee" ? <Navigate to="/" replace /> : <NewJoiner />}
              />
              <Route path="/assistant" element={<Assistant />} />
            </Routes>
          </div>
        </main>
      </div>
    </div>
  );
}

function UserFooter() {
  const { auth, logout } = useAuth();
  return (
    <div className="px-6 py-4 border-t border-white/10">
      <p className="text-sm font-medium text-white">{auth.username}</p>
      <p className="text-[11px] text-slate-light mb-3">{ROLE_LABEL[auth.role] || auth.role}</p>
      <button
        onClick={logout}
        className="text-xs font-medium text-paper/70 hover:text-white transition-colors"
      >
        Sign out
      </button>
    </div>
  );
}

function MobileUserBadge() {
  const { auth, logout } = useAuth();
  return (
    <button onClick={logout} className="text-xs text-paper/70">
      {auth.username} · Sign out
    </button>
  );
}

function GridIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </svg>
  );
}
function PeopleIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
      <circle cx="9" cy="8" r="3.2" />
      <path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6" />
      <circle cx="17" cy="8" r="2.6" />
      <path d="M15.5 14.2c2.6.5 4.5 2.7 4.5 5.8" />
    </svg>
  );
}
function SeatIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
      <path d="M6 12V6a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v6" />
      <path d="M5 12h14a1 1 0 0 1 1 1v2a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-2a1 1 0 0 1 1-1Z" />
      <path d="M7 17v3M17 17v3" />
    </svg>
  );
}
function PlusIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
      <circle cx="12" cy="8" r="3.5" />
      <path d="M4.5 20c0-3.6 3.4-6.5 7.5-6.5" />
      <path d="M17 14v6M14 17h6" />
    </svg>
  );
}
function SparkIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
      <path d="M12 3v4M12 17v4M3 12h4M17 12h4" />
      <path d="M12 8a4 4 0 0 0 4 4 4 4 0 0 0-4 4 4 4 0 0 0-4-4 4 4 0 0 0 4-4Z" />
    </svg>
  );
}
function BookmarkIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
      <path d="M7 4h10a1 1 0 0 1 1 1v15l-6-3.5L6 20V5a1 1 0 0 1 1-1Z" />
    </svg>
  );
}
