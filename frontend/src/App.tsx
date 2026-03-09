import { useState, useEffect } from 'react';
import axios from 'axios';
import {
  LayoutDashboard, AlertTriangle, Lightbulb, Settings, Menu,
  Server, Globe, Box, DollarSign, Building2, TrendingUp, Bot,
} from 'lucide-react';
import { Routes, Route, Link, useLocation } from 'react-router-dom';

import DashboardOverviewPage from './pages/DashboardOverview';
import AnomalyAlertsPage from './pages/AnomalyAlerts';
import RecommendationsPage from './pages/Recommendations';
import ServiceCostPage from './pages/ServiceCost';
import RegionCostPage from './pages/RegionCost';
import KubernetesCostPage from './pages/KubernetesCost';
import BudgetsPage from './pages/Budgets';
import OrganizationsPage from './pages/Organizations';
import CostForecastPage from './pages/CostForecast';
import AIEnginePage from './pages/AIEngine';
import AutopilotPage from './pages/Autopilot';
import { useAuth } from './context/AuthContext';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const navItems = [
  { to: '/',             label: 'Dashboard',      icon: LayoutDashboard },
  { to: '/alerts',       label: 'Alerts',          icon: AlertTriangle },
  { to: '/recommendations', label: 'Recommendations', icon: Lightbulb },
  { to: '/budgets',      label: 'Budgets',         icon: DollarSign },
  { to: '/forecast',     label: 'Forecast',        icon: TrendingUp },
  { to: '/autopilot',    label: 'Autopilot',       icon: Bot },
  { to: '/ai-engine',   label: 'AI Engine',       icon: Server },
  { to: '/organizations', label: 'Organizations',  icon: Building2 },
  { to: '/service-cost', label: 'Service Cost',    icon: Server },
  { to: '/region-cost',  label: 'Region Cost',     icon: Globe },
  { to: '/kubernetes-cost', label: 'Kubernetes',   icon: Box },
];

function App() {
  const location = useLocation();
  const { role, setRole } = useAuth();
  const [overview, setOverview] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [forecast, setForecast] = useState<any>(null);
  const [anomalies, setAnomalies] = useState<any[]>([]);
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [costByService, setCostByService] = useState<Record<string, number>>({});
  const [resources, setResources] = useState<any[]>([]);
  const [budgetAlerts, setBudgetAlerts] = useState<any[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [ovRes, histRes, forcRes, anomRes, recRes, cbsRes, resRes, baRes] = await Promise.all([
          axios.get(`${API_BASE}/api/dashboard/overview`),
          axios.get(`${API_BASE}/api/cost-history`),
          axios.get(`${API_BASE}/api/forecast`),
          axios.get(`${API_BASE}/api/anomalies`),
          axios.get(`${API_BASE}/api/recommendations`),
          axios.get(`${API_BASE}/api/cost-by-service`),
          axios.get(`${API_BASE}/api/resources`),
          axios.get(`${API_BASE}/api/budget-alerts`),
        ]);

        setOverview(ovRes.data);
        setHistory(histRes.data);
        // Support both old (array) and new (object) forecast shapes
        setForecast(Array.isArray(forcRes.data) ? { forecast: forcRes.data, eom_projected_spend: 0 } : forcRes.data);
        setAnomalies(anomRes.data);
        setRecommendations(recRes.data);
        setCostByService(cbsRes.data);
        setResources(resRes.data);
        setBudgetAlerts(baRes.data);
      } catch (err) {
        console.error('Error fetching data', err);
      }
    };
    fetchData();
  }, []);

  const criticalBudgets = budgetAlerts.filter((a: any) => a.severity === 'critical').length;

  return (
    <div className="flex h-screen bg-background text-zinc-100 overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 bg-surface border-r border-zinc-800 hidden md:flex flex-col">
        <div className="p-4 border-b border-zinc-800 text-xl font-bold flex items-center gap-2 text-primary">
          <Settings className="w-6 h-6" /> FinOps AI
        </div>
        <nav className="flex-1 p-4 flex flex-col gap-0.5 overflow-y-auto">
          {navItems.map(({ to, label, icon: Icon }) => {
            const isActive = location.pathname === to;
            const isBudgets = to === '/budgets' && criticalBudgets > 0;
            return (
              <Link
                key={to}
                to={to}
                className={`flex items-center gap-3 p-3 rounded-md transition-colors ${
                  isActive
                    ? 'bg-primary/10 text-primary font-medium'
                    : 'hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200'
                }`}
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span className="text-sm">{label}</span>
                {isBudgets && (
                  <span className="ml-auto text-xs bg-red-600 text-white rounded-full px-1.5 py-0.5 font-bold">
                    {criticalBudgets}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
        <div className="p-4 border-t border-zinc-800 text-xs text-zinc-500">
          FinOps SaaS · v3.0.0
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-full overflow-y-auto">
        {/* Topbar */}
        <header className="h-16 border-b border-zinc-800 flex items-center justify-between px-6 bg-surface/50 sticky top-0 backdrop-blur z-10">
          <div className="flex items-center gap-4 md:hidden">
            <Menu className="w-6 h-6" />
            <span className="font-bold text-lg">FinOps AI</span>
          </div>
          <div className="hidden md:flex items-center gap-2 text-sm text-zinc-500">
            <span className="text-zinc-100 font-medium capitalize">
              {navItems.find(n => n.to === location.pathname)?.label ?? 'Dashboard'}
            </span>
          </div>
          <div className="ml-auto flex items-center gap-4">
            <select 
              value={role} 
              onChange={(e) => setRole(e.target.value as any)}
              className="bg-zinc-800 text-sm text-zinc-300 rounded border border-zinc-700 px-2 py-1 outline-none focus:ring-1 focus:ring-violet-500"
            >
              <option value="admin">Admin</option>
              <option value="finance">Finance</option>
              <option value="viewer">Viewer</option>
            </select>
            {criticalBudgets > 0 && (
              <Link to="/budgets" className="flex items-center gap-1.5 text-xs text-red-400 bg-red-900/30 border border-red-800/50 rounded-full px-3 py-1 hover:bg-red-900/50 transition-colors">
                <AlertTriangle className="w-3 h-3" />
                {criticalBudgets} budget{criticalBudgets > 1 ? 's' : ''} over limit
              </Link>
            )}
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" title="Backend Online" />
              <span className="text-xs text-zinc-500 hidden md:block">Live</span>
            </div>
            <div className="w-8 h-8 rounded-full bg-violet-700 flex items-center justify-center text-xs font-bold">
              FO
            </div>
          </div>
        </header>

        <Routes>
          <Route path="/" element={<DashboardOverviewPage overview={overview} history={history} forecast={forecast} costByService={costByService} resources={resources} budgetAlerts={budgetAlerts} />} />
          <Route path="/alerts" element={<AnomalyAlertsPage anomalies={anomalies} />} />
          <Route path="/recommendations" element={<RecommendationsPage recommendations={recommendations} />} />
          <Route path="/budgets" element={<BudgetsPage />} />
          <Route path="/forecast" element={<CostForecastPage />} />
          <Route path="/autopilot" element={<AutopilotPage />} />
          <Route path="/ai-engine" element={<AIEnginePage />} />
          <Route path="/organizations" element={<OrganizationsPage />} />
          <Route path="/service-cost" element={<ServiceCostPage />} />
          <Route path="/region-cost" element={<RegionCostPage />} />
          <Route path="/kubernetes-cost" element={<KubernetesCostPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
