import { useEffect, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getCandles } from "../lib/api";
import { ema, sma } from "../lib/indicators";

function shortDate(iso) {
  const d = new Date(iso);
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

export default function PriceChart({ symbol }) {
  const [data, setData] = useState([]);
  const [status, setStatus] = useState("loading"); // loading | ok | error
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setStatus("loading");
    getCandles(symbol)
      .then((candles) => {
        if (!active) return;
        const sma20 = sma(candles.close, 20);
        const ema50 = ema(candles.close, 50);
        const rows = candles.dates.map((iso, i) => ({
          date: shortDate(iso),
          close: candles.close[i],
          sma20: sma20[i],
          ema50: ema50[i],
        }));
        setData(rows);
        setStatus("ok");
      })
      .catch((e) => {
        if (active) {
          setError(String(e.message || e));
          setStatus("error");
        }
      });
    return () => {
      active = false;
    };
  }, [symbol]);

  if (status === "loading")
    return <p className="text-sm text-slate-400">Loading chart…</p>;
  if (status === "error")
    return <p className="text-sm text-red-400">Couldn’t load chart: {error}</p>;

  return (
    <div className="h-80 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -8 }}>
          <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
          <XAxis
            dataKey="date"
            stroke="#64748b"
            tick={{ fontSize: 11 }}
            minTickGap={40}
          />
          <YAxis
            stroke="#64748b"
            tick={{ fontSize: 11 }}
            domain={["auto", "auto"]}
            width={56}
          />
          <Tooltip
            contentStyle={{
              background: "#0f172a",
              border: "1px solid #334155",
              borderRadius: 8,
              fontSize: 12,
            }}
            labelStyle={{ color: "#94a3b8" }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Line type="monotone" dataKey="close" name="Close" stroke="#38bdf8" dot={false} strokeWidth={1.6} />
          <Line type="monotone" dataKey="sma20" name="SMA20" stroke="#a78bfa" dot={false} strokeWidth={1.2} />
          <Line type="monotone" dataKey="ema50" name="EMA50" stroke="#f59e0b" dot={false} strokeWidth={1.2} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
