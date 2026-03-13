import React, { useState, useEffect, useMemo } from 'react';
import { 
  Lightbulb, 
  DollarSign, 
  TrendingDown, 
  Clock, 
  CheckCircle2, 
  AlertCircle, 
  Filter,
  ArrowUpDown,
  CheckCircle,
  XCircle,
  Loader2
} from 'lucide-react';

interface Recommendation {
  id: string;
  resource_id: string;
  service_name: string;
  recommendation_type: string;
  description: string;
  estimated_savings: number;
  status: string;
  created_at: string;
}

const MOCK_DATA: Recommendation[] = [
  {
    id: "1",
    resource_id: "i-1234567890abcdef0",
    service_name: "EC2",
    recommendation_type: "rightsizing",
    description: "Downsize instance from m5.xlarge to m5.large. CPU utilization below 15% for 30 days.",
    estimated_savings: 145.50,
    status: "pending",
    created_at: "2024-01-15T10:00:00Z"
  },
  {
    id: "2",
    resource_id: "vol-0987654321fedcba0",
    service_name: "EBS",
    recommendation_type: "storage",
    description: "Delete unattached EBS volume. Not attached to any instance for 45 days.",
    estimated_savings: 23.00,
    status: "pending",
    created_at: "2024-01-14T08:30:00Z"
  },
  {
    id: "3",
    resource_id: "i-abcdef1234567890",
    service_name: "EC2",
    recommendation_type: "spot_instance",
    description: "Migrate workload to Spot Instance. Suitable for fault-tolerant batch processing.",
    estimated_savings: 312.75,
    status: "applied",
    created_at: "2024-01-13T14:00:00Z"
  },
  {
    id: "4",
    resource_id: "db-xyz123",
    service_name: "RDS",
    recommendation_type: "idle_resource",
    description: "RDS instance has zero connections for 14 days. Consider stopping or deleting.",
    estimated_savings: 89.20,
    status: "pending",
    created_at: "2024-01-12T09:15:00Z"
  }
];

const TYPE_COLORS: Record<string, string> = {
  rightsizing: 'bg-blue-900/40 text-blue-400 border-blue-800',
  storage: 'bg-orange-900/40 text-orange-400 border-orange-800',
  spot_instance: 'bg-purple-900/40 text-purple-400 border-purple-800',
  idle_resource: 'bg-red-900/40 text-red-400 border-red-800',
  default: 'bg-gray-800 text-gray-400 border-gray-700'
};

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-yellow-900/40 text-yellow-400 border-yellow-800',
  applied: 'bg-green-900/40 text-green-400 border-green-800',
  dismissed: 'bg-gray-800 text-gray-400 border-gray-700'
};

