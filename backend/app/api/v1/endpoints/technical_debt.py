import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.technical_debt_service import technical_debt_service
from app.services.dependency_service import dependency_service
from app.schemas.technical_debt import (
    TechnicalDebtSummaryResponse,
    IssueAgeAnalysisResponse,
    PRAgeAnalysisResponse,
    BranchAgeAnalysisResponse,
    InvestigationHotspotsResponse,
    DependenciesResponse,
)

logger = logging.getLogger("digital_twin.api.technical_debt")
router = APIRouter()


def _adapt_summary_for_frontend(raw: dict) -> dict:
    """
    Adapts the raw service output to the frontend TechnicalDebtData shape.
    Adds debt_categories, commit_type_breakdown, refactoring_candidates, and metrics.
    """
    indicators = raw.get("indicators", [])
    composite = raw.get("composite_score", 0.0)
    level = raw.get("level", "low")

    icon_map = {
        "issue_backlog_age": "bug",
        "pr_cycle_delay": "git-pull-request",
        "fix_commit_concentration": "refresh-cw",
        "hotspot_concentration": "file-text",
        "branch_sprawl": "git-branch",
    }

    debt_categories = []
    for ind in indicators:
        ind_type = ind.get("indicator_type", "")
        evidence = ind.get("evidence", {})
        est_hours = 0
        items_count = 0
        stale_items = 0
        if ind_type == "issue_backlog_age":
            items_count = evidence.get("open_issues", 0)
            stale_items = evidence.get("stale_issues_90d", 0)
            est_hours = stale_items * 4
        elif ind_type == "pr_cycle_delay":
            items_count = evidence.get("open_prs", 0)
            est_hours = items_count * 3
        elif ind_type == "fix_commit_concentration":
            items_count = evidence.get("fix_commits", 0)
            est_hours = int(items_count * 1.5)
        elif ind_type == "hotspot_concentration":
            items_count = evidence.get("total_hotspots_tracked", 0)
            est_hours = evidence.get("high_priority_hotspots", 0) * 8
        elif ind_type == "branch_sprawl":
            items_count = evidence.get("non_default_branches", 0)
            est_hours = items_count
        debt_categories.append({
            "category": ind.get("name", ind_type),
            "score": ind.get("score", 0.0),
            "items": items_count,
            "stale_items": stale_items,
            "description": ind.get("description", ""),
            "estimated_hours": est_hours,
            "icon": icon_map.get(ind_type, "file-text"),
        })

    fix_ind = next((i for i in indicators if i.get("indicator_type") == "fix_commit_concentration"), {})
    fix_ev = fix_ind.get("evidence", {})
    total_commits = fix_ev.get("total_commits", 0)
    fix_commits_count = fix_ev.get("fix_commits", 0)
    feature_commits = max(0, total_commits - fix_commits_count)
    commit_type_breakdown = []
    if total_commits > 0:
        commit_type_breakdown = [
            {"type": "fix/bug", "count": fix_commits_count, "percentage": round(fix_commits_count / total_commits * 100, 1)},
            {"type": "feature/other", "count": feature_commits, "percentage": round(feature_commits / total_commits * 100, 1)},
        ]

    refactoring_candidates = []
    for ind in indicators:
        sev = ind.get("severity", "low")
        if sev in ("high", "medium"):
            effort_map = {"high": "3-5 days", "medium": "1-2 days"}
            refactoring_candidates.append({
                "area": ind.get("name", ""),
                "priority": sev,
                "description": ind.get("description", ""),
                "effort": effort_map.get(sev, "< 1 day"),
            })

    issue_ind = next((i for i in indicators if i.get("indicator_type") == "issue_backlog_age"), {})
    issue_ev = issue_ind.get("evidence", {})
    pr_ind = next((i for i in indicators if i.get("indicator_type") == "pr_cycle_delay"), {})
    pr_ev = pr_ind.get("evidence", {})
    branch_ind = next((i for i in indicators if i.get("indicator_type") == "branch_sprawl"), {})
    branch_ev = branch_ind.get("evidence", {})

    metrics = {
        "total_commits": total_commits,
        "fix_commits": fix_commits_count,
        "fix_ratio_pct": fix_ev.get("fix_ratio_pct", 0.0),
        "open_issues": issue_ev.get("open_issues", 0),
        "stale_issues": issue_ev.get("stale_issues_90d", 0),
        "total_branches": branch_ev.get("total_branches", 0),
        "non_default_branches": branch_ev.get("non_default_branches", 0),
        "slow_prs": pr_ev.get("open_prs", 0),
        "total_merged_prs": 0,
    }

    raw["debt_categories"] = debt_categories
    raw["commit_type_breakdown"] = commit_type_breakdown
    raw["refactoring_candidates"] = refactoring_candidates
    raw["metrics"] = metrics
    raw["overall_debt_score"] = composite
    raw["debt_level"] = level
    raw["total_estimated_debt_hours"] = float(raw.get("total_estimated_remediation_hours", 0))
    raw["has_sufficient_data"] = True
    return raw


