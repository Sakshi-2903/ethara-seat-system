import { useEffect, useState } from "react";
import { api } from "../api.js";

const STATUS_STYLES = {
  active: "bg-ok-bg text-ok",
  pending_allocation: "bg-signal/15 text-signal-dark",
  inactive: "bg-paper-dim text-slate-light",
};

export default function Directory() {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [employees, setEmployees] = useState([]);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const timer = setTimeout(async () => {
      setLoading(true);
      setError(null);
      try {
        const params = { limit: "40" };
        if (search) params.search = search;
        if (status) params.status = status;
        const data = await api.listEmployees(params);
        if (!cancelled) setEmployees(data);
      } catch (e) {
        if (!cancelled) setError(e.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, 300);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [search, status]);

  async function openDetail(emp) {
    setSelected(emp.id);
    setDetail(null);
    try {
      const d = await api.getEmployee(emp.id);
      setDetail(d);
    } catch (e) {
      setDetail({ error: e.message });
    }
  }

  return (
    <div className="max-w-6xl mx-auto px-4 md:px-8 py-8">
      <header className="mb-6">
        <p className="text-[11px] font-semibold tracking-wider uppercase text-signal-dark mb-1">
          Directory
        </p>
        <h1 className="font-display text-2xl md:text-3xl font-semibold text-ink">
          Find an employee
        </h1>
        <p className="text-sm text-slate mt-1">
          Search by name, employee ID, or email to see project and seat assignment.
        </p>
      </header>

      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search name, ID, or email…"
          className="flex-1 px-4 py-2.5 rounded-lg border border-border bg-white text-sm focus:outline-none focus:ring-2 focus:ring-signal/40"
        />
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="px-4 py-2.5 rounded-lg border border-border bg-white text-sm focus:outline-none focus:ring-2 focus:ring-signal/40"
        >
          <option value="">All statuses</option>
          <option value="active">Active</option>
          <option value="pending_allocation">Pending allocation</option>
          <option value="inactive">Inactive</option>
        </select>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-warn/30 bg-warn-bg text-warn text-sm px-4 py-3">
          {error}
        </div>
      )}

      <div className="grid md:grid-cols-3 gap-6">
        <div className="md:col-span-2 card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[11px] uppercase tracking-wide text-slate-light bg-paper-dim">
                <th className="px-4 py-2.5 font-medium">Employee</th>
                <th className="px-4 py-2.5 font-medium">Department</th>
                <th className="px-4 py-2.5 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {employees.map((emp) => (
                <tr
                  key={emp.id}
                  onClick={() => openDetail(emp)}
                  className={`border-t border-border cursor-pointer hover:bg-paper-dim/60 transition-colors ${
                    selected === emp.id ? "bg-paper-dim/80" : ""
                  }`}
                >
                  <td className="px-4 py-2.5">
                    <p className="font-medium text-ink">{emp.name}</p>
                    <p className="text-xs text-slate-light font-mono">{emp.employee_code}</p>
                  </td>
                  <td className="px-4 py-2.5 text-slate">{emp.department}</td>
                  <td className="px-4 py-2.5">
                    <span className={`inline-block px-2 py-0.5 rounded-full text-[11px] font-medium ${STATUS_STYLES[emp.status] || ""}`}>
                      {emp.status.replace("_", " ")}
                    </span>
                  </td>
                </tr>
              ))}
              {!loading && employees.length === 0 && (
                <tr>
                  <td colSpan={3} className="px-4 py-8 text-center text-slate-light text-sm">
                    No employees match this search.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="card p-5 h-fit sticky top-6">
          <h2 className="font-display font-semibold text-ink mb-3">Employee detail</h2>
          {!selected && (
            <p className="text-sm text-slate-light">Select an employee to view their seat and project.</p>
          )}
          {detail && detail.error && (
            <p className="text-sm text-warn">{detail.error}</p>
          )}
          {detail && !detail.error && (
            <div className="space-y-3 text-sm">
              <div>
                <p className="font-display font-semibold text-ink text-lg">{detail.name}</p>
                <p className="text-slate-light font-mono text-xs">{detail.employee_code}</p>
              </div>
              <dl className="space-y-2">
                <Row label="Email" value={detail.email} mono />
                <Row label="Department" value={detail.department} />
                <Row label="Role" value={detail.role} />
                <Row label="Project" value={detail.project_name || "Unassigned"} />
                <Row
                  label="Seat"
                  value={detail.seat ? `${detail.seat} · Floor ${detail.floor}, Zone ${detail.zone}` : "Not allocated"}
                  mono={!!detail.seat}
                />
                <Row label="Joined" value={detail.joining_date} />
              </dl>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Row({ label, value, mono }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-slate-light">{label}</dt>
      <dd className={`text-right text-ink ${mono ? "font-mono text-xs" : ""}`}>{value}</dd>
    </div>
  );
}
