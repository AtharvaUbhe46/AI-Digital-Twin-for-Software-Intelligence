import React, { useState } from 'react';
import {
  Settings, Key, Github, Database, RefreshCw, Save, CheckCircle,
  Eye, EyeOff, Trash2, AlertTriangle, Info, Globe, Shield
} from 'lucide-react';
import { Project } from '../types';
import { apiService } from '../services/api';

interface Props {
  activeProject: Project | null;
  onOpenConnectModal: () => void;
  onProjectDeleted?: () => void;
}

const Section: React.FC<{ title: string; icon: React.ReactNode; children: React.ReactNode }> = ({ title, icon, children }) => (
  <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 space-y-4">
    <div className="flex items-center space-x-2">
      <div className="text-cyan-400">{icon}</div>
      <h3 className="text-sm font-semibold text-gray-200">{title}</h3>
    </div>
    {children}
  </div>
);

const InputField: React.FC<{
  label: string; value: string; placeholder?: string; type?: string;
  onChange?: (v: string) => void; readOnly?: boolean; hint?: string;
}> = ({ label, value, placeholder, type = 'text', onChange, readOnly, hint }) => {
  const [show, setShow] = useState(false);
  const isPassword = type === 'password';
  return (
    <div className="space-y-1.5">
      <label className="text-xs font-medium text-gray-400">{label}</label>
      <div className="relative">
        <input
          type={isPassword && !show ? 'password' : 'text'}
          value={value}
          onChange={e => onChange?.(e.target.value)}
          readOnly={readOnly}
          placeholder={placeholder}
          className="w-full px-3 py-2 rounded-lg bg-gray-900/60 border border-gray-700 text-sm text-gray-200 placeholder-gray-600
            focus:outline-none focus:border-cyan-600 focus:ring-1 focus:ring-cyan-600/30 transition-all
            read-only:opacity-60 read-only:cursor-default font-mono"
        />
        {isPassword && (
          <button
            onClick={() => setShow(s => !s)}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 transition-colors"
            type="button"
          >
            {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        )}
      </div>
      {hint && <p className="text-xs text-gray-500">{hint}</p>}
    </div>
  );
};

export const SettingsPage: React.FC<Props> = ({ activeProject, onOpenConnectModal, onProjectDeleted }) => {
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  // Read env token hints (not editable for security – users should set in .env)
  const backendUrl = (window as any).__ENV_API_URL || 'http://localhost:8000';

  const handleDelete = async () => {
    if (!activeProject) return;
    setIsDeleting(true);
    setDeleteError(null);
    try {
      await apiService.deleteProject(activeProject.id);
      onProjectDeleted?.();
      setDeleteConfirm(false);
    } catch (e: any) {
      setDeleteError(e?.response?.data?.detail || 'Failed to delete project');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleFakeSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold text-white">Settings & Configuration</h1>
        <p className="text-sm text-gray-400 mt-1">Manage API credentials, sync behavior, and project connections.</p>
      </div>

      {/* Active Project Info */}
      <Section title="Active Repository" icon={<Github className="w-4 h-4" />}>
        {activeProject ? (
          <div className="space-y-3">
            <div className="flex items-center space-x-3 p-3 rounded-xl bg-gray-900/50 border border-gray-800">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-cyan-500 to-violet-600 flex items-center justify-center text-white text-xs font-bold shrink-0">
                {activeProject.github_owner[0]?.toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-white truncate">{activeProject.full_name}</p>
                <p className="text-xs text-gray-500">{activeProject.language || 'Unknown language'} · {activeProject.visibility} · {activeProject.default_branch}</p>
              </div>
              <a
                href={activeProject.html_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center space-x-1 px-2.5 py-1.5 rounded-lg bg-gray-800 border border-gray-700 text-xs text-gray-300 hover:text-cyan-400 hover:border-cyan-700 transition-colors shrink-0"
              >
                <Globe className="w-3.5 h-3.5" />
                <span>GitHub</span>
              </a>
            </div>
            <InputField label="Repository URL" value={activeProject.html_url} readOnly />
            <InputField label="Default Branch" value={activeProject.default_branch} readOnly />
            <InputField
              label="Last Synced At"
              value={activeProject.last_synced_at ? new Date(activeProject.last_synced_at).toLocaleString() : 'Never'}
              readOnly
            />
            <button
              onClick={onOpenConnectModal}
              className="text-sm text-cyan-400 hover:underline"
            >
              + Connect another repository
            </button>
          </div>
        ) : (
          <div className="text-center py-6 space-y-2">
            <Github className="w-8 h-8 text-gray-600 mx-auto" />
            <p className="text-sm text-gray-400">No repository connected.</p>
            <button
              onClick={onOpenConnectModal}
              className="px-4 py-2 rounded-lg bg-cyan-700/40 border border-cyan-700 text-cyan-400 text-sm hover:bg-cyan-700/60 transition-all"
            >
              Connect GitHub Repository
            </button>
          </div>
        )}
      </Section>

      {/* GitHub API */}
      <Section title="GitHub API Configuration" icon={<Key className="w-4 h-4" />}>
        <div className="p-3 rounded-xl bg-blue-900/20 border border-blue-800 flex items-start space-x-2 text-xs text-blue-300">
          <Info className="w-4 h-4 shrink-0 mt-0.5" />
          <p>API credentials are configured via environment variables in the backend <code className="font-mono bg-blue-900/40 px-1 py-0.5 rounded">.env</code> file for security. The GitHub Personal Access Token enables higher rate limits (5000 req/hr vs 60 req/hr).</p>
        </div>
        <InputField
          label="GitHub Token Status"
          value="Configured via GITHUB_TOKEN environment variable"
          readOnly
          hint="Set GITHUB_TOKEN in backend/.env or the root .env file to authenticate with GitHub."
        />
        <InputField
          label="Backend API URL"
          value={backendUrl}
          readOnly
          hint="The frontend communicates with the FastAPI backend at this address."
        />
      </Section>

      {/* Database */}
      <Section title="Database Connection" icon={<Database className="w-4 h-4" />}>
        <div className="p-3 rounded-xl bg-blue-900/20 border border-blue-800 flex items-start space-x-2 text-xs text-blue-300">
          <Info className="w-4 h-4 shrink-0 mt-0.5" />
          <p>PostgreSQL connection is configured via <code className="font-mono bg-blue-900/40 px-1 py-0.5 rounded">DATABASE_URL</code> environment variable. All project data is persisted here.</p>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <InputField label="Database Engine" value="PostgreSQL 16" readOnly />
          <InputField label="ORM" value="SQLAlchemy 2.x" readOnly />
        </div>
        <InputField
          label="Connection String"
          value="postgresql://user:****@localhost:5432/software_digital_twin"
          type="password"
          readOnly
          hint="Edit DATABASE_URL in the .env file to change the connection."
        />
      </Section>

      {/* Sync Settings */}
      <Section title="Sync & Data Collection" icon={<RefreshCw className="w-4 h-4" />}>
        <div className="grid grid-cols-2 gap-3">
          <InputField label="Commits per Sync" value="50" readOnly hint="Latest 50 commits fetched per sync." />
          <InputField label="Issues per Sync" value="50" readOnly hint="Latest 50 issues fetched per sync." />
          <InputField label="PRs per Sync" value="50" readOnly hint="Latest 50 pull requests per sync." />
          <InputField label="Contributors per Sync" value="30" readOnly hint="Top 30 contributors by commits." />
        </div>
        <div className="p-3 rounded-xl bg-amber-900/20 border border-amber-800 flex items-start space-x-2 text-xs text-amber-300">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <p>Auto-sync is not yet enabled. Click the "Sync" button in the header to refresh data manually. Scheduled background sync is planned for Phase 3.</p>
        </div>
      </Section>

      {/* Danger Zone */}
      {activeProject && (
        <Section title="Danger Zone" icon={<Shield className="w-4 h-4 text-red-400" />}>
          <div className="p-3 rounded-xl bg-red-900/20 border border-red-800 flex items-start space-x-2 text-xs text-red-300">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
            <p>Disconnecting a repository removes all synced data from PostgreSQL including commits, issues, PRs, and events. This action cannot be undone.</p>
          </div>
          {!deleteConfirm ? (
            <button
              onClick={() => setDeleteConfirm(true)}
              className="flex items-center space-x-2 px-4 py-2 rounded-xl border border-red-800 bg-red-900/20 text-red-400 text-sm font-medium hover:bg-red-900/40 transition-all"
            >
              <Trash2 className="w-4 h-4" />
              <span>Disconnect & Delete "{activeProject.full_name}"</span>
            </button>
          ) : (
            <div className="flex items-center space-x-3">
              <span className="text-sm text-gray-300">Are you sure? This is irreversible.</span>
              <button
                onClick={handleDelete}
                disabled={isDeleting}
                className="px-4 py-1.5 rounded-lg bg-red-700 text-white text-sm font-semibold hover:bg-red-600 disabled:opacity-50 transition-all"
              >
                {isDeleting ? 'Deleting...' : 'Yes, Delete'}
              </button>
              <button
                onClick={() => { setDeleteConfirm(false); setDeleteError(null); }}
                className="px-4 py-1.5 rounded-lg bg-gray-800 text-gray-300 text-sm hover:bg-gray-700 transition-all"
              >
                Cancel
              </button>
            </div>
          )}
          {deleteError && <p className="text-xs text-red-400">{deleteError}</p>}
        </Section>
      )}

      {/* About */}
      <Section title="About" icon={<Info className="w-4 h-4" />}>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-xs">
          {[
            { label: 'Project', val: 'AI Digital Twin for Software Intelligence' },
            { label: 'Version', val: '0.1.0 MVP' },
            { label: 'Frontend', val: 'React + Vite + TypeScript' },
            { label: 'Backend', val: 'FastAPI + SQLAlchemy' },
            { label: 'Database', val: 'PostgreSQL 16' },
            { label: 'B.Tech Project', val: 'CSE Major Project' },
          ].map(({ label, val }, i) => (
            <div key={i} className="px-3 py-2 rounded-lg bg-gray-900/50 border border-gray-800">
              <p className="text-gray-500">{label}</p>
              <p className="text-gray-200 font-medium mt-0.5">{val}</p>
            </div>
          ))}
        </div>
      </Section>
    </div>
  );
};
