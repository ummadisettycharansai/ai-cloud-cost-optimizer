import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function CostByRegionChart({ data }: { data: any[] }) {
  if (!data || data.length === 0) {
     return null;
  }

  // Aggregate costs by region
  const regionMap = new Map();
  data.forEach(resource => {
    const region = resource.region || 'Unknown';
    const cost = resource.monthly_cost || 0;
    
    if (regionMap.has(region)) {
        regionMap.set(region, regionMap.get(region) + cost);
    } else {
        regionMap.set(region, cost);
    }
  });

  const chartData = Array.from(regionMap.entries())
    .map(([region, cost]) => ({
      region,
      cost: Number(cost.toFixed(2))
    }))
    .sort((a, b) => b.cost - a.cost); // Sort descending

  return (
    <div className="bg-surface border border-zinc-800 rounded-xl p-6 shadow-sm h-full">
      <h3 className="text-lg font-bold mb-6 text-zinc-100">Cost by Region</h3>
      <div className="h-[300px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" stroke="#27272a" horizontal={false} />
            <XAxis 
              type="number"
              stroke="#52525b" 
              tick={{fill: '#a1a1aa', fontSize: 12}}
              tickFormatter={(val) => `$${val}`}
            />
            <YAxis 
              dataKey="region" 
              type="category"
              stroke="#52525b" 
              tick={{fill: '#a1a1aa', fontSize: 12}}
              width={100}
            />
            <Tooltip 
              contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', borderRadius: '8px', color: '#f4f4f5' }}
              itemStyle={{ color: '#e4e4e7' }}
              formatter={(value) => [`$${parseFloat(String(value)).toFixed(2)}`, 'Cost']}
              cursor={{fill: '#27272a'}}
            />
            <Bar dataKey="cost" fill="#8b5cf6" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
