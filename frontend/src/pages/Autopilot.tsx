import { useState, useEffect } from 'react';
import axios from 'axios';
import { Bot, Power, Zap, Play, Activity } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

import { API_BASE } from '../services/api';

interface AutopilotPolicy {
  id: number;
  org_id: number;
  enabled: boolean;
  max_daily_actions: number;
  allowed_actions: string;
}

interface AutopilotAction {
  id: number;
  org_id: number;
  provider: string;
  resource_id: string;
  action: string;
  status: string;
  estimated_savings: number;
  executed_at: string;
}

export default function AutopilotPage() {
  const [policy, setPolicy] = useState<AutopilotPolicy | null>(null);
  const [actions, setActions] = useState<AutopilotAction[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const { isAdminOrFinance } = useAuth();

  const loadData = async () => {
    try {
      const [pRes, aRes] = await Promise.all([
        axios.get(`${API_BASE}/api/autopilot/status`),
        axios.get(`${API_BASE}/api/autopilot/actions`)
      ]);
      setPolicy(pRes.data);
      setActions(aRes.data);
    } catch (err) {
      console.error('Failed to load autopilot data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const toggleStatus = async () => {
    if (!isAdminOrFinance) return;
    try {
      const endpoint = policy?.enabled ? '/api/autopilot/disable' : '/api/autopilot/enable';
      const res = await axios.post(`${API_BASE}${endpoint}`);
      setPolicy(res.data);
    } catch (err) {
      console.error('Failed to toggle autopilot status', err);
    }
  };

  const runManual = async () => {
    if (!isAdminOrFinance || !policy?.enabled) return;
    setRunning(true);
    try {
      await axios.post(`${API_BASE}/api/autopilot/run`);
      await loadData();
    } catch (err) {
      console.error('Failed to run autopilot', err);
    } finally {
      setRunning(false);
    }
  };

  const totalSaved = actions
    .filter(a => a.status === 'success')
    .reduce((sum, a) => sum + a.estimated_savings, 0);

  if (loading) return <div className="p-6 text-zinc-400">Loading Autopilot engine...</div>;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Bot className="w-6 h-6 text-indigo-400" />
            <h1 className="text-2xl font-bold text-zinc-100">Cost Autopilot</h1>
          </div>
          <p className="text-sm text-zinc-500">Autonomous remediation engine and safe waste elimination.</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={runManual}
            disabled={!policy?.enabled || running || !isAdminOrFinance}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              !policy?.enabled || !isAdminOrFinance
                ? 'bg-zinc-800 text-zinc-600 cursor-not-allowed'
                : 'bg-zinc-800 hover:bg-zinc-700 text-zinc-300 border border-zinc-700'
            }`}
          >
            {running ? <Activity className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            {running ? 'Executing...' : 'Run Now'}
          </button>
          
          <button
            onClick={toggleStatus}
            disabled={!isAdminOrFinance}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              !isAdminOrFinance ? 'opacity-50 cursor-not-allowed' : ''
            } ${
              policy?.enabled 
                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20'
                : 'bg-zinc-800 text-zinc-400 border border-zinc-700 hover:bg-zinc-700'
            }`}
          >
            <Power className="w-4 h-4" />
            {policy?.enabled ? 'Autopilot Active' : 'Enable Autopilot'}
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-indigo-500/10 rounded-lg">
              <Zap className="w-5 h-5 text-indigo-400" />
            </div>
            <h3 className="text-zinc-400 text-sm font-medium">Actions Executed</h3>
          </div>
          <p className="text-2xl font-semibold text-zinc-100">{actions.length}</p>
        </div>
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-emerald-500/10 rounded-lg">
              <Bot className="w-5 h-5 text-emerald-400" />
            </div>
            <h3 className="text-zinc-400 text-sm font-medium">Autopilot Savings</h3>
          </div>
          <p className="text-2xl font-semibold text-zinc-100">${totalSaved.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
        </div>
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-zinc-800 rounded-lg">
              <Activity className="w-5 h-5 text-zinc-400" />
            </div>
            <h3 className="text-zinc-400 text-sm font-medium">Daily Limit</h3>
          </div>
          <p className="text-2xl font-semibold text-zinc-100">{policy?.max_daily_actions || 0}</p>
        </div>
      </div>

      {/* Allowed Actions Notice */}
      <div className="bg-indigo-900/20 border border-indigo-500/20 rounded-xl p-4 flex gap-3">
        <Bot className="w-5 h-5 text-indigo-400 shrink-0" />
        <div>
          <h4 className="text-sm font-medium text-indigo-300">Safety Policy Info</h4>
          <p className="text-xs text-indigo-200/70 mt-1">
            When enabled, the remediation engine automatically executes high-confidence recommendations matching these allowed types: <span className="font-mono bg-indigo-950 px-1 py-0.5 rounded text-indigo-300">{policy?.allowed_actions || 'None'}</span>
          </p>
        </div>
      </div>

      {/* Action Event Log */}
      <div>
        <h2 className="text-sm font-semibold text-zinc-400 mb-3 uppercase tracking-wider">Execution Log</h2>
        {actions.length === 0 ? (
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl py-12 text-center text-zinc-500 text-sm">
            <Power className="w-8 h-8 mx-auto mb-2 opacity-30" />
            <p>No automatic operations have run yet.</p>
          </div>
        ) : (
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-800 text-zinc-500 text-xs uppercase tracking-wider bg-zinc-900/50">
                  <th className="text-left px-4 py-3">Time</th>
                  <th className="text-left px-4 py-3">Provider</th>
                  <th className="text-left px-4 py-3">Resource</th>
                  <th className="text-left px-4 py-3">Action</th>
                  <th className="text-left px-4 py-3">Savings</th>
                  <th className="text-left px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800">
                {actions.map(a => (
                  <tr key={a.id} className="hover:bg-zinc-800/50 transition-colors">
                    <td className="px-4 py-3 text-zinc-400 whitespace-nowrap">
                      {new Date(a.executed_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-zinc-300">{a.provider}</td>
                    <td className="px-4 py-3 text-zinc-300 font-mono text-xs">{a.resource_id}</td>
                    <td className="px-4 py-3">
                      <span className="text-xs px-2 py-0.5 rounded bg-zinc-800 border border-zinc-700 text-zinc-300 capitalize">
                        {a.action.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-emerald-400 font-medium">
                      +${a.estimated_savings.toFixed(2)}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                        a.status === 'success' ? 'bg-emerald-500/10 text-emerald-400' : 
                        a.status === 'pending' ? 'bg-yellow-500/10 text-yellow-400' : 
                        'bg-red-500/10 text-red-400'
                      }`}>
                        {a.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
