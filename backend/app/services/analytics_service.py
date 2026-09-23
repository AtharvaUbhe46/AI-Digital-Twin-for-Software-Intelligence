import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from app.models.project import (
    Project,
    Contributor,
    Commit,
    Issue,
    PullRequest,
    Release,
    Branch,
)

logger = logging.getLogger("digital_twin.analytics")


class AnalyticsService:

    @staticmethod
    def get_software_health(project_id: int, db: Session) -> Dict[str, Any]:
        """
        Derives comprehensive software health metrics from real GitHub data.
        Returns health index breakdown, issue trends, PR velocity, and commit trends.
        """
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project {project_id} not found")

        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        sixty_days_ago = now - timedelta(days=60)

        # --- Commit Trends (last 30 days by week) ---
        commits = db.query(Commit).filter(
            Commit.project_id == project_id,
            Commit.author_date.isnot(None)
        ).order_by(Commit.author_date).all()

        commit_by_week = defaultdict(int)
        commit_by_author = defaultdict(int)
        recent_commit_count = 0

        for c in commits:
            if c.author_date:
                if c.author_date >= thirty_days_ago:
                    recent_commit_count += 1
                    week_key = c.author_date.strftime("W%W")
                    commit_by_week[week_key] += 1
                if c.author_login:
                    commit_by_author[c.author_login] += 1

        # Build weekly commit series (last 8 weeks)
        weekly_commits = []
        for i in range(7, -1, -1):
            week_start = now - timedelta(weeks=i + 1)
            week_key = week_start.strftime("W%W")
            label = week_start.strftime("%b %d")
            weekly_commits.append({"week": label, "commits": commit_by_week.get(week_key, 0)})

        # --- Issue Trends ---
        all_issues = db.query(Issue).filter(Issue.project_id == project_id).all()
        open_issues = [i for i in all_issues if i.state == "open"]
        closed_issues = [i for i in all_issues if i.state == "closed"]

        # Avg issue resolution time for closed issues
        resolution_times = []
        for iss in closed_issues:
            if iss.created_at and iss.closed_at:
                delta = (iss.closed_at - iss.created_at).total_seconds() / 3600
                resolution_times.append(delta)

        avg_resolution_hours = round(sum(resolution_times) / len(resolution_times), 1) if resolution_times else 0

        # Issue label frequency
        label_freq = defaultdict(int)
        for iss in all_issues:
            for lbl in (iss.labels or []):
                label_freq[str(lbl)] += 1

        top_labels = sorted(label_freq.items(), key=lambda x: x[1], reverse=True)[:8]

        # --- PR Metrics ---
        all_prs = db.query(PullRequest).filter(PullRequest.project_id == project_id).all()
        merged_prs = [pr for pr in all_prs if pr.is_merged]
        open_prs = [pr for pr in all_prs if pr.state == "open"]

        # PR merge time averages
        merge_times = []
        for pr in merged_prs:
            if pr.created_at and pr.merged_at:
                delta = (pr.merged_at - pr.created_at).total_seconds() / 3600
                merge_times.append(delta)

        avg_merge_hours = round(sum(merge_times) / len(merge_times), 1) if merge_times else 0
        merge_rate = round((len(merged_prs) / len(all_prs)) * 100, 1) if all_prs else 0

        # --- Contributor Distribution ---
        contributors = db.query(Contributor).filter(
            Contributor.project_id == project_id
        ).order_by(desc(Contributor.contributions)).limit(10).all()

        contributor_data = [
            {"login": c.login, "contributions": c.contributions, "avatar_url": c.avatar_url}
            for c in contributors
        ]

        # Top author commit distribution
        top_authors_commits = sorted(commit_by_author.items(), key=lambda x: x[1], reverse=True)[:8]
        commit_distribution = [{"author": a, "commits": n} for a, n in top_authors_commits]

        # --- Health Index from project ---
        health_index = project.health_index_details or {}
        health_score = project.health_score or 0

        # --- Releases trend ---
        releases = db.query(Release).filter(
            Release.project_id == project_id
        ).order_by(desc(Release.published_at)).limit(10).all()

        release_timeline = [
            {
                "tag": r.tag_name,
                "name": r.name,
                "date": r.published_at.isoformat() if r.published_at else None,
                "is_prerelease": r.is_prerelease,
                "url": r.html_url
            }
            for r in releases
        ]

        return {
            "project_id": project_id,
            "health_score": health_score,
            "health_index": health_index,
            "metrics": {
                "total_commits": len(commits),
                "recent_commits_30d": recent_commit_count,
                "total_issues": len(all_issues),
                "open_issues": len(open_issues),
                "closed_issues": len(closed_issues),
                "avg_issue_resolution_hours": avg_resolution_hours,
                "total_prs": len(all_prs),
                "merged_prs": len(merged_prs),
                "open_prs": len(open_prs),
                "pr_merge_rate_pct": merge_rate,
                "avg_pr_merge_hours": avg_merge_hours,
                "total_contributors": db.query(Contributor).filter(Contributor.project_id == project_id).count(),
                "total_releases": len(releases),
                "stars": project.stars_count,
                "forks": project.forks_count
            },
            "weekly_commits": weekly_commits,
            "commit_distribution": commit_distribution,
            "contributor_leaderboard": contributor_data,
            "top_issue_labels": [{"label": l, "count": c} for l, c in top_labels],
            "release_timeline": release_timeline,
        }

    @staticmethod
    def get_risk_analysis(project_id: int, db: Session) -> Dict[str, Any]:
        """
        Derives software risk signals from real data patterns.
        Identifies high-risk commit authors, stale issues, draft/stuck PRs, etc.
        """
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project {project_id} not found")

        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        fourteen_days_ago = now - timedelta(days=14)
        ninety_days_ago = now - timedelta(days=90)

        risks = []

        # --- Commit Recency Risk ---
        recent_commits = db.query(Commit).filter(
            Commit.project_id == project_id,
            Commit.author_date >= thirty_days_ago
        ).count()

        if recent_commits == 0:
            risks.append({
                "id": "commit-inactivity",
                "category": "Activity",
                "severity": "critical",
                "title": "No commits in last 30 days",
                "description": "The repository has had zero commits in the last 30 days, indicating potential project abandonment or a significant development pause.",
                "signal_value": "0 commits",
                "recommendation": "Investigate project status. Check if development moved to another branch or fork.",
                "affected_area": "Commit Activity"
            })
        elif recent_commits < 5:
            risks.append({
                "id": "low-commit-velocity",
                "category": "Activity",
                "severity": "medium",
                "title": "Low commit velocity",
                "description": f"Only {recent_commits} commits in the last 30 days. Low activity may indicate reduced team engagement.",
                "signal_value": f"{recent_commits} commits/month",
                "recommendation": "Review sprint/release cadence and team capacity.",
                "affected_area": "Commit Activity"
            })

        # --- Bus Factor Risk (contributor concentration) ---
        contributors = db.query(Contributor).filter(
            Contributor.project_id == project_id
        ).order_by(desc(Contributor.contributions)).all()

        total_contrib = sum(c.contributions for c in contributors)
        if total_contrib > 0 and contributors:
            top_contributor_share = contributors[0].contributions / total_contrib
            if top_contributor_share > 0.7:
                risks.append({
                    "id": "bus-factor-risk",
                    "category": "Knowledge",
                    "severity": "high",
                    "title": f"High contributor concentration (Bus Factor Risk)",
                    "description": f"{contributors[0].login} accounts for {round(top_contributor_share*100)}% of all commits. Single point of knowledge failure.",
                    "signal_value": f"{round(top_contributor_share*100)}% by {contributors[0].login}",
                    "recommendation": "Encourage knowledge sharing through pair programming and documentation.",
                    "affected_area": f"Contributor: {contributors[0].login}"
                })
            elif top_contributor_share > 0.5:
                risks.append({
                    "id": "bus-factor-moderate",
                    "category": "Knowledge",
                    "severity": "medium",
                    "title": "Moderate contributor concentration",
                    "description": f"{contributors[0].login} accounts for {round(top_contributor_share*100)}% of commits.",
                    "signal_value": f"{round(top_contributor_share*100)}% concentration",
                    "recommendation": "Distribute code ownership and cross-train team members.",
                    "affected_area": f"Contributor: {contributors[0].login}"
                })

        # --- Stale Issues Risk ---
        stale_issues = db.query(Issue).filter(
            Issue.project_id == project_id,
            Issue.state == "open",
            Issue.created_at <= ninety_days_ago
        ).count()

        if stale_issues > 10:
            risks.append({
                "id": "stale-issues",
                "category": "Maintenance",
                "severity": "high",
                "title": f"{stale_issues} issues open for 90+ days",
                "description": f"High number of long-standing unresolved issues indicates backlog debt and potential user-facing problems.",
                "signal_value": f"{stale_issues} stale issues",
                "recommendation": "Prioritize a sprint dedicated to issue triage and resolution.",
                "affected_area": "Issue Tracker"
            })
        elif stale_issues > 3:
            risks.append({
                "id": "stale-issues-moderate",
                "category": "Maintenance",
                "severity": "medium",
                "title": f"{stale_issues} stale issues (90+ days)",
                "description": f"{stale_issues} issues remain open without resolution for over 90 days.",
                "signal_value": f"{stale_issues} unresolved",
                "recommendation": "Schedule regular issue grooming sessions.",
                "affected_area": "Issue Tracker"
            })

        # --- Stuck PRs Risk ---
        stuck_prs = db.query(PullRequest).filter(
            PullRequest.project_id == project_id,
            PullRequest.state == "open",
            PullRequest.created_at <= fourteen_days_ago
        ).count()

        if stuck_prs > 5:
            risks.append({
                "id": "stuck-prs",
                "category": "Collaboration",
                "severity": "high",
                "title": f"{stuck_prs} PRs stuck open for 14+ days",
                "description": "Large number of stale open pull requests may indicate bottlenecks in code review process.",
                "signal_value": f"{stuck_prs} stale PRs",
                "recommendation": "Review PR process - consider mandatory review SLAs and automated reminders.",
                "affected_area": "Pull Requests"
            })
        elif stuck_prs > 2:
            risks.append({
                "id": "stuck-prs-moderate",
                "category": "Collaboration",
                "severity": "medium",
                "title": f"{stuck_prs} PRs open for 14+ days",
                "description": f"{stuck_prs} open pull requests are awaiting review or approval.",
                "signal_value": f"{stuck_prs} stale PRs",
                "recommendation": "Assign reviewers and set review deadlines.",
                "affected_area": "Pull Requests"
            })

        # --- Draft PR Risk ---
        draft_prs = db.query(PullRequest).filter(
            PullRequest.project_id == project_id,
            PullRequest.draft == True,
            PullRequest.state == "open"
        ).count()

        if draft_prs > 3:
            risks.append({
                "id": "draft-prs",
                "category": "Collaboration",
                "severity": "low",
                "title": f"{draft_prs} draft PRs in progress",
                "description": "Multiple draft PRs indicate parallel WIP work that has not been reviewed yet.",
                "signal_value": f"{draft_prs} drafts",
                "recommendation": "Track draft PR aging and ensure they progress to review state.",
                "affected_area": "Pull Requests"
            })

        # --- No releases risk ---
        release_count = db.query(Release).filter(Release.project_id == project_id).count()
        if release_count == 0:
            risks.append({
                "id": "no-releases",
                "category": "Delivery",
                "severity": "low",
                "title": "No versioned releases found",
                "description": "The repository has no tagged releases, which may make it hard for users to track stable versions.",
                "signal_value": "0 releases",
                "recommendation": "Implement a versioning strategy using semantic versioning (semver) and GitHub Releases.",
                "affected_area": "Releases"
            })

        # --- Low star count risk indicator ---
        if project.stars_count < 5 and project.forks_count < 2:
            risks.append({
                "id": "low-adoption",
                "category": "Community",
                "severity": "low",
                "title": "Low community adoption signals",
                "description": f"The repository has {project.stars_count} stars and {project.forks_count} forks indicating limited external discovery.",
                "signal_value": f"{project.stars_count} stars, {project.forks_count} forks",
                "recommendation": "Improve documentation, add README badges, and consider publishing to package registries.",
                "affected_area": "Community Metrics"
            })

        # --- Risk Summary ---
        severity_counts = {
            "critical": sum(1 for r in risks if r["severity"] == "critical"),
            "high": sum(1 for r in risks if r["severity"] == "high"),
            "medium": sum(1 for r in risks if r["severity"] == "medium"),
            "low": sum(1 for r in risks if r["severity"] == "low"),
        }

        overall_risk_level = "low"
        if severity_counts["critical"] > 0:
            overall_risk_level = "critical"
        elif severity_counts["high"] > 0:
            overall_risk_level = "high"
        elif severity_counts["medium"] > 1:
            overall_risk_level = "medium"

        # Contributor concentration chart data
        contrib_chart = [
            {"name": c.login, "value": c.contributions}
            for c in contributors[:8]
        ]

        # Issue open vs closed counts per week (last 8 weeks)
        all_issues = db.query(Issue).filter(Issue.project_id == project_id).all()
        issue_weekly = []
        for i in range(7, -1, -1):
            week_start = now - timedelta(weeks=i + 1)
            week_end = now - timedelta(weeks=i)
            label = week_start.strftime("%b %d")
            opened = sum(1 for iss in all_issues if iss.created_at and week_start <= iss.created_at < week_end)
            closed = sum(1 for iss in all_issues if iss.closed_at and week_start <= iss.closed_at < week_end)
            issue_weekly.append({"week": label, "opened": opened, "closed": closed})

        return {
            "project_id": project_id,
            "overall_risk_level": overall_risk_level,
            "risk_count": len(risks),
            "severity_summary": severity_counts,
            "risks": sorted(risks, key=lambda x: ["critical", "high", "medium", "low"].index(x["severity"])),
            "contributor_concentration": contrib_chart,
            "issue_trend": issue_weekly,
            "metadata": {
                "total_commits": len(db.query(Commit).filter(Commit.project_id == project_id).all()),
                "total_contributors": len(contributors),
                "total_issues": len(all_issues),
                "total_prs": db.query(PullRequest).filter(PullRequest.project_id == project_id).count(),
                "health_score": project.health_score,
                "last_synced": project.last_synced_at.isoformat() if project.last_synced_at else None
            }
        }

    @staticmethod
    def get_evolution_data(project_id: int, db: Session) -> Dict[str, Any]:
        """
        Returns project evolution timeline: releases, major commit milestones,
        and contributor growth over time.
        """
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Releases as milestone markers
        releases = db.query(Release).filter(
            Release.project_id == project_id
        ).order_by(Release.published_at).all()

        release_milestones = [
            {
                "type": "release",
                "label": r.tag_name,
                "name": r.name or r.tag_name,
                "date": r.published_at.isoformat() if r.published_at else None,
                "is_prerelease": r.is_prerelease,
                "url": r.html_url
            }
            for r in releases if r.published_at
        ]

        # Commits by month (all time)
        commits = db.query(Commit).filter(
            Commit.project_id == project_id,
            Commit.author_date.isnot(None)
        ).order_by(Commit.author_date).all()

        commit_by_month = defaultdict(int)
        for c in commits:
            if c.author_date:
                month_key = c.author_date.strftime("%Y-%m")
                commit_by_month[month_key] += 1

        # Build sorted commit monthly series
        sorted_months = sorted(commit_by_month.keys())
        monthly_commits = [
            {"month": m, "commits": commit_by_month[m]}
            for m in sorted_months[-24:]  # last 24 months
        ]

        # PR merged by month
        prs = db.query(PullRequest).filter(
            PullRequest.project_id == project_id,
            PullRequest.is_merged == True,
            PullRequest.merged_at.isnot(None)
        ).all()

        pr_by_month = defaultdict(int)
        for pr in prs:
            if pr.merged_at:
                month_key = pr.merged_at.strftime("%Y-%m")
                pr_by_month[month_key] += 1

        # Merge monthly_commits with PR data
        for item in monthly_commits:
            item["merged_prs"] = pr_by_month.get(item["month"], 0)

        # Contributor growth: unique contributors per month
        contributor_months = defaultdict(set)
        for c in commits:
            if c.author_date and c.author_login:
                month_key = c.author_date.strftime("%Y-%m")
                contributor_months[month_key].add(c.author_login)

        cumulative_contributors = set()
        contributor_growth = []
        for month in sorted_months[-24:]:
            cumulative_contributors.update(contributor_months.get(month, set()))
            contributor_growth.append({
                "month": month,
                "new_contributors": len(contributor_months.get(month, set())),
                "total_contributors": len(cumulative_contributors)
            })

        # Project timeline summary
        timeline_events = []
        if project.repo_created_at:
            timeline_events.append({
                "type": "project_start",
                "label": "Repository Created",
                "date": project.repo_created_at.isoformat()
            })

        for rel in release_milestones:
            timeline_events.append(rel)

        if project.last_synced_at:
            timeline_events.append({
                "type": "sync",
                "label": "Last Synced with GitHub",
                "date": project.last_synced_at.isoformat()
            })

        timeline_events.sort(key=lambda x: x.get("date") or "")

        return {
            "project_id": project_id,
            "project_name": project.full_name,
            "repo_created_at": project.repo_created_at.isoformat() if project.repo_created_at else None,
            "repo_pushed_at": project.repo_pushed_at.isoformat() if project.repo_pushed_at else None,
            "monthly_activity": monthly_commits,
            "contributor_growth": contributor_growth,
            "release_milestones": release_milestones,
            "timeline_events": timeline_events,
            "totals": {
                "total_commits": len(commits),
                "total_releases": len(releases),
                "total_merged_prs": len(prs),
                "total_contributors": db.query(Contributor).filter(Contributor.project_id == project_id).count()
            }
        }

    @staticmethod
    def get_technical_debt(project_id: int, db: Session) -> Dict[str, Any]:
        """
        Derives proxy technical debt signals from GitHub activity patterns.
        Analyzes issue backlog debt, PR cycle time debt, stale branch debt.
        """
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project {project_id} not found")

        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        sixty_days_ago = now - timedelta(days=60)

        all_issues = db.query(Issue).filter(Issue.project_id == project_id).all()
        all_prs = db.query(PullRequest).filter(PullRequest.project_id == project_id).all()
        all_branches = db.query(Branch).filter(Branch.project_id == project_id).all()
        all_commits = db.query(Commit).filter(Commit.project_id == project_id).all()

        # Issue Backlog Debt
        open_issues = [i for i in all_issues if i.state == "open"]
        stale_issues = [i for i in open_issues if i.created_at and i.created_at <= sixty_days_ago]
        issue_debt_score = min(100, len(open_issues) * 2 + len(stale_issues) * 5)

        # PR Cycle Time Debt
        merged_prs = [p for p in all_prs if p.is_merged and p.created_at and p.merged_at]
        slow_prs = [p for p in merged_prs if (p.merged_at - p.created_at).total_seconds() > 7 * 24 * 3600]
        pr_debt_score = min(100, (len(slow_prs) / max(len(merged_prs), 1)) * 100)

        # Branch Proliferation Debt
        non_default_branches = [b for b in all_branches if not b.is_default]
        branch_debt_score = min(100, len(non_default_branches) * 5)

        # Code Churn Proxy (commits with "fix", "hotfix", "bug" in message)
        fix_commits = [c for c in all_commits if any(
            kw in (c.message or "").lower() for kw in ["fix", "hotfix", "bug", "patch", "revert"]
        )]
        total_commits = len(all_commits)
        churn_ratio = (len(fix_commits) / total_commits) * 100 if total_commits > 0 else 0
        churn_debt_score = min(100, churn_ratio * 2)

        # Documentation Debt (commits with "docs", "readme", "changelog")
        doc_commits = [c for c in all_commits if any(
            kw in (c.message or "").lower() for kw in ["docs", "readme", "documentation", "changelog"]
        )]
        doc_ratio = (len(doc_commits) / total_commits) * 100 if total_commits > 0 else 0
        doc_debt_score = max(0, 100 - doc_ratio * 10)

        # Overall Debt Score
        overall_debt_score = round(
            (issue_debt_score * 0.3 + pr_debt_score * 0.25 + branch_debt_score * 0.15 +
             churn_debt_score * 0.2 + doc_debt_score * 0.1), 1
        )

        # Debt categories
        debt_categories = [
            {
                "category": "Issue Backlog",
                "score": round(issue_debt_score, 1),
                "items": len(open_issues),
                "stale_items": len(stale_issues),
                "description": f"{len(open_issues)} open issues, {len(stale_issues)} stale (60+ days)",
                "estimated_hours": len(open_issues) * 4,
                "icon": "bug"
            },
            {
                "category": "PR Cycle Time",
                "score": round(pr_debt_score, 1),
                "items": len(slow_prs),
                "stale_items": len(slow_prs),
                "description": f"{len(slow_prs)} of {len(merged_prs)} PRs took 7+ days to merge",
                "estimated_hours": len(slow_prs) * 2,
                "icon": "git-pull-request"
            },
            {
                "category": "Branch Proliferation",
                "score": round(branch_debt_score, 1),
                "items": len(non_default_branches),
                "stale_items": 0,
                "description": f"{len(non_default_branches)} non-default branches in repository",
                "estimated_hours": len(non_default_branches) * 1,
                "icon": "git-branch"
            },
            {
                "category": "Code Churn (Fix Rate)",
                "score": round(churn_debt_score, 1),
                "items": len(fix_commits),
                "stale_items": 0,
                "description": f"{len(fix_commits)} of {total_commits} commits are fix/revert/bug commits ({round(churn_ratio, 1)}%)",
                "estimated_hours": len(fix_commits) * 3,
                "icon": "refresh-cw"
            },
            {
                "category": "Documentation",
                "score": round(doc_debt_score, 1),
                "items": len(doc_commits),
                "stale_items": 0,
                "description": f"Only {round(doc_ratio, 1)}% of commits include documentation updates",
                "estimated_hours": max(0, 20 - len(doc_commits)) * 2,
                "icon": "file-text"
            }
        ]

        # Commit message quality breakdown for chart
        commit_types = {"fix": 0, "feat": 0, "docs": 0, "refactor": 0, "test": 0, "chore": 0, "other": 0}
        for c in all_commits:
            msg = (c.message or "").lower()
            if "fix" in msg or "bug" in msg or "hotfix" in msg:
                commit_types["fix"] += 1
            elif msg.startswith("feat") or "feature" in msg or "add " in msg:
                commit_types["feat"] += 1
            elif "docs" in msg or "readme" in msg:
                commit_types["docs"] += 1
            elif "refactor" in msg or "cleanup" in msg or "clean up" in msg:
                commit_types["refactor"] += 1
            elif "test" in msg:
                commit_types["test"] += 1
            elif "chore" in msg or "update dep" in msg or "bump" in msg:
                commit_types["chore"] += 1
            else:
                commit_types["other"] += 1

        commit_type_chart = [{"type": k, "count": v} for k, v in commit_types.items() if v > 0]

        total_estimated_hours = sum(d["estimated_hours"] for d in debt_categories)

        return {
            "project_id": project_id,
            "overall_debt_score": overall_debt_score,
            "debt_level": "high" if overall_debt_score > 60 else ("medium" if overall_debt_score > 30 else "low"),
            "total_estimated_debt_hours": total_estimated_hours,
            "debt_categories": debt_categories,
            "commit_type_breakdown": commit_type_chart,
            "refactoring_candidates": [
                {
                    "area": "Long-lived branches",
                    "priority": "medium",
                    "description": f"Clean up {len(non_default_branches)} non-default branches",
                    "effort": f"{len(non_default_branches)}h"
                },
                {
                    "area": "Stale issue triage",
                    "priority": "high" if len(stale_issues) > 5 else "medium",
                    "description": f"Resolve or close {len(stale_issues)} issues open for 60+ days",
                    "effort": f"{len(stale_issues) * 2}h"
                },
                {
                    "area": "Fix-commit refactoring",
                    "priority": "medium" if churn_ratio > 30 else "low",
                    "description": f"Investigate root causes of {len(fix_commits)} fix/hotfix commits",
                    "effort": f"{len(fix_commits) // 2}h"
                },
                {
                    "area": "Documentation updates",
                    "priority": "low",
                    "description": f"Improve documentation coverage (currently {round(doc_ratio, 1)}% of commits mention docs)",
                    "effort": "8-16h"
                }
            ],
            "metrics": {
                "total_commits": total_commits,
                "fix_commits": len(fix_commits),
                "fix_ratio_pct": round(churn_ratio, 1),
                "open_issues": len(open_issues),
                "stale_issues": len(stale_issues),
                "total_branches": len(all_branches),
                "non_default_branches": len(non_default_branches),
                "slow_prs": len(slow_prs),
                "total_merged_prs": len(merged_prs)
            }
        }

    @staticmethod
    def get_digital_twin_state(project_id: int, db: Session) -> Dict[str, Any]:
        """
        Returns the current Digital Twin state model of the repository.
        Summarizes entity counts, sync state, and twin fidelity.
        """
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project {project_id} not found")

        commit_count = db.query(Commit).filter(Commit.project_id == project_id).count()
        contributor_count = db.query(Contributor).filter(Contributor.project_id == project_id).count()
        issue_count = db.query(Issue).filter(Issue.project_id == project_id).count()
        pr_count = db.query(PullRequest).filter(PullRequest.project_id == project_id).count()
        release_count = db.query(Release).filter(Release.project_id == project_id).count()
        branch_count = db.query(Branch).filter(Branch.project_id == project_id).count()

        total_entities = commit_count + contributor_count + issue_count + pr_count + release_count + branch_count

        # Compute twin fidelity based on synced data completeness
        fidelity_components = [
            {"name": "Commits", "synced": commit_count, "icon": "git-commit"},
            {"name": "Contributors", "synced": contributor_count, "icon": "users"},
            {"name": "Issues", "synced": issue_count, "icon": "alert-circle"},
            {"name": "Pull Requests", "synced": pr_count, "icon": "git-pull-request"},
            {"name": "Releases", "synced": release_count, "icon": "tag"},
            {"name": "Branches", "synced": branch_count, "icon": "git-branch"},
        ]

        has_data = sum(1 for f in fidelity_components if f["synced"] > 0)
        fidelity_score = round((has_data / len(fidelity_components)) * 100, 1)

        # Calculate staleness
        now = datetime.now(timezone.utc)
        staleness_minutes = None
        if project.last_synced_at:
            staleness_minutes = round((now - project.last_synced_at).total_seconds() / 60, 1)

        sync_status = "fresh"
        if staleness_minutes is None:
            sync_status = "never_synced"
        elif staleness_minutes > 1440:  # 24 hours
            sync_status = "stale"
        elif staleness_minutes > 60:
            sync_status = "aging"

        return {
            "project_id": project_id,
            "twin_name": f"Digital Twin: {project.full_name}",
            "twin_status": project.status,
            "sync_status": sync_status,
            "staleness_minutes": staleness_minutes,
            "last_synced_at": project.last_synced_at.isoformat() if project.last_synced_at else None,
            "health_score": project.health_score,
            "fidelity_score": fidelity_score,
            "total_entities": total_entities,
            "entity_map": fidelity_components,
            "repository": {
                "full_name": project.full_name,
                "html_url": project.html_url,
                "language": project.language,
                "default_branch": project.default_branch,
                "visibility": project.visibility,
                "stars": project.stars_count,
                "forks": project.forks_count,
                "license": project.license_name,
                "created_at": project.repo_created_at.isoformat() if project.repo_created_at else None,
                "pushed_at": project.repo_pushed_at.isoformat() if project.repo_pushed_at else None,
            },
            "layers": [
                {
                    "name": "Data Collection Layer",
                    "status": "active" if commit_count > 0 else "empty",
                    "description": "GitHub API → PostgreSQL ETL pipeline",
                    "metrics": f"{total_entities} entities synced"
                },
                {
                    "name": "State Model Layer",
                    "status": "active" if project.status == "synced" else "syncing",
                    "description": "Normalized entity relationship model",
                    "metrics": f"{fidelity_score}% fidelity"
                },
                {
                    "name": "Health Analysis Layer",
                    "status": "active" if project.health_score > 0 else "pending",
                    "description": "Repository Health Index computation engine",
                    "metrics": f"Score: {project.health_score}/100"
                },
                {
                    "name": "Risk Detection Layer",
                    "status": "active",
                    "description": "Pattern-based risk signal analyzer",
                    "metrics": "Live pattern matching"
                },
                {
                    "name": "AI Intelligence Layer",
                    "status": "planned",
                    "description": "LLM-powered insights and Q&A",
                    "metrics": "Phase 3 roadmap"
                }
            ]
        }


analytics_service = AnalyticsService()
