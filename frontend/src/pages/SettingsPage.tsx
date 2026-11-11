import React, { useState } from 'react';
import {
  Github, RefreshCw,
  Eye, EyeOff, Trash2, AlertTriangle, Globe, Shield, Sun, Moon
} from 'lucide-react';
import { Project } from '../types';
import { apiService } from '../services/api';
import { useTheme } from '../context/ThemeContext';

interface Props {
  activeProject: Project | null;
  onOpenConnectModal: () => void;
  onProjectDeleted?: () => void;
}

const Section: React.FC<{ title: string; icon: React.ReactNode; children: React.ReactNode }> = ({ title, icon, children }) => (
  <div className="bg-white dark:bg-[#111827] border border-slate-200 dark:border-gray-800 rounded-xl p-5 space-y-4 shadow-sm">
    <div className="flex items-center space-x-2">
      <div className="text-cyan-600 dark:text-cyan-400">{icon}</div>
      <h3 className="text-sm font-semibold text-slate-900 dark:text-gray-200">{title}</h3>
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
      <label className="text-xs font-medium text-slate-600 dark:text-gray-400">{label}</label>
      <div className="relative">
        <input
          type={isPassword && !show ? 'password' : 'text'}
          value={value}
          onChange={e => onChange?.(e.target.value)}
          readOnly={readOnly}
          placeholder={placeholder}
          className="w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-gray-900/60 border border-slate-300 dark:border-gray-700 text-sm text-slate-800 dark:text-gray-200 placeholder-slate-400 dark:placeholder-gray-600
            focus:outline-none focus:border-cyan-600 focus:ring-1 focus:ring-cyan-600/30 transition-all
            read-only:opacity-80 dark:read-only:opacity-60 read-only:cursor-default font-mono"
        />
        {isPassword && (
          <button
            onClick={() => setShow(s => !s)}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 dark:text-gray-500 hover:text-slate-600 dark:hover:text-gray-300 transition-colors cursor-pointer"
            type="button"
          >
            {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        )}
      </div>
      {hint && <p className="text-xs text-slate-500 dark:text-gray-500">{hint}</p>}
    </div>
  );
};

