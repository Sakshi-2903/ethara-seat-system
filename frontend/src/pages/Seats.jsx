import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";

const STATUS_STYLES = {
  available: "bg-ok-bg text-ok",
  occupied: "bg-warn-bg text-warn",
  reserved: "bg-hold-bg text-hold",
  maintenance: "bg-paper-dim text-slate-light",
};

export default function Seats() {
  const { canWrite } = useAuth();
  const [floor, setFloor] = useState("");
  const [zone, setZone] = useState("");
  const [status, setStatus] = useState("");
  const [seats, setSeats] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const params = { limit: "60" };
      if (floor) params.floor = floor;
      if (zone) params.zone = zone;
      if (status) params.status = status;
      const data = await api.listSeats(params);
      setSeats(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [floor, zone, status]);

  async function handleRelease(seat) {
    setMessage(null);
    try {
      await api.releaseSeat({ seat_id: seat.id });
      setMessage(`Seat ${seat.zone}${seat.bay}-${seat.seat_number} released.`);
      load();
    } catch (e) {
      setMessage(e.message);
    }
  }

  return (
    <div className="max-w-6xl mx-auto px-4 md:px-8 py-8">
      <header className="mb-6">
        <p className="text-[11px] font-semibold tracking-wider uppercase text-signal-dark mb-1">
          Floor Plan
        </p>
        <h1 className="font-display text-2xl md:text-3xl font-semibold text-ink">Seat map</h1>
        <p className="text-sm text-slate mt-1">
          {canWrite
            ? "Filter seats by floor, zone, or status. Release a seat to send it back to the available pool."
            : "Filter seats by floor, zone, or status. You have read-only access — contact HR or Admin to release a seat."}
        </p>
      </header>

      <div className="flex flex-wrap gap-3 mb-6">
        <select value={floor} onChange={(e) => setFloor(e.target.value)}
          className="px-4 py-2.5 rounded-lg border border-border bg-white text-sm">
          <option value="">All floors</option>
          {[1, 2, 3, 4, 5].map((f) => (
            <option key={f} value={f}>Floor {f}</option>
          ))}
        </select>
        <select value={zone} onChange={(e) => setZone(e.target.value)}
          className="px-4 py-2.5 rounded-lg border border-border bg-white text-sm">
          <option value="">All zones</option>
          {"ABCDEFGHIJ".split("").map((z) => (
            <option key={z} value={z}>Zone {z}</option>
          ))}
        </select>
        <select value={status} onChange={(e) => setStatus(e.target.value)}
          className="px-4 py-2.5 rounded-lg border border-border bg-white text-sm">
          <option value="">All statuses</option>
          <option value="available">Available</option>
          <option value="occupied">Occupied</option>
          <option value="reserved">Reserved</option>
          <option value="maintenance">Maintenance</option>
        </select>
      </div>

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

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
        {seats.map((seat) => (
          <div key={seat.id} className="card p-4">
            <div className="flex items-start justify-between mb-2">
              <span className="seat-tag font-semibold text-ink text-sm">
                {seat.zone}{seat.bay}-{seat.seat_number}
              </span>
              <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${STATUS_STYLES[seat.status]}`}>
                {seat.status}
              </span>
            </div>
            <p className="text-xs text-slate-light">Floor {seat.floor} · Zone {seat.zone}</p>
            {seat.status === "occupied" && canWrite && (
              <button
                onClick={() => handleRelease(seat)}
                className="mt-3 text-xs font-medium text-warn hover:underline"
              >
                Release seat
              </button>
            )}
          </div>
        ))}
        {!loading && seats.length === 0 && (
          <p className="col-span-full text-sm text-slate-light py-8 text-center">
            No seats match this filter.
          </p>
        )}
      </div>
    </div>
  );
}
