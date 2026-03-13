import React, { useState, useEffect, useMemo } from 'react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Cell
} from 'recharts';
import { 
  Lightbulb, 
  DollarSign, 
  TrendingDown, 
  Clock, 
  CheckCircle2, 
  Filter,
  CheckCircle,
  XCircle,
  Loader2,
  AlertTriangle
} from 'lucide-react';

interface Recommendation {
  id: string;
  resource_id: string;
  service_name: string;
  recommendation_type: string;
  description: string;
  estimated_savings: number;
  status: string;
  created_at?: string;
  region?: string;
}

const MOCK_RECOMMENDATIONS: Recommendation[] = [
  {
    id: "1",
    resource_id: "i-1234567890abcdef0",
    service_name: "EC2",
    recommendation_type: "rightsizing",
    description: "Downsize from m5.xlarge to m5.large. CPU below 15% for 30 days.",
    estimated_savings: 145.50,
    status: "pending",
    region: "ap-southeast-1",
    created_at: "2024-01-15T10:00:00Z"
  },
  {
    id: "2",
    resource_id: "vol-0987654321fedcba0",
    service_name: "EBS",
    recommendation_type: "storage",
    description: "Delete unattached EBS volume. No instance attached for 45 days.",
    estimated_savings: 23.00,
    status: "pending",
    region: "us-east-1",
    created_at: "2024-01-14T08:30:00Z"
  },
  {
    id: "3",
    resource_id: "i-abcdef1234567890",
    service_name: "EC2",
    recommendation_type: "spot_instance",
    description: "Migrate to Spot Instance. Suitable for fault-tolerant workloads.",
    estimated_savings: 312.75,
    status: "applied",
    region: "us-west-2",
    created_at: "2024-01-13T14:00:00Z"
  },
  {
    id: "4",
    resource_id: "db-xyz123",
    service_name: "RDS",
    recommendation_type: "idle_resource",
    description: "RDS instance has zero connections for 14 days.",
    estimated_savings: 89.20,
    status: "dismissed",
    region: "eu-west-1",
    created_at: "2024-01-12T09:15:00Z"
  },
  {
    id: "5",
    resource_id: "s3-bucket-logs-old",
    service_name: "S3",
    recommendation_type: "storage",
    description: "Move infrequently accessed data to S3 Glacier tier.",
    estimated_savings: 67.30,
    status: "pending",
    region: "ap-southeast-1",
    created_at: "2024-01-11T11:00:00Z"
  }
];

const TYPE_COLORS: Record<string, string> = {
  rightsizing: 'bg-blue-500/20 text-blue-400',
  spot_instance: 'bg-purple-500/20 text-purple-400',
  storage: 'bg-orange-500/20 text-orange-400',
  idle_resource: 'bg-red-500/20 text-red-400'
};

const STATUS_BADGES: Record<string, string> = {
  pending: 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30',
  applied: 'bg-green-500/20 text-green-400 border border-green-500/30',
  dismissed: 'bg-gray-500/20 text-gray-400 border border-gray-500/30'
};

// Safe Tooltip Component
const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload || !payload.length) return null;
  return (
    <div className="bg-gray-800 border border-gray-700 p-3 rounded-lg shadow-xl">
      <p className="text-gray-400 text-[10px] uppercase font-bold mb-1">{payload[0]?.payload?.name ?? 'Service'}</p>
      <p className="text-green-400 font-bold text-sm">
        ${(Number(payload[0]?.value) || 0).toFixed(2)}
      </p>
    </div>
  );
};

