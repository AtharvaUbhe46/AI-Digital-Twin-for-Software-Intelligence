import React from 'react';
import {
  LayoutDashboard,
  FolderGit2,
  Cpu,
  ShieldAlert,
  HeartPulse,
  Share2,
  Network,
  AlertTriangle,
  Bot,
  Sliders,
  Settings,
  Sparkles,
  Activity,
} from 'lucide-react';

export interface NavItem {
  id: string;
  name: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
  phase?: string;
}

interface SidebarProps {
  activeTab: string;
  onTabChange: (id: string) => void;
}

export const NAV_ITEMS: NavItem[] = [
  { id: 'dashboard', name: 'Dashboard', icon: LayoutDashboard },
  { id: 'project-overview', name: 'Project Overview', icon: FolderGit2 },
  { id: 'digital-twin', name: 'Digital Twin Core', icon: Cpu },
  { id: 'software-health', name: 'Software Health', icon: HeartPulse },
  { id: 'risk-analysis', name: 'Risk Detection', icon: ShieldAlert },
  { id: 'knowledge-graph', name: 'Knowledge Graph', icon: Share2 },
  { id: 'architecture', name: 'Architecture & Deps', icon: Network },
  { id: 'technical-debt', name: 'Technical Debt', icon: AlertTriangle },
  { id: 'ai-assistant', name: 'AI Project Assistant', icon: Bot },
  { id: 'simulation', name: 'What-If Simulation', icon: Sliders },
  { id: 'settings', name: 'Settings & Config', icon: Settings },
];

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, onTabChange }) => {
  return (
    <aside className="w-64 bg-white dark:bg-[#0B0F17] border-r border-slate-200 dark:border-gray-800 flex flex-col shrink-0 h-screen sticky top-0 select-none transition-colors duration-200">
      {/* Brand Logo */}
      <div className="h-16 flex items-center px-6 border-b border-slate-200 dark:border-gray-800 space-x-3">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-600 to-blue-500 flex items-center justify-center shadow-lg shadow-cyan-500/20 shrink-0">
          <Sparkles className="w-4 h-4 text-white" />
        </div>
        <div className="min-w-0">
          <h1 className="font-bold text-sm tracking-tight text-slate-900 dark:text-white flex items-center">
            DigitalTwin <span className="text-cyan-500 dark:text-cyan-400 ml-1">AI</span>
          </h1>
          <p className="text-[10px] text-slate-500 dark:text-gray-400 font-mono tracking-wider uppercase truncate">
            Software Intelligence
          </p>
        </div>
      </div>

      {/* Navigation Menu */}
      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
        <div className="px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-slate-400 dark:text-gray-400">
          Observability Platform
        </div>
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all group ${
                isActive
                  ? 'bg-cyan-50 text-cyan-700 border border-cyan-200 shadow-sm font-semibold dark:bg-cyan-500/10 dark:text-cyan-400 dark:border-cyan-500/30 dark:shadow-none'
                  : 'text-slate-600 dark:text-gray-400 hover:text-slate-900 dark:hover:text-gray-200 hover:bg-slate-100 dark:hover:bg-gray-800/60'
              }`}
            >
              <div className="flex items-center space-x-3 truncate">
                <Icon
                  className={`w-4 h-4 shrink-0 transition-colors ${
                    isActive
                      ? 'text-cyan-600 dark:text-cyan-400'
                      : 'text-slate-400 dark:text-gray-400 group-hover:text-slate-600 dark:group-hover:text-gray-300'
                  }`}
                />
                <span className="truncate">{item.name}</span>
              </div>
            </button>
          );
        })}
      </div>

      {/* System Status Footer */}
      <div className="p-4 border-t border-slate-200 dark:border-gray-800 bg-slate-50/80 dark:bg-gray-900/40">
        <div className="text-[11px] text-slate-600 dark:text-gray-400 flex items-center justify-between mb-1.5">
          <span className="font-medium">System Status</span>
          <span className="inline-flex items-center space-x-1 text-emerald-600 dark:text-emerald-400 font-mono font-medium text-[10px]">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span>Operational</span>
          </span>
        </div>
        <div className="w-full bg-slate-200 dark:bg-gray-800 h-1.5 rounded-full overflow-hidden">
          <div className="bg-gradient-to-r from-cyan-500 to-blue-500 h-full w-[100%] rounded-full" />
        </div>
        <div className="mt-2 text-[10px] text-slate-500 dark:text-gray-400 leading-relaxed flex items-center space-x-1">
          <Activity className="w-3 h-3 text-cyan-500 shrink-0" />
          <span className="truncate">AI Assistant (Ollama + Qwen)</span>
        </div>
      </div>
    </aside>
  );
};
