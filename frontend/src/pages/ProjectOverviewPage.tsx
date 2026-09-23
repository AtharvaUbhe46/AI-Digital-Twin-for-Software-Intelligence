import React, { useState } from 'react';
import {
  Github,
  Star,
  GitFork,
  Eye,
  GitBranch,
  Tag,
  AlertCircle,
  GitPullRequest,
  Users,
  ExternalLink,
  Code2,
  Lock,
  Globe,
  Calendar,
  GitCommit,
} from 'lucide-react';
import { Project, ProjectOverviewData } from '../types';
import { EmptyState } from '../components/common/EmptyState';

interface ProjectOverviewPageProps {
  activeProject: Project | null;
  overviewData: ProjectOverviewData | null;
  isLoading: boolean;
  onOpenConnectModal: () => void;
}

export const ProjectOverviewPage: React.FC<ProjectOverviewPageProps> = ({
  activeProject,
  overviewData,
  isLoading,
  onOpenConnectModal,
}) => {
  const [activeTab, setActiveTab] = useState<'contributors' | 'issues' | 'prs' | 'releases' | 'branches'>('contributors');

  if (!activeProject && !isLoading) {
    return <EmptyState onConnectClick={onOpenConnectModal} />;
  }

  if (isLoading && !overviewData) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="flex flex-col items-center space-y-3">
          <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-xs text-gray-400 font-mono">
            Loading repository overview for {activeProject?.full_name || 'active project'}...
          </span>
        </div>
      </div>
    );
  }

  const identity = overviewData?.identity;
  const stats = overviewData?.statistics;

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return 'N/A';
    try {
      return new Date(dateStr).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="space-y-6 pb-12 animate-fadeIn max-w-7xl mx-auto">
      {/* Top Identity Card */}
      <div className="rounded-2xl border border-gray-800 bg-[#111827]/90 p-6 backdrop-blur-md">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-4 pb-6 border-b border-gray-800/80">
          <div className="flex items-start space-x-4">
            <div className="p-3 rounded-2xl bg-gradient-to-tr from-cyan-600/20 to-blue-600/20 border border-cyan-500/30 text-cyan-400 mt-1">
              <Github className="w-8 h-8" />
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2.5">
                <h1 className="text-xl font-bold text-white font-mono tracking-tight">
                  {identity?.full_name || activeProject?.full_name}
                </h1>
                <span className="flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-gray-800 text-gray-300 border border-gray-700">
                  {identity?.visibility === 'public' ? (
                    <>
                      <Globe className="w-3 h-3 text-emerald-400" />
                      <span>Public</span>
                    </>
                  ) : (
                    <>
                      <Lock className="w-3 h-3 text-amber-400" />
                      <span>Private</span>
                    </>
                  )}
                </span>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-cyan-950 text-cyan-400 border border-cyan-800">
                  Active Context
                </span>
              </div>

              <p className="mt-2 text-sm text-gray-300 max-w-3xl leading-relaxed">
                {identity?.description || 'No description provided by repository.'}
              </p>

              <div className="flex flex-wrap items-center gap-4 mt-3 text-xs text-gray-400">
                {identity?.language && (
                  <div className="flex items-center space-x-1.5">
                    <Code2 className="w-3.5 h-3.5 text-cyan-400" />
                    <span>Language: <strong className="text-white font-mono">{identity.language}</strong></span>
                  </div>
                )}
                <div className="flex items-center space-x-1.5">
                  <GitBranch className="w-3.5 h-3.5 text-purple-400" />
                  <span>Default Branch: <strong className="text-white font-mono">{identity?.default_branch || 'main'}</strong></span>
                </div>
                <div className="flex items-center space-x-1.5">
                  <Calendar className="w-3.5 h-3.5 text-gray-500" />
                  <span>Created: {formatDate(identity?.created_at)}</span>
                </div>
                <div className="flex items-center space-x-1.5">
                  <Calendar className="w-3.5 h-3.5 text-gray-500" />
                  <span>Last Updated: {formatDate(identity?.updated_at)}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Direct Link to GitHub */}
          {identity?.html_url && (
            <a
              href={identity.html_url}
              target="_blank"
              rel="noreferrer"
              className="flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-gray-800 hover:bg-gray-700 text-xs font-semibold text-white border border-gray-700 transition shrink-0"
            >
              <span>View on GitHub</span>
              <ExternalLink className="w-3.5 h-3.5 text-gray-400" />
            </a>
          )}
        </div>

        {/* Live Repository Statistics Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3 mt-6">
          <div className="p-3 rounded-xl bg-gray-900/60 border border-gray-800/80">
            <div className="flex items-center space-x-1.5 text-amber-400 text-xs">
              <Star className="w-3.5 h-3.5" />
              <span className="text-gray-400 font-medium">Stars</span>
            </div>
            <div className="text-lg font-bold text-white font-mono mt-1">
              {stats?.stars.toLocaleString() ?? '0'}
            </div>
          </div>

          <div className="p-3 rounded-xl bg-gray-900/60 border border-gray-800/80">
            <div className="flex items-center space-x-1.5 text-blue-400 text-xs">
              <GitFork className="w-3.5 h-3.5" />
              <span className="text-gray-400 font-medium">Forks</span>
            </div>
            <div className="text-lg font-bold text-white font-mono mt-1">
              {stats?.forks.toLocaleString() ?? '0'}
            </div>
          </div>

          <div className="p-3 rounded-xl bg-gray-900/60 border border-gray-800/80">
            <div className="flex items-center space-x-1.5 text-purple-400 text-xs">
              <Eye className="w-3.5 h-3.5" />
              <span className="text-gray-400 font-medium">Watchers</span>
            </div>
            <div className="text-lg font-bold text-white font-mono mt-1">
              {stats?.watchers.toLocaleString() ?? '0'}
            </div>
          </div>

          <div className="p-3 rounded-xl bg-gray-900/60 border border-gray-800/80">
            <div className="flex items-center space-x-1.5 text-rose-400 text-xs">
              <AlertCircle className="w-3.5 h-3.5" />
              <span className="text-gray-400 font-medium">Open Issues</span>
            </div>
            <div className="text-lg font-bold text-white font-mono mt-1">
              {stats?.open_issues.toLocaleString() ?? '0'}
            </div>
          </div>

          <div className="p-3 rounded-xl bg-gray-900/60 border border-gray-800/80">
            <div className="flex items-center space-x-1.5 text-cyan-400 text-xs">
              <GitPullRequest className="w-3.5 h-3.5" />
              <span className="text-gray-400 font-medium">Open PRs</span>
            </div>
            <div className="text-lg font-bold text-white font-mono mt-1">
              {stats?.open_prs.toLocaleString() ?? '0'}
            </div>
          </div>

          <div className="p-3 rounded-xl bg-gray-900/60 border border-gray-800/80">
            <div className="flex items-center space-x-1.5 text-emerald-400 text-xs">
              <GitCommit className="w-3.5 h-3.5" />
              <span className="text-gray-400 font-medium">Commits</span>
            </div>
            <div className="text-lg font-bold text-white font-mono mt-1">
              {stats?.commits_count.toLocaleString() ?? '0'}
            </div>
          </div>

          <div className="p-3 rounded-xl bg-gray-900/60 border border-gray-800/80">
            <div className="flex items-center space-x-1.5 text-indigo-400 text-xs">
              <Users className="w-3.5 h-3.5" />
              <span className="text-gray-400 font-medium">Authors</span>
            </div>
            <div className="text-lg font-bold text-white font-mono mt-1">
              {stats?.contributors_count.toLocaleString() ?? '0'}
            </div>
          </div>

          <div className="p-3 rounded-xl bg-gray-900/60 border border-gray-800/80">
            <div className="flex items-center space-x-1.5 text-pink-400 text-xs">
              <Tag className="w-3.5 h-3.5" />
              <span className="text-gray-400 font-medium">Releases</span>
            </div>
            <div className="text-lg font-bold text-white font-mono mt-1">
              {stats?.releases_count.toLocaleString() ?? '0'}
            </div>
          </div>
        </div>
      </div>

      {/* Tabs for Detailed Entity Inspection */}
      <div className="rounded-2xl border border-gray-800 bg-[#111827]/90 backdrop-blur-md overflow-hidden">
        <div className="flex border-b border-gray-800 bg-gray-900/40 px-6 pt-3 space-x-2 overflow-x-auto">
          {[
            { id: 'contributors', label: 'Contributors', count: overviewData?.contributors.length },
            { id: 'issues', label: 'Recent Issues', count: overviewData?.recent_issues.length },
            { id: 'prs', label: 'Pull Requests', count: overviewData?.recent_pull_requests.length },
            { id: 'releases', label: 'Releases', count: overviewData?.releases.length },
            { id: 'branches', label: 'Branches', count: overviewData?.branches.length },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center space-x-2 px-4 py-2.5 text-xs font-semibold rounded-t-xl transition border-b-2 ${
                activeTab === tab.id
                  ? 'border-cyan-400 text-cyan-300 bg-gray-800/60'
                  : 'border-transparent text-gray-400 hover:text-gray-200 hover:bg-gray-800/30'
              }`}
            >
              <span>{tab.label}</span>
              {typeof tab.count === 'number' && (
                <span className="px-1.5 py-0.5 rounded-full text-[10px] bg-gray-800 text-gray-300 font-mono">
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {/* Contributors Tab */}
          {activeTab === 'contributors' && (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3.5">
              {overviewData?.contributors && overviewData.contributors.length > 0 ? (
                overviewData.contributors.map((c) => (
                  <div
                    key={c.id}
                    className="p-3.5 rounded-xl bg-gray-900/60 border border-gray-800/80 flex items-center space-x-3 hover:border-gray-700 transition"
                  >
                    {c.avatar_url ? (
                      <img
                        src={c.avatar_url}
                        alt={c.login}
                        className="w-10 h-10 rounded-full border border-gray-700 shrink-0"
                      />
                    ) : (
                      <div className="w-10 h-10 rounded-full bg-cyan-900/40 border border-cyan-800 flex items-center justify-center font-bold text-cyan-400 text-xs">
                        {c.login.substring(0, 2).toUpperCase()}
                      </div>
                    )}
                    <div className="truncate flex-1">
                      <div className="font-semibold text-white text-xs truncate flex items-center justify-between">
                        <span className="truncate">{c.login}</span>
                        {c.html_url && (
                          <a
                            href={c.html_url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-gray-500 hover:text-cyan-400 ml-1"
                          >
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                      </div>
                      <div className="text-[11px] text-gray-400 mt-0.5">
                        <strong className="text-cyan-400 font-mono">{c.contributions}</strong> commits
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="col-span-full text-xs text-gray-400 italic p-6 text-center">
                  No contributor data available.
                </div>
              )}
            </div>
          )}

          {/* Issues Tab */}
          {activeTab === 'issues' && (
            <div className="divide-y divide-gray-800/60">
              {overviewData?.recent_issues && overviewData.recent_issues.length > 0 ? (
                overviewData.recent_issues.map((iss) => (
                  <div key={iss.id} className="py-3 flex items-start justify-between gap-4">
                    <div className="flex items-start space-x-3">
                      <AlertCircle
                        className={`w-4 h-4 shrink-0 mt-0.5 ${
                          iss.state === 'open' ? 'text-emerald-400' : 'text-purple-400'
                        }`}
                      />
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className="text-xs font-semibold text-white hover:text-cyan-300 transition">
                            {iss.title}
                          </span>
                          <span className="text-[11px] font-mono text-gray-500">#{iss.number}</span>
                        </div>
                        <div className="flex flex-wrap items-center gap-2 mt-1 text-[11px] text-gray-400">
                          <span>by {iss.author_login || 'ghost'}</span>
                          <span>•</span>
                          <span>{formatDate(iss.created_at)}</span>
                          {iss.labels && iss.labels.map((lbl, idx) => (
                            <span
                              key={idx}
                              className="px-1.5 py-0.5 rounded bg-gray-800 text-[10px] text-cyan-300 border border-gray-700"
                            >
                              {lbl}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                    {iss.html_url && (
                      <a
                        href={iss.html_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-gray-400 hover:text-cyan-400 shrink-0 p-1"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    )}
                  </div>
                ))
              ) : (
                <div className="text-xs text-gray-400 italic p-6 text-center">
                  No issues found for this repository.
                </div>
              )}
            </div>
          )}

          {/* Pull Requests Tab */}
          {activeTab === 'prs' && (
            <div className="divide-y divide-gray-800/60">
              {overviewData?.recent_pull_requests && overviewData.recent_pull_requests.length > 0 ? (
                overviewData.recent_pull_requests.map((pr) => (
                  <div key={pr.id} className="py-3 flex items-start justify-between gap-4">
                    <div className="flex items-start space-x-3">
                      <GitPullRequest
                        className={`w-4 h-4 shrink-0 mt-0.5 ${
                          pr.is_merged ? 'text-purple-400' : (pr.state === 'open' ? 'text-emerald-400' : 'text-rose-400')
                        }`}
                      />
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className="text-xs font-semibold text-white hover:text-cyan-300 transition">
                            {pr.title}
                          </span>
                          <span className="text-[11px] font-mono text-gray-500">#{pr.number}</span>
                          {pr.is_merged && (
                            <span className="px-1.5 py-0.2 rounded text-[10px] bg-purple-950 text-purple-300 border border-purple-800">
                              Merged
                            </span>
                          )}
                        </div>
                        <div className="flex items-center space-x-2 mt-1 text-[11px] text-gray-400">
                          <span>by {pr.author_login || 'ghost'}</span>
                          <span>•</span>
                          <span>{formatDate(pr.created_at)}</span>
                        </div>
                      </div>
                    </div>
                    {pr.html_url && (
                      <a
                        href={pr.html_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-gray-400 hover:text-cyan-400 shrink-0 p-1"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    )}
                  </div>
                ))
              ) : (
                <div className="text-xs text-gray-400 italic p-6 text-center">
                  No pull requests recorded.
                </div>
              )}
            </div>
          )}

          {/* Releases Tab */}
          {activeTab === 'releases' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {overviewData?.releases && overviewData.releases.length > 0 ? (
                overviewData.releases.map((rel) => (
                  <div
                    key={rel.id}
                    className="p-4 rounded-xl bg-gray-900/60 border border-gray-800/80 hover:border-gray-700 transition"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center space-x-2">
                          <Tag className="w-3.5 h-3.5 text-cyan-400" />
                          <span className="font-bold text-white text-xs font-mono">{rel.tag_name}</span>
                          {rel.is_prerelease && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-950 text-amber-400 border border-amber-800">
                              Pre-release
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-gray-300 mt-1 font-semibold">
                          {rel.name || rel.tag_name}
                        </div>
                        <div className="text-[11px] text-gray-400 mt-2">
                          Published on {formatDate(rel.published_at)} by {rel.author_login || 'maintainer'}
                        </div>
                      </div>
                      {rel.html_url && (
                        <a
                          href={rel.html_url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-gray-400 hover:text-cyan-400"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      )}
                    </div>
                  </div>
                ))
              ) : (
                <div className="col-span-full text-xs text-gray-400 italic p-6 text-center">
                  No releases found on this repository.
                </div>
              )}
            </div>
          )}

          {/* Branches Tab */}
          {activeTab === 'branches' && (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              {overviewData?.branches && overviewData.branches.length > 0 ? (
                overviewData.branches.map((br) => (
                  <div
                    key={br.id}
                    className="p-3 rounded-xl bg-gray-900/60 border border-gray-800/80 flex items-center justify-between"
                  >
                    <div className="flex items-center space-x-2 truncate">
                      <GitBranch className="w-3.5 h-3.5 text-purple-400 shrink-0" />
                      <span className="font-mono text-xs text-white truncate">{br.name}</span>
                      {br.is_default && (
                        <span className="text-[10px] px-1.5 py-0.2 rounded bg-cyan-950 text-cyan-400 border border-cyan-800 shrink-0">
                          default
                        </span>
                      )}
                    </div>
                    {br.commit_sha && (
                      <span className="text-[10px] font-mono text-gray-500 shrink-0 ml-2">
                        {br.commit_sha.substring(0, 7)}
                      </span>
                    )}
                  </div>
                ))
              ) : (
                <div className="col-span-full text-xs text-gray-400 italic p-6 text-center">
                  No branch details recorded.
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