export const SettingsPage: React.FC<Props> = ({ activeProject, onOpenConnectModal, onProjectDeleted }) => {
  const { theme, toggleTheme } = useTheme();
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

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

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Settings & Configuration</h1>
        <p className="text-sm text-slate-500 dark:text-gray-400 mt-1">Manage display appearance, sync behavior, and active repository connections.</p>
      </div>

      {/* Appearance & Theme Section */}
      <Section title="Appearance & Visual Theme" icon={theme === 'dark' ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}>
        <div className="space-y-2">
          <p className="text-xs text-slate-500 dark:text-gray-400">
            Select your preferred display theme. Theme changes apply instantaneously across the entire software intelligence platform and are persisted in your browser.
          </p>
          <div className="grid grid-cols-2 gap-3 pt-2">
            <button
              onClick={() => theme !== 'light' && toggleTheme()}
              className={`p-3.5 rounded-xl border text-left transition-all flex items-center space-x-3 cursor-pointer ${
                theme === 'light'
                  ? 'border-cyan-500 bg-cyan-50 text-cyan-900 ring-2 ring-cyan-500/20'
                  : 'border-slate-200 dark:border-gray-800 bg-slate-50 dark:bg-gray-900/50 text-slate-600 dark:text-gray-400 hover:border-slate-300 dark:hover:border-gray-700'
              }`}
            >
              <div className="p-2 rounded-lg bg-amber-500/10 text-amber-500">
                <Sun className="w-5 h-5" />
              </div>
              <div>
                <p className="text-xs font-bold text-slate-900 dark:text-white">Light Theme</p>
                <p className="text-[11px] text-slate-500 dark:text-gray-400">Crisp, high-contrast daylight workspace</p>
              </div>
            </button>

            <button
              onClick={() => theme !== 'dark' && toggleTheme()}
              className={`p-3.5 rounded-xl border text-left transition-all flex items-center space-x-3 cursor-pointer ${
                theme === 'dark'
                  ? 'border-cyan-500 bg-cyan-950/40 text-cyan-200 ring-2 ring-cyan-500/20'
                  : 'border-slate-200 dark:border-gray-800 bg-slate-50 dark:bg-gray-900/50 text-slate-600 dark:text-gray-400 hover:border-slate-300 dark:hover:border-gray-700'
              }`}
            >
              <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400">
                <Moon className="w-5 h-5" />
              </div>
              <div>
                <p className="text-xs font-bold text-slate-900 dark:text-white">Dark Theme</p>
                <p className="text-[11px] text-slate-500 dark:text-gray-400">Deep obsidian twin observability view</p>
              </div>
            </button>
          </div>
        </div>
      </Section>

      {/* Active Project Info */}
      <Section title="Active Repository" icon={<Github className="w-4 h-4" />}>
        {activeProject ? (
          <div className="space-y-3">
            <div className="flex items-center space-x-3 p-3 rounded-xl bg-slate-50 dark:bg-gray-900/50 border border-slate-200 dark:border-gray-800">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-cyan-500 to-violet-600 flex items-center justify-center text-white text-xs font-bold shrink-0">
                {activeProject.github_owner[0]?.toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-900 dark:text-white truncate">{activeProject.full_name}</p>
                <p className="text-xs text-slate-500 dark:text-gray-500">{activeProject.language || 'Unknown language'} · {activeProject.visibility} · {activeProject.default_branch}</p>
              </div>
              <a
                href={activeProject.html_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center space-x-1 px-2.5 py-1.5 rounded-lg bg-white dark:bg-gray-800 border border-slate-200 dark:border-gray-700 text-xs text-slate-700 dark:text-gray-300 hover:text-cyan-600 dark:hover:text-cyan-400 hover:border-cyan-600 dark:hover:border-cyan-700 transition-colors shrink-0"
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
              className="text-sm text-cyan-600 dark:text-cyan-400 hover:underline cursor-pointer"
            >
              + Connect another repository
            </button>
          </div>
        ) : (
          <div className="text-center py-6 space-y-2">
            <Github className="w-8 h-8 text-slate-400 dark:text-gray-600 mx-auto" />
            <p className="text-sm text-slate-500 dark:text-gray-400">No repository connected.</p>
            <button
              onClick={onOpenConnectModal}
              className="px-4 py-2 rounded-lg bg-cyan-700/40 border border-cyan-700 text-cyan-400 text-sm hover:bg-cyan-700/60 transition-all cursor-pointer"
            >
              Connect GitHub Repository
            </button>
          </div>
        )}
      </Section>

      {/* Sync Settings */}
      <Section title="Sync & Data Collection" icon={<RefreshCw className="w-4 h-4" />}>
        <div className="grid grid-cols-2 gap-3">
          <InputField label="Commits per Sync" value="50" readOnly hint="Latest 50 commits fetched per sync." />
          <InputField label="Issues per Sync" value="50" readOnly hint="Latest 50 issues fetched per sync." />
          <InputField label="PRs per Sync" value="50" readOnly hint="Latest 50 pull requests per sync." />
          <InputField label="Contributors per Sync" value="30" readOnly hint="Top 30 contributors by commits." />
        </div>
        <div className="p-3 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 flex items-start space-x-2 text-xs text-amber-700 dark:text-amber-300">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <p>Auto-sync is not yet enabled. Click the "Sync" button in the header to refresh data manually. Scheduled background sync can be configured in backend environment parameters.</p>
        </div>
      </Section>

      {/* Danger Zone */}
      {activeProject && (
        <Section title="Danger Zone" icon={<Shield className="w-4 h-4 text-red-500" />}>
          <div className="p-3 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 flex items-start space-x-2 text-xs text-red-700 dark:text-red-300">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
            <p>Disconnecting a repository removes all synced data from PostgreSQL including commits, issues, PRs, and events. This action cannot be undone.</p>
          </div>
          {!deleteConfirm ? (
            <button
              onClick={() => setDeleteConfirm(true)}
              className="flex items-center space-x-2 px-4 py-2 rounded-xl border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm font-medium hover:bg-red-100 dark:hover:bg-red-900/40 transition-all cursor-pointer"
            >
              <Trash2 className="w-4 h-4" />
              <span>Disconnect & Delete "{activeProject.full_name}"</span>
            </button>
          ) : (
            <div className="flex items-center space-x-3">
              <span className="text-sm text-slate-700 dark:text-gray-300">Are you sure? This is irreversible.</span>
              <button
                onClick={handleDelete}
                disabled={isDeleting}
                className="px-4 py-1.5 rounded-lg bg-red-600 text-white text-sm font-semibold hover:bg-red-700 disabled:opacity-50 transition-all cursor-pointer"
              >
                {isDeleting ? 'Deleting...' : 'Yes, Delete'}
              </button>
              <button
                onClick={() => { setDeleteConfirm(false); setDeleteError(null); }}
                className="px-4 py-1.5 rounded-lg bg-slate-200 dark:bg-gray-800 text-slate-700 dark:text-gray-300 text-sm hover:bg-slate-300 dark:hover:bg-gray-700 transition-all cursor-pointer"
              >
                Cancel
              </button>
            </div>
          )}
          {deleteError && <p className="text-xs text-red-600 dark:text-red-400">{deleteError}</p>}
        </Section>
      )}
    </div>
  );
};
