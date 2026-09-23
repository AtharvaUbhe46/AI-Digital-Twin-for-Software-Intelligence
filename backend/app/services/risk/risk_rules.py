from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.project import Commit, Issue, PullRequest, Release, Contributor
from app.core.config import settings


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass
class RiskDetectionResult:
    risk_type: str
    title: str
    description: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    fingerprint: str
    detection_rule: str
    metric_value: str
    threshold_value: str
    evidence: Dict[str, Any]
    affected_entities: List[Dict[str, Any]]


class BaseRiskRule(ABC):
    rule_id: str
    name: str
    description: str

    @abstractmethod
    def evaluate(self, project_id: int, db: Session) -> Optional[RiskDetectionResult]:
        pass


class RepositoryInactivityRule(BaseRiskRule):
    """
    RISK 1: Triggers when days since last commit exceeds RISK_INACTIVITY_DAYS.
    """
    rule_id = "REPOSITORY_INACTIVITY_RULE"
    name = "Repository Inactivity"
    description = "Detects when commit activity has ceased beyond configured inactivity threshold."

    def evaluate(self, project_id: int, db: Session) -> Optional[RiskDetectionResult]:
        latest_commit = (
            db.query(Commit)
            .filter(Commit.project_id == project_id)
            .order_by(desc(Commit.author_date))
            .first()
        )
        if not latest_commit or not latest_commit.author_date:
            return None

        now = datetime.now(timezone.utc)
        latest_date = ensure_utc(latest_commit.author_date)
        days_inactive = max(0, (now - latest_date).days)
        threshold = settings.RISK_INACTIVITY_DAYS

        if days_inactive > threshold:
            if days_inactive >= 60:
                severity = "CRITICAL"
            elif days_inactive >= 30:
                severity = "HIGH"
            else:
                severity = "MEDIUM"

            return RiskDetectionResult(
                risk_type="REPOSITORY_INACTIVITY",
                title=f"Repository Inactive for {days_inactive} Days",
                description=(
                    f"No commits have been pushed for {days_inactive} days, "
                    f"exceeding the inactivity threshold of {threshold} days."
                ),
                severity=severity,
                fingerprint=f"inactivity_{project_id}",
                detection_rule=f"days_since_last_commit > {threshold}",
                metric_value=f"{days_inactive} days",
                threshold_value=f"{threshold} days",
                evidence={
                    "last_commit_sha": latest_commit.sha[:8] if latest_commit.sha else None,
                    "last_commit_date": latest_date.isoformat(),
                    "days_inactive": days_inactive,
                    "threshold_days": threshold,
                    "author": latest_commit.author_login or latest_commit.author_name,
                },
                affected_entities=[{
                    "type": "commit",
                    "id": latest_commit.sha[:8] if latest_commit.sha else "HEAD",
                    "url": latest_commit.html_url,
                }],
            )
        return None


class StaleIssuesRule(BaseRiskRule):
    """
    RISK 2: Triggers when open issues exceed RISK_STALE_ISSUE_DAYS.
    """
    rule_id = "STALE_ISSUES_RULE"
    name = "Stale Open Issues"
    description = "Detects open issues exceeding configured staleness age threshold."

    def evaluate(self, project_id: int, db: Session) -> Optional[RiskDetectionResult]:
        now = datetime.now(timezone.utc)
        threshold = settings.RISK_STALE_ISSUE_DAYS

        open_issues = db.query(Issue).filter(
            Issue.project_id == project_id,
            Issue.state == "open"
        ).all()

        stale_issues = []
        for issue in open_issues:
            c_at = ensure_utc(issue.created_at)
            if c_at:
                age_days = (now - c_at).days
                if age_days >= threshold:
                    stale_issues.append((issue, age_days))

        if stale_issues:
            stale_issues.sort(key=lambda x: x[1], reverse=True)
            oldest_age = stale_issues[0][1]
            stale_count = len(stale_issues)

            if stale_count >= 10:
                severity = "CRITICAL"
            elif stale_count >= 5:
                severity = "HIGH"
            else:
                severity = "MEDIUM"

            affected = [
                {
                    "type": "issue",
                    "number": iss.number,
                    "title": iss.title,
                    "age_days": age,
                    "url": iss.html_url,
                }
                for iss, age in stale_issues[:10]
            ]

            return RiskDetectionResult(
                risk_type="STALE_ISSUES",
                title=f"{stale_count} Stale Open Issue(s)",
                description=(
                    f"{stale_count} issue(s) have remained open beyond the {threshold}-day "
                    f"threshold (oldest is {oldest_age} days old)."
                ),
                severity=severity,
                fingerprint=f"stale_issues_{project_id}",
                detection_rule=f"open_issue_age >= {threshold} days",
                metric_value=f"{stale_count} stale issues (oldest: {oldest_age}d)",
                threshold_value=f"{threshold} days",
                evidence={
                    "stale_count": stale_count,
                    "total_open_issues": len(open_issues),
                    "oldest_age_days": oldest_age,
                    "threshold_days": threshold,
                },
                affected_entities=affected,
            )
        return None


