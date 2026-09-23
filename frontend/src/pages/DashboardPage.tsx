import React from 'react';
import {
  HeartPulse,
  ShieldAlert,
  GitCommit,
  Users,
  GitPullRequest,
  AlertCircle,
  Clock,
  ExternalLink,
} from 'lucide-react';
import { HealthResponse, Project, LiveDashboardData, RiskSummary } from '../types';
import { apiService } from '../services/api';
import { SystemStatusBanner } from '../components/dashboard/SystemStatusBanner';
import { StatCard } from '../components/common/StatCard';
import { HealthScoreGauge } from '../components/dashboard/HealthScoreGauge';
import { ActivityChart } from '../components/dashboard/ActivityChart';
import { ModuleRiskTable } from '../components/dashboard/ModuleRiskTable';
import { EmptyState } from '../components/common/EmptyState';

interface DashboardPageProps {
  health: HealthResponse | null;
  activeProject: Project | null;
  dashboardData: LiveDashboardData | null;
  isLoading: boolean;
  error: string | null;
  onOpenConnectModal: () => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  health,
  activeProject,
  dashboardData,
  isLoading,
  error,
  onOpenConnectModal,
}) => {
  const [riskSummary, setRiskSummary] = React.useState<RiskSummary | null>(null);

  React.useEffect(() => {
    if (!activeProject) {
      setRiskSummary(null);
      return;
    }
    apiService
      .getRisksSummary(activeProject.id)
      .then(res => setRiskSummary(res))
      .catch(() => setRiskSummary(null));
  }, [activeProject?.id]);

  // If no repository is connected, display clean Empty State
  if (!activeProject && !isLoading) {
    return <EmptyState onConnectClick={onOpenConnectModal} />;
  }

  if (isLoading && !dashboardData) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="flex flex-col items-center space-y-3">
          <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-xs text-gray-400 font-mono">
            Extracting live GitHub telemetry for {activeProject?.full_name || 'project'}...
          </span>
        </div>
      </div>
    );
  }

  const avgHealth = dashboardData?.health_score ?? activeProject?.health_score ?? 0;

  // Format relative event time
  const formatEventTime = (timeStr?: string) => {
    if (!timeStr) return '';
    try {
      const dt = new Date(timeStr);
      const now = new Date();
      const diffSec = Math.floor((now.getTime() - dt.getTime()) / 1000);
      if (diffSec < 60) return 'Just now';
      const diffMin = Math.floor(diffSec / 60);
      if (diffMin < 60) return `${diffMin}m ago`;
      const diffHrs = Math.floor(diffMin / 60);
      if (diffHrs < 24) return `${diffHrs}h ago`;
      const diffDays = Math.floor(diffHrs / 24);
      return `${diffDays}d ago`;
    } catch {
      return timeStr;
    }
  };

  return (
    <div className="space-y-6 pb-12 animate-fadeIn">
      {/* Live System Architecture Banner */}
      <SystemStatusBanner health={health} activeProject={activeProject} error={error} />

      {/* Primary Real KPI Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <StatCard
          title="Health Index"
          value={`${avgHealth.toFixed(1)}%`}
          subtitle="Repository Health Score"
          change={avgHealth >= 70 ? 'Optimal' : 'Active'}
          isPositive={avgHealth >= 60}
          icon={HeartPulse}
          color="emerald"
        />
        <StatCard
          title="Open Risks"
          value={riskSummary ? String(riskSummary.open_count) : '0'}
          subtitle={
            riskSummary
              ? `${riskSummary.critical_count} critical, ${riskSummary.high_count} high`
              : 'Rule-based analysis'
          }
          change={riskSummary && riskSummary.critical_count > 0 ? 'Critical' : 'Phase 4'}
          isPositive={!riskSummary || (riskSummary.critical_count === 0 && riskSummary.high_count === 0)}
          icon={ShieldAlert}
          color={
            riskSummary && riskSummary.critical_count > 0
              ? 'rose'
              : riskSummary && riskSummary.high_count > 0
              ? 'amber'
              : 'emerald'
          }
        />
        <StatCard
          title="Commits Tracked"
          value={dashboardData?.total_commits.toLocaleString() ?? '0'}
          subtitle="Recent default branch"
          change="Live"
          isPositive={true}
          icon={GitCommit}
          color="cyan"
        />
        <StatCard
          title="Active Authors"
          value={dashboardData?.total_contributors.toLocaleString() ?? '0'}
          subtitle="Repository contributors"
          change="Real"
          isPositive={true}
          icon={Users}
          color="purple"
        />
        <StatCard
          title="Open PRs"
          value={dashboardData?.open_pull_requests.toLocaleString() ?? '0'}
          subtitle="Pending integration"
          change="Live"
          isPositive={true}
          icon={GitPullRequest}
          color="cyan"
        />
        <StatCard
          title="Open Issues"
          value={dashboardData?.open_issues.toLocaleString() ?? '0'}
          subtitle="Active defect backlog"
          change="Live"
          isPositive={true}
          icon={AlertCircle}
          color="rose"
        />
      </div>

      {/* Row 2: Explainable Health Model & Live Activity Velocity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <HealthScoreGauge score={avgHealth} healthIndex={dashboardData?.health_index} />
        <ActivityChart timeline={dashboardData?.activity_timeline ?? []} />
      </div>

      {/* Row 3: Component Risk Breakdown & Real Event Feed */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2">
          <ModuleRiskTable activeProject={activeProject} />
        </div>

        {/* Live GitHub Event Feed */}
        <div className="rounded-xl border border-gray-800 bg-[#111827]/80 p-5 backdrop-blur-md flex flex-col">
          <div className="flex items-center justify-between border-b border-gray-800/80 pb-3.5 mb-4">
            <div className="flex items-center space-x-2">
              <Clock className="w-4 h-4 text-cyan-400" />
              <h3 className="text-sm font-semibold text-white">Digital Twin Event Feed</h3>
            </div>
            <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950 px-2 py-0.5 rounded border border-emerald-800">
              Live GitHub
            </span>
          </div>

          <div className="space-y-3 flex-1 overflow-y-auto max-h-[380px]">
            {dashboardData?.recent_activity && dashboardData.recent_activity.length > 0 ? (
              dashboardData.recent_activity.map((act) => (
                <div
                  key={act.id}
                  className="p-3 rounded-lg bg-gray-900/60 border border-gray-800/60 hover:border-gray-700 transition"
                >
                  <div className="flex items-start justify-between">
                    <span className="text-xs font-semibold text-white leading-snug break-words">
                      {act.title}
                    </span>
                    {act.html_url && (
                      <a
                        href={act.html_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-gray-400 hover:text-cyan-400 shrink-0 ml-2"
                        title="View on GitHub"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    )}
                  </div>
                  <div className="mt-2 flex items-center justify-between text-[11px] text-gray-400">
                    <span className="font-mono text-cyan-400 truncate max-w-[120px]">
                      {act.actor_login || 'GitHub User'}
                    </span>
                    <span>{formatEventTime(act.event_time)}</span>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-xs text-gray-400 italic p-6 text-center">
                No recent events recorded.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
