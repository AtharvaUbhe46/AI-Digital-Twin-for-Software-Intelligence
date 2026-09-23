from typing import Dict, Any, List


def explain_activity(metrics: Dict[str, Any]) -> List[str]:
    if not metrics.get("has_data"):
        return [metrics.get("reason", "No commit activity available for analysis.")]

    days = metrics.get("days_since_last_commit", 0)
    recent = metrics.get("recent_commits", 0)
    window = metrics.get("recent_window_days", 30)
    cpw = metrics.get("commits_per_week", 0.0)
    active = metrics.get("active_contributors_recent", 0)

    bullets = []
    if days == 0:
        bullets.append("Repository had commit activity today.")
    elif days == 1:
        bullets.append("Last commit was recorded yesterday.")
    else:
        bullets.append(f"Last commit was recorded {days} days ago.")

    bullets.append(f"{recent} commits authored by {active} contributor(s) over the last {window} days (~{cpw} commits/week).")
    return bullets


def explain_issues(metrics: Dict[str, Any]) -> List[str]:
    if not metrics.get("has_data"):
        return [metrics.get("reason", "No issue tracking data available.")]

    total_open = metrics.get("total_open", 0)
    stale = metrics.get("stale_count", 0)
    stale_days = metrics.get("stale_threshold_days", 30)
    avg_age = metrics.get("avg_age_days", 0)
    closure_rate = metrics.get("closure_rate", 0.0)

    bullets = []
    if total_open == 0:
        bullets.append("Zero open issues currently in backlog.")
    else:
        bullets.append(f"{total_open} open issues with an average age of {avg_age} days.")

    if stale > 0:
        bullets.append(f"{stale} open issue(s) exceed the {stale_days}-day stale threshold.")
    else:
        bullets.append(f"No open issues exceed the {stale_days}-day stale threshold.")

    bullets.append(f"Recent issue closure rate is {closure_rate}%.")
    return bullets


def explain_pull_requests(metrics: Dict[str, Any]) -> List[str]:
    if not metrics.get("has_data"):
        return [metrics.get("reason", "No pull request data available.")]

    total_open = metrics.get("total_open", 0)
    stale = metrics.get("stale_count", 0)
    stale_days = metrics.get("stale_threshold_days", 14)
    avg_age = metrics.get("avg_age_days", 0)
    merge_rate = metrics.get("merge_rate", 0.0)

    bullets = []
    if total_open == 0:
        bullets.append("No open pull requests awaiting review.")
    else:
        bullets.append(f"{total_open} open pull request(s) with an average age of {avg_age} days.")

    if stale > 0:
        bullets.append(f"{stale} open pull request(s) exceed the {stale_days}-day review threshold.")
    else:
        bullets.append(f"All open pull requests are within the {stale_days}-day review window.")

    bullets.append(f"Recent pull request merge rate is {merge_rate}%.")
    return bullets


def explain_contributors(metrics: Dict[str, Any]) -> List[str]:
    if not metrics.get("has_data"):
        return [metrics.get("reason", "No contributor records available.")]

    active = metrics.get("active_contributors_recent", 0)
    total = metrics.get("total_contributors", 0)
    top_pct = metrics.get("top_contributor_percentage", 0.0)
    window = metrics.get("recent_window_days", 30)

    bullets = []
    bullets.append(f"{active} active contributor(s) during the last {window} days ({total} total tracked).")

    if top_pct >= 65.0:
        bullets.append(f"Primary contributor accounts for {top_pct}% of recent commits (elevated concentration).")
    else:
        bullets.append(f"Primary contributor accounts for {top_pct}% of commits (balanced contribution share).")

    return bullets


def explain_releases(metrics: Dict[str, Any]) -> List[str]:
    if not metrics.get("has_data"):
        return [metrics.get("reason", "No published releases recorded for this repository.")]

    tag = metrics.get("latest_release_tag", "unknown")
    days = metrics.get("days_since_latest_release", 0)
    total = metrics.get("total_releases", 0)

    bullets = [f"Latest release ({tag}) was published {days} days ago ({total} total releases tracked)."]
    return bullets


def explain_maintenance(metrics: Dict[str, Any]) -> List[str]:
    if not metrics.get("has_data"):
        return ["Insufficient data to determine maintenance state."]

    days = metrics.get("days_since_last_commit", 0)
    stale_issues = metrics.get("stale_issues_count", 0)
    stale_prs = metrics.get("stale_prs_count", 0)

    bullets = []
    if days > 30:
        bullets.append(f"Repository has been inactive for {days} days without new commits.")
    else:
        bullets.append(f"Repository has regular maintenance commits (last active {days} days ago).")

    total_stale = stale_issues + stale_prs
    if total_stale > 0:
        bullets.append(f"{total_stale} total stale items ({stale_issues} issues, {stale_prs} PRs) requiring attention.")
    else:
        bullets.append("No stale issues or stale pull requests in the backlog.")

    return bullets


def generate_overall_explanations(dimensions: List[Dict[str, Any]], overall_score: float, overall_status: str) -> List[str]:
    """Generates a concise list of high-level deterministic explanations for the overall health."""
    bullets = []
    bullets.append(f"Overall engineering health score: {overall_score} ({overall_status}).")

    for dim in dimensions:
        status = dim.get("status")
        name = dim.get("name")
        score = dim.get("score")

        if status == "CRITICAL":
            bullets.append(f"CRITICAL: {name} scored {score}/100 and requires immediate remediation.")
        elif status == "DEGRADED":
            bullets.append(f"DEGRADED: {name} scored {score}/100 indicating reduced engineering throughput or staleness.")
        elif status == "INSUFFICIENT_DATA":
            bullets.append(f"Note: {name} had insufficient repository history to evaluate.")

    if len(bullets) == 1:
        bullets.append("All available dimensions are operating within acceptable engineering thresholds.")

    return bullets
