import { useEffect, useState } from "react";
import { api } from "../api.js";

const DEPARTMENTS = ["Engineering", "HR", "Finance", "Operations", "Sales", "Marketing", "Design", "Support"];

export default function NewJoiner() {
  const [projects, setProjects] = useState([]);
  const [form, setForm] = useState({
    name: "",
    email: "",
    department: DEPARTMENTS[0],
    role: "",
    joining_date: new Date().toISOString().slice(0, 10),
    project_id: "",
  });
  const [createdEmployee, setCreatedEmployee] = useState(null);
  const [allocation, setAllocation] = useState(null);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api.listProjects().then(setProjects).catch(() => {});
  }, []);

  function updateField(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    setCreatedEmployee(null);
    setAllocation(null);
    try {
      const employee = await api.createEmployee({
        ...form,
        project_id: form.project_id ? Number(form.project_id) : null,
      });
      setCreatedEmployee(employee);

      const alloc = await api.allocateSeat({ employee_id: employee.id });
      setAllocation(alloc);
    } catch (e) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  }

  function resetForm() {
    setForm({
      name: "",
      email: "",
      department: DEPARTMENTS[0],
      role: "",
      joining_date: new Date().toISOString().slice(0, 10),
      project_id: "",
    });
    setCreatedEmployee(null);
    setAllocation(null);
    setError(null);
  }

  return (
    <div className="max-w-3xl mx-auto px-4 md:px-8 py-8">
      <header className="mb-6">
        <p className="text-[11px] font-semibold tracking-wider uppercase text-signal-dark mb-1">
          Onboarding
        </p>
        <h1 className="font-display text-2xl md:text-3xl font-semibold text-ink">
          Add a new joiner
        </h1>
        <p className="text-sm text-slate mt-1">
          Create the employee record and the system will suggest the nearest available seat
          to their project team automatically.
        </p>
      </header>

      {!createdEmployee ? (
        <form onSubmit={handleSubmit} className="card p-6 space-y-4">
          <div className="grid sm:grid-cols-2 gap-4">
            <Field label="Full name">
              <input required value={form.name} onChange={(e) => updateField("name", e.target.value)}
                className="input" placeholder="e.g. Priya Sharma" />
            </Field>
            <Field label="Work email">
              <input required type="email" value={form.email} onChange={(e) => updateField("email", e.target.value)}
                className="input" placeholder="priya.sharma@ethara.ai" />
            </Field>
            <Field label="Department">
              <select value={form.department} onChange={(e) => updateField("department", e.target.value)} className="input">
                {DEPARTMENTS.map((d) => <option key={d} value={d}>{d}</option>)}
              </select>
            </Field>
            <Field label="Role">
              <input required value={form.role} onChange={(e) => updateField("role", e.target.value)}
                className="input" placeholder="e.g. Software Engineer" />
            </Field>
            <Field label="Joining date">
              <input required type="date" value={form.joining_date} onChange={(e) => updateField("joining_date", e.target.value)}
                className="input" />
            </Field>
            <Field label="Project">
              <select value={form.project_id} onChange={(e) => updateField("project_id", e.target.value)} className="input">
                <option value="">Unassigned</option>
                {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </Field>
          </div>

          {error && (
            <div className="rounded-lg border border-warn/30 bg-warn-bg text-warn text-sm px-4 py-3">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full sm:w-auto px-5 py-2.5 rounded-lg bg-ink text-white text-sm font-medium hover:bg-ink-soft transition-colors disabled:opacity-50"
          >
            {submitting ? "Creating & allocating seat…" : "Create employee & allocate seat"}
          </button>
        </form>
      ) : (
        <div className="card p-6">
          <div className="flex items-center gap-2 mb-4 text-ok">
            <CheckIcon className="h-5 w-5" />
            <p className="font-display font-semibold">Employee onboarded</p>
          </div>
          <dl className="space-y-2 text-sm mb-6">
            <Row label="Name" value={createdEmployee.name} />
            <Row label="Employee code" value={createdEmployee.employee_code} mono />
            <Row label="Email" value={createdEmployee.email} mono />
          </dl>

          {allocation ? (
            <div className="rounded-lg bg-ok-bg text-ok px-4 py-3 text-sm">
              Seat allocated — allocation #{allocation.id}. Look them up in the Directory
              or Seat Map to see the exact floor/zone/seat.
            </div>
          ) : (
            <div className="rounded-lg bg-warn-bg text-warn px-4 py-3 text-sm">
              Employee created, but seat allocation didn't complete. Try allocating manually from the Seat Map.
            </div>
          )}

          <button
            onClick={resetForm}
            className="mt-5 px-5 py-2.5 rounded-lg border border-border text-sm font-medium hover:bg-paper-dim transition-colors"
          >
            Add another employee
          </button>
        </div>
      )}

      <style>{`
        .input {
          width: 100%;
          padding: 0.6rem 0.9rem;
          border-radius: 0.5rem;
          border: 1px solid var(--color-border);
          background: white;
          font-size: 0.875rem;
        }
        .input:focus {
          outline: none;
          box-shadow: 0 0 0 2px rgba(226,168,61,0.4);
        }
      `}</style>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <label className="block">
      <span className="block text-xs font-medium text-slate mb-1">{label}</span>
      {children}
    </label>
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

function CheckIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" {...props}>
      <circle cx="12" cy="12" r="9" />
      <path d="M8 12.5l2.5 2.5L16 9.5" />
    </svg>
  );
}
