import { useState, useEffect } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';
import { Bot, Zap, CheckCircle, XCircle, ArrowRight } from 'lucide-react';
import DashboardOverviewComponent from '../components/DashboardOverview';
import CostChart from '../components/CostChart';
import CostByServiceChart from '../components/CostByServiceChart';
import CostByRegionChart from '../components/CostByRegionChart';

import { API_BASE } from '../services/api';

interface AutopilotAction {
  id: number;
  provider: string;
  resource_id: string;
  action: string;
  status: string;
  estimated_savings: number;
  executed_at: string;
}

interface AutopilotPolicy {
  enabled: boolean;
  max_daily_actions: number;
  allowed_actions: string;
}

export default function DashboardOverview({ overview, history, forecast, costByService, resources }: any) {
  const [policy, setPolicy] = useState<AutopilotPolicy | null>(null);
  const [recentActions, setRecentActions] = useState<AutopilotAction[]>([]);

  // Local state for fallback charts
  const [localHistory, setLocalHistory] = useState<any[]>(history || []);
  const [localCostByService, setLocalCostByService] = useState<Record<string, number>>(costByService || {});
  const [localResources, setLocalResources] = useState<any[]>(resources || []);

  useEffect(() => {
    // Check if real history exists
    if (history && history.length > 0) {
      setLocalHistory(history);
      setLocalCostByService(costByService);
      setLocalResources(resources);
      return;
    }

    // Fallback: Use demo data
    axios.get(`${API_BASE}/api/demo-costs`)
      .then(res => {
        const demoData = res.data;

        // 1. Transform for CostTrend Chart
        const histMap = new Map();
        demoData.forEach((item: any) => {
          histMap.set(item.date, (histMap.get(item.date) || 0) + item.cost);
        });
        const mappedHistory = Array.from(histMap.entries()).map(([date, cost]) => ({ date, cost: Number(cost.toFixed(2)) }));
        mappedHistory.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
        setLocalHistory(mappedHistory);

        // 2. Transform for CostByService Chart
        const srvMap: Record<string, number> = {};
        demoData.forEach((item: any) => {
          srvMap[item.service] = (srvMap[item.service] || 0) + item.cost;
        });
        setLocalCostByService(srvMap);

        // 3. Transform for CostByRegion (Mocking resources based on service totals)
        const regions = ['us-east-1', 'eu-west-1', 'ap-south-1', 'us-west-2'];
        const mockResources = Object.entries(srvMap).map(([_, cost], idx) => ({
          region: regions[idx % regions.length],
          monthly_cost: cost
        }));
        setLocalResources(mockResources);
      })
      .catch(err => console.error("Failed to fetch demo costs", err));
  }, [history, costByService, resources]);

  useEffect(() => {
    Promise.all([
      axios.get(`${API_BASE}/api/autopilot/status`).catch(() => null),
      axios.get(`${API_BASE}/api/autopilot/actions?limit=5`).catch(() => null),
    ]).then(([pRes, aRes]) => {
      if (pRes) setPolicy(pRes.data);
      if (aRes) setRecentActions(aRes.data.slice(0, 5));
    });
  }, []);

  const successActions = recentActions.filter(a => a.status === 'success');
  const totalSaved = successActions.reduce((sum, a) => sum + a.estimated_savings, 0);

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto w-full">
      <h1 className="text-2xl font-bold">Cloud Cost Overview</h1>

      {/* KPI Overview Cards */}
      {overview && <DashboardOverviewComponent data={overview} />}

      {/* Cost Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="col-span-1 lg:col-span-2">
          <CostChart history={localHistory} forecast={forecast} />
        </div>
        <div className="col-span-1">
          <CostByServiceChart data={localCostByService} />
        </div>
        <div className="col-span-1 lg:col-span-3">
          <CostByRegionChart data={localResources} />
        </div>
      </div>

      {/* Autopilot Status Panel */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className={`p-2 rounded-lg ${policy?.enabled ? 'bg-emerald-500/10' : 'bg-zinc-800'}`}>
              <Bot className={`w-5 h-5 ${policy?.enabled ? 'text-emerald-400' : 'text-zinc-500'}`} />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-zinc-200">Cost Autopilot</h2>
              <p className="text-xs text-zinc-500">Autonomous waste elimination engine</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className={`flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full font-medium border ${policy?.enabled
              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
              : 'bg-zinc-800 text-zinc-500 border-zinc-700'
              }`}>
              {policy?.enabled
                ? <><CheckCircle className="w-3 h-3" /> Active</>
                : <><XCircle className="w-3 h-3" /> Disabled</>
              }
            </span>
            <Link
              to="/autopilot"
              className="flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
            >
              Manage <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 mb-4">
          <div className="bg-zinc-800/50 rounded-lg p-3">
            <p className="text-xs text-zinc-500 mb-1">Savings Rescued</p>
            <p className="text-lg font-bold text-emerald-400">
              ${(overview?.autopilot_savings || totalSaved).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </p>
          </div>
          <div className="bg-zinc-800/50 rounded-lg p-3">
            <p className="text-xs text-zinc-500 mb-1">Actions Run</p>
            <p className="text-lg font-bold text-zinc-100">{recentActions.length}</p>
          </div>
          <div className="bg-zinc-800/50 rounded-lg p-3">
            <p className="text-xs text-zinc-500 mb-1">Daily Limit</p>
            <p className="text-lg font-bold text-zinc-100">{policy?.max_daily_actions ?? '—'}</p>
          </div>
        </div>

        {recentActions.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs text-zinc-500 uppercase tracking-wider font-medium">Recent Actions</p>
            {recentActions.map(action => (
              <div key={action.id} className="flex items-center justify-between text-xs bg-zinc-800/40 rounded-lg px-3 py-2">
                <div className="flex items-center gap-2">
                  <Zap className="w-3 h-3 text-zinc-500" />
                  <span className="text-zinc-300 font-mono">{action.resource_id}</span>
                  <span className="text-zinc-500">—</span>
                  <span className="text-zinc-400 capitalize">{action.action.replace(/_/g, ' ')}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-emerald-400 font-medium">+${action.estimated_savings.toFixed(2)}</span>
                  <span className={`px-2 py-0.5 rounded-full font-medium ${action.status === 'success' ? 'bg-emerald-500/10 text-emerald-400' :
                    action.status === 'pending' ? 'bg-yellow-500/10 text-yellow-400' :
                      'bg-red-500/10 text-red-400'
                    }`}>
                    {action.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}

        {recentActions.length === 0 && (
          <div className="text-center py-4 text-zinc-600 text-xs">
            {policy?.enabled
              ? 'No actions executed yet. Run Autopilot to eliminate waste.'
              : 'Enable Autopilot to start automatically optimizing your cloud costs.'}
          </div>
        )}
      </div>
    </div>
  );
}
