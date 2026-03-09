import { useState, useEffect } from 'react';
import axios from 'axios';
import { DollarSign, AlertTriangle, PlusCircle, ChevronDown, ChevronUp } from 'lucide-react';
import BudgetGauge from '../components/BudgetGauge';
import { useAuth } from '../context/AuthContext';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface Budget {
  id: number;
  name: string;
  monthly_limit: number;
  alert_threshold_pct: number;
  cloud_provider: string;
  org_id: number;
  project_id: number | null;
  active: boolean;
  period_start: string;
}

interface BudgetAlert {
  budget_id: number;
  budget_name: string;
  monthly_limit: number;
  current_spend: number;
  utilization_pct: number;
  forecast_eom: number;
  severity: string;
  cloud_provider?: string;
}

const SEVERITY_BADGE: Record<string, string> = {
  critical: 'bg-red-900/50 text-red-400 border border-red-700',
  warning:  'bg-orange-900/50 text-orange-400 border border-orange-700',
  info:     'bg-yellow-900/50 text-yellow-400 border border-yellow-700',
  ok:       'bg-green-900/50 text-green-400 border border-green-700',
};

const PROVIDER_COLORS: Record<string, string> = {
  AWS:   'bg-orange-500/20 text-orange-300',
  GCP:   'bg-blue-500/20 text-blue-300',
  Azure: 'bg-sky-500/20 text-sky-300',
  All:   'bg-zinc-500/20 text-zinc-300',
};

