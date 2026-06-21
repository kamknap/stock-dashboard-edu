import { useEffect, useState } from "react";
import { getCandles } from "../lib/api";

const UP = "#1a7f4b";
const DOWN = "#b3261e";

// Downsample a series to at most `n` evenly spaced points (keeps first + last).
function downsample(values, n) {
  if (values.length <= n) return values;
  const step = (values.length - 1) / (n - 1);
  return Array.from({ length: n }, (_, i) => values[Math.round(i * step)]);
}

// A tiny inline price sparkline driven by real recent closes (not faked).
// Green when the period closed up, red when down.
export default function Sparkline({ symbol, up, width = 76, height = 22 }) {
  const [points, setPoints] = useState(null);

  useEffect(() => {
    let active = true;
    getCandles(symbol, "1mo")
      .then((c) => {
        if (!active) return;
        const closes = (c.close || []).filter((v) => v != null);
        setPoints(downsample(closes, 16));
      })
      .catch(() => active && setPoints([]));
    return () => {
      active = false;
    };
  }, [symbol]);

  if (!points || points.length < 2) {
    return <svg width={width} height={height} aria-hidden="true" />;
  }

  const min = Math.min(...points);
  const max = Math.max(...points);
  const span = max - min || 1;
  const step = width / (points.length - 1);
  const coords = points
    .map((v, i) => {
      const x = (i * step).toFixed(1);
      const y = (height - 1 - ((v - min) / span) * (height - 2)).toFixed(1);
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-hidden="true">
      <polyline
        points={coords}
        fill="none"
        stroke={up ? UP : DOWN}
        strokeWidth="1.6"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}