class StalePullRequestsRule(BaseRiskRule):
    """
    RISK 3: Triggers when open PRs exceed RISK_STALE_PR_DAYS.
    """
    rule_id = "STALE_PULL_REQUESTS_RULE"
    name = "Stale Pull Requests"
    description = "Detects unresolved pull requests that remain open beyond review threshold."

    def evaluate(self, project_id: int, db: Session) -> Optional[RiskDetectionResult]:
        now = datetime.now(timezone.utc)
        threshold = settings.RISK_STALE_PR_DAYS

        open_prs = db.query(PullRequest).filter(
            PullRequest.project_id == project_id,
            PullRequest.state == "open"
        ).all()

        stale_prs = []
        for pr in open_prs:
            c_at = ensure_utc(pr.created_at)
            if c_at:
                age_days = (now - c_at).days
                if age_days >= threshold:
                    stale_prs.append((pr, age_days))

        if stale_prs:
            stale_prs.sort(key=lambda x: x[1], reverse=True)
            oldest_age = stale_prs[0][1]
            stale_count = len(stale_prs)

            if stale_count >= 5 or oldest_age >= 60:
                severity = "CRITICAL"
            elif stale_count >= 2 or oldest_age >= 30:
                severity = "HIGH"
            else:
                severity = "MEDIUM"

            affected = [
                {
                    "type": "pull_request",
                    "number": pr.number,
                    "title": pr.title,
                    "age_days": age,
                    "url": pr.html_url,
                }
                for pr, age in stale_prs[:10]
            ]

            return RiskDetectionResult(
                risk_type="STALE_PULL_REQUESTS",
                title=f"{stale_count} Stale Pull Request(s)",
                description=(
                    f"{stale_count} pull request(s) have remained unmerged beyond "
                    f"the {threshold}-day review threshold (oldest is {oldest_age} days old)."
                ),
                severity=severity,
                fingerprint=f"stale_prs_{project_id}",
                detection_rule=f"open_pr_age >= {threshold} days",
                metric_value=f"{stale_count} stale PRs (oldest: {oldest_age}d)",
                threshold_value=f"{threshold} days",
                evidence={
                    "stale_count": stale_count,
                    "total_open_prs": len(open_prs),
                    "oldest_age_days": oldest_age,
                    "threshold_days": threshold,
                },
                affected_entities=affected,
            )
        return None


class IssueBacklogGrowthRule(BaseRiskRule):
    """
    RISK 4: Triggers when issue creation significantly exceeds resolution in configured period.
    """
    rule_id = "ISSUE_BACKLOG_GROWTH_RULE"
    name = "Issue Backlog Growth"
    description = "Detects rapid expansion of open issue backlog exceeding resolution throughput."

    def evaluate(self, project_id: int, db: Session) -> Optional[RiskDetectionResult]:
        now = datetime.now(timezone.utc)
        window_days = settings.RISK_BACKLOG_WINDOW_DAYS
        window_start = now - timedelta(days=window_days)
        threshold_net = settings.RISK_ISSUE_BACKLOG_THRESHOLD

        issues = db.query(Issue).filter(Issue.project_id == project_id).all()
        opened_recent = sum(1 for i in issues if ensure_utc(i.created_at) and ensure_utc(i.created_at) >= window_start)
        closed_recent = sum(1 for i in issues if i.state == "closed" and ensure_utc(i.closed_at) and ensure_utc(i.closed_at) >= window_start)

        net_growth = opened_recent - closed_recent

        if net_growth >= threshold_net and opened_recent > 0:
            severity = "HIGH" if net_growth >= (threshold_net * 2) else "MEDIUM"
            return RiskDetectionResult(
                risk_type="ISSUE_BACKLOG_GROWTH",
                title="Issue Backlog Accumulating Rapidly",
                description=(
                    f"Issues opened ({opened_recent}) exceed issues closed ({closed_recent}) "
                    f"by {net_growth} over the last {window_days} days."
                ),
                severity=severity,
                fingerprint=f"issue_backlog_growth_{project_id}",
                detection_rule=f"net_issue_growth >= {threshold_net} in {window_days}d",
                metric_value=f"+{net_growth} net issues",
                threshold_value=f"+{threshold_net} net issues",
                evidence={
                    "opened_recent": opened_recent,
                    "closed_recent": closed_recent,
                    "net_growth": net_growth,
                    "window_days": window_days,
                },
                affected_entities=[],
            )
        return None


