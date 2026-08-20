import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";

export default function MySeat() {
  const { auth } = useAuth();
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);
  const [floor, setFloor] = useState("");
  const [zone, setZone] = useState("");
  const [working, setWorking] = useState(false);

  async function load() {
    if (!auth.employeeId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const d = await api.getEmployee(auth.employeeId);
      setDetail(d);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleBook(e) {
    e.preventDefault();
    setWorking(true);
    setMessage(null);
    setError(null);
    try {
      const payload = {};
      if (floor) payload.preferred_floor = Number(floor);
      if (zone) payload.preferred_zone = zone;
      await api.allocateSeat(payload);
      setMessage("Seat booked.");
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setWorking(false);
    }
  }

  async function handleRelease() {
    setWorking(true);
    setMessage(null);
    setError(null);
    try {
      await api.releaseSeat({});
      setMessage("Seat released — it's now available for others.");
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setWorking(false);
    }
  }

  if (!auth.employeeId) {
    return (
      <div className="max-w-2xl mx-auto px-4 md:px-8 py-8">
        <header className="mb-6">
          <p className="text-[11px] font-semibold tracking-wider uppercase text-signal-dark mb-1">
            My Seat
          </p>
          <h1 className="font-display text-2xl md:text-3xl font-semibold text-ink">Book your seat</h1>
        </header>
        <div className="card p-6 text-sm text-slate">
          Your login isn't linked to an employee record, so there's no seat to book or release from
          this account. This applies to shared Admin/HR accounts — contact HR if you believe this is
          a mistake.
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4 md:px-8 py-8">
      <header className="mb-6">
        <p className="text-[11px] font-semibold tracking-wider uppercase text-signal-dark mb-1">
          My Seat
        </p>
        <h1 className="font-display text-2xl md:text-3xl font-semibold text-ink">Book your seat</h1>
        <p className="text-sm text-slate mt-1">
          Book an available seat for yourself, or release the one you're in.
        </p>
      </header>

      {message && (
        <div className="mb-4 rounded-lg border border-signal/30 bg-signal/10 text-signal-dark text-sm px-4 py-2.5">
          {message}
        </div>
      )}
      {error && (
        <div className="mb-4 rounded-lg border border-warn/30 bg-warn-bg text-warn text-sm px-4 py-3">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-sm text-slate-light">Loading…</p>
      ) : detail?.seat ? (
        <div className="card p-6">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-light mb-1">
            Your current seat
          </p>
          <p className="seat-tag text-2xl font-semibold text-ink mb-1">{detail.seat}</p>
          <p className="text-sm text-slate mb-5">
            Floor {detail.floor} · Zone {detail.zone} · Project {detail.project_name || "Unassigned"}
          </p>
          <button
            onClick={handleRelease}
            disabled={working}
            className="px-5 py-2.5 rounded-lg border border-warn/40 text-warn text-sm font-medium hover:bg-warn-bg transition-colors disabled:opacity-50"
          >
            {working ? "Releasing…" : "Release my seat"}
          </button>
        </div>
      ) : (
        <div className="card p-6">
          <p className="text-sm text-slate mb-4">
            You don't currently have a seat allocated. Book one below — leave floor/zone blank to
            let the system pick the best spot near your project team.
          </p>
          <form onSubmit={handleBook} className="flex flex-wrap gap-3 items-end">
            <div>
              <label className="block text-xs font-medium text-slate mb-1">Preferred floor</label>
              <select value={floor} onChange={(e) => setFloor(e.target.value)}
                className="px-3 py-2 rounded-lg border border-border bg-white text-sm">
                <option value="">Any</option>
                {[1, 2, 3, 4, 5].map((f) => <option key={f} value={f}>Floor {f}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate mb-1">Preferred zone</label>
              <select value={zone} onChange={(e) => setZone(e.target.value)}
                className="px-3 py-2 rounded-lg border border-border bg-white text-sm">
                <option value="">Any</option>
                {"ABCDEFGHIJ".split("").map((z) => <option key={z} value={z}>Zone {z}</option>)}
              </select>
            </div>
            <button
              type="submit"
              disabled={working}
              className="px-5 py-2.5 rounded-lg bg-ink text-white text-sm font-medium hover:bg-ink-soft transition-colors disabled:opacity-50"
            >
              {working ? "Booking…" : "Book a seat"}
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