export default function BudgetsPage() {
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [alerts, setAlerts] = useState<BudgetAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const { isAdminOrFinance } = useAuth();

  // Create form state
  const [form, setForm] = useState({
    name: '', org_id: 1, monthly_limit: '', alert_threshold_pct: 0.80,
    cloud_provider: 'All', project_id: '',
  });

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const [bRes, aRes] = await Promise.all([
          axios.get(`${API_BASE}/api/budgets`),
          axios.get(`${API_BASE}/api/budget-alerts`),
        ]);
        setBudgets(bRes.data);
        setAlerts(aRes.data);
      } catch (err) {
        console.error('Failed to load budgets', err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const getAlertForBudget = (id: number): BudgetAlert | undefined =>
    alerts.find(a => a.budget_id === id);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await axios.post(`${API_BASE}/api/budgets`, {
        name: form.name,
        org_id: Number(form.org_id),
        monthly_limit: Number(form.monthly_limit),
        alert_threshold_pct: Number(form.alert_threshold_pct),
        cloud_provider: form.cloud_provider,
        project_id: form.project_id ? Number(form.project_id) : null,
      });
      // Refetch
      const [bRes, aRes] = await Promise.all([
        axios.get(`${API_BASE}/api/budgets`),
        axios.get(`${API_BASE}/api/budget-alerts`),
      ]);
      setBudgets(bRes.data);
      setAlerts(aRes.data);
      setShowForm(false);
      setForm({ name: '', org_id: 1, monthly_limit: '', alert_threshold_pct: 0.80, cloud_provider: 'All', project_id: '' });
    } catch (err) {
      console.error('Failed to create budget', err);
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-100">Budget Management</h1>
          <p className="text-sm text-zinc-500 mt-1">Monitor monthly spending limits and threshold alerts</p>
        </div>
        {isAdminOrFinance && (
          <button
            onClick={() => setShowForm(v => !v)}
            className="flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-sm font-medium transition-colors"
          >
            <PlusCircle className="w-4 h-4" />
            New Budget
            {showForm ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        )}
      </div>

      {/* Alert Banner */}
      {alerts.filter(a => a.severity === 'critical').length > 0 && (
        <div className="flex items-center gap-3 px-4 py-3 bg-red-900/30 border border-red-700/50 rounded-lg">
          <AlertTriangle className="w-5 h-5 text-red-400 shrink-0" />
          <p className="text-sm text-red-300">
            <span className="font-semibold">{alerts.filter(a => a.severity === 'critical').length} budget(s) have exceeded their monthly limit.</span>
            {' '}Immediate action required.
          </p>
        </div>
      )}

      {/* Create Budget Form */}
      {showForm && (
        <form onSubmit={handleCreate} className="bg-zinc-900 border border-zinc-700 rounded-xl p-5 grid grid-cols-2 gap-4">
          <h2 className="col-span-2 text-sm font-semibold text-zinc-300 mb-1">Create New Budget</h2>
          {[
            { label: 'Budget Name', key: 'name', type: 'text', placeholder: 'e.g. Q1 AWS Budget' },
            { label: 'Monthly Limit (USD)', key: 'monthly_limit', type: 'number', placeholder: '5000' },
            { label: 'Org ID', key: 'org_id', type: 'number', placeholder: '1' },
            { label: 'Alert Threshold (%)', key: 'alert_threshold_pct', type: 'number', placeholder: '0.80' },
          ].map(({ label, key, type, placeholder }) => (
            <div key={key}>
              <label className="text-xs text-zinc-400 block mb-1">{label}</label>
              <input
                type={type}
                placeholder={placeholder}
                value={(form as any)[key]}
                onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                className="w-full bg-zinc-800 border border-zinc-600 rounded-lg px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-violet-500"
                required={key !== 'project_id'}
              />
            </div>
          ))}
          <div>
            <label className="text-xs text-zinc-400 block mb-1">Cloud Provider</label>
            <select
              value={form.cloud_provider}
              onChange={e => setForm(f => ({ ...f, cloud_provider: e.target.value }))}
              className="w-full bg-zinc-800 border border-zinc-600 rounded-lg px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-violet-500"
            >
              {['All', 'AWS', 'GCP', 'Azure'].map(p => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          </div>
          <div className="col-span-2 flex gap-3 mt-2">
            <button type="submit" className="px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-sm font-medium transition-colors">
              Create Budget
            </button>
            <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 text-zinc-300 rounded-lg text-sm font-medium transition-colors">
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Gauge Grid */}
      {budgets.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-zinc-400 mb-3 uppercase tracking-wider">Utilization Overview</h2>
          <div className="flex flex-wrap gap-4">
            {budgets.map(b => {
              const alert = getAlertForBudget(b.id);
              return (
                <div key={b.id} className="bg-zinc-900 border border-zinc-800 rounded-xl">
                  <BudgetGauge
                    utilization={alert?.utilization_pct ?? 0}
                    label={b.name}
                    limit={b.monthly_limit}
                    spent={alert?.current_spend ?? 0}
                  />
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Budget Table */}
      <div>
        <h2 className="text-sm font-semibold text-zinc-400 mb-3 uppercase tracking-wider">All Budgets</h2>
        {loading ? (
          <div className="text-zinc-500 text-sm py-8 text-center">Loading budgets…</div>
        ) : budgets.length === 0 ? (
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl py-12 text-center text-zinc-500">
            <DollarSign className="w-8 h-8 mx-auto mb-2 opacity-30" />
            <p className="text-sm">No budgets configured yet. Create your first budget above.</p>
          </div>
        ) : (
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-800 text-zinc-500 text-xs uppercase tracking-wider">
                  {['Name', 'Provider', 'Monthly Limit', 'Spent', 'Utilization', 'EOM Forecast', 'Status'].map(h => (
                    <th key={h} className="text-left px-4 py-3">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800">
                {budgets.map(b => {
                  const alert = getAlertForBudget(b.id);
                  const severity = alert?.severity ?? 'ok';
                  const spent = alert?.current_spend ?? 0;
                  const utilPct = alert?.utilization_pct ?? 0;
                  const eom = alert?.forecast_eom ?? 0;
                  return (
                    <tr key={b.id} className="hover:bg-zinc-800/50 transition-colors">
                      <td className="px-4 py-3 font-medium text-zinc-200">{b.name}</td>
                      <td className="px-4 py-3">
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${PROVIDER_COLORS[b.cloud_provider] ?? PROVIDER_COLORS.All}`}>
                          {b.cloud_provider}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-zinc-300">${b.monthly_limit.toLocaleString()}</td>
                      <td className="px-4 py-3 text-zinc-300">${spent.toLocaleString()}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className="w-20 h-1.5 bg-zinc-700 rounded-full overflow-hidden">
                            <div
                              className="h-full rounded-full transition-all"
                              style={{
                                width: `${Math.min(utilPct, 100)}%`,
                                backgroundColor: utilPct >= 100 ? '#ef4444' : utilPct >= 80 ? '#f97316' : '#22c55e',
                              }}
                            />
                          </div>
                          <span className="text-zinc-400 text-xs">{utilPct.toFixed(1)}%</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-zinc-300">${eom.toLocaleString()}</td>
                      <td className="px-4 py-3">
                        <span className={`text-xs px-2 py-1 rounded-full font-medium capitalize ${SEVERITY_BADGE[severity]}`}>
                          {severity}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
