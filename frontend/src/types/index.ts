export interface DatabaseHealth {
  connected: boolean;
  status: string;
  latency_ms?: number;
  error?: string;
}

export interface GitHubHealth {
  connected: boolean;
  remaining_rate_limit: number;
  limit: number;
  authenticated: boolean;
}

export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  service: string;
  version: string;
  environment: string;
  timestamp: string;
  database: DatabaseHealth;
  github?: GitHubHealth;
  details?: Record<string, any>;
}

export interface Project {
  id: number;
  github_owner: string;
  github_repo: string;
  name: string;
  full_name: string;
  description?: string;
  html_url: string;
  default_branch: string;
  language?: string;
  visibility: string;
  stars_count: number;
  forks_count: number;
  watchers_count: number;
  open_issues_count: number;
  open_prs_count: number;
  license_name?: string;
  repo_created_at?: string;
  repo_updated_at?: string;
  repo_pushed_at?: string;
  last_synced_at?: string;
  is_active: boolean;
  health_score: number;
  status: 'synced' | 'syncing' | 'error';
  created_at: string;
  updated_at: string;
}

export interface HealthIndexComponent {
  name: string;
  weight: string;
  score: number;
  max_score: number;
  detail: string;
}

export interface HealthIndexDetails {
  score: number;
  formula: string;
  components: HealthIndexComponent[];
}

export interface TimelineDataPoint {
  date: string;
  commits: number;
  pull_requests: number;
}

export interface ProjectEvent {
  id: number;
  event_type: 'commit' | 'pr_open' | 'pr_merge' | 'pr_close' | 'issue_open' | 'issue_close' | 'release';
  title: string;
  actor_login?: string;
  actor_avatar_url?: string;
  event_time: string;
  html_url?: string;
}

export interface LiveDashboardData {
  project_id: number;
  full_name: string;
  health_score: number;
  health_index?: HealthIndexDetails;
  total_commits: number;
  total_contributors: number;
  open_pull_requests: number;
  open_issues: number;
  last_synced_at?: string;
  risk_modules_status: string;
  activity_timeline: TimelineDataPoint[];
  recent_activity: ProjectEvent[];
}

export interface Contributor {
  id: number;
  login: string;
  avatar_url?: string;
  html_url?: string;
  contributions: number;
  contributor_type: string;
}

export interface Branch {
  id: number;
  name: string;
  commit_sha?: string;
  is_protected: boolean;
  is_default: boolean;
}

export interface Release {
  id: number;
  tag_name: string;
  name?: string;
  author_login?: string;
  published_at?: string;
  html_url?: string;
  is_prerelease: boolean;
}

export interface Issue {
  id: number;
  number: number;
  title: string;
  state: string;
  author_login?: string;
  author_avatar_url?: string;
  labels?: string[];
  comments_count: number;
  created_at?: string;
  closed_at?: string;
  html_url?: string;
}

export interface PullRequest {
  id: number;
  number: number;
  title: string;
  state: string;
  author_login?: string;
  author_avatar_url?: string;
  is_merged: boolean;
  draft: boolean;
  created_at?: string;
  updated_at?: string;
  merged_at?: string;
  closed_at?: string;
  html_url?: string;
}

export interface RepoIdentity {
  name: string;
  owner: string;
  repo: string;
  full_name: string;
  description?: string;
  html_url: string;
  default_branch: string;
  language?: string;
  visibility: string;
  license_name?: string;
  created_at?: string;
  updated_at?: string;
  pushed_at?: string;
  last_synced_at?: string;
}

export interface RepoStatistics {
  stars: number;
  forks: number;
  watchers: number;
  open_issues: number;
  open_prs: number;
  commits_count: number;
  contributors_count: number;
  releases_count: number;
}

export interface ProjectOverviewData {
  project_id: number;
  identity: RepoIdentity;
  statistics: RepoStatistics;
  contributors: Contributor[];
  branches: Branch[];
  releases: Release[];
  recent_issues: Issue[];
  recent_pull_requests: PullRequest[];
}

// =========================================
// Analytics Types
// =========================================

export interface WeeklyCommit {
  week: string;
  commits: number;
}

export interface CommitDistribution {
  author: string;
  commits: number;
}

export interface ContributorLeaderboard {
  login: string;
  contributions: number;
  avatar_url?: string;
}

export interface IssueLabelCount {
  label: string;
  count: number;
}

export interface ReleaseMilestone {
  tag: string;
  name?: string;
  date?: string;
  is_prerelease: boolean;
  url?: string;
}