class PRBacklogGrowthRule(BaseRiskRule):
    """
    RISK 5: Triggers when open PR creation significantly exceeds merge/closure rate.
    """
    rule_id = "PR_BACKLOG_GROWTH_RULE"
    name = "PR Backlog Growth"
    description = "Detects incoming pull request arrival rate outpacing review and merge capacity."

    def evaluate(self, project_id: int, db: Session) -> Optional[RiskDetectionResult]:
        now = datetime.now(timezone.utc)
        window_days = settings.RISK_BACKLOG_WINDOW_DAYS
        window_start = now - timedelta(days=window_days)
        threshold_net = settings.RISK_PR_BACKLOG_THRESHOLD

        prs = db.query(PullRequest).filter(PullRequest.project_id == project_id).all()
        opened_recent = sum(1 for p in prs if ensure_utc(p.created_at) and ensure_utc(p.created_at) >= window_start)
        merged_recent = sum(1 for p in prs if ensure_utc(p.merged_at) and ensure_utc(p.merged_at) >= window_start)

        net_growth = opened_recent - merged_recent

        if net_growth >= threshold_net and opened_recent > 0:
            severity = "HIGH" if net_growth >= (threshold_net * 2) else "MEDIUM"
            return RiskDetectionResult(
                risk_type="PR_BACKLOG_GROWTH",
                title="PR Queue Growing Faster than Merges",
                description=(
                    f"New PRs opened ({opened_recent}) exceed PRs merged ({merged_recent}) "
                    f"by {net_growth} over the last {window_days} days."
                ),
                severity=severity,
                fingerprint=f"pr_backlog_growth_{project_id}",
                detection_rule=f"net_pr_growth >= {threshold_net} in {window_days}d",
                metric_value=f"+{net_growth} net PRs",
                threshold_value=f"+{threshold_net} net PRs",
                evidence={
                    "opened_recent": opened_recent,
                    "merged_recent": merged_recent,
                    "net_growth": net_growth,
                    "window_days": window_days,
                },
                affected_entities=[],
            )
        return None


class LowContributorDiversityRule(BaseRiskRule):
    """
    RISK 6: Triggers when contribution activity is overly concentrated in a single author.
    Presented neutrally as an engineering concentration signal.
    """
    rule_id = "LOW_CONTRIBUTOR_DIVERSITY_RULE"
    name = "High Contributor Concentration"
    description = "Detects disproportionate concentration of commits authored by a single contributor."

    def evaluate(self, project_id: int, db: Session) -> Optional[RiskDetectionResult]:
        commits = db.query(Commit).filter(Commit.project_id == project_id).all()
        if len(commits) < 5:  # Not enough sample size to assert concentration
            return None

        author_counts: Dict[str, int] = {}
        for c in commits:
            login = c.author_login or c.author_email or "unknown"
            author_counts[login] = author_counts.get(login, 0) + 1

        total = sum(author_counts.values())
        sorted_authors = sorted(author_counts.items(), key=lambda x: x[1], reverse=True)
        top_author, top_count = sorted_authors[0]
        concentration = top_count / total
        threshold = settings.RISK_CONTRIBUTOR_CONCENTRATION_THRESHOLD

        if concentration >= threshold:
            pct_formatted = round(concentration * 100.0, 1)
            severity = "HIGH" if concentration >= 0.85 else "MEDIUM"
            return RiskDetectionResult(
                risk_type="LOW_CONTRIBUTOR_DIVERSITY",
                title="High Contributor Concentration Risk",
                description=(
                    f"A large portion ({pct_formatted}%) of recent repository commit activity "
                    f"is authored by a single contributor ({top_author})."
                ),
                severity=severity,
                fingerprint=f"contributor_concentration_{project_id}",
                detection_rule=f"top_contributor_percentage >= {int(threshold * 100)}%",
                metric_value=f"{pct_formatted}%",
                threshold_value=f"{int(threshold * 100)}%",
                evidence={
                    "top_contributor": top_author,
                    "top_contributor_commits": top_count,
                    "total_commits": total,
                    "concentration_percentage": pct_formatted,
                    "total_contributors": len(author_counts),
                },
                affected_entities=[{
                    "type": "contributor",
                    "login": top_author,
                }],
            )
        return None


