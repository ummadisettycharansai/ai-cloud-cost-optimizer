import { useEffect, useState } from 'react';
import axios from 'axios';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';

import { API_BASE } from '../services/api';
const COLORS = ['#3b82f6', '#ec4899', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#6366f1'];

export default function ServiceCost() {
  const [data, setData] = useState<{name: string; value: number}[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get(`${API_BASE}/api/cost-by-service`)
      .then(res => {
         const parsed = Object.keys(res.data).map(key => ({
            name: key,
            value: res.data[key]
        })).sort((a,b) => b.value - a.value);
        
        setData(parsed);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to fetch service cost", err);
        setLoading(false);
      });
  }, []);

  return (
    <div className="p-6 max-w-7xl mx-auto w-full">
      <h1 className="text-2xl font-bold mb-6">Cost by Cloud Service</h1>
      
      {loading ? (
        <div className="flex items-center justify-center p-12">Loading Service Cost Data...</div>
      ) : (
        <div className="bg-surface p-6 rounded-lg border border-zinc-800 w-full h-96 flex flex-col items-center">
           <ResponsiveContainer width="100%" height="85%">
             <PieChart>
               <Pie
                 data={data}
                 cx="50%"
                 cy="50%"
                 innerRadius={60}
                 outerRadius={100}
                 paddingAngle={5}
                 dataKey="value"
               >
                 {data.map((_, index) => (
                   <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                 ))}
               </Pie>
               <Tooltip 
                 contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a' }}
                 itemStyle={{ color: '#e4e4e7' }}
                 formatter={(value: any) => [`$${Number(value).toFixed(2)}`, 'Cost']}
               />
               <Legend verticalAlign="bottom" height={36}/>
             </PieChart>
           </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
