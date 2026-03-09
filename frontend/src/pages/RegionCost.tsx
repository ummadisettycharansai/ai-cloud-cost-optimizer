import { useEffect, useState } from 'react';
import axios from 'axios';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function RegionCost() {
  const [data, setData] = useState<{name: string; value: number}[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get(`${API_BASE}/api/cost-by-region`)
      .then(res => {
        // Transform { "us-east": 150.0 } into array for charts
        const parsed = Object.keys(res.data).map(key => ({
            name: key,
            value: res.data[key]
        })).sort((a,b) => b.value - a.value);
        
        setData(parsed);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to fetch region cost", err);
        setLoading(false);
      });
  }, []);

  return (
    <div className="p-6 max-w-7xl mx-auto w-full">
      <h1 className="text-2xl font-bold mb-6">Multi-Cloud Cost by Region</h1>
      
      {loading ? (
        <div className="flex items-center justify-center p-12">Loading Region Data...</div>
      ) : (
        <div className="bg-surface p-6 rounded-lg border border-zinc-800 w-full h-96">
           <ResponsiveContainer width="100%" height="100%">
             <BarChart data={data} layout="vertical">
               <CartesianGrid strokeDasharray="3 3" stroke="#3f3f46" horizontal={false} />
               <XAxis type="number" tickFormatter={(val) => `$${val}`} stroke="#a1a1aa" />
               <YAxis dataKey="name" type="category" stroke="#a1a1aa" width={100} />
               <Tooltip 
                 contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a' }}
                 itemStyle={{ color: '#e4e4e7' }}
                 formatter={(value: any) => [`$${Number(value).toFixed(2)}`, 'Cost']}
               />
               <Bar dataKey="value" fill="#ec4899" radius={[0, 4, 4, 0]} />
             </BarChart>
           </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
