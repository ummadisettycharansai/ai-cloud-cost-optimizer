import { useState, useEffect } from 'react';
import axios from 'axios';
import { Building2, Layers, PlusCircle, Server } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

import { API_BASE } from '../services/api';

interface Organization {
  id: number;
  name: string;
  slug: string;
  plan: string;
  created_at: string;
}

interface Project {
  id: number;
  org_id: number;
  name: string;
  cloud_provider: string;
  description: string;
  tags: string;
  created_at: string;
}

const PLAN_BADGE: Record<string, string> = {
  free:       'bg-zinc-700 text-zinc-300',
  pro:        'bg-violet-700/60 text-violet-300',
  enterprise: 'bg-amber-700/60 text-amber-300',
};

const PROVIDER_ICON: Record<string, string> = {
  AWS:   '🟠',
  GCP:   '🔵',
  Azure: '🔷',
  Multi: '🌐',
};

export default function OrganizationsPage() {
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showOrgForm, setShowOrgForm] = useState(false);
  const [showProjForm, setShowProjForm] = useState(false);
  const [selectedOrg, setSelectedOrg] = useState<number | null>(null);
  const { isAdminOrFinance } = useAuth();

  const [orgForm, setOrgForm] = useState({ name: '', slug: '', plan: 'free' });
  const [projForm, setProjForm] = useState({ name: '', org_id: '', cloud_provider: 'AWS', description: '' });

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const [oRes, pRes] = await Promise.all([
          axios.get(`${API_BASE}/api/organizations`),
          axios.get(`${API_BASE}/api/projects`),
        ]);
        setOrgs(oRes.data);
        setProjects(pRes.data);
      } catch (err) {
        console.error('Error loading orgs/projects', err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const projectsFor = (orgId: number) => projects.filter(p => p.org_id === orgId);

  const handleCreateOrg = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await axios.post(`${API_BASE}/api/organizations`, orgForm);
      const oRes = await axios.get(`${API_BASE}/api/organizations`);
      setOrgs(oRes.data);
      setShowOrgForm(false);
      setOrgForm({ name: '', slug: '', plan: 'free' });
    } catch (err) { console.error(err); }
  };

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await axios.post(`${API_BASE}/api/projects`, {
        ...projForm,
        org_id: Number(projForm.org_id),
      });
      const pRes = await axios.get(`${API_BASE}/api/projects`);
      setProjects(pRes.data);
      setShowProjForm(false);
      setProjForm({ name: '', org_id: '', cloud_provider: 'AWS', description: '' });
    } catch (err) { console.error(err); }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-zinc-100">Organizations</h1>
          <p className="text-sm text-zinc-500 mt-1">Manage tenants, teams, and cloud projects</p>
        </div>
        {isAdminOrFinance && (
          <div className="flex gap-2">
            <button
              onClick={() => setShowProjForm(v => !v)}
              className="flex items-center gap-2 px-3 py-2 bg-zinc-700 hover:bg-zinc-600 text-zinc-200 rounded-lg text-sm font-medium transition-colors"
            >
              <Layers className="w-4 h-4" /> New Project
            </button>
            <button
              onClick={() => setShowOrgForm(v => !v)}
              className="flex items-center gap-2 px-3 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-sm font-medium transition-colors"
            >
              <PlusCircle className="w-4 h-4" /> New Org
            </button>
          </div>
        )}
      </div>

      {/* Create Org Form */}
      {showOrgForm && (
        <form onSubmit={handleCreateOrg} className="bg-zinc-900 border border-zinc-700 rounded-xl p-5 grid grid-cols-3 gap-4">
          <h2 className="col-span-3 text-sm font-semibold text-zinc-300">Create Organization</h2>
          {[{ label: 'Name', key: 'name', placeholder: 'Acme Corp' }, { label: 'Slug', key: 'slug', placeholder: 'acme-corp' }].map(f => (
            <div key={f.key}>
              <label className="text-xs text-zinc-400 block mb-1">{f.label}</label>
              <input
                type="text" placeholder={f.placeholder} required
                value={(orgForm as any)[f.key]}
                onChange={e => setOrgForm(o => ({ ...o, [f.key]: e.target.value }))}
                className="w-full bg-zinc-800 border border-zinc-600 rounded-lg px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-violet-500"
              />
            </div>
          ))}
          <div>
            <label className="text-xs text-zinc-400 block mb-1">Plan</label>
            <select
              value={orgForm.plan}
              onChange={e => setOrgForm(o => ({ ...o, plan: e.target.value }))}
              className="w-full bg-zinc-800 border border-zinc-600 rounded-lg px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-violet-500"
            >
              {['free', 'pro', 'enterprise'].map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          <div className="col-span-3 flex gap-3">
            <button type="submit" className="px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-sm font-medium">Create</button>
            <button type="button" onClick={() => setShowOrgForm(false)} className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 text-zinc-300 rounded-lg text-sm font-medium">Cancel</button>
          </div>
        </form>
      )}

      {/* Create Project Form */}
      {showProjForm && (
        <form onSubmit={handleCreateProject} className="bg-zinc-900 border border-zinc-700 rounded-xl p-5 grid grid-cols-2 gap-4">
          <h2 className="col-span-2 text-sm font-semibold text-zinc-300">Create Project</h2>
          <div>
            <label className="text-xs text-zinc-400 block mb-1">Project Name</label>
            <input
              type="text" placeholder="Production Infra" required
              value={projForm.name}
              onChange={e => setProjForm(f => ({ ...f, name: e.target.value }))}
              className="w-full bg-zinc-800 border border-zinc-600 rounded-lg px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-violet-500"
            />
          </div>
          <div>
            <label className="text-xs text-zinc-400 block mb-1">Organization</label>
            <select
              value={projForm.org_id}
              onChange={e => setProjForm(f => ({ ...f, org_id: e.target.value }))}
              required
              className="w-full bg-zinc-800 border border-zinc-600 rounded-lg px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-violet-500"
            >
              <option value="">Select org…</option>
              {orgs.map(o => <option key={o.id} value={o.id}>{o.name}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-zinc-400 block mb-1">Cloud Provider</label>
            <select
              value={projForm.cloud_provider}
              onChange={e => setProjForm(f => ({ ...f, cloud_provider: e.target.value }))}
              className="w-full bg-zinc-800 border border-zinc-600 rounded-lg px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-violet-500"
            >
              {['AWS', 'GCP', 'Azure', 'Multi'].map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-zinc-400 block mb-1">Description</label>
            <input
              type="text" placeholder="Optional"
              value={projForm.description}
              onChange={e => setProjForm(f => ({ ...f, description: e.target.value }))}
              className="w-full bg-zinc-800 border border-zinc-600 rounded-lg px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-violet-500"
            />
          </div>
          <div className="col-span-2 flex gap-3">
            <button type="submit" className="px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-sm font-medium">Create</button>
            <button type="button" onClick={() => setShowProjForm(false)} className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 text-zinc-300 rounded-lg text-sm font-medium">Cancel</button>
          </div>
        </form>
      )}

      {/* Org Cards */}
      {loading ? (
        <div className="text-zinc-500 text-sm py-8 text-center">Loading…</div>
      ) : orgs.length === 0 ? (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl py-12 text-center text-zinc-500">
          <Building2 className="w-8 h-8 mx-auto mb-2 opacity-30" />
          <p className="text-sm">No organizations yet. Create your first tenant above.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {orgs.map(org => {
            const orgProjects = projectsFor(org.id);
            const isSelected = selectedOrg === org.id;
            return (
              <div
                key={org.id}
                onClick={() => setSelectedOrg(isSelected ? null : org.id)}
                className={`bg-zinc-900 border rounded-xl p-5 cursor-pointer transition-all hover:border-violet-600 ${isSelected ? 'border-violet-600 ring-1 ring-violet-600/30' : 'border-zinc-800'}`}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className="w-9 h-9 rounded-lg bg-violet-700/30 flex items-center justify-center">
                      <Building2 className="w-4 h-4 text-violet-400" />
                    </div>
                    <div>
                      <p className="font-semibold text-zinc-100 text-sm">{org.name}</p>
                      <p className="text-xs text-zinc-500">/{org.slug}</p>
                    </div>
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium capitalize ${PLAN_BADGE[org.plan] ?? PLAN_BADGE.free}`}>
                    {org.plan}
                  </span>
                </div>
                <div className="text-xs text-zinc-500 mb-3">
                  Created {new Date(org.created_at).toLocaleDateString()}
                </div>
                <div className="flex items-center gap-2 text-sm text-zinc-400">
                  <Layers className="w-4 h-4" />
                  <span>{orgProjects.length} project{orgProjects.length !== 1 ? 's' : ''}</span>
                </div>

                {/* Expanded project list */}
                {isSelected && orgProjects.length > 0 && (
                  <div className="mt-4 border-t border-zinc-800 pt-3 space-y-2">
                    {orgProjects.map(p => (
                      <div key={p.id} className="flex items-center gap-2 text-xs text-zinc-400 py-1">
                        <Server className="w-3 h-3 text-zinc-600" />
                        <span className="text-zinc-300 font-medium">{p.name}</span>
                        <span>{PROVIDER_ICON[p.cloud_provider] ?? '🌐'} {p.cloud_provider}</span>
                      </div>
                    ))}
                  </div>
                )}
                {isSelected && orgProjects.length === 0 && (
                  <p className="mt-3 text-xs text-zinc-600 border-t border-zinc-800 pt-3">No projects yet.</p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
