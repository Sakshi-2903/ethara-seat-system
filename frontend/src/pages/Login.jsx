import { useState } from "react";
import { useAuth } from "../auth.jsx";
import BackgroundWatermark from "../components/BackgroundWatermark.jsx";

const DEMO_ACCOUNTS = [
  { role: "Admin", username: "admin", password: "admin123", note: "Full read/write access" },
  { role: "Employee", username: "employee", password: "employee123", note: "Read-only + book your own seat" },
];

export default function Login() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [showForgot, setShowForgot] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(username, password);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  function fillDemo(acc) {
    setUsername(acc.username);
    setPassword(acc.password);
    setError(null);
  }

  return (
    <div className="relative min-h-screen bg-ink flex items-center justify-center px-4 overflow-hidden">
      <BackgroundWatermark opacity={0.07} />

      <div className="relative w-full max-w-sm">
        <div className="flex items-center gap-2.5 justify-center mb-8">
          <img
            src="/logo.png"
            alt="Ethara.AI"
            className="h-10 w-10 rounded-md object-contain bg-white shadow-sm"
          />
          <div>
            <p className="font-display font-semibold text-white text-lg leading-none">Ethara</p>
            <p className="text-[11px] text-slate-light uppercase tracking-wide mt-1">Seat Directory</p>
          </div>
        </div>

        <div className="card p-6 shadow-xl">
          <h1 className="font-display text-lg font-semibold text-ink mb-1">Sign in</h1>
          <p className="text-sm text-slate mb-5">Access the seat and project directory.</p>

          <form onSubmit={handleSubmit} className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-slate mb-1">Username</label>
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                autoFocus
                autoComplete="username"
                className="w-full px-3 py-2.5 rounded-lg border border-border bg-white text-sm focus:outline-none focus:ring-2 focus:ring-signal/40"
              />
            </div>
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-xs font-medium text-slate">Password</label>
                <button
                  type="button"
                  onClick={() => setShowForgot((v) => !v)}
                  className="text-xs text-slate-light hover:text-signal-dark transition-colors"
                >
                  Forgot password?
                </button>
              </div>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                  className="w-full px-3 py-2.5 pr-10 rounded-lg border border-border bg-white text-sm focus:outline-none focus:ring-2 focus:ring-signal/40"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  className="absolute inset-y-0 right-0 flex items-center px-3 text-slate-light hover:text-ink transition-colors"
                >
                  {showPassword ? <EyeOffIcon className="h-4 w-4" /> : <EyeIcon className="h-4 w-4" />}
                </button>
              </div>
            </div>

            {showForgot && (
              <div className="rounded-lg bg-paper-dim text-slate text-xs px-3 py-2.5 leading-relaxed">
                This is a demo environment without email-based password reset.
                Use one of the demo accounts below, or ask your Admin/HR to
                reset your account if this were a real deployment.
              </div>
            )}

            {error && (
              <div className="rounded-lg border border-warn/30 bg-warn-bg text-warn text-sm px-3 py-2">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="w-full px-4 py-2.5 rounded-lg bg-ink text-white text-sm font-medium hover:bg-ink-soft transition-colors disabled:opacity-50"
            >
              {submitting ? "Signing in…" : "Sign in"}
            </button>
          </form>
        </div>

        <div className="mt-4 card p-4 shadow-xl">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-light mb-2">
            Demo accounts
          </p>
          <div className="space-y-1.5">
            {DEMO_ACCOUNTS.map((acc) => (
              <button
                key={acc.username}
                onClick={() => fillDemo(acc)}
                className="w-full flex items-center justify-between text-left px-3 py-2 rounded-lg hover:bg-paper-dim transition-colors"
              >
                <span>
                  <span className="text-sm font-medium text-ink">{acc.role}</span>
                  <span className="block text-[11px] text-slate-light">{acc.note}</span>
                </span>
                <span className="seat-tag text-xs text-slate">{acc.username}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function EyeIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
      <path d="M2.5 12S6 5 12 5s9.5 7 9.5 7-3.5 7-9.5 7-9.5-7-9.5-7Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}
function EyeOffIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
      <path d="M3 3l18 18" />
      <path d="M10.6 5.1A9.4 9.4 0 0 1 12 5c6 0 9.5 7 9.5 7a13.7 13.7 0 0 1-2.6 3.4M6.6 6.6C4 8.4 2.5 12 2.5 12s3.5 7 9.5 7a9.4 9.4 0 0 0 3.4-.6" />
      <path d="M9.9 9.9a3 3 0 0 0 4.2 4.2" />
    </svg>
  );
}