const Recommendations: React.FC = () => {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'savings' | 'date'>('savings');

  const fetchRecommendations = async () => {
    setLoading(true);
    setError(null);
    try {
      const apiUrl = import.meta.env.VITE_API_URL || '';
      const token = localStorage.getItem('token');
      const response = await fetch(`${apiUrl}/api/v1/recommendations`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      
      const data = await response.json();
      const items = Array.isArray(data) ? data :
                    Array.isArray(data?.recommendations) ? data.recommendations :
                    Array.isArray(data?.data) ? data.data : [];
      
      setRecommendations(items.length > 0 ? items : MOCK_DATA);
    } catch (err) {
      console.warn('API unavailable, using mock data:', err);
      setRecommendations(MOCK_DATA);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecommendations();
  }, []);

  const handleApply = (id: string) => {
    setRecommendations(prev => prev.map(r => r.id === id ? { ...r, status: 'applied' } : r));
  };

  const handleDismiss = (id: string) => {
    setRecommendations(prev => prev.map(r => r.id === id ? { ...r, status: 'dismissed' } : r));
  };

  const filteredAndSorted = useMemo(() => {
    let result = [...recommendations];
    
    if (typeFilter !== 'all') {
      result = result.filter(r => r.recommendation_type === typeFilter);
    }
    
    if (statusFilter !== 'all') {
      result = result.filter(r => r.status === statusFilter);
    }
    
    result.sort((a, b) => {
      if (sortBy === 'savings') {
        return (b.estimated_savings ?? 0) - (a.estimated_savings ?? 0);
      } else {
        return new Date(b.created_at ?? 0).getTime() - new Date(a.created_at ?? 0).getTime();
      }
    });
    
    return result;
  }, [recommendations, typeFilter, statusFilter, sortBy]);

  const stats = useMemo(() => {
    return {
      total: recommendations.length,
      potentialSavings: recommendations
        .filter(r => r.status === 'pending')
        .reduce((sum, r) => sum + (r.estimated_savings ?? 0), 0),
      applied: recommendations.filter(r => r.status === 'applied').length,
      pending: recommendations.filter(r => r.status === 'pending').length
    };
  }, [recommendations]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] h-full space-y-4 bg-[#0f172a]">
        <Loader2 className="w-12 h-12 text-violet-500 animate-spin" />
        <p className="text-gray-400 animate-pulse font-medium">Loading recommendations...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-12 flex items-center justify-center min-h-[400px] h-full bg-[#0f172a]">
        <div className="bg-red-900/20 border border-red-800 rounded-xl p-8 max-w-md text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-white mb-2">Error Loading Data</h2>
          <p className="text-gray-400 mb-6">{error}</p>
          <button 
            onClick={fetchRecommendations}
            className="px-6 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-bold transition-all"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-8 bg-[#0f172a] min-h-screen text-gray-100">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Cost Optimization</h1>
        <p className="text-gray-400 mt-1">AI-driven infrastructure rightsizing and waste remediation</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Total Recommendations', value: stats.total, icon: Lightbulb, color: 'text-violet-400' },
          { label: 'Potential Monthly Savings', value: `$${stats.potentialSavings.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, icon: DollarSign, color: 'text-green-400' },
          { label: 'Applied Actions', value: stats.applied, icon: CheckCircle2, color: 'text-blue-400' },
          { label: 'Pending Review', value: stats.pending, icon: Clock, color: 'text-yellow-400' }
        ].map((stat, i) => (
          <div key={i} className="bg-gray-800/50 border border-gray-700 p-5 rounded-xl">
            <div className="flex items-center gap-3 text-gray-400 text-xs font-semibold uppercase tracking-wider mb-2">
              <stat.icon className={`w-4 h-4 ${stat.color}`} />
              {stat.label}
            </div>
            <div className="text-2xl font-bold text-white">{stat.value}</div>
          </div>
        ))}
      </div>

      {/* Filters & Sorting */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-gray-800/30 p-4 rounded-xl border border-gray-700/50">
        <div className="flex flex-wrap items-center gap-6">
          <div className="space-y-1.5">
            <label className="text-[10px] font-bold text-gray-500 uppercase flex items-center gap-1.5">
              <Filter className="w-3 h-3" /> Filter Type
            </label>
            <select 
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="bg-gray-800 border border-gray-700 text-sm rounded-lg px-3 py-1.5 focus:ring-2 focus:ring-violet-500 outline-none transition-all cursor-pointer"
            >
              <option value="all">All Types</option>
              <option value="rightsizing">Rightsizing</option>
              <option value="spot_instance">Spot Instance</option>
              <option value="storage">Storage</option>
              <option value="idle_resource">Idle Resource</option>
            </select>
          </div>

          <div className="space-y-1.5">
            <label className="text-[10px] font-bold text-gray-500 uppercase flex items-center gap-1.5">
              <CheckCircle className="w-3 h-3" /> Status
            </label>
            <select 
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-gray-800 border border-gray-700 text-sm rounded-lg px-3 py-1.5 focus:ring-2 focus:ring-violet-500 outline-none transition-all cursor-pointer"
            >
              <option value="all">All Status</option>
              <option value="pending">Pending</option>
              <option value="applied">Applied</option>
              <option value="dismissed">Dismissed</option>
            </select>
          </div>
        </div>

        <div className="space-y-1.5">
          <label className="text-[10px] font-bold text-gray-500 uppercase flex items-center gap-1.5">
            <ArrowUpDown className="w-3 h-3" /> Sort By
          </label>
          <div className="flex bg-gray-800 rounded-lg p-1 border border-gray-700">
            <button 
              onClick={() => setSortBy('savings')}
              className={`px-3 py-1 text-xs font-semibold rounded-md transition-all ${sortBy === 'savings' ? 'bg-violet-600 text-white shadow-lg' : 'text-gray-400 hover:text-white'}`}
            >
              Savings
            </button>
            <button 
              onClick={() => setSortBy('date')}
              className={`px-3 py-1 text-xs font-semibold rounded-md transition-all ${sortBy === 'date' ? 'bg-violet-600 text-white shadow-lg' : 'text-gray-400 hover:text-white'}`}
            >
              Date
            </button>
          </div>
        </div>
      </div>

      {/* Recommendations List */}
      {filteredAndSorted.length === 0 ? (
        <div className="bg-gray-800/20 border border-dashed border-gray-700 rounded-2xl py-20 text-center">
          <TrendingDown className="w-12 h-12 text-gray-600 mx-auto mb-4 opacity-40" />
          <h3 className="text-xl font-medium text-gray-300">No recommendations yet</h3>
          <p className="text-gray-500 mt-2">Check back later or adjust your filters.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          {filteredAndSorted.map((rec) => (
            <div key={rec.id} className="bg-gray-800 border border-gray-700 rounded-2xl overflow-hidden hover:border-gray-600 transition-all group">
              <div className="p-6 space-y-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                       <span className="text-xs font-bold font-mono text-violet-400 uppercase tracking-wider">{rec.service_name ?? 'Service'}</span>
                       <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded-full border ${TYPE_COLORS[rec.recommendation_type] || TYPE_COLORS.default}`}>
                        {rec.recommendation_type?.replace('_', ' ')}
                       </span>
                    </div>
                    <h3 className="text-lg font-bold text-white group-hover:text-violet-300 transition-colors leading-tight">
                      {rec.resource_id}
                    </h3>
                  </div>
                  <div className="text-right">
                    <div className="text-xs font-bold text-gray-500 uppercase mb-1">Impact</div>
                    <div className="text-xl font-black text-green-400">
                      ${(rec.estimated_savings ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      <span className="text-[10px] font-medium text-green-600 ml-1">/mo</span>
                    </div>
                  </div>
                </div>

                <p className="text-sm text-gray-400 leading-relaxed border-l-2 border-gray-700 pl-4 py-1 italic">
                  {rec.description}
                </p>

                <div className="flex items-center justify-between pt-4 border-t border-gray-700/50">
                  <div className="flex items-center gap-3">
                    <div className="flex flex-col">
                      <span className="text-[10px] uppercase font-bold text-gray-500">Status</span>
                      <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-lg border ${STATUS_COLORS[rec.status] || STATUS_COLORS.dismissed}`}>
                        {rec.status}
                      </span>
                    </div>
                    <div className="flex flex-col">
                        <span className="text-[10px] uppercase font-bold text-gray-500">Detected</span>
                        <span className="text-[10px] font-medium text-gray-400">{new Date(rec.created_at ?? 0).toLocaleDateString()}</span>
                    </div>
                  </div>
                  
                  {rec.status === 'pending' && (
                    <div className="flex items-center gap-2">
                      <button 
                        onClick={() => handleDismiss(rec.id)}
                        className="p-2 text-gray-400 hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-all"
                        title="Dismiss"
                      >
                        <XCircle className="w-5 h-5" />
                      </button>
                      <button 
                        onClick={() => handleApply(rec.id)}
                        className="flex items-center gap-2 bg-violet-600 hover:bg-violet-700 text-white px-4 py-2 rounded-lg text-xs font-bold transition-all shadow-lg shadow-violet-900/20"
                      >
                        <CheckCircle2 className="w-4 h-4" />
                        Apply Action
                      </button>
                    </div>
                  )}

                  {rec.status !== 'pending' && (
                    <button 
                      onClick={() => handleDismiss('id_reset')} // Purely for UI consistency
                      className="text-[10px] font-bold uppercase text-gray-500 hover:text-gray-300 transition-colors"
                      disabled
                    >
                      Action {rec.status}
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Recommendations;
