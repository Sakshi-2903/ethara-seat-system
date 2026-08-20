import { useState } from "react";
import { useAuth } from "../auth.jsx";

const DEMO_ACCOUNTS = [
  { role: "Admin", username: "admin", password: "admin123", note: "Full read/write access" },
  { role: "HR", username: "hr", password: "hr123", note: "Full read/write access" },
  { role: "Employee", username: "employee", password: "employee123", note: "Read-only access" },
];

export default function Login() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

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
  }

  return (
    <div className="min-h-screen bg-ink flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="flex items-center gap-2 justify-center mb-8">
          <div className="h-9 w-9 rounded-md bg-signal flex items-center justify-center font-display font-bold text-ink">
            E
          </div>
          <div>
            <p className="font-display font-semibold text-white leading-none">Ethara</p>
            <p className="text-[11px] text-slate-light uppercase tracking-wide mt-1">Seat Directory</p>
          </div>
        </div>

        <div className="card p-6">
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
                className="w-full px-3 py-2.5 rounded-lg border border-border bg-white text-sm focus:outline-none focus:ring-2 focus:ring-signal/40"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate mb-1">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full px-3 py-2.5 rounded-lg border border-border bg-white text-sm focus:outline-none focus:ring-2 focus:ring-signal/40"
              />
            </div>

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

        <div className="mt-4 card p-4">
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
