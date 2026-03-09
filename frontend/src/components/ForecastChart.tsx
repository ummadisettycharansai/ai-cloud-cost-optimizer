/**
 * ForecastChart — Recharts area+line chart showing:
 *   - Historical costs (solid teal line)
 *   - Forecast costs (dashed purple line)
 *   - Confidence band (shaded area between forecast_low and forecast_high)
 */
import {
  ResponsiveContainer, ComposedChart, Area, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine,
} from 'recharts';

interface HistoryPoint {
  date: string;
  cost: number;
}

interface ForecastPoint {
  date: string;
  forecast_cost: number;
  forecast_low?: number;
  forecast_high?: number;
}

interface ForecastChartProps {
  history: HistoryPoint[];
  forecast: ForecastPoint[];
  eomProjected?: number;
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-3 text-xs shadow-xl">
      <p className="font-semibold text-zinc-300 mb-1">{label}</p>
      {payload.map((p: any) => (
        <p key={p.dataKey} style={{ color: p.color }}>
          {p.name}: ${Number(p.value || 0).toLocaleString()}
        </p>
      ))}
    </div>
  );
};

export default function ForecastChart({ history, forecast, eomProjected }: ForecastChartProps) {
  // Merge history and forecast into one unified dataset
  const historySet = new Set(history.map(h => h.date));
  const merged = [
    ...history.map(h => ({ date: formatDate(h.date), actual: h.cost })),
    ...forecast
      .filter(f => !historySet.has(f.date))
      .map(f => ({
        date: formatDate(f.date),
        forecast: f.forecast_cost,
        forecast_low: f.forecast_low,
        forecast_high: f.forecast_high,
      })),
  ];

  const todayLabel = formatDate(new Date().toISOString().slice(0, 10));

  return (
    <div>
      {eomProjected !== undefined && (
        <div className="mb-4 flex items-center gap-3">
          <span className="text-sm text-zinc-400">EOM Projected Spend:</span>
          <span className="text-lg font-bold text-violet-400">
            ${eomProjected.toLocaleString()}
          </span>
        </div>
      )}
      <ResponsiveContainer width="100%" height={320}>
        <ComposedChart data={merged} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
          <XAxis
            dataKey="date"
            tick={{ fill: '#71717a', fontSize: 11 }}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fill: '#71717a', fontSize: 11 }}
            tickFormatter={v => `$${v.toLocaleString()}`}
            width={70}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend wrapperStyle={{ color: '#a1a1aa', fontSize: '12px' }} />

          {/* Today marker */}
          <ReferenceLine x={todayLabel} stroke="#6366f1" strokeDasharray="4 2" label={{ value: 'Today', fill: '#6366f1', fontSize: 10 }} />

          {/* Confidence band */}
          <Area
            dataKey="forecast_high"
            fill="#7c3aed"
            fillOpacity={0.12}
            stroke="none"
            name="Forecast High"
            legendType="none"
          />
          <Area
            dataKey="forecast_low"
            fill="#ffffff"
            fillOpacity={1}
            stroke="none"
            name="Forecast Low"
            legendType="none"
          />

          {/* Actual cost line */}
          <Line
            dataKey="actual"
            stroke="#14b8a6"
            strokeWidth={2}
            dot={false}
            name="Actual Cost"
            connectNulls={false}
          />

          {/* Forecast line */}
          <Line
            dataKey="forecast"
            stroke="#a78bfa"
            strokeWidth={2}
            strokeDasharray="6 3"
            dot={false}
            name="Forecast"
            connectNulls={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