@router.get(
    "/projects/{project_id}/technical-debt",
    response_model=TechnicalDebtSummaryResponse,
    summary="Get Technical Debt Intelligence Summary",
    description="Returns composite heuristic indicator, weighted components, and frontend-compatible debt categories.",
)
async def get_technical_debt_summary(project_id: int, db: Session = Depends(get_db)):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    try:
        raw = technical_debt_service.get_technical_debt_summary(project_id, db)
        adapted = _adapt_summary_for_frontend(raw)
        return adapted
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Technical debt summary failed for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/projects/{project_id}/technical-debt/indicators",
    summary="Get Technical Debt Indicators Breakdown",
    description="Returns detailed weighted indicators with underlying observable evidence and mathematical formulas.",
)
async def get_indicators_breakdown(project_id: int, db: Session = Depends(get_db)):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    try:
        summary = technical_debt_service.get_technical_debt_summary(project_id, db)
        return {
            "project_id": project_id,
            "indicator_title": summary["indicator_title"],
            "composite_score": summary["composite_score"],
            "level": summary["level"],
            "indicators": summary["indicators"],
            "weights": summary["weights"],
            "formula_description": summary["formula_description"],
            "limitations": summary["limitations"],
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Technical debt indicators failed for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/projects/{project_id}/technical-debt/hotspots",
    response_model=InvestigationHotspotsResponse,
    summary="Get Technical Debt Investigation Hotspots",
    description="Combines change frequency, churn volume, and associated issues to highlight areas requiring investigation.",
)
async def get_investigation_hotspots(
    project_id: int,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    try:
        raw = technical_debt_service.get_investigation_hotspots(project_id, db, limit=limit)
        hotspots = []
        for h in raw.get("hotspots", []):
            hotspots.append({
                "path": h.get("path", ""),
                "change_count": h.get("change_count", 0),
                "churn": h.get("churn", 0),
                "contributor_count": h.get("contributor_count", 1),
                "last_changed_at": h.get("last_changed_at"),
                "associated_open_issues": h.get("associated_issues", 0),
                "investigation_score": float(h.get("change_count", 0)),
                "signal": h.get("evidence_summary", ""),
            })
        return {
            "project_id": project_id,
            "has_sufficient_data": len(hotspots) > 0,
            "hotspots": hotspots,
            "definition": raw.get("methodology", ""),
            "framing_notice": "Investigation hotspots highlight areas for review — NOT confirmed defects.",
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Investigation hotspots failed for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/projects/{project_id}/technical-debt/issues",
    response_model=IssueAgeAnalysisResponse,
    summary="Get Issue Age Analysis",
    description="Analyzes unresolved issue age distribution: median age, oldest issue, and age brackets.",
)
async def get_issue_age_analysis(project_id: int, db: Session = Depends(get_db)):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    try:
        return technical_debt_service.get_issue_age_analysis(project_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Issue age analysis failed for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/projects/{project_id}/technical-debt/prs",
    response_model=PRAgeAnalysisResponse,
    summary="Get Pull Request Age Analysis",
    description="Analyzes pull request duration: median open PR age, oldest PR, and merge turnaround rate.",
)
async def get_pr_age_analysis(project_id: int, db: Session = Depends(get_db)):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    try:
        raw = technical_debt_service.get_pr_age_analysis(project_id, db)
        return {
            "project_id": project_id,
            "total_open_prs": raw.get("total_open_prs", 0),
            "median_open_age_days": raw.get("median_open_pr_age_days", 0.0),
            "oldest_open_pr": raw.get("oldest_open_pr"),
            "age_distribution": raw.get("distribution", []),
            "merge_turnaround": {
                "avg_days": raw.get("avg_merge_turnaround_days"),
                "total_merged": raw.get("total_merged_prs", 0),
            },
            "framing_notice": raw.get("framing_notice", ""),
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"PR age analysis failed for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/projects/{project_id}/technical-debt/branches",
    response_model=BranchAgeAnalysisResponse,
    summary="Get Branch Age Analysis",
    description="Analyzes branch proliferation and long-lived branches, noting API metadata constraints.",
)
async def get_branch_age_analysis(project_id: int, db: Session = Depends(get_db)):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    try:
        raw = technical_debt_service.get_branch_age_analysis(project_id, db)
        return {
            "project_id": project_id,
            "total_branches": raw.get("total_branches", 0),
            "non_default_branches": raw.get("non_default_branches", 0),
            "protected_branches": 0,
            "branches": [],
            "api_limitation_notice": raw.get("note", ""),
            "framing_notice": "Branch count is an observable indicator; does NOT confirm stale code.",
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Branch age analysis failed for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/projects/{project_id}/dependencies",
    response_model=DependenciesResponse,
    summary="Get Repository Dependencies",
    description="Returns detected package manifests and declared dependencies. Vulnerability scanning requires CVE database.",
)
async def get_dependencies(project_id: int, db: Session = Depends(get_db)):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    try:
        return dependency_service.get_project_dependencies(project_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Dependency retrieval failed for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
