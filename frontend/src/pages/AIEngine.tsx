import { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Cpu, DollarSign, Zap, TrendingDown, AlertCircle,
  CheckCircle, Clock, ChevronDown, ChevronUp, Info,
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ─── Types ────────────────────────────────────────────────────────────────────
interface RightsizingRec {
  resource_id: string;
  service_name: string;
  provider: string;
  current_monthly_cost: number;
  current_cpu_utilization: number;
  recommended_instance: string;
  recommended_vcpu: number;
  recommended_memory_gb: number;
  recommended_cost: number;
  estimated_monthly_savings: number;
  confidence_score: number;
  reason: string;
  cross_cloud_equivalent?: Record<string, string>;
}

interface SavingsPlanRec {
  plan_name: string;
  provider: string;
  commitment_type: string;
  commitment_months: number;
  discount_pct: number;
  estimated_monthly_savings: number;
  estimated_annual_savings: number;
  breakeven_months: number;
  confidence_score: number;
  recommended: boolean;
  current_monthly_spend: number;
}

interface AnomalyExplanation {
  date: string;
  actual_cost: number;
  expected_cost: number;
  deviation_pct: number;
  severity: string;
  root_cause: string;
  description: string;
  suggested_actions: string[];
  consecutive_anomaly_days: number;
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function ConfidenceBar({ score }: { score: number }) {
  const color = score >= 70 ? '#22c55e' : score >= 40 ? '#eab308' : '#ef4444';
  return (
    <div className="flex items-center gap-2">
      <div className="w-24 h-1.5 bg-zinc-700 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${score}%`, backgroundColor: color }}
        />
      </div>
      <span className="text-xs text-zinc-400">{score.toFixed(0)}%</span>
    </div>
  );
}

const ROOT_CAUSE_META: Record<string, { icon: string; color: string }> = {
  service_spike:    { icon: '⚡', color: 'text-orange-400' },
  new_resource:     { icon: '🆕', color: 'text-blue-400' },
  sustained_growth: { icon: '📈', color: 'text-yellow-400' },
  unknown:          { icon: '❓', color: 'text-zinc-400' },
};

const SEVERITY_COLOR: Record<string, string> = {
  critical: 'border-red-700 bg-red-900/20',
  high:     'border-orange-700 bg-orange-900/20',
  medium:   'border-yellow-700 bg-yellow-900/20',
  low:      'border-zinc-700 bg-zinc-900/20',
};

const PROVIDER_BADGE: Record<string, string> = {
  AWS:   'bg-orange-500/20 text-orange-300',
  GCP:   'bg-blue-500/20 text-blue-300',
  Azure: 'bg-sky-500/20 text-sky-300',
};

// ─── Page ─────────────────────────────────────────────────────────────────────

type TabId = 'rightsizing' | 'savings' | 'anomalies';

export default function AIEnginePage() {
  const [tab, setTab] = useState<TabId>('rightsizing');
  const [loading, setLoading] = useState(true);

  const [rightsizing, setRightsizing] = useState<RightsizingRec[]>([]);
  const [savings, setSavings] = useState<{ recommendations: SavingsPlanRec[]; summary: any; monthly_spend: number } | null>(null);
  const [anomalies, setAnomalies] = useState<AnomalyExplanation[]>([]);
  const [expandedAnomaly, setExpandedAnomaly] = useState<string | null>(null);
  const [providerFilter, setProviderFilter] = useState('all');

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const [rsRes, spRes, anRes] = await Promise.all([
          axios.get(`${API_BASE}/api/rightsizing`),
          axios.get(`${API_BASE}/api/savings-plans?provider=${providerFilter}`),
          axios.get(`${API_BASE}/api/anomaly-explain`),
        ]);
        setRightsizing(rsRes.data);
        setSavings(spRes.data);
        setAnomalies(anRes.data);
      } catch (err) {
        console.error('AI Engine load error', err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [providerFilter]);

  // Summary stats
  const totalRightsizeSavings = rightsizing.reduce((s, r) => s + r.estimated_monthly_savings, 0);
  const bestSavingsPlan = savings?.recommendations.find(r => r.recommended);
  const criticalAnomalies = anomalies.filter(a => a.severity === 'critical').length;

  const TABS: { id: TabId; label: string; icon: React.ReactNode; count?: number }[] = [
    { id: 'rightsizing', label: 'Right-Sizing',    icon: <Cpu className="w-4 h-4" />,       count: rightsizing.length },
    { id: 'savings',     label: 'Savings Plans',   icon: <DollarSign className="w-4 h-4" />, count: savings?.summary?.recommendation_count },
    { id: 'anomalies',   label: 'Anomaly Insights', icon: <Zap className="w-4 h-4" />,       count: anomalies.length },
  ];

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-zinc-100 flex items-center gap-2">
          <Zap className="w-6 h-6 text-violet-400" /> AI Optimization Engine
        </h1>
        <p className="text-sm text-zinc-500 mt-1">
          ML-powered right-sizing, savings plan analysis, and anomaly root-cause intelligence
        </p>
      </div>

      {/* Summary tiles */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Right-Size Savings/mo', value: `$${totalRightsizeSavings.toLocaleString(undefined, {maximumFractionDigits:0})}`, color: 'text-green-400', icon: <TrendingDown className="w-4 h-4" /> },
          { label: 'Best Annual Commitment', value: bestSavingsPlan ? `$${bestSavingsPlan.estimated_annual_savings.toLocaleString()}` : '—', color: 'text-violet-400', icon: <DollarSign className="w-4 h-4" /> },
          { label: 'Critical Anomalies', value: String(criticalAnomalies), color: criticalAnomalies > 0 ? 'text-red-400' : 'text-green-400', icon: <AlertCircle className="w-4 h-4" /> },
          { label: 'Resources Analysed', value: String(rightsizing.length), color: 'text-teal-400', icon: <Cpu className="w-4 h-4" /> },
        ].map(tile => (
          <div key={tile.label} className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
            <div className="flex items-center gap-2 text-zinc-500 text-xs mb-2">
              {tile.icon} {tile.label}
            </div>
            <p className={`text-2xl font-bold ${tile.color}`}>{tile.value}</p>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-zinc-800 rounded-lg p-1 w-fit">
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              tab === t.id ? 'bg-violet-600 text-white' : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            {t.icon} {t.label}
            {t.count !== undefined && (
              <span className={`text-xs rounded-full px-1.5 py-0.5 ${tab === t.id ? 'bg-violet-800' : 'bg-zinc-700'}`}>
                {t.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16 text-zinc-500 text-sm">
          Running AI analysis…
        </div>
      ) : (
        <>
          {/* ─── RIGHT-SIZING TAB ─────────────────────────────────────────── */}
          {tab === 'rightsizing' && (
            <div>
              {rightsizing.length === 0 ? (
                <div className="bg-zinc-900 border border-zinc-800 rounded-xl py-12 text-center text-zinc-500">
                  <CheckCircle className="w-8 h-8 mx-auto mb-2 opacity-30 text-green-500" />
                  <p className="text-sm">All resources are already optimally sized. 🎉</p>
                </div>
              ) : (
                <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-x-auto">
                  <table className="w-full text-sm min-w-[900px]">
                    <thead>
                      <tr className="border-b border-zinc-800 text-zinc-500 text-xs uppercase tracking-wider">
                        {['Provider', 'Resource', 'CPU %', 'Current Cost', '→ Recommended', 'Savings/mo', 'Confidence', 'Reason'].map(h => (
                          <th key={h} className="text-left px-4 py-3">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-800">
                      {rightsizing.map((r, i) => (
                        <tr key={i} className="hover:bg-zinc-800/50 transition-colors">
                          <td className="px-4 py-3">
                            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${PROVIDER_BADGE[r.provider] ?? ''}`}>
                              {r.provider}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-xs font-mono text-zinc-400 max-w-[140px] truncate">{r.resource_id}</td>
                          <td className="px-4 py-3">
                            <span className={`font-semibold ${r.current_cpu_utilization < 10 ? 'text-red-400' : 'text-yellow-400'}`}>
                              {r.current_cpu_utilization.toFixed(1)}%
                            </span>
                          </td>
                          <td className="px-4 py-3 text-zinc-300">${r.current_monthly_cost.toLocaleString()}</td>
                          <td className="px-4 py-3">
                            <div className="flex flex-col gap-0.5">
                              <span className="font-medium text-teal-400">{r.recommended_instance}</span>
                              <span className="text-xs text-zinc-500">{r.recommended_vcpu}vCPU / {r.recommended_memory_gb}GB → ${r.recommended_cost}/mo</span>
                            </div>
                          </td>
                          <td className="px-4 py-3 font-bold text-green-400">${r.estimated_monthly_savings.toLocaleString()}</td>
                          <td className="px-4 py-3"><ConfidenceBar score={r.confidence_score} /></td>
                          <td className="px-4 py-3 text-xs text-zinc-500 max-w-[160px] leading-relaxed">{r.reason}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* ─── SAVINGS PLANS TAB ────────────────────────────────────────── */}
          {tab === 'savings' && savings && (
            <div className="space-y-4">
              {/* Provider filter */}
              <div className="flex gap-1 bg-zinc-800 rounded-lg p-1 w-fit">
                {['all', 'AWS', 'GCP', 'Azure'].map(p => (
                  <button
                    key={p}
                    onClick={() => setProviderFilter(p)}
                    className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${providerFilter === p ? 'bg-teal-600 text-white' : 'text-zinc-400 hover:text-zinc-200'}`}
                  >
                    {p.toUpperCase()}
                  </button>
                ))}
              </div>

              {/* Summary card */}
              <div className="bg-gradient-to-r from-violet-900/30 to-zinc-900 border border-violet-700/40 rounded-xl p-5">
                <p className="text-xs text-zinc-400 uppercase tracking-wider mb-1">Monthly Cloud Spend</p>
                <p className="text-3xl font-bold text-violet-300">${savings.monthly_spend.toLocaleString()}</p>
                {savings.summary.best_plan !== 'N/A' && (
                  <p className="text-sm text-zinc-400 mt-2">
                    Best plan: <span className="text-violet-300 font-medium">{savings.summary.best_plan}</span>
                    {' '}— saves{' '}
                    <span className="text-green-400 font-bold">${savings.summary.best_annual_savings.toLocaleString()}/yr</span>
                  </p>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {savings.recommendations.map((plan, i) => (
                  <div
                    key={i}
                    className={`bg-zinc-900 border rounded-xl p-5 transition-all ${plan.recommended ? 'border-violet-600 ring-1 ring-violet-600/20' : 'border-zinc-800'}`}
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <p className="font-semibold text-zinc-100 text-sm">{plan.plan_name}</p>
                        <p className="text-xs text-zinc-500 mt-0.5">{plan.commitment_months} month commitment</p>
                      </div>
                      {plan.recommended && (
                        <span className="text-xs bg-violet-700/60 text-violet-300 border border-violet-600 px-2 py-0.5 rounded-full font-medium">
                          ✓ Recommended
                        </span>
                      )}
                    </div>

                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <div>
                        <p className="text-xs text-zinc-500">Discount</p>
                        <p className="font-bold text-green-400 text-lg">{plan.discount_pct}%</p>
                      </div>
                      <div>
                        <p className="text-xs text-zinc-500">Monthly Savings</p>
                        <p className="font-bold text-teal-400 text-lg">${plan.estimated_monthly_savings.toLocaleString()}</p>
                      </div>
                      <div>
                        <p className="text-xs text-zinc-500">Annual Savings</p>
                        <p className="font-semibold text-zinc-200">${plan.estimated_annual_savings.toLocaleString()}</p>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <Clock className="w-3 h-3 text-zinc-500" />
                        <div>
                          <p className="text-xs text-zinc-500">Break-Even</p>
                          <p className="font-semibold text-zinc-200">
                            {plan.breakeven_months === 0 ? 'Immediate' : `${plan.breakeven_months} mo`}
                          </p>
                        </div>
                      </div>
                    </div>

                    <div className="mt-3">
                      <p className="text-xs text-zinc-500 mb-1">Confidence</p>
                      <ConfidenceBar score={plan.confidence_score} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ─── ANOMALY INSIGHTS TAB ─────────────────────────────────────── */}
          {tab === 'anomalies' && (
            <div className="space-y-3">
              {anomalies.length === 0 ? (
                <div className="bg-zinc-900 border border-zinc-800 rounded-xl py-12 text-center text-zinc-500">
                  <CheckCircle className="w-8 h-8 mx-auto mb-2 text-green-500 opacity-50" />
                  <p className="text-sm">No anomalies detected in history. Spend is stable 🎉</p>
                </div>
              ) : (
                anomalies.map((anomaly, i) => {
                  const meta = ROOT_CAUSE_META[anomaly.root_cause] ?? ROOT_CAUSE_META.unknown;
                  const isExpanded = expandedAnomaly === anomaly.date;
                  return (
                    <div
                      key={i}
                      className={`border rounded-xl overflow-hidden transition-all ${SEVERITY_COLOR[anomaly.severity] ?? SEVERITY_COLOR.low}`}
                    >
                      <button
                        onClick={() => setExpandedAnomaly(isExpanded ? null : anomaly.date)}
                        className="w-full flex items-center gap-4 px-5 py-4 text-left hover:bg-white/5 transition-colors"
                      >
                        <span className="text-xl">{meta.icon}</span>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-3 flex-wrap">
                            <span className="font-semibold text-zinc-100">{anomaly.date}</span>
                            <span className={`text-xs capitalize font-medium ${meta.color}`}>
                              {anomaly.root_cause.replace('_', ' ')}
                            </span>
                            <span className="text-xs text-zinc-500 capitalize border border-current/20 rounded px-1.5 py-0.5">
                              {anomaly.severity}
                            </span>
                          </div>
                          <p className="text-sm text-zinc-400 mt-0.5">
                            ${anomaly.actual_cost.toLocaleString()} actual vs ${anomaly.expected_cost.toLocaleString()} expected
                            <span className="text-red-400 font-semibold ml-2">+{anomaly.deviation_pct.toFixed(0)}%</span>
                          </p>
                        </div>
                        {isExpanded ? <ChevronUp className="w-4 h-4 text-zinc-500 shrink-0" /> : <ChevronDown className="w-4 h-4 text-zinc-500 shrink-0" />}
                      </button>

                      {isExpanded && (
                        <div className="px-5 pb-5 space-y-3 border-t border-white/10 pt-4">
                          <div className="flex gap-2">
                            <Info className="w-4 h-4 text-zinc-400 shrink-0 mt-0.5" />
                            <p className="text-sm text-zinc-300 leading-relaxed">{anomaly.description}</p>
                          </div>
                          <div>
                            <p className="text-xs text-zinc-500 uppercase tracking-wider mb-2">Suggested Actions</p>
                            <ul className="space-y-1.5">
                              {anomaly.suggested_actions.map((action, j) => (
                                <li key={j} className="flex items-start gap-2 text-sm text-zinc-400">
                                  <span className="text-violet-400 mt-0.5">›</span>
                                  {action}
                                </li>
                              ))}
                            </ul>
                          </div>
                          {anomaly.consecutive_anomaly_days > 1 && (
                            <p className="text-xs text-yellow-400">
                              ⚠ Anomaly persisted for {anomaly.consecutive_anomaly_days} consecutive days
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
