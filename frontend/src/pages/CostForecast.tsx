import { useState, useEffect } from 'react';
import axios from 'axios';
import { TrendingUp } from 'lucide-react';
import ForecastChart from '../components/ForecastChart';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

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

interface ForecastResponse {
  forecast: ForecastPoint[];
  eom_projected_spend: number;
  model_used: string;
}

const HORIZON_OPTIONS = [
  { label: '30 days', value: 30 },
  { label: '60 days', value: 60 },
  { label: '90 days', value: 90 },
];

export default function CostForecastPage() {
  const [history, setHistory] = useState<HistoryPoint[]>([]);
  const [forecastData, setForecastData] = useState<ForecastResponse | null>(null);
  const [horizon, setHorizon] = useState(30);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const [hRes, fRes] = await Promise.all([
          axios.get(`${API_BASE}/api/cost-history`),
          axios.get(`${API_BASE}/api/forecast?days=${horizon}`),
        ]);
        setHistory(hRes.data);
        // Handle both old (array) and new (object) response shapes
        if (Array.isArray(fRes.data)) {
          setForecastData({ forecast: fRes.data, eom_projected_spend: 0, model_used: 'prophet' });
        } else {
          setForecastData(fRes.data);
        }
      } catch (err) {
        console.error('Forecast load error', err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [horizon]);

  const forecast = forecastData?.forecast ?? [];
  const eom = forecastData?.eom_projected_spend ?? 0;
  const modelUsed = forecastData?.model_used ?? 'unknown';

  // Summary stats
  const avgForecast = forecast.length > 0
    ? forecast.reduce((s, f) => s + f.forecast_cost, 0) / forecast.length
    : 0;
  const peakForecast = forecast.length > 0
    ? Math.max(...forecast.map(f => f.forecast_high ?? f.forecast_cost))
    : 0;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-zinc-100">Cost Forecast</h1>
          <p className="text-sm text-zinc-500 mt-1">AI-driven spending projections with confidence intervals</p>
        </div>
        {/* Horizon switcher */}
        <div className="flex gap-1 bg-zinc-800 rounded-lg p-1">
          {HORIZON_OPTIONS.map(opt => (
            <button
              key={opt.value}
              onClick={() => setHorizon(opt.value)}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                horizon === opt.value
                  ? 'bg-violet-600 text-white'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'EOM Projected Spend', value: `$${eom.toLocaleString()}`, color: 'text-violet-400', icon: '📅' },
          { label: 'Avg Daily Forecast', value: `$${avgForecast.toLocaleString(undefined, { maximumFractionDigits: 0 })}`, color: 'text-teal-400', icon: '📊' },
          { label: 'Peak Forecast', value: `$${peakForecast.toLocaleString(undefined, { maximumFractionDigits: 0 })}`, color: 'text-orange-400', icon: '📈' },
          { label: 'Model', value: modelUsed.charAt(0).toUpperCase() + modelUsed.slice(1), color: 'text-zinc-300', icon: '🤖' },
        ].map(card => (
          <div key={card.label} className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
            <div className="text-xl mb-1">{card.icon}</div>
            <p className="text-xs text-zinc-500 uppercase tracking-wider">{card.label}</p>
            <p className={`text-xl font-bold mt-1 ${card.color}`}>{card.value}</p>
          </div>
        ))}
      </div>

      {/* Chart */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp className="w-4 h-4 text-violet-400" />
          <h2 className="text-sm font-semibold text-zinc-300">Historical + {horizon}-Day Forecast</h2>
          <div className="ml-auto flex items-center gap-4 text-xs text-zinc-500">
            <span className="flex items-center gap-1.5">
              <span className="inline-block w-6 h-0.5 bg-teal-400"></span> Actual
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block w-6 h-0.5 bg-violet-400 border-dashed border-t border-violet-400"></span> Forecast
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block w-6 h-3 bg-violet-500/20 rounded-sm"></span> Confidence Band
            </span>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-64 text-zinc-500 text-sm">
            Computing forecast…
          </div>
        ) : (
          <ForecastChart
            history={history}
            forecast={forecast}
            eomProjected={eom}
          />
        )}
      </div>

      {/* Forecast data table */}
      {forecast.length > 0 && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
          <div className="px-5 py-3 border-b border-zinc-800">
            <h2 className="text-sm font-semibold text-zinc-300">Forecast Details (next {Math.min(14, forecast.length)} days)</h2>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800 text-zinc-500 text-xs uppercase tracking-wider">
                {['Date', 'Forecast', 'Low', 'High', 'Spread'].map(h => (
                  <th key={h} className="text-left px-4 py-3">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800">
              {forecast.slice(0, 14).map(f => {
                const low = f.forecast_low ?? f.forecast_cost * 0.9;
                const high = f.forecast_high ?? f.forecast_cost * 1.1;
                const spread = high - low;
                return (
                  <tr key={f.date} className="hover:bg-zinc-800/50 transition-colors">
                    <td className="px-4 py-2.5 text-zinc-400">{f.date}</td>
                    <td className="px-4 py-2.5 font-medium text-violet-300">${f.forecast_cost.toLocaleString()}</td>
                    <td className="px-4 py-2.5 text-green-400">${low.toFixed(0)}</td>
                    <td className="px-4 py-2.5 text-red-400">${high.toFixed(0)}</td>
                    <td className="px-4 py-2.5 text-zinc-500">${spread.toFixed(0)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