const Recommendations: React.FC = () => {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const fetchRecommendations = async () => {
    setLoading(true);
    try {
      const apiUrl = import.meta.env.VITE_API_URL || '';
      const token = localStorage.getItem('token') || localStorage.getItem('access_token') || '';
      
      const response = await fetch(`${apiUrl}/api/v1/recommendations`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      const data = await response.json();
      const items = Array.isArray(data) ? data :
                    Array.isArray(data?.recommendations) ? data.recommendations :
                    Array.isArray(data?.data) ? data.data : [];
      
      setRecommendations(items.length > 0 ? items : MOCK_RECOMMENDATIONS);
    } catch (err) {
      console.warn('API failed, using mock data:', err);
      setRecommendations(MOCK_RECOMMENDATIONS);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecommendations();
  }, []);

  const handleAction = (id: string, newStatus: string) => {
    setRecommendations(prev => (prev ?? []).map(r => r.id === id ? { ...r, status: newStatus } : r));
  };

  const filteredItems = useMemo(() => {
    return (recommendations ?? []).filter(item => {
      const typeMatch = typeFilter === 'all' || item?.recommendation_type === typeFilter;
      const statusMatch = statusFilter === 'all' || item?.status === statusFilter;
      return typeMatch && statusMatch;
    });
  }, [recommendations, typeFilter, statusFilter]);

  const stats = useMemo(() => {
    const items = recommendations ?? [];
    return {
      total: items.length,
      potentialSavings: items
        .filter(r => r?.status === 'pending')
        .reduce((sum, r) => sum + (Number(r?.estimated_savings) || 0), 0),
      applied: items.filter(r => r?.status === 'applied').length,
      pending: items.filter(r => r?.status === 'pending').length
    };
  }, [recommendations]);

  const chartData = useMemo(() => {
    const dataMap = (recommendations ?? [])
      .filter(r => r?.status === 'pending')
      .reduce((acc, item) => {
        const key = item?.service_name ?? 'Unknown';
        const existing = acc.find(a => a.name === key);
        if (existing) {
          existing.savings = (existing.savings ?? 0) + (Number(item?.estimated_savings) || 0);
        } else {
          acc.push({ name: key, savings: Number(item?.estimated_savings) || 0 });
        }
        return acc;
      }, [] as { name: string; savings: number }[]);
    
    return dataMap.sort((a, b) => b.savings - a.savings);
  }, [recommendations]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] h-full space-y-4 bg-gray-900 text-white">
        <Loader2 className="w-10 h-10 text-blue-500 animate-spin" />
        <p className="text-gray-400 font-medium">Loading recommendations...</p>
      </div>
    );
  }

  return (
    <div className="p-8 bg-gray-900 min-h-screen space-y-8 animate-in fade-in duration-500 text-white">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Recommendations</h1>
          <p className="text-gray-400 mt-1">Optimize your cloud spend with AI-driven resource remediation</p>
        </div>
        <div className="bg-green-500/10 border border-green-500/20 px-4 py-2 rounded-lg flex items-center gap-2">
          <TrendingDown className="w-4 h-4 text-green-400" />
          <span className="text-sm font-semibold text-green-400">
            Total Potential Savings: ${stats.potentialSavings.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Total Recommendations', value: stats.total, icon: Lightbulb, color: 'text-blue-400' },
          { label: 'Potential Savings', value: `$${stats.potentialSavings.toLocaleString(undefined, { minimumFractionDigits: 2 })}`, icon: DollarSign, color: 'text-green-400' },
          { label: 'Applied Action', value: stats.applied, icon: CheckCircle2, color: 'text-purple-400' },
          { label: 'Pending Review', value: stats.pending, icon: Clock, color: 'text-yellow-400' }
        ].map((stat, i) => (
          <div key={i} className="bg-gray-800 border border-gray-700 p-6 rounded-xl shadow-sm">
            <div className="flex items-center gap-3 text-gray-400 text-xs font-bold uppercase tracking-widest mb-2">
              <stat.icon className={`w-4 h-4 ${stat.color}`} />
              {stat.label}
            </div>
            <div className="text-2xl font-bold text-white">{stat.value}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 text-white">
        {/* Chart Section */}
        <div className="lg:col-span-1 bg-gray-800 border border-gray-700 p-6 rounded-xl">
          <h3 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
            <TrendingDown className="w-5 h-5 text-blue-400" />
            Savings by Service
          </h3>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={Array.isArray(chartData) ? chartData : []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
                <XAxis 
                  dataKey="name" 
                  stroke="#9CA3AF" 
                  fontSize={10} 
                  tickLine={false} 
                  axisLine={false}
                />
                <YAxis 
                  stroke="#9CA3AF" 
                  fontSize={10} 
                  tickLine={false} 
                  axisLine={false}
                  tickFormatter={(val) => `$${val}`}
                />
                <Tooltip content={<CustomTooltip />} cursor={{ fill: '#374151', opacity: 0.4 }} />
                <Bar dataKey="savings" radius={[4, 4, 0, 0]}>
                  {(chartData ?? []).map((_entry, index) => (
                    <Cell key={`cell-${index}`} fill={index === 0 ? '#3B82F6' : '#60A5FA'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Content Section */}
        <div className="lg:col-span-2 space-y-6">
          {/* Filters */}
          <div className="flex flex-wrap items-center gap-4 bg-gray-800/50 p-4 rounded-xl border border-gray-700">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-gray-500" />
              <select 
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="bg-gray-800 border border-gray-700 text-xs text-white rounded-lg px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500/50"
              >
                <option value="all">All Types</option>
                <option value="rightsizing">Rightsizing</option>
                <option value="spot_instance">Spot Instance</option>
                <option value="storage">Storage</option>
                <option value="idle_resource">Idle Resource</option>
              </select>
            </div>
            <select 
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-gray-800 border border-gray-700 text-xs text-white rounded-lg px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500/50"
            >
              <option value="all">All Status</option>
              <option value="pending">Pending</option>
              <option value="applied">Applied</option>
              <option value="dismissed">Dismissed</option>
            </select>
          </div>

          {/* List */}
          <div className="space-y-4">
            {filteredItems.length === 0 ? (
              <div className="bg-gray-800/20 border border-dashed border-gray-700 rounded-xl p-12 text-center text-gray-500">
                No recommendations found matching your filters.
              </div>
            ) : (
              (filteredItems ?? []).map((rec) => (
                <div key={rec.id} className="bg-gray-800 border border-gray-700 rounded-xl p-6 transition-all hover:border-gray-600 group">
                  <div className="flex items-start justify-between gap-4 text-white">
                    <div className="space-y-3 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-xs font-bold text-white font-mono bg-gray-700 px-2 py-0.5 rounded cursor-default">
                          {rec?.service_name ?? 'AWS'}
                        </span>
                        <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded-full ${TYPE_COLORS[rec?.recommendation_type] || 'bg-gray-700 text-gray-300'}`}>
                          {rec?.recommendation_type?.replace('_', ' ') ?? 'General'}
                        </span>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-lg ${STATUS_BADGES[rec?.status] || 'bg-gray-700 text-gray-300'}`}>
                          {rec?.status}
                        </span>
                        {rec?.region && (
                          <span className="text-[10px] font-medium text-gray-500 flex items-center gap-1">
                            <AlertTriangle className="w-3 h-3" /> {rec.region}
                          </span>
                        )}
                      </div>
                      <h4 className="text-sm font-bold text-white group-hover:text-blue-400 transition-colors uppercase tracking-tight leading-none">
                        {rec?.resource_id ?? 'Unknown Resource'}
                      </h4>
                      <p className="text-sm text-gray-400 leading-relaxed italic border-l-2 border-gray-700 pl-3 py-1 mt-2">
                        {rec?.description ?? 'No description available.'}
                      </p>
                    </div>
                    <div className="text-right">
                      <div className="text-xl font-bold text-green-400">
                        +${(Number(rec?.estimated_savings) || 0).toFixed(2)}
                      </div>
                      <div className="text-[10px] uppercase font-bold text-gray-500 mt-1">Monthly Savings</div>
                    </div>
                  </div>

                  {rec.status === 'pending' && (
                    <div className="flex items-center justify-end gap-3 mt-6 pt-4 border-t border-gray-700/50">
                      <button 
                        onClick={() => handleAction(rec.id, 'dismissed')}
                        className="flex items-center gap-2 px-4 py-2 text-xs font-bold text-gray-400 hover:text-white hover:bg-gray-700 transition-all rounded-lg"
                      >
                        <XCircle className="w-4 h-4" /> Dismiss
                      </button>
                      <button 
                        onClick={() => handleAction(rec.id, 'applied')}
                        className="flex items-center gap-2 px-4 py-2 text-xs font-bold bg-blue-600 hover:bg-blue-700 text-white transition-all rounded-lg shadow-lg shadow-blue-900/20"
                      >
                        <CheckCircle className="w-4 h-4" /> Apply Action
                      </button>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Recommendations;