class ReleaseStagnationRule(BaseRiskRule):
    """
    RISK 7: Triggers when days since latest release exceeds threshold (only if releases exist).
    """
    rule_id = "RELEASE_STAGNATION_RULE"
    name = "Release Stagnation"
    description = "Detects prolonged hiatus between published software releases."

    def evaluate(self, project_id: int, db: Session) -> Optional[RiskDetectionResult]:
        releases = (
            db.query(Release)
            .filter(Release.project_id == project_id)
            .order_by(desc(Release.published_at))
            .all()
        )
        if not releases:
            # If no releases exist, do NOT create a risk; marked as insufficient data in health
            return None

        latest = releases[0]
        if not latest.published_at:
            return None

        now = datetime.now(timezone.utc)
        latest_date = ensure_utc(latest.published_at)
        days = max(0, (now - latest_date).days)
        threshold = settings.RISK_RELEASE_STAGNATION_DAYS

        if days > threshold:
            severity = "HIGH" if days >= 180 else "MEDIUM"
            return RiskDetectionResult(
                risk_type="RELEASE_STAGNATION",
                title=f"Release Stagnation ({days} Days)",
                description=(
                    f"No new release has been published in {days} days "
                    f"(latest was {latest.tag_name}), exceeding threshold of {threshold} days."
                ),
                severity=severity,
                fingerprint=f"release_stagnation_{project_id}",
                detection_rule=f"days_since_latest_release > {threshold}",
                metric_value=f"{days} days",
                threshold_value=f"{threshold} days",
                evidence={
                    "latest_release_tag": latest.tag_name,
                    "published_at": latest_date.isoformat(),
                    "days_since_release": days,
                    "threshold_days": threshold,
                },
                affected_entities=[{
                    "type": "release",
                    "tag": latest.tag_name,
                    "url": latest.html_url,
                }],
            )
        return None


class ActivitySpikeRule(BaseRiskRule):
    """
    RISK 8: Triggers when recent commit activity dramatically spikes over historical baseline.
    """
    rule_id = "ACTIVITY_SPIKE_RULE"
    name = "Unusual Activity Spike"
    description = "Detects rapid bursts in commit velocity compared against baseline history."

    def evaluate(self, project_id: int, db: Session) -> Optional[RiskDetectionResult]:
        now = datetime.now(timezone.utc)
        window_days = settings.HEALTH_RECENT_DAYS
        window_start = now - timedelta(days=window_days)

        commits = db.query(Commit).filter(Commit.project_id == project_id).all()
        if len(commits) < 20:  # Need minimum history to establish baseline
            return None

        recent_commits = [c for c in commits if ensure_utc(c.author_date) and ensure_utc(c.author_date) >= window_start]
        recent_count = len(recent_commits)

        oldest = min((ensure_utc(c.author_date) for c in commits if ensure_utc(c.author_date)), default=None)
        if not oldest:
            return None

        repo_age = max(1, (now - oldest).days)
        baseline_monthly = (len(commits) / repo_age) * window_days
        multiplier_threshold = settings.RISK_ACTIVITY_SPIKE_MULTIPLIER

        if baseline_monthly >= 2.0 and recent_count >= 15:
            ratio = round(recent_count / baseline_monthly, 2)
            if ratio >= multiplier_threshold:
                return RiskDetectionResult(
                    risk_type="ACTIVITY_SPIKE",
                    title=f"Activity Spike ({ratio}x Monthly Baseline)",
                    description=(
                        f"Recent commit velocity ({recent_count} commits in {window_days}d) "
                        f"is {ratio}x higher than the historical baseline ({round(baseline_monthly, 1)} commits/mo)."
                    ),
                    severity="LOW",
                    fingerprint=f"activity_spike_{project_id}",
                    detection_rule=f"recent_activity_ratio >= {multiplier_threshold}x",
                    metric_value=f"{ratio}x",
                    threshold_value=f"{multiplier_threshold}x",
                    evidence={
                        "recent_commits": recent_count,
                        "historical_baseline_monthly": round(baseline_monthly, 1),
                        "ratio": ratio,
                        "window_days": window_days,
                    },
                    affected_entities=[],
                )
        return None


# Rule Registry containing all 8 rules
ALL_RISK_RULES: List[BaseRiskRule] = [
    RepositoryInactivityRule(),
    StaleIssuesRule(),
    StalePullRequestsRule(),
    IssueBacklogGrowthRule(),
    PRBacklogGrowthRule(),
    LowContributorDiversityRule(),
    ReleaseStagnationRule(),
    ActivitySpikeRule(),
]
