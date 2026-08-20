import { useEffect, useState } from "react";
import { api } from "../api.js";
import StatCard from "../components/StatCard.jsx";

export default function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [projects, setProjects] = useState([]);
  const [floors, setFloors] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [s, p, f] = await Promise.all([
          api.dashboardSummary(),
          api.projectUtilization(),
          api.floorUtilization(),
        ]);
        if (!cancelled) {
          setSummary(s);
          setProjects(p.sort((a, b) => b.employees - a.employees));
          setFloors(f.sort((a, b) => a.floor - b.floor));
        }
      } catch (e) {
        if (!cancelled) setError(e.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="max-w-6xl mx-auto px-4 md:px-8 py-8">
      <header className="mb-8">
        <p className="text-[11px] font-semibold tracking-wider uppercase text-signal-dark mb-1">
          Directory Board
        </p>
        <h1 className="font-display text-2xl md:text-3xl font-semibold text-ink">
          Seat &amp; Project Overview
        </h1>
        <p className="text-sm text-slate mt-1">
          Live snapshot of headcount, seating, and project utilization across all floors.
        </p>
      </header>

      {error && (
        <div className="mb-6 rounded-lg border border-warn/30 bg-warn-bg text-warn text-sm px-4 py-3">
          Couldn't load dashboard data: {error}. Is the backend running on port 8000?
        </div>
      )}

      {loading && !summary && (
        <p className="text-sm text-slate-light">Loading dashboard…</p>
      )}

      {summary && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            <StatCard eyebrow="Headcount" label="Total employees" value={summary.total_employees.toLocaleString()} />
            <StatCard eyebrow="Inventory" label="Total seats" value={summary.total_seats.toLocaleString()} />
            <StatCard eyebrow="In use" label="Occupied seats" value={summary.occupied_seats.toLocaleString()} tone="warn" />
            <StatCard eyebrow="Free" label="Available seats" value={summary.available_seats.toLocaleString()} tone="ok" />
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-10">
            <StatCard eyebrow="Held" label="Reserved seats" value={summary.reserved_seats.toLocaleString()} tone="hold" />
            <StatCard eyebrow="Offline" label="Maintenance seats" value={summary.maintenance_seats.toLocaleString()} />
            <StatCard eyebrow="Action needed" label="New joiners pending allocation" value={summary.pending_allocation.toLocaleString()} tone="signal" />
          </div>
        </>
      )}

      <div className="grid md:grid-cols-2 gap-6">
        <section className="card p-5">
          <h2 className="font-display font-semibold text-ink mb-4">Floor-wise occupancy</h2>
          <div className="space-y-3">
            {floors.map((f) => {
              const pct = f.total_seats ? Math.round((f.occupied / f.total_seats) * 100) : 0;
              return (
                <div key={f.floor}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="font-mono font-semibold text-ink">Floor {f.floor}</span>
                    <span className="text-slate">
                      {f.occupied}/{f.total_seats} occupied · {f.available} free
                    </span>
                  </div>
                  <div className="h-2 rounded-full bg-paper-dim overflow-hidden">
                    <div
                      className="h-full bg-signal rounded-full"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
            {floors.length === 0 && !loading && (
              <p className="text-sm text-slate-light">No floor data yet.</p>
            )}
          </div>
        </section>

        <section className="card p-5">
          <h2 className="font-display font-semibold text-ink mb-4">Project-wise allocation</h2>
          <div className="max-h-80 overflow-y-auto scrollbar-thin pr-1">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] uppercase tracking-wide text-slate-light border-b border-border">
                  <th className="pb-2 font-medium">Project</th>
                  <th className="pb-2 font-medium text-right">Employees</th>
                  <th className="pb-2 font-medium text-right">Seated</th>
                </tr>
              </thead>
              <tbody>
                {projects.map((p) => (
                  <tr key={p.project_id} className="border-b border-border/60 last:border-0">
                    <td className="py-2 font-medium text-ink">{p.project_name}</td>
                    <td className="py-2 text-right text-slate">{p.employees}</td>
                    <td className="py-2 text-right font-mono text-ok">{p.seats_occupied}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {projects.length === 0 && !loading && (
              <p className="text-sm text-slate-light">No project data yet.</p>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
