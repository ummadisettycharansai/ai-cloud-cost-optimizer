import { Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Line, ComposedChart } from 'recharts';

interface CostChartProps {
  history: any[];
  // forecast can be: null | ForecastPoint[] | { forecast: ForecastPoint[], eom_projected_spend: number }
  forecast: any;
}

export default function CostChart({ history, forecast }: CostChartProps) {
  // Normalise forecast into a plain array regardless of API response shape
  const forecastArray: any[] = Array.isArray(forecast)
    ? forecast
    : (forecast && Array.isArray(forecast.forecast) ? forecast.forecast : []);

  // Merge history and forecast data for the chart
  const dataMap = new Map<string, any>();

  (history ?? []).forEach((item: any) => {
    dataMap.set(item.date, { date: item.date, actual_cost: item.cost });
  });

  forecastArray.forEach((item: any) => {
    if (dataMap.has(item.date)) {
      dataMap.get(item.date).forecast_cost = item.forecast_cost;
    } else {
      dataMap.set(item.date, { date: item.date, forecast_cost: item.forecast_cost });
    }
  });

  const mergedData = Array.from(dataMap.values()).sort(
    (a: any, b: any) => new Date(a.date).getTime() - new Date(b.date).getTime()
  );

  if (mergedData.length === 0) {
    return (
      <div className="bg-surface border border-zinc-800 rounded-xl p-6 shadow-sm">
        <h3 className="text-lg font-bold mb-4 text-zinc-100">Cost Trend &amp; Forecast</h3>
        <div className="h-[400px] flex items-center justify-center text-zinc-500 text-sm">
          Loading cost data…
        </div>
      </div>
    );
  }

  return (
    <div className="bg-surface border border-zinc-800 rounded-xl p-6 shadow-sm">
      <h3 className="text-lg font-bold mb-6 text-zinc-100">Cost Trend &amp; Forecast</h3>
      <div className="h-[400px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={mergedData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="colorActual" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <XAxis
              dataKey="date"
              stroke="#52525b"
              tick={{ fill: '#a1a1aa', fontSize: 12 }}
              tickMargin={10}
              tickFormatter={(val) => {
                const date = new Date(val);
                return `${date.getMonth() + 1}/${date.getDate()}`;
              }}
            />
            <YAxis
              stroke="#52525b"
              tick={{ fill: '#a1a1aa', fontSize: 12 }}
              tickFormatter={(val) => `$${val}`}
            />
            <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
            <Tooltip
              contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', borderRadius: '8px', color: '#f4f4f5' }}
              itemStyle={{ color: '#e4e4e7' }}
              formatter={(value) => [`$${parseFloat(String(value)).toFixed(2)}`, '']}
            />
            <Area type="monotone" dataKey="actual_cost" name="Actual Cost" stroke="#3b82f6" fillOpacity={1} fill="url(#colorActual)" />
            <Line type="monotone" dataKey="forecast_cost" name="Forecast" stroke="#f59e0b" strokeWidth={2} strokeDasharray="5 5" dot={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
