import React, { useState } from 'react';
import {
  Layers,
  Package,
  ArrowDownLeft,
  ArrowUpRight,
  AlertCircle,
  CheckCircle2,
  ExternalLink,
  Search,
} from 'lucide-react';
import { ModuleCouplingMetric, PackageDependency } from '../../types';

interface Props {
  modules: ModuleCouplingMetric[];
  packages: PackageDependency[];
}

export const DependencyMatrixTable: React.FC<Props> = ({ modules, packages }) => {
  const [activeTab, setActiveTab] = useState<'modules' | 'packages'>('modules');
  const [searchTerm, setSearchTerm] = useState<string>('');

  const filteredModules = modules.filter((m) =>
    m.module.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const filteredPackages = packages.filter((p) =>
    p.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="bg-[#111827] border border-gray-800 rounded-2xl p-6 space-y-5 shadow-xl">
      {/* Subheader and Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center space-x-2 bg-[#0B0F17] p-1 rounded-xl border border-gray-800 w-fit">
          <button
            onClick={() => setActiveTab('modules')}
            className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center space-x-2 ${
              activeTab === 'modules'
                ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 shadow-sm'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Module Coupling ({modules.length})</span>
          </button>
          <button
            onClick={() => setActiveTab('packages')}
            className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center space-x-2 ${
              activeTab === 'packages'
                ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40 shadow-sm'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            <Package className="w-3.5 h-3.5" />
            <span>External Packages ({packages.length})</span>
          </button>
        </div>

        {/* Search */}
        <div className="relative max-w-xs w-full">
          <Search className="w-3.5 h-3.5 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder={activeTab === 'modules' ? 'Filter modules...' : 'Filter packages...'}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-[#0B0F17] border border-gray-800 rounded-xl pl-9 pr-3 py-1.5 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-cyan-500/50"
          />
        </div>
      </div>

      {/* Content View 1: Module Coupling Matrix */}
      {activeTab === 'modules' && (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-gray-300">
            <thead className="bg-[#0B0F17] text-gray-400 uppercase text-[10px] font-mono tracking-wider border-b border-gray-800">
              <tr>
                <th className="px-4 py-3">Module</th>
                <th className="px-4 py-3">Files</th>
                <th className="px-4 py-3 text-center">
                  <span className="flex items-center justify-center space-x-1" title="Afferent Coupling: incoming dependents">
                    <ArrowDownLeft className="w-3 h-3 text-cyan-400" />
                    <span>Fan-In (Ca)</span>
                  </span>
                </th>
                <th className="px-4 py-3 text-center">
                  <span className="flex items-center justify-center space-x-1" title="Efferent Coupling: outgoing dependencies">
                    <ArrowUpRight className="w-3 h-3 text-blue-400" />
                    <span>Fan-Out (Ce)</span>
                  </span>
                </th>
                <th className="px-4 py-3">Instability Index (I)</th>
                <th className="px-4 py-3 text-right">Architectural Role</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/60 font-mono">
              {filteredModules.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-gray-400 italic">
                    No matching modules found.
                  </td>
                </tr>
              ) : (
                filteredModules.map((m) => {
                  const stabilityClass =
                    m.instability <= 0.25
                      ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30'
                      : m.instability >= 0.75
                      ? 'text-amber-400 bg-amber-500/10 border-amber-500/30'
                      : 'text-blue-400 bg-blue-500/10 border-blue-500/30';

                  const roleLabel =
                    m.instability <= 0.25
                      ? 'Core Service (Stable)'
                      : m.instability >= 0.75
                      ? 'High Instability / Consumer'
                      : 'Balanced Layer';

                  return (
                    <tr key={m.module} className="hover:bg-gray-800/40 transition-colors">
                      <td className="px-4 py-3 font-semibold text-white truncate max-w-xs">
                        {m.module}
                      </td>
                      <td className="px-4 py-3 text-gray-400">{m.total_files}</td>
                      <td className="px-4 py-3 text-center text-cyan-400 font-bold">
                        {m.afferent_coupling}
                      </td>
                      <td className="px-4 py-3 text-center text-blue-400 font-bold">
                        {m.efferent_coupling}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center space-x-2">
                          <span className="w-8 text-right font-bold text-gray-200">
                            {m.instability.toFixed(2)}
                          </span>
                          <div className="w-24 bg-gray-800 h-1.5 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full ${
                                m.instability <= 0.25
                                  ? 'bg-emerald-400'
                                  : m.instability >= 0.75
                                  ? 'bg-amber-400'
                                  : 'bg-blue-400'
                              }`}
                              style={{ width: `${m.instability * 100}%` }}
                            />
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className={`text-[10px] px-2 py-0.5 rounded border uppercase ${stabilityClass}`}>
                          {roleLabel}
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Content View 2: External Packages */}
      {activeTab === 'packages' && (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-gray-300">
            <thead className="bg-[#0B0F17] text-gray-400 uppercase text-[10px] font-mono tracking-wider border-b border-gray-800">
              <tr>
                <th className="px-4 py-3">Package Name</th>
                <th className="px-4 py-3">Version Spec</th>
                <th className="px-4 py-3">Declared In</th>
                <th className="px-4 py-3 text-center">Files Using</th>
                <th className="px-4 py-3 text-right">Usage Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/60 font-mono">
              {filteredPackages.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-gray-400 italic">
                    No matching external packages found.
                  </td>
                </tr>
              ) : (
                filteredPackages.map((pkg) => (
                  <tr key={`${pkg.name}-${pkg.declared_in}`} className="hover:bg-gray-800/40 transition-colors">
                    <td className="px-4 py-3 font-semibold text-white flex items-center space-x-2">
                      <Package className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                      <span>{pkg.name}</span>
                    </td>
                    <td className="px-4 py-3 text-gray-400">{pkg.version || 'Any'}</td>
                    <td className="px-4 py-3 text-gray-400 truncate max-w-xs">{pkg.declared_in}</td>
                    <td className="px-4 py-3 text-center font-bold text-gray-200">
                      {pkg.usage_count}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {pkg.is_unused ? (
                        <span className="inline-flex items-center space-x-1 text-[10px] px-2 py-0.5 rounded border border-rose-500/30 bg-rose-500/10 text-rose-400 uppercase font-bold">
                          <AlertCircle className="w-3 h-3" />
                          <span>Potentially Unused</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center space-x-1 text-[10px] px-2 py-0.5 rounded border border-emerald-500/30 bg-emerald-500/10 text-emerald-400 uppercase font-bold">
                          <CheckCircle2 className="w-3 h-3" />
                          <span>Active ({pkg.usage_count} imports)</span>
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
