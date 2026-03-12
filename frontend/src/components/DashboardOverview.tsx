import { DollarSign, Activity, AlertCircle, CloudLightning } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function DashboardOverview({ data }: { data: any }) {
  const { permissions } = useAuth();

  const formatCost = (val: number) => {
    if (!permissions.canSeeFinancials) return "—";
    return `$${val.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
  };

  const cards = [
    {
      title: "Total Monthly Cost",
      value: formatCost(data.total_monthly_cost),
      subtitle: permissions.canSeeFinancials ? `${data.cost_change_percentage}% from last month` : "Data restricted",
      icon: <DollarSign className="w-6 h-6 text-primary" />
    },
    {
      title: "Active Resources",
      value: data.active_resources,
      subtitle: "Across 4 regions",
      icon: <Activity className="w-6 h-6 text-success" />
    },
    {
      title: "Cost Anomalies",
      value: data.detected_anomalies_count,
      subtitle: "Requires attention",
      icon: <AlertCircle className="w-6 h-6 text-danger" />
    },
    {
      title: "Autopilot Savings",
      value: formatCost(data.autopilot_savings || 0),
      subtitle: permissions.canSeeFinancials ? "Rescued automatically" : "Data restricted",
      icon: <CloudLightning className="w-6 h-6 text-emerald-400" />
    }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((c, i) => (
        <div key={i} className="bg-surface border border-zinc-800 rounded-xl p-5 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex justify-between items-start mb-4">
            <div>
              <p className="text-sm text-zinc-400 font-medium">{c.title}</p>
              <h3 className="text-2xl font-bold mt-1 text-zinc-100">{c.value}</h3>
            </div>
            <div className="p-2 bg-zinc-900 rounded-lg">
              {c.icon}
            </div>
          </div>
          <p className="text-xs text-zinc-500">{c.subtitle}</p>
        </div>
      ))}
    </div>
  );
}
