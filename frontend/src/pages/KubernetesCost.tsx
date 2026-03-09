import { useEffect, useState } from 'react';
import axios from 'axios';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function KubernetesCost() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get(`${API_BASE}/api/kubernetes-cost`)
      .then(res => {
        setData(res.data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to fetch k8s cost", err);
        setLoading(false);
      });
  }, []);

  return (
    <div className="p-6 max-w-7xl mx-auto w-full h-full flex flex-col">
      <h1 className="text-2xl font-bold mb-6">Kubernetes Cost Analysis</h1>
      
      {loading ? (
        <div className="flex-1 flex items-center justify-center">Loading Data...</div>
      ) : (
        <div className="grid grid-cols-1 gap-6">
          <div className="bg-surface p-6 rounded-lg border border-zinc-800">
             <h3 className="text-lg font-medium text-zinc-100 mb-4">Cost by Namespace</h3>
             <div className="h-80 w-full">
               <ResponsiveContainer width="100%" height="100%">
                 <BarChart data={data}>
                   <CartesianGrid strokeDasharray="3 3" stroke="#3f3f46" vertical={false} />
                   <XAxis dataKey="namespace" stroke="#a1a1aa" />
                   <YAxis tickFormatter={(val) => `$${val}`} stroke="#a1a1aa" />
                   <Tooltip 
                     contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a' }}
                     itemStyle={{ color: '#e4e4e7' }}
                     formatter={(value: any) => [`$${Number(value).toFixed(2)}`, 'Cost']}
                   />
                   <Bar dataKey="monthly_cost" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                 </BarChart>
               </ResponsiveContainer>
             </div>
          </div>
          
          <div className="bg-surface p-6 rounded-lg border border-zinc-800 overflow-x-auto">
             <h3 className="text-lg font-medium text-zinc-100 mb-4">Namespace Resource Utilization</h3>
             <table className="w-full text-left text-sm text-zinc-400">
                <thead className="bg-zinc-800/50 text-zinc-300">
                    <tr>
                        <th className="px-4 py-3 rounded-tl-md">Namespace</th>
                        <th className="px-4 py-3">Cluster</th>
                        <th className="px-4 py-3 text-right">CPU Util</th>
                        <th className="px-4 py-3 text-right">Mem Util</th>
                        <th className="px-4 py-3 text-right rounded-tr-md">Monthly Cost</th>
                    </tr>
                </thead>
                <tbody>
                    {data.map((ns: any, i) => (
                        <tr key={i} className="border-b border-zinc-800 hover:bg-zinc-800/20">
                            <td className="px-4 py-3 font-medium text-zinc-200">{ns.namespace}</td>
                            <td className="px-4 py-3">{ns.cluster_name}</td>
                            <td className="px-4 py-3 text-right">{ns.cpu_utilization.toFixed(1)}%</td>
                            <td className="px-4 py-3 text-right">{ns.memory_utilization.toFixed(1)}%</td>
                            <td className="px-4 py-3 text-right text-primary font-medium">${ns.monthly_cost.toFixed(2)}</td>
                        </tr>
                    ))}
                </tbody>
             </table>
          </div>
        </div>
      )}
    </div>
  );
}
