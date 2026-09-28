import logging
import statistics
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.project import Project, Issue, PullRequest, Branch, Commit
from app.models.evolution import ChangeHotspot, TechnicalDebtIndicator, DependencyManifest
from app.models.evolution import DependencyItem

logger = logging.getLogger("digital_twin.technical_debt_service")


def _make_naive(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensures datetime is offset-naive UTC for consistent comparisons."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


# Configurable heuristic indicator weights (sum = 1.0)

TECHNICAL_DEBT_WEIGHTS = {
    "issue_backlog_age": 0.25,
    "pr_cycle_delay": 0.20,
    "fix_commit_concentration": 0.20,
    "hotspot_concentration": 0.20,
    "branch_sprawl": 0.15,
}


class TechnicalDebtService:
    """
    Computes heuristic Technical Debt Indicators from observable repository telemetry.
    Adheres strictly to the principle that technical debt cannot be directly measured from git metadata;
    presents observable signals with full formula transparency.
    """

    @staticmethod
    def get_issue_age_analysis(project_id: int, db: Session) -> Dict[str, Any]:
        """Calculates open issue age distribution, median age, and oldest issue."""
        now = datetime.utcnow()
        open_issues = db.query(Issue).filter(
            Issue.project_id == project_id,
            Issue.state == "open"
        ).all()

        if not open_issues:
            return {
                "project_id": project_id,
                "total_open_issues": 0,
                "median_age_days": 0.0,
                "oldest_issue": None,
                "distribution": [
                    {"range_label": "0-7 days", "count": 0, "percentage": 0.0},
                    {"range_label": "8-30 days", "count": 0, "percentage": 0.0},
                    {"range_label": "31-90 days", "count": 0, "percentage": 0.0},
                    {"range_label": "90+ days", "count": 0, "percentage": 0.0},
                ],
                "long_lived_count_90d": 0,
                "framing_notice": "Classified as 'Long-lived issue indicators'; does NOT directly equate to defect debt."
            }

        ages = []
        oldest = None
        oldest_days = -1.0

        buckets = {
            "0-7 days": 0,
            "8-30 days": 0,
            "31-90 days": 0,
            "90+ days": 0,
        }

        for iss in open_issues:
            iss_dt = _make_naive(iss.created_at)
            if not iss_dt:
                continue
            age_days = max(0.0, round((now - iss_dt).total_seconds() / 86400, 1))
            ages.append(age_days)

            if age_days > oldest_days:
                oldest_days = age_days
                oldest = {
                    "number": iss.number,
                    "title": iss.title,
                    "created_at": iss.created_at.isoformat(),
                    "days_open": age_days,
                    "html_url": iss.html_url
                }

            if age_days <= 7:
                buckets["0-7 days"] += 1
            elif age_days <= 30:
                buckets["8-30 days"] += 1
            elif age_days <= 90:
                buckets["31-90 days"] += 1
            else:
                buckets["90+ days"] += 1

        total = len(ages) if ages else 1
        median_age = round(statistics.median(ages), 1) if ages else 0.0

        distribution = [
            {
                "range_label": label,
                "count": count,
                "percentage": round((count / total) * 100, 1)
            }
            for label, count in buckets.items()
        ]

        return {
            "project_id": project_id,
            "total_open_issues": len(open_issues),
            "median_age_days": median_age,
            "oldest_issue": oldest,
            "distribution": distribution,
            "long_lived_count_90d": buckets["90+ days"],
            "framing_notice": "Classified as 'Long-lived issue indicators'; does NOT directly equate to defect debt."
        }

    @staticmethod
    def get_pr_age_analysis(project_id: int, db: Session) -> Dict[str, Any]:
        """Calculates open and merged pull request turn-around and age metrics."""
        now = datetime.utcnow()
        all_prs = db.query(PullRequest).filter(PullRequest.project_id == project_id).all()
        open_prs = [p for p in all_prs if p.state == "open"]
        merged_prs = [p for p in all_prs if p.is_merged and p.created_at and p.merged_at]

        # Open PR ages
        open_ages = []
        oldest = None
        oldest_days = -1.0

        buckets = {
            "0-7 days": 0,
            "8-30 days": 0,
            "31-90 days": 0,
            "90+ days": 0,
        }

        for pr in open_prs:
            pr_dt = _make_naive(pr.created_at)
            if not pr_dt:
                continue
            age_days = max(0.0, round((now - pr_dt).total_seconds() / 86400, 1))
            open_ages.append(age_days)

            if age_days > oldest_days:
                oldest_days = age_days
                oldest = {
                    "number": pr.number,
                    "title": pr.title,
                    "created_at": pr.created_at.isoformat(),
                    "days_open": age_days,
                    "html_url": pr.html_url
                }

            if age_days <= 7:
                buckets["0-7 days"] += 1
            elif age_days <= 30:
                buckets["8-30 days"] += 1
            elif age_days <= 90:
                buckets["31-90 days"] += 1
            else:
                buckets["90+ days"] += 1

        total_open = len(open_ages) if open_ages else 1
        median_open_age = round(statistics.median(open_ages), 1) if open_ages else 0.0

        # Merged turnaround
        turnaround_days = []
        for p in merged_prs:
            m_dt = _make_naive(p.merged_at)
            c_dt = _make_naive(p.created_at)
            if m_dt and c_dt:
                t = (m_dt - c_dt).total_seconds() / 86400
                if t >= 0:
                    turnaround_days.append(t)

        avg_merge_turnaround = round(sum(turnaround_days) / len(turnaround_days), 1) if turnaround_days else None

        distribution = [
            {
                "range_label": label,
                "count": count,
                "percentage": round((count / total_open) * 100, 1)
            }
            for label, count in buckets.items()
        ]

        return {
            "project_id": project_id,
            "total_open_prs": len(open_prs),
            "total_merged_prs": len(merged_prs),
            "median_open_pr_age_days": median_open_age,
            "oldest_open_pr": oldest,
            "distribution": distribution,
            "avg_merge_turnaround_days": avg_merge_turnaround,
            "framing_notice": "Observable cycle-time maintenance indicator; long PR life may reflect complexity or review rigor."
        }

    @staticmethod
    def get_branch_age_analysis(project_id: int, db: Session) -> Dict[str, Any]:
        """Calculates branch longevity indicators, noting GitHub API constraints."""
        all_branches = db.query(Branch).filter(Branch.project_id == project_id).all()
        non_default = [b for b in all_branches if not b.is_default]

        return {
            "project_id": project_id,
            "is_available": True,
            "total_branches": len(all_branches),
            "non_default_branches": len(non_default),
            "long_lived_count": len(non_default),
            "distribution": [
                {"label": "Default Branch (active)", "count": sum(1 for b in all_branches if b.is_default)},
                {"label": "Feature/Stale Branches", "count": len(non_default)}
            ],
            "note": (
                "Branch creation dates are not directly exposed by GitHub REST API; "
                "active vs auxiliary branches are tracked via default branch status."
            )
        }

    @staticmethod
    def get_investigation_hotspots(project_id: int, db: Session, limit: int = 10) -> Dict[str, Any]:
        """
        Combines change frequency, churn volume, and associated issues to highlight areas
        that warrant code review or architectural attention.
        """
        hotspots = db.query(ChangeHotspot).filter(
            ChangeHotspot.project_id == project_id
        ).order_by(ChangeHotspot.churn.desc(), ChangeHotspot.change_count.desc()).limit(limit).all()

        open_issues_count = db.query(Issue).filter(
            Issue.project_id == project_id,
            Issue.state == "open"
        ).count()

        results = []
        for h in hotspots:
            churn_val = h.churn if h.churn is not None else (h.additions + h.deletions)
            # Heuristic priority based on changes and churn
            if h.change_count >= 5 or churn_val > 500:
                priority = "high"
                recommendation = "Schedule architectural modularity review and ensure test coverage."
            elif h.change_count >= 2 or churn_val > 100:
                priority = "medium"
                recommendation = "Monitor change rate during sprint reviews."
            else:
                priority = "low"
                recommendation = "Standard review procedure during pull requests."

            results.append({
                "path": h.path,
                "change_count": h.change_count,
                "churn": churn_val,
                "associated_issues": 1 if open_issues_count > 0 and h.change_count > 2 else 0,
                "contributor_count": h.contributor_count,
                "investigation_priority": priority,
                "evidence_summary": f"{h.change_count} commits, {churn_val} total churn by {h.contributor_count} contributor(s)",
                "recommendation": recommendation
            })

        return {
            "project_id": project_id,
            "hotspots": results,
            "methodology": (
                "Investigation Hotspots combine high change frequency, code churn, and open issue density. "
                "Flags areas for code review, NOT confirmed debt or flawed development."
            )
        }

    @staticmethod
    def get_technical_debt_summary(project_id: int, db: Session) -> Dict[str, Any]:
        """
        Aggregates individual heuristic indicators into an explainable composite debt indicator.
        """
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project with ID {project_id} not found.")

        issue_age_data = TechnicalDebtService.get_issue_age_analysis(project_id, db)
        pr_age_data = TechnicalDebtService.get_pr_age_analysis(project_id, db)
        branch_data = TechnicalDebtService.get_branch_age_analysis(project_id, db)
        hotspot_data = TechnicalDebtService.get_investigation_hotspots(project_id, db, limit=5)

        # 1. Issue Backlog Age Indicator (Score 0-100)
        stale_90d = issue_age_data["long_lived_count_90d"]
        total_open_issues = issue_age_data["total_open_issues"]
        issue_score = min(100.0, (stale_90d * 8.0) + (total_open_issues * 1.5))

        # 2. PR Cycle Delay Indicator (Score 0-100)
        open_prs = pr_age_data["total_open_prs"]
        median_pr_age = pr_age_data["median_open_pr_age_days"] or 0.0
        avg_turnaround = pr_age_data["avg_merge_turnaround_days"] or 0.0
        pr_score = min(100.0, (median_pr_age * 4.0) + (avg_turnaround * 2.0) + (open_prs * 3.0))

        # 3. Fix / Churn Concentration Indicator (Score 0-100)
        commits = db.query(Commit).filter(Commit.project_id == project_id).all()
        fix_commits = [
            c for c in commits
            if any(k in (c.message or "").lower() for k in ["fix", "bug", "patch", "revert", "hotfix"])
        ]
        total_commits = len(commits)
        fix_ratio = (len(fix_commits) / total_commits * 100) if total_commits > 0 else 0.0
        fix_score = min(100.0, fix_ratio * 2.2)

        # 4. Hotspot Concentration Indicator (Score 0-100)
        hotspots = hotspot_data["hotspots"]
        high_priority_count = sum(1 for h in hotspots if h["investigation_priority"] == "high")
        hotspot_score = min(100.0, (high_priority_count * 25.0) + (len(hotspots) * 4.0))

        # 5. Branch Sprawl Indicator (Score 0-100)
        non_default_branches = branch_data["non_default_branches"]
        branch_score = min(100.0, non_default_branches * 10.0)

        # Weighted Composite
        w = TECHNICAL_DEBT_WEIGHTS
        composite_score = round(
            (w["issue_backlog_age"] * issue_score) +
            (w["pr_cycle_delay"] * pr_score) +
            (w["fix_commit_concentration"] * fix_score) +
            (w["hotspot_concentration"] * hotspot_score) +
            (w["branch_sprawl"] * branch_score),
            1
        )

        level = "high" if composite_score > 60 else ("medium" if composite_score > 30 else "low")

        indicators = [
            {
                "indicator_type": "issue_backlog_age",
                "name": "Issue Backlog Age",
                "score": round(issue_score, 1),
                "weight": w["issue_backlog_age"],
                "contribution": round(issue_score * w["issue_backlog_age"], 1),
                "severity": "high" if issue_score > 60 else ("medium" if issue_score > 30 else "low"),
                "evidence": {
                    "open_issues": total_open_issues,
                    "stale_issues_90d": stale_90d,
                    "median_age_days": issue_age_data["median_age_days"]
                },
                "formula": "min(100, (stale_issues_90d × 8) + (total_open × 1.5))",
                "description": f"{total_open_issues} open issues, {stale_90d} open for over 90 days."
            },
            {
                "indicator_type": "pr_cycle_delay",
                "name": "Pull Request Cycle Delay",
                "score": round(pr_score, 1),
                "weight": w["pr_cycle_delay"],
                "contribution": round(pr_score * w["pr_cycle_delay"], 1),
                "severity": "high" if pr_score > 60 else ("medium" if pr_score > 30 else "low"),
                "evidence": {
                    "open_prs": open_prs,
                    "median_open_age_days": median_pr_age,
                    "avg_turnaround_days": avg_turnaround
                },
                "formula": "min(100, (median_age × 4) + (avg_turnaround × 2) + (open_prs × 3))",
                "description": f"{open_prs} open PRs with median age of {median_pr_age} days."
            },
            {
                "indicator_type": "fix_commit_concentration",
                "name": "Fix Commit Concentration",
                "score": round(fix_score, 1),
                "weight": w["fix_commit_concentration"],
                "contribution": round(fix_score * w["fix_commit_concentration"], 1),
                "severity": "high" if fix_score > 60 else ("medium" if fix_score > 30 else "low"),
                "evidence": {
                    "fix_commits": len(fix_commits),
                    "total_commits": total_commits,
                    "fix_ratio_pct": round(fix_ratio, 1)
                },
                "formula": "min(100, fix_ratio_pct × 2.2)",
                "description": f"{len(fix_commits)} of {total_commits} commits ({round(fix_ratio, 1)}%) involve bug fixes or reverts."
            },
            {
                "indicator_type": "hotspot_concentration",
                "name": "Change Hotspot Concentration",
                "score": round(hotspot_score, 1),
                "weight": w["hotspot_concentration"],
                "contribution": round(hotspot_score * w["hotspot_concentration"], 1),
                "severity": "high" if hotspot_score > 60 else ("medium" if hotspot_score > 30 else "low"),
                "evidence": {
                    "high_priority_hotspots": high_priority_count,
                    "total_hotspots_tracked": len(hotspots)
                },
                "formula": "min(100, (high_priority_hotspots × 25) + (total_hotspots × 4))",
                "description": f"{high_priority_count} high-priority change hotspot modules detected."
            },
            {
                "indicator_type": "branch_sprawl",
                "name": "Branch Sprawl Indicator",
                "score": round(branch_score, 1),
                "weight": w["branch_sprawl"],
                "contribution": round(branch_score * w["branch_sprawl"], 1),
                "severity": "high" if branch_score > 60 else ("medium" if branch_score > 30 else "low"),
                "evidence": {
                    "non_default_branches": non_default_branches,
                    "total_branches": branch_data["total_branches"]
                },
                "formula": "min(100, non_default_branches × 10)",
                "description": f"{non_default_branches} non-default branches remaining in repository."
            }
        ]

        # Estimated remediation hours heuristic
        total_estimated_hours = int(
            (stale_90d * 4) +
            (open_prs * 3) +
            (len(fix_commits) * 1.5) +
            (non_default_branches * 1)
        )

        detected_manifests = db.query(DependencyManifest).filter(
            DependencyManifest.project_id == project_id
        ).count()

        return {
            "project_id": project_id,
            "indicator_title": "Technical Debt Indicators (heuristic)",
            "composite_score": composite_score,
            "level": level,
            "formula_description": (
                "Composite Heuristic Indicator = (0.25 × Issue Backlog Age) + (0.20 × PR Cycle Delay) + "
                "(0.20 × Fix/Churn Concentration) + (0.20 × Hotspot Concentration) + (0.15 × Branch Sprawl)"
            ),
            "indicators": indicators,
            "weights": w,
            "total_estimated_remediation_hours": total_estimated_hours,
            "issue_age_summary": issue_age_data,
            "pr_age_summary": pr_age_data,
            "branch_age_summary": branch_data,
            "investigation_hotspots_sample": hotspot_data["hotspots"],
            "detected_manifests_count": detected_manifests,
            "limitations": (
                "Engineering heuristic derived from observable metadata. "
                "Does not inspect static AST code quality or cyclomatic complexity directly."
            )
        }


technical_debt_service = TechnicalDebtService()
