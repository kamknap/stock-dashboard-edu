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

export default function PriceChart({ symbol, height = 200 }) {
  const [data, setData] = useState([]);
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    let active = true;
    setStatus("loading");
    getCandles(symbol)
      .then((candles) => {
        if (!active) return;
        const sma20 = sma(candles.close, 20);
        const ema50 = ema(candles.close, 50);
        setData(
          candles.dates.map((iso, i) => ({
            date: shortDate(iso),
            close: candles.close[i],
            sma20: sma20[i],
            ema50: ema50[i],
          })),
        );
        setStatus("ok");
      })
      .catch(() => active && setStatus("error"));
    return () => {
      active = false;
    };
  }, [symbol]);

  if (status === "loading")
    return <p className="text-xs text-inksoft">Loading chart…</p>;
  if (status === "error")
    return <p className="text-xs text-down">Chart unavailable.</p>;

  return (
    <div style={{ height }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 6, right: 8, bottom: 0, left: -12 }}>
          <CartesianGrid stroke="#ece7dc" strokeDasharray="3 3" />
          <XAxis dataKey="date" stroke="#9a9488" tick={{ fontSize: 10 }} minTickGap={40} />
          <YAxis stroke="#9a9488" tick={{ fontSize: 10 }} domain={["auto", "auto"]} width={48} />
          <Tooltip
            contentStyle={{
              background: "#ffffff",
              border: "1px solid #e4ded3",
              borderRadius: 6,
              fontSize: 12,
              color: "#141414",
            }}
          />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Line type="monotone" dataKey="close" name="Close" stroke="#141414" dot={false} strokeWidth={1.8} />
          <Line type="monotone" dataKey="sma20" name="SMA20" stroke="#9a7b1f" dot={false} strokeWidth={1.1} />
          <Line type="monotone" dataKey="ema50" name="EMA50" stroke="#8a6d3b" dot={false} strokeWidth={1.1} strokeDasharray="4 2" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
