import React from 'react';
import {
  LayoutDashboard,
  FolderGit2,
  Cpu,
  ShieldAlert,
  HeartPulse,
  Share2,
  Network,
  History,
  AlertTriangle,
  Bot,
  Sliders,
  Settings,
  Sparkles,
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
  { id: 'dashboard', name: 'Dashboard', icon: LayoutDashboard, badge: 'Phase 1' },
  { id: 'project-overview', name: 'Project Overview', icon: FolderGit2, phase: 'Phase 2' },
  { id: 'digital-twin', name: 'Digital Twin Core', icon: Cpu, phase: 'Phase 3' },
  { id: 'software-health', name: 'Software Health', icon: HeartPulse, phase: 'Phase 4' },
  { id: 'risk-analysis', name: 'Risk Detection', icon: ShieldAlert, phase: 'Phase 4' },
  { id: 'knowledge-graph', name: 'Knowledge Graph', icon: Share2, phase: 'Phase 5' },
  { id: 'architecture', name: 'Architecture & Deps', icon: Network, phase: 'Phase 5' },
  { id: 'evolution', name: 'Software Evolution', icon: History, phase: 'Phase 6' },
  { id: 'technical-debt', name: 'Technical Debt', icon: AlertTriangle, phase: 'Phase 6' },
  { id: 'ai-assistant', name: 'AI Project Assistant', icon: Bot, phase: 'Phase 7' },
  { id: 'simulation', name: 'What-If Simulation', icon: Sliders, phase: 'Phase 8' },
  { id: 'settings', name: 'Settings & Config', icon: Settings, phase: 'Phase 9' },
];

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, onTabChange }) => {
  return (
    <aside className="w-64 bg-[#0B0F17] border-r border-gray-800 flex flex-col shrink-0 h-screen sticky top-0 select-none">
      {/* Brand Logo */}
      <div className="h-16 flex items-center px-6 border-b border-gray-800 space-x-3">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-600 to-blue-500 flex items-center justify-center shadow-lg shadow-cyan-500/20">
          <Sparkles className="w-4 h-4 text-white" />
        </div>
        <div>
          <h1 className="font-bold text-sm tracking-tight text-white flex items-center">
            DigitalTwin <span className="text-cyan-400 ml-1">AI</span>
          </h1>
          <p className="text-[10px] text-gray-400 font-mono tracking-wider uppercase">
            Software Intelligence
          </p>
        </div>
      </div>

      {/* Navigation Menu */}
      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
        <div className="px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-gray-400">
          Intelligence Core
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
                  ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/60'
              }`}
            >
              <div className="flex items-center space-x-3">
                <Icon
                  className={`w-4 h-4 transition-colors ${
                    isActive ? 'text-cyan-400' : 'text-gray-400 group-hover:text-gray-300'
                  }`}
                />
                <span>{item.name}</span>
              </div>
              {item.badge && (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800/80">
                  {item.badge}
                </span>
              )}
              {item.phase && !isActive && (
                <span className="text-[9px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-400 border border-gray-700/50">
                  {item.phase}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* System Phase Info Footer */}
      <div className="p-4 border-t border-gray-800 bg-gray-900/40">
        <div className="text-[11px] text-gray-400 flex items-center justify-between mb-1">
          <span>Active Architecture</span>
          <span className="text-cyan-400 font-mono font-medium">Phase 1 / 9</span>
        </div>
        <div className="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden">
          <div className="bg-gradient-to-r from-cyan-500 to-blue-500 h-full w-[12%] rounded-full" />
        </div>
        <div className="mt-2 text-[10px] text-gray-400 leading-relaxed">
          Foundation & Modular Scaffolding MVP
        </div>
      </div>
    </aside>
  );
};
