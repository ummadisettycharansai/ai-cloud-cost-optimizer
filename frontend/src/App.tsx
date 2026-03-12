import { useState, useEffect } from 'react';
import axios from 'axios';
import {
  LayoutDashboard, AlertTriangle, Lightbulb, Settings, Menu,
  Server, Globe, Box, DollarSign, Building2, TrendingUp, Bot, Lock, ShieldCheck, Shield
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
import type { Role } from './context/AuthContext';
import RestrictedCard from './components/RestrictedCard';

import { API_BASE } from './services/api';

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, permission: null },
  { to: '/alerts', label: 'Alerts', icon: AlertTriangle, permission: 'canSeeAlerts' },
  { to: '/recommendations', label: 'Recommendations', icon: Lightbulb, permission: 'canSeeRecommendations' },
  { to: '/budgets', label: 'Budgets', icon: DollarSign, permission: 'canSeeBudgets' },
  { to: '/forecast', label: 'Forecast', icon: TrendingUp, permission: 'canSeeForecast' },
  { to: '/autopilot', label: 'Autopilot', icon: Bot, permission: 'canSeeAutopilot' },
  { to: '/ai-engine', label: 'AI Engine', icon: Server, permission: 'canSeeAIEngine' },
  { to: '/organizations', label: 'Organizations', icon: Building2, permission: 'canSeeOrganizations' },
  { to: '/service-cost', label: 'Service Cost', icon: Server, permission: 'canSeeServiceCost' },
  { to: '/region-cost', label: 'Region Cost', icon: Globe, permission: 'canSeeFinancials' },
  { to: '/kubernetes-cost', label: 'Kubernetes', icon: Box, permission: 'canSeeKubernetes' },
];

const RoleBanner = ({ role }: { role: Role }) => {
  const config = {
    admin: { icon: ShieldCheck, color: 'bg-indigo-600', text: 'Administrative Access - Full System Control' },
    finance: { icon: Shield, color: 'bg-emerald-600', text: 'Financial Analyst Access - Cost Data & Reporting' },
    viewer: { icon: Lock, color: 'bg-zinc-700', text: 'ReadOnly Access - Limited Reporting Visibility' },
  };
  const { icon: Icon, color, text } = config[role];

  return (
    <div className={`${color} text-white px-6 py-1 text-xs flex items-center justify-center gap-2 font-medium transition-colors duration-300`}>
      <Icon className="w-3 h-3" />
      <span>Currently active: <strong>{role.toUpperCase()}</strong>. {text}</span>
    </div>
  );
};

function App() {
  const location = useLocation();
  const { role, setRole, permissions } = useAuth();
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
          {navItems.map(({ to, label, icon: Icon, permission }) => {
            const isActive = location.pathname === to;
            const isBudgets = to === '/budgets' && criticalBudgets > 0;
            const hasAccess = !permission || (permissions as any)[permission];

            return (
              <Link
                key={to}
                to={hasAccess ? to : '#'}
                onClick={(e) => !hasAccess && e.preventDefault()}
                className={`flex items-center gap-3 p-3 rounded-md transition-all ${!hasAccess
                  ? 'opacity-40 grayscale cursor-not-allowed hover:bg-transparent'
                  : isActive
                    ? 'bg-primary/10 text-primary font-medium'
                    : 'hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200'
                  }`}
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span className="text-sm flex-1">{label}</span>
                {!hasAccess && <Lock className="w-3 h-3 text-zinc-500" />}
                {isBudgets && hasAccess && (
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
        <Header role={role} setRole={setRole} criticalBudgets={criticalBudgets} location={location} />
        <RoleBanner role={role} />

        <div className="flex-1 overflow-y-auto">
          <Routes>
            <Route path="/" element={<DashboardOverviewPage overview={overview} history={history} forecast={forecast} costByService={costByService} resources={resources} budgetAlerts={budgetAlerts} />} />
            <Route path="/alerts" element={permissions.canSeeAlerts ? <AnomalyAlertsPage anomalies={anomalies} /> : <PageRestricted title="Alerts Access Restricted" />} />
            <Route path="/recommendations" element={permissions.canSeeRecommendations ? <RecommendationsPage recommendations={recommendations} /> : <PageRestricted title="Recommendations Restricted" />} />
            <Route path="/budgets" element={permissions.canSeeBudgets ? <BudgetsPage /> : <PageRestricted title="Budgets Access Restricted" />} />
            <Route path="/forecast" element={permissions.canSeeForecast ? <CostForecastPage /> : <PageRestricted title="Forecast Access Restricted" />} />
            <Route path="/autopilot" element={permissions.canSeeAutopilot ? <AutopilotPage /> : <PageRestricted title="Autopilot Restricted" />} />
            <Route path="/ai-engine" element={permissions.canSeeAIEngine ? <AIEnginePage /> : <PageRestricted title="AI Engine Access Restricted" />} />
            <Route path="/organizations" element={permissions.canSeeOrganizations ? <OrganizationsPage /> : <PageRestricted title="Organization Access Restricted" />} />
            <Route path="/service-cost" element={permissions.canSeeServiceCost ? <ServiceCostPage /> : <PageRestricted title="Service Spend Restricted" />} />
            <Route path="/region-cost" element={permissions.canSeeFinancials ? <RegionCostPage /> : <PageRestricted title="Regional Spend Restricted" />} />
            <Route path="/kubernetes-cost" element={permissions.canSeeKubernetes ? <KubernetesCostPage /> : <PageRestricted title="K8s Spend Restricted" />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}

function Header({ role, setRole, criticalBudgets, location }: any) {
  return (
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
        <div className="flex items-center gap-2">
          <label className="text-[10px] uppercase font-bold text-zinc-500 tracking-wider">Active Role:</label>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value as any)}
            className="bg-zinc-800 text-xs text-zinc-100 rounded border border-zinc-700 px-3 py-1.5 outline-none focus:ring-1 focus:ring-violet-500 font-medium cursor-pointer"
          >
            <option value="admin">Admin</option>
            <option value="finance">Finance</option>
            <option value="viewer">Viewer</option>
          </select>
        </div>
        {criticalBudgets > 0 && (
          <Link to="/budgets" className="flex items-center gap-1.5 text-xs text-red-400 bg-red-900/30 border border-red-800/50 rounded-full px-3 py-1 hover:bg-red-900/50 transition-colors">
            <AlertTriangle className="w-3 h-3" />
            {criticalBudgets}
          </Link>
        )}
        <div className="w-8 h-8 rounded-full bg-violet-700 flex items-center justify-center text-xs font-bold ring-2 ring-violet-500/20">
          FO
        </div>
      </div>
    </header>
  );
}

function PageRestricted({ title }: { title: string }) {
  return (
    <div className="p-12 flex items-center justify-center h-full">
      <RestrictedCard title={title} className="max-w-md w-full" />
    </div>
  );
}

export default App;
