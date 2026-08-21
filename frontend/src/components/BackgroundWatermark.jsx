/**
 * Subtle, repeated Ethara mark in the background of a page. Sits behind all
 * content (relies on normal DOM stacking order — rendered first, no z-index
 * needed) and never intercepts clicks.
 */
export default function BackgroundWatermark({ opacity = 0.05 }) {
  return (
    <div
      aria-hidden="true"
      className="fixed inset-0 pointer-events-none"
      style={{
        backgroundImage: "url(/logo-watermark.png)",
        backgroundRepeat: "repeat",
        backgroundSize: "130px 130px",
        opacity,
      }}
    />
  );
}