export interface SoftwareHealthData {
  project_id: number;
  health_score: number;
  health_index?: HealthIndexDetails;
  metrics: {
    total_commits: number;
    recent_commits_30d: number;
    total_issues: number;
    open_issues: number;
    closed_issues: number;
    avg_issue_resolution_hours: number;
    total_prs: number;
    merged_prs: number;
    open_prs: number;
    pr_merge_rate_pct: number;
    avg_pr_merge_hours: number;
    total_contributors: number;
    total_releases: number;
    stars: number;
    forks: number;
  };
  weekly_commits: WeeklyCommit[];
  commit_distribution: CommitDistribution[];
  contributor_leaderboard: ContributorLeaderboard[];
  top_issue_labels: IssueLabelCount[];
  release_timeline: ReleaseMilestone[];
}

// ==========================================
// Phase 4: Software Health & Risk Detection
// ==========================================

export interface HealthDimension {
  id?: number;
  dimension: string;
  name: string;
  score: number | null;
  weight: number;
  status: 'HEALTHY' | 'ATTENTION' | 'DEGRADED' | 'CRITICAL' | 'INSUFFICIENT_DATA';
  metrics?: Record<string, any>;
  explanation?: string[];
}

export interface SoftwareHealthSnapshot {
  id: number;
  project_id: number;
  twin_version?: number;
  overall_score: number;
  overall_status: 'HEALTHY' | 'ATTENTION' | 'DEGRADED' | 'CRITICAL' | 'INSUFFICIENT_DATA';
  calculated_at: string;
  calculation_version: string;
  explanations?: string[];
  dimensions: HealthDimension[];
}

export interface HealthHistoryPoint {
  id: number;
  project_id: number;
  calculated_at: string;
  overall_score: number;
  overall_status: string;
  twin_version?: number;
}

export interface SoftwareRisk {
  id: number;
  project_id: number;
  risk_type: string;
  title: string;
  description: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  status: 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED';
  fingerprint: string;
  detection_rule: string;
  metric_value?: string;
  threshold_value?: string;
  evidence?: Record<string, any>;
  affected_entities?: Array<{
    type: string;
    id?: string | number;
    number?: number;
    title?: string;
    age_days?: number;
    url?: string;
    login?: string;
    tag?: string;
  }>;
  detected_at: string;
  acknowledged_at?: string;
  resolved_at?: string;
}

export interface RiskSummary {
  total_risks: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  open_count: number;
  acknowledged_count: number;
  resolved_count: number;
}

export interface RiskItem {
  id: string;
  category: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  title: string;
  description: string;
  signal_value: string;
  recommendation: string;
  affected_area: string;
}

export interface ContributorConcentration {
  name: string;
  value: number;
}

export interface IssueWeeklyTrend {
  week: string;
  opened: number;
  closed: number;
}

export interface RiskAnalysisData {
  project_id: number;
  overall_risk_level: 'critical' | 'high' | 'medium' | 'low';
  risk_count: number;
  severity_summary: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
  risks: RiskItem[];
  contributor_concentration: ContributorConcentration[];
  issue_trend: IssueWeeklyTrend[];
  metadata: {
    total_commits: number;
    total_contributors: number;
    total_issues: number;
    total_prs: number;
    health_score: number;
    last_synced?: string;
  };
}

export interface MonthlyActivity {
  month: string;
  commits: number;
  merged_prs: number;
}

export interface ContributorGrowth {
  month: string;
  new_contributors: number;
  total_contributors: number;
}

export interface EvolutionTimelineEvent {
  type: string;
  label: string;
  date?: string;
  is_prerelease?: boolean;
  url?: string;
}

export interface EvolutionData {
  project_id: number;
  project_name: string;
  repo_created_at?: string;
  repo_pushed_at?: string;
  monthly_activity: MonthlyActivity[];
  contributor_growth: ContributorGrowth[];
  release_milestones: ReleaseMilestone[];
  timeline_events: EvolutionTimelineEvent[];
  totals: {
    total_commits: number;
    total_releases: number;
    total_merged_prs: number;
    total_contributors: number;
  };
}

export interface DebtCategory {
  category: string;
  score: number;
  items: number;
  stale_items: number;
  description: string;
  estimated_hours: number;
  icon: string;
}

export interface CommitTypeBreakdown {
  type: string;
  count: number;
}

export interface RefactoringCandidate {
  area: string;
  priority: 'high' | 'medium' | 'low';
  description: string;
  effort: string;
}

export interface TechnicalDebtData {
  project_id: number;
  overall_debt_score: number;
  debt_level: 'high' | 'medium' | 'low';
  total_estimated_debt_hours: number;
  debt_categories: DebtCategory[];
  commit_type_breakdown: CommitTypeBreakdown[];
  refactoring_candidates: RefactoringCandidate[];
  metrics: {
    total_commits: number;
    fix_commits: number;
    fix_ratio_pct: number;
    open_issues: number;
    stale_issues: number;
    total_branches: number;
    non_default_branches: number;
    slow_prs: number;
    total_merged_prs: number;
  };
}

