import { useState, useMemo } from 'react';
import { Lightbulb, DollarSign, TrendingDown, Clock } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import RestrictedCard from '../components/RestrictedCard';

interface Recommendation {
  resource_id: string;
  service_name: string;
  provider?: string;
  recommendation_type: string;
  description: string;
  estimated_savings: number;
  priority?: string;
  roi_score?: number;
  payback_months?: number;
}

interface RecommendationsPageProps {
  recommendations: Recommendation[];
}

const PRIORITY_CONFIG: Record<string, { label: string; className: string; sort: number }> = {
  critical: { label: 'Critical', className: 'bg-red-900/50 text-red-400 border border-red-700', sort: 0 },
  high: { label: 'High', className: 'bg-orange-900/50 text-orange-400 border border-orange-700', sort: 1 },
  medium: { label: 'Medium', className: 'bg-yellow-900/50 text-yellow-400 border border-yellow-700', sort: 2 },
  low: { label: 'Low', className: 'bg-zinc-700/50 text-zinc-400 border border-zinc-600', sort: 3 },
};

const PROVIDER_BADGE: Record<string, string> = {
  AWS: 'bg-orange-500/20 text-orange-300',
  GCP: 'bg-blue-500/20 text-blue-300',
  Azure: 'bg-sky-500/20 text-sky-300',
};

export default function RecommendationsPage({ recommendations }: RecommendationsPageProps) {
  const { permissions } = useAuth();
  const [filter, setFilter] = useState<string>('all');
  const [providerFilter, setProviderFilter] = useState<string>('all');

  const filtered = useMemo(() => {
    return recommendations.filter(r => {
      const matchesPriority = filter === 'all' || r.priority === filter;
      const matchesProvider = providerFilter === 'all' || r.provider === providerFilter;
      return matchesPriority && matchesProvider;
    });
  }, [recommendations, filter, providerFilter]);

  const totalSavings = recommendations.reduce((s, r) => s + (r.estimated_savings ?? 0), 0);
  const avgROI = recommendations.length > 0
    ? recommendations.reduce((s, r) => s + (r.roi_score ?? 0), 0) / recommendations.length
    : 0;

  if (!permissions.canSeeRecommendations) {
    return (
      <div className="p-12 flex items-center justify-center">
        <RestrictedCard title="Recommendations Restricted" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-zinc-100">Optimization Recommendations</h1>
        <p className="text-sm text-zinc-500 mt-1">AI-driven cost reduction opportunities across all cloud providers</p>
      </div>

      {/* Summary tiles */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
          <div className="flex items-center gap-2 text-zinc-500 text-xs mb-2"><Lightbulb className="w-3 h-3" /> Recommendations</div>
          <p className="text-2xl font-bold text-zinc-100">{recommendations.length}</p>
        </div>
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
          <div className="flex items-center gap-2 text-zinc-500 text-xs mb-2"><DollarSign className="w-3 h-3" /> Total Potential Savings</div>
          <p className="text-2xl font-bold text-green-400">
            {permissions.canSeeFinancials ? `$${totalSavings.toLocaleString(undefined, { maximumFractionDigits: 0 })}` : "—"}
          </p>
        </div>
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
          <div className="flex items-center gap-2 text-zinc-500 text-xs mb-2"><TrendingDown className="w-3 h-3" /> Avg ROI Score</div>
          <p className="text-2xl font-bold text-violet-400">{avgROI.toFixed(1)}%</p>
        </div>
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
          <div className="flex items-center gap-2 text-zinc-500 text-xs mb-2">🔴 Critical Actions</div>
          <p className="text-2xl font-bold text-red-400">
            {recommendations.filter(r => r.priority === 'critical').length}
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="flex gap-1 bg-zinc-800 rounded-lg p-1">
          {['all', 'critical', 'high', 'medium', 'low'].map(p => (
            <button
              key={p}
              onClick={() => setFilter(p)}
              className={`px-3 py-1 rounded-md text-xs font-medium capitalize transition-colors ${filter === p ? 'bg-violet-600 text-white' : 'text-zinc-400 hover:text-zinc-200'
                }`}
            >
              {p}
            </button>
          ))}
        </div>
        <div className="flex gap-1 bg-zinc-800 rounded-lg p-1">
          {['all', 'AWS', 'GCP', 'Azure'].map(p => (
            <button
              key={p}
              onClick={() => setProviderFilter(p)}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${providerFilter === p ? 'bg-teal-600 text-white' : 'text-zinc-400 hover:text-zinc-200'
                }`}
            >
              {p}
            </button>
          ))}
        </div>
        <span className="text-xs text-zinc-500 self-center">{filtered.length} of {recommendations.length} shown</span>
      </div>

      {/* Recommendations Table */}
      {filtered.length === 0 ? (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl py-12 text-center text-zinc-500">
          <Lightbulb className="w-8 h-8 mx-auto mb-2 opacity-30" />
          <p className="text-sm">No recommendations match the current filters.</p>
        </div>
      ) : (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-x-auto">
          <table className="w-full text-sm min-w-[860px]">
            <thead>
              <tr className="border-b border-zinc-800 text-zinc-500 text-xs uppercase tracking-wider">
                {['Priority', 'Provider', 'Service', 'Action', 'Description', 'Savings/mo', 'ROI %', 'Payback'].map(h => (
                  <th key={h} className="text-left px-4 py-3">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800">
              {filtered.map((r, i) => {
                const pc = PRIORITY_CONFIG[r.priority ?? 'low'];
                return (
                  <tr key={i} className="hover:bg-zinc-800/50 transition-colors group">
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${pc.className}`}>
                        {pc.label}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {r.provider && (
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${PROVIDER_BADGE[r.provider] ?? 'bg-zinc-700 text-zinc-400'}`}>
                          {r.provider}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs font-mono text-zinc-400">{r.service_name}</td>
                    <td className="px-4 py-3 font-medium text-zinc-200 text-xs">{r.recommendation_type}</td>
                    <td className="px-4 py-3 text-zinc-400 text-xs max-w-[260px] leading-relaxed">{r.description}</td>
                    <td className="px-4 py-3 font-bold text-green-400">
                      {permissions.canSeeFinancials ? `$${r.estimated_savings.toLocaleString()}` : "—"}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`font-semibold ${(r.roi_score ?? 0) >= 50 ? 'text-violet-400' : 'text-zinc-400'}`}>
                        {r.roi_score?.toFixed(1) ?? '—'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-zinc-400 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {r.payback_months !== undefined ? `${r.payback_months}mo` : '—'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
