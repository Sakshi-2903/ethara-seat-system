export default function StatCard({ label, value, tone = "default", eyebrow }) {
  const toneMap = {
    default: "text-ink",
    ok: "text-ok",
    warn: "text-warn",
    hold: "text-hold",
    signal: "text-signal-dark",
  };

  return (
    <div className="card px-5 py-4">
      {eyebrow && (
        <p className="text-[10px] font-semibold tracking-wider uppercase text-slate-light mb-1">
          {eyebrow}
        </p>
      )}
      <p className={`font-display text-3xl font-semibold ${toneMap[tone]}`}>
        {value}
      </p>
      <p className="text-sm text-slate mt-0.5">{label}</p>
    </div>
  );
}