export interface TwinEntityMap {
  name: string;
  synced: number;
  icon: string;
}

export interface TwinLayer {
  name: string;
  status: 'active' | 'syncing' | 'pending' | 'planned' | 'empty';
  description: string;
  metrics: string;
}

export interface DigitalTwinStateData {
  project_id: number;
  twin_name: string;
  twin_status: string;
  sync_status: 'fresh' | 'aging' | 'stale' | 'never_synced';
  staleness_minutes?: number;
  last_synced_at?: string;
  health_score: number;
  fidelity_score: number;
  total_entities: number;
  entity_map: TwinEntityMap[];
  repository: {
    full_name: string;
    html_url: string;
    language?: string;
    default_branch: string;
    visibility: string;
    stars: number;
    forks: number;
    license?: string;
    created_at?: string;
    pushed_at?: string;
  };
  layers: TwinLayer[];
}

// ─── Phase 3: Digital Twin Core Interfaces ───────────────────────────────────

export interface DigitalTwinCore {
  id: number;
  project_id: number;
  current_version: number;
  status: 'NOT_INITIALIZED' | 'INITIALIZING' | 'ACTIVE' | 'SYNCING' | 'OUTDATED' | 'ERROR';
  error_message?: string;
  last_synced_at?: string;
  fidelity_score: number;
  stale_threshold_minutes: number;
  is_outdated: boolean;
  staleness_minutes?: number;
  created_at: string;
  updated_at: string;
}

export interface DigitalTwinSnapshot {
  id: number;
  digital_twin_id: number;
  version: number;
  created_at: string;
  source: string;
  summary?: string;
  change_count: number;
  entity_counts?: Record<string, number>;
  state_data?: Record<string, any>;
}

export interface DigitalTwinChange {
  id: number;
  digital_twin_id: number;
  snapshot_id?: number;
  entity_type: string;
  entity_id: string;
  change_type: 'CREATED' | 'UPDATED' | 'DELETED' | 'STATE_CHANGED';
  change_summary: string;
  old_value?: Record<string, any>;
  new_value?: Record<string, any>;
  detected_at: string;
  source: string;
}

export interface DigitalTwinEvent {
  id: number;
  digital_twin_id: number;
  snapshot_id?: number;
  event_type: string;
  entity_type: string;
  entity_id: string;
  title: string;
  description?: string;
  timestamp: string;
  actor_login?: string;
  actor_avatar_url?: string;
  source: string;
  event_metadata?: Record<string, any>;
}

export interface EntityDiffItem {
  entity_type: string;
  entity_id: string;
  change_type: string;
  summary: string;
  old_value?: Record<string, any>;
  new_value?: Record<string, any>;
}

export interface DigitalTwinCompareResult {
  project_id: number;
  twin_id: number;
  v_from: number;
  v_to: number;
  added: EntityDiffItem[];
  updated: EntityDiffItem[];
  removed: EntityDiffItem[];
  summary: {
    total_added?: number;
    total_updated?: number;
    total_removed?: number;
    entity_count_diffs?: Record<string, number>;
    version_span?: string;
    message?: string;
  };
}

export interface DigitalTwinSyncResult {
  twin_id: number;
  project_id: number;
  previous_version: number;
  current_version: number;
  status: string;
  changes_detected: number;
  changes_summary: string[];
  message: string;
  synced_at: string;
}

export interface DigitalTwinFullState {
  twin: DigitalTwinCore;
  repository: {
    id: number;
    owner: string;
    repo: string;
    full_name: string;
    html_url: string;
    description?: string;
    default_branch: string;
    language?: string;
    stars: number;
    forks: number;
    open_issues: number;
    open_prs: number;
    license?: string;
    health_score: number;
  };
  current_snapshot?: DigitalTwinSnapshot;
  entity_counts: {
    commits: number;
    contributors: number;
    issues: number;
    pull_requests: number;
    branches: number;
    releases: number;
    files: number;
  };
  latest_commit?: {
    sha: string;
    message: string;
    author: string;
    date?: string;
  };
  latest_release?: {
    tag: string;
    name: string;
    published_at?: string;
  };
  current_branch?: string;
  fidelity_components: Array<{
    key: string;
    name: string;
    synced: number;
    icon: string;
    active: boolean;
  }>;
  recent_changes: DigitalTwinChange[];
  recent_events: DigitalTwinEvent[];
}

