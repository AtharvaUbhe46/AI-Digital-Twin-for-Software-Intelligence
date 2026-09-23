from typing import Dict, Any, Tuple, Optional, List
from app.core.config import settings


def score_to_status(score: Optional[float]) -> str:
    """Map numeric score (0-100) to standard status string."""
    if score is None:
        return "INSUFFICIENT_DATA"
    if score >= 75.0:
        return "HEALTHY"
    if score >= 50.0:
        return "ATTENTION"
    if score >= 30.0:
        return "DEGRADED"
    return "CRITICAL"


def score_activity(metrics: Dict[str, Any]) -> Tuple[Optional[float], str]:
    if not metrics.get("has_data"):
        return None, "INSUFFICIENT_DATA"

    days = metrics.get("days_since_last_commit", 999)
    cpw = metrics.get("commits_per_week", 0.0)

    # Recency score
    if days <= 3:
        recency_score = 100.0
    elif days <= 7:
        recency_score = 90.0
    elif days <= 14:
        recency_score = 75.0
    elif days <= 30:
        recency_score = 55.0
    elif days <= 60:
        recency_score = 35.0
    else:
        recency_score = 15.0

    # Frequency score
    if cpw >= 10.0:
        freq_score = 100.0
    elif cpw >= 3.0:
        freq_score = 85.0
    elif cpw >= 1.0:
        freq_score = 70.0
    elif cpw > 0.0:
        freq_score = 50.0
    else:
        freq_score = 25.0

    final_score = round(0.60 * recency_score + 0.40 * freq_score, 1)
    return final_score, score_to_status(final_score)


def score_issues(metrics: Dict[str, Any]) -> Tuple[Optional[float], str]:
    if not metrics.get("has_data"):
        return None, "INSUFFICIENT_DATA"

    total_open = metrics.get("total_open", 0)
    if total_open == 0:
        return 95.0, "HEALTHY"

    stale_ratio = metrics.get("stale_ratio", 0.0)
    closure_rate = metrics.get("closure_rate", 50.0)

    # Stale ratio score (lower ratio is better)
    if stale_ratio == 0.0:
        stale_score = 100.0
    elif stale_ratio <= 15.0:
        stale_score = 85.0
    elif stale_ratio <= 35.0:
        stale_score = 65.0
    elif stale_ratio <= 60.0:
        stale_score = 45.0
    else:
        stale_score = 25.0

    # Closure rate score
    if closure_rate >= 80.0:
        closure_score = 100.0
    elif closure_rate >= 50.0:
        closure_score = 80.0
    elif closure_rate >= 25.0:
        closure_score = 60.0
    else:
        closure_score = 40.0

    final_score = round(0.65 * stale_score + 0.35 * closure_score, 1)
    return final_score, score_to_status(final_score)


def score_pull_requests(metrics: Dict[str, Any]) -> Tuple[Optional[float], str]:
    if not metrics.get("has_data"):
        return None, "INSUFFICIENT_DATA"

    total_open = metrics.get("total_open", 0)
    if total_open == 0:
        return 95.0, "HEALTHY"

    stale_ratio = metrics.get("stale_ratio", 0.0)
    merge_rate = metrics.get("merge_rate", 50.0)

    if stale_ratio == 0.0:
        stale_score = 100.0
    elif stale_ratio <= 20.0:
        stale_score = 85.0
    elif stale_ratio <= 40.0:
        stale_score = 65.0
    elif stale_ratio <= 65.0:
        stale_score = 45.0
    else:
        stale_score = 25.0

    if merge_rate >= 75.0:
        merge_score = 100.0
    elif merge_rate >= 50.0:
        merge_score = 80.0
    elif merge_rate >= 25.0:
        merge_score = 60.0
    else:
        merge_score = 40.0

    final_score = round(0.65 * stale_score + 0.35 * merge_score, 1)
    return final_score, score_to_status(final_score)


def score_contributors(metrics: Dict[str, Any]) -> Tuple[Optional[float], str]:
    if not metrics.get("has_data"):
        return None, "INSUFFICIENT_DATA"

    top_pct = metrics.get("top_contributor_percentage", 50.0)
    active = metrics.get("active_contributors_recent", 1)

    # Diversity score (lower concentration = healthier distribution)
    if top_pct <= 35.0:
        div_score = 100.0
    elif top_pct <= 50.0:
        div_score = 85.0
    elif top_pct <= 65.0:
        div_score = 70.0
    elif top_pct <= 80.0:
        div_score = 50.0
    else:
        div_score = 35.0

    # Active count score
    if active >= 10:
        active_score = 100.0
    elif active >= 5:
        active_score = 85.0
    elif active >= 2:
        active_score = 70.0
    elif active >= 1:
        active_score = 55.0
    else:
        active_score = 30.0

    final_score = round(0.60 * div_score + 0.40 * active_score, 1)
    return final_score, score_to_status(final_score)


def score_releases(metrics: Dict[str, Any]) -> Tuple[Optional[float], str]:
    if not metrics.get("has_data"):
        return None, "INSUFFICIENT_DATA"

    days = metrics.get("days_since_latest_release", 999)

    if days <= 30:
        final_score = 100.0
    elif days <= 60:
        final_score = 90.0
    elif days <= 90:
        final_score = 75.0
    elif days <= 180:
        final_score = 60.0
    elif days <= 365:
        final_score = 40.0
    else:
        final_score = 25.0

    return final_score, score_to_status(final_score)


def score_maintenance(metrics: Dict[str, Any]) -> Tuple[Optional[float], str]:
    if not metrics.get("has_data"):
        return None, "INSUFFICIENT_DATA"

    days = metrics.get("days_since_last_commit", 0)
    stale_issues = metrics.get("stale_issues_count", 0)
    stale_prs = metrics.get("stale_prs_count", 0)

    # Inactivity penalty
    if days <= 7:
        inactivity_score = 100.0
    elif days <= 14:
        inactivity_score = 85.0
    elif days <= 30:
        inactivity_score = 65.0
    elif days <= 60:
        inactivity_score = 45.0
    else:
        inactivity_score = 20.0

    # Backlog staleness penalty
    total_stale = stale_issues + stale_prs
    if total_stale == 0:
        stale_score = 100.0
    elif total_stale <= 2:
        stale_score = 85.0
    elif total_stale <= 5:
        stale_score = 70.0
    elif total_stale <= 10:
        stale_score = 50.0
    else:
        stale_score = 30.0

    final_score = round(0.50 * inactivity_score + 0.50 * stale_score, 1)
    return final_score, score_to_status(final_score)


def calculate_overall_health(dimensions: List[Dict[str, Any]]) -> Tuple[float, str]:
    """
    Computes overall score from available dimensions with dynamic weight normalization.
    Missing/insufficient dimensions are not treated as 0; weights of available dimensions
    are normalized to sum to 1.0.
    """
    valid_dims = [d for d in dimensions if d.get("score") is not None and d.get("status") != "INSUFFICIENT_DATA"]

    if not valid_dims:
        return 0.0, "INSUFFICIENT_DATA"

    total_weight = sum(d["weight"] for d in valid_dims)
    if total_weight <= 0:
        # Fallback to equal weighting if configured weights sum to 0
        normalized_score = sum(d["score"] for d in valid_dims) / len(valid_dims)
    else:
        normalized_score = sum(d["score"] * (d["weight"] / total_weight) for d in valid_dims)

    final_score = round(normalized_score, 1)
    return final_score, score_to_status(final_score)
