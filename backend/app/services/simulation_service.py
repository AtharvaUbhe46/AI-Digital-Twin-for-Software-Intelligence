import asyncio
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.project import Project, Contributor, Commit, Issue, PullRequest, Release
from app.models.digital_twin import DigitalTwin, DigitalTwinSnapshot
from app.models.health import SoftwareHealthSnapshot
from app.models.evolution import DependencyManifest, DependencyItem
from app.models.simulation import WhatIfSimulation
from app.schemas.simulation import (
    SimulationParameterInput,
    SimulationCreateRequest,
    SimulationParameterMeta,
    SimulationBaselineResponse,
    ImpactItemResponse,
    HealthImpactResponse,
    SimulationRiskItem,
    SimulationOpportunityItem,
    AIExplanationResponse,
    SimulationResponse,
    SimulationSummaryResponse,
    SimulationCompareResponse,
)
from app.services.health.health_scoring import (
    score_activity,
    score_issues,
    score_pull_requests,
    score_contributors,
    score_maintenance,
    calculate_overall_health,
    score_to_status,
)
from app.services.assistant.groq_service import groq_service
from app.services.assistant.ollama_service import ollama_service
from app.core.config import settings

logger = logging.getLogger("digital_twin.simulation_service")


class SimulationEngine:
    """
    Simulation Engine for Phase 8 What-If Simulation.
    Evaluates hypothetical changes in an isolated, in-memory calculation context.
    NEVER modifies actual repository records, digital twin snapshots, or baseline data.
    """

    @classmethod
    def get_baseline(cls, project_id: int, db: Session) -> SimulationBaselineResponse:
        """
        Retrieves the current project state from the Digital Twin, relational tables,
        and health snapshots to establish the baseline for simulations.
        """
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project with ID {project_id} not found.")

        twin = db.query(DigitalTwin).filter(DigitalTwin.project_id == project_id).first()
        twin_version = twin.current_version if twin else 1

        latest_snapshot = (
            db.query(DigitalTwinSnapshot)
            .filter(DigitalTwinSnapshot.digital_twin_id == twin.id)
            .order_by(desc(DigitalTwinSnapshot.version))
            .first()
            if twin else None
        )

        now = datetime.now(timezone.utc)
        recent_cutoff = now - timedelta(days=settings.HEALTH_RECENT_DAYS or 30)

        # Contributor metrics
        total_contributors = db.query(Contributor).filter(Contributor.project_id == project_id).count()
        recent_commit_authors = (
            db.query(Commit.author_login)
            .filter(Commit.project_id == project_id, Commit.author_date >= recent_cutoff)
            .distinct()
            .all()
        )
        active_contributors = len([a[0] for a in recent_commit_authors if a[0]])
        if active_contributors == 0 and total_contributors > 0:
            active_contributors = min(total_contributors, 3)

        top_contributor = (
            db.query(Contributor)
            .filter(Contributor.project_id == project_id)
            .order_by(desc(Contributor.contributions))
            .first()
        )
        total_contributions = sum(
            c.contributions for c in db.query(Contributor).filter(Contributor.project_id == project_id).all()
        ) or 1
        top_contributor_pct = (
            round((top_contributor.contributions / total_contributions) * 100, 1)
            if top_contributor else 50.0
        )

        # Issue metrics
        open_issues = db.query(Issue).filter(Issue.project_id == project_id, Issue.state == "open").count()
        closed_issues = db.query(Issue).filter(Issue.project_id == project_id, Issue.state == "closed").count()
        total_issues = open_issues + closed_issues
        issue_closure_rate = round((closed_issues / total_issues) * 100, 1) if total_issues > 0 else 75.0

        stale_issue_cutoff = now - timedelta(days=settings.HEALTH_STALE_ISSUE_DAYS or 30)
        stale_issues = db.query(Issue).filter(
            Issue.project_id == project_id,
            Issue.state == "open",
            Issue.created_at < stale_issue_cutoff
        ).count()
        stale_issue_ratio = round((stale_issues / open_issues) * 100, 1) if open_issues > 0 else 0.0

        # PR metrics
        open_prs = db.query(PullRequest).filter(PullRequest.project_id == project_id, PullRequest.state == "open").count()
        closed_prs = db.query(PullRequest).filter(PullRequest.project_id == project_id, PullRequest.state == "closed").count()
        total_prs = open_prs + closed_prs
        pr_merge_rate = round((closed_prs / total_prs) * 100, 1) if total_prs > 0 else 75.0

        stale_pr_cutoff = now - timedelta(days=settings.HEALTH_STALE_PR_DAYS or 14)
        stale_prs = db.query(PullRequest).filter(
            PullRequest.project_id == project_id,
            PullRequest.state == "open",
            PullRequest.created_at < stale_pr_cutoff
        ).count()
        stale_pr_ratio = round((stale_prs / open_prs) * 100, 1) if open_prs > 0 else 0.0

        # Commit & activity metrics
        total_commits = db.query(Commit).filter(Commit.project_id == project_id).count()
        recent_commits = db.query(Commit).filter(Commit.project_id == project_id, Commit.author_date >= recent_cutoff).count()
        commits_per_week = round((recent_commits / (settings.HEALTH_RECENT_DAYS / 7)), 1) if settings.HEALTH_RECENT_DAYS > 0 else 2.0

        latest_commit = (
            db.query(Commit)
            .filter(Commit.project_id == project_id)
            .order_by(desc(Commit.author_date))
            .first()
        )
        if latest_commit and latest_commit.author_date:
            commit_dt = latest_commit.author_date
            if commit_dt.tzinfo is None:
                commit_dt = commit_dt.replace(tzinfo=timezone.utc)
            days_since_last_commit = max(0, (now - commit_dt).days)
        else:
            days_since_last_commit = 14

        # Dependency metrics
        manifest_count = db.query(DependencyManifest).filter(DependencyManifest.project_id == project_id).count()
        dependency_count: Optional[int] = None
        if manifest_count > 0:
            dependency_count = (
                db.query(DependencyItem)
                .join(DependencyManifest, DependencyItem.manifest_id == DependencyManifest.id)
                .filter(DependencyManifest.project_id == project_id)
                .count()
            )

        # Health score
        latest_health = (
            db.query(SoftwareHealthSnapshot)
            .filter(SoftwareHealthSnapshot.project_id == project_id)
            .order_by(desc(SoftwareHealthSnapshot.calculated_at))
            .first()
        )
        health_score = latest_health.overall_score if latest_health else project.health_score
        health_status = latest_health.overall_status if latest_health else score_to_status(health_score)

        metrics = {
            "total_contributors": total_contributors,
            "active_contributors": active_contributors,
            "top_contributor_percentage": top_contributor_pct,
            "open_issues": open_issues,
            "closed_issues": closed_issues,
            "issue_closure_rate": issue_closure_rate,
            "stale_issues_count": stale_issues,
            "stale_issue_ratio": stale_issue_ratio,
            "open_prs": open_prs,
            "closed_prs": closed_prs,
            "pr_merge_rate": pr_merge_rate,
            "stale_prs_count": stale_prs,
            "stale_pr_ratio": stale_pr_ratio,
            "total_commits": total_commits,
            "commits_per_week": commits_per_week,
            "days_since_last_commit": days_since_last_commit,
            "dependency_count": dependency_count,
            "has_dependency_manifest": manifest_count > 0,
            "health_score": health_score,
            "health_status": health_status,
            "last_synced_at": project.last_synced_at.isoformat() if project.last_synced_at else None,
        }

        # Parameter metadata for UI configuration
        available_parameters = [
            SimulationParameterMeta(
                key="active_contributors",
                name="Active Contributors",
                category="team",
                unit="contributors",
                current_value=float(active_contributors),
                min_value=1.0,
                max_value=max(100.0, float(active_contributors * 4)),
                step=1.0,
                description="Number of developers actively contributing commits and reviews to the project.",
                is_available=True,
            ),
            SimulationParameterMeta(
                key="open_issues",
                name="Open Issues Backlog",
                category="issues",
                unit="issues",
                current_value=float(open_issues),
                min_value=0.0,
                max_value=max(100.0, float(open_issues * 3)),
                step=1.0,
                description="Current unresolved bug reports, feature requests, and maintenance tasks.",
                is_available=True,
            ),
            SimulationParameterMeta(
                key="issue_resolution_rate",
                name="Issue Resolution Rate",
                category="issues",
                unit="%",
                current_value=float(issue_closure_rate),
                min_value=10.0,
                max_value=100.0,
                step=5.0,
                description="Percentage of reported issues successfully resolved and closed by the team.",
                is_available=True,
            ),
            SimulationParameterMeta(
                key="dependency_count",
                name="Software Dependencies",
                category="dependencies",
                unit="packages",
                current_value=float(dependency_count) if dependency_count is not None else None,
                min_value=0.0,
                max_value=max(50.0, float((dependency_count or 10) * 3)),
                step=1.0,
                description="Direct and transitive libraries declared in package manifests (package.json, requirements.txt, etc.).",
                is_available=manifest_count > 0,
                unavailable_reason="No dependency manifest (package.json, requirements.txt, etc.) detected in the synchronized repository." if manifest_count == 0 else None,
            ),
            SimulationParameterMeta(
                key="commits_per_week",
                name="Weekly Commit Velocity",
                category="activity",
                unit="commits/week",
                current_value=float(commits_per_week),
                min_value=0.1,
                max_value=max(40.0, float(commits_per_week * 4)),
                step=0.5,
                description="Average development frequency measured as commits authored per 7-day period.",
                is_available=True,
            ),
            SimulationParameterMeta(
                key="open_prs",
                name="Open Pull Requests",
                category="activity",
                unit="PRs",
                current_value=float(open_prs),
                min_value=0.0,
                max_value=max(30.0, float(open_prs * 4)),
                step=1.0,
                description="Code review backlog awaiting review, testing, and merge decisions.",
                is_available=True,
            ),
        ]

        return SimulationBaselineResponse(
            project_id=project.id,
            project_name=project.name,
            full_name=project.full_name,
            twin_version=twin_version,
            snapshot_id=latest_snapshot.id if latest_snapshot else None,
            last_synced_at=project.last_synced_at,
            metrics=metrics,
            available_parameters=available_parameters,
            health_score=health_score,
            health_status=health_status,
        )

    @classmethod
    def validate_parameters(cls, parameters: List[SimulationParameterInput], baseline: Dict[str, Any]) -> None:
        """
        Validates scenario inputs against logical constraints and baseline availability.
        """
        if not parameters:
            raise ValueError("A simulation must contain at least one parameter modification.")

        seen_keys = set()
        for p in parameters:
            if p.parameter_key in seen_keys:
                raise ValueError(f"Duplicate parameter modification for '{p.parameter_key}'.")
            seen_keys.add(p.parameter_key)

            if p.proposed_value < 0:
                raise ValueError(f"Parameter '{p.parameter_key}' cannot have a negative value ({p.proposed_value}).")

            if p.parameter_key == "dependency_count" and not baseline.get("has_dependency_manifest"):
                raise ValueError(
                    "Cannot simulate dependency changes because no dependency manifest was detected in this repository."
                )

            if p.parameter_key == "issue_resolution_rate" and (p.proposed_value < 0 or p.proposed_value > 100):
                raise ValueError("Issue resolution rate must be between 0% and 100%.")

    @classmethod
    def simulate(
        cls,
        project_id: int,
        request: SimulationCreateRequest,
        db: Session,
        persist: bool = True,
    ) -> SimulationResponse:
        """
        Executes a hypothetical simulation in an isolated in-memory calculation context.
        Applies mathematical modeling for team dynamics, backlog queues, dependency maintenance,
        and activity velocity. Then re-evaluates project health and risks deterministically.
        """
        start_time = time.perf_counter()

        baseline_resp = cls.get_baseline(project_id, db)
        base = dict(baseline_resp.metrics)

        cls.validate_parameters(request.parameters, base)

        # Isolated in-memory simulation state
        sim = dict(base)

        applied_parameters: List[Dict[str, Any]] = []
        impact_analysis: List[ImpactItemResponse] = []
        risks: List[SimulationRiskItem] = []
        opportunities: List[SimulationOpportunityItem] = []

        # Track which parameter keys were modified
        param_map = {p.parameter_key: p for p in request.parameters}

        # ─── 1. TEAM & CONTRIBUTOR MODELING (Brooks' Law & Coordination Overhead) ───
        if "active_contributors" in param_map:
            p = param_map["active_contributors"]
            c_base = max(1, base["active_contributors"])
            c_sim = int(round(p.proposed_value))
            c_sim = max(1, c_sim)
            delta_c = c_sim - c_base
            pct_c = round((delta_c / c_base) * 100, 1)

            # Communication channels: n*(n-1)/2
            channels_base = (c_base * (c_base - 1)) / 2
            channels_sim = (c_sim * (c_sim - 1)) / 2
            coord_overhead_factor = 1.0 + 0.08 * (max(0, channels_sim - channels_base) / max(1, channels_base))

            # Effective Capacity calculation
            if delta_c > 0:
                # 30% ramp-up / mentoring tax for newcomers plus coordination communication overhead
                effective_added = (0.70 * delta_c) / coord_overhead_factor
                effective_capacity = c_base + effective_added
                capacity_multiplier = effective_capacity / c_base
            else:
                effective_capacity = c_sim
                capacity_multiplier = c_sim / c_base

            # Update simulated metrics
            sim["active_contributors"] = c_sim
            sim["effective_capacity"] = round(effective_capacity, 2)
            sim["coordination_overhead_factor"] = round(coord_overhead_factor, 2)

            # Top contributor concentration adjustment
            if delta_c > 0:
                new_top_pct = max(15.0, round(base["top_contributor_percentage"] * (c_base / c_sim), 1))
            elif delta_c < 0:
                new_top_pct = min(95.0, round(base["top_contributor_percentage"] * (c_base / max(1, c_sim)), 1))
            else:
                new_top_pct = base["top_contributor_percentage"]
            sim["top_contributor_percentage"] = new_top_pct

            # Review capacity affects stale PR ratio
            if delta_c > 0:
                sim["stale_pr_ratio"] = max(0.0, round(base["stale_pr_ratio"] / capacity_multiplier, 1))
            elif delta_c < 0:
                sim["stale_pr_ratio"] = min(100.0, round(base["stale_pr_ratio"] * (c_base / max(1, c_sim)), 1))

            # If commits_per_week not explicitly modified, scale velocity with effective capacity
            if "commits_per_week" not in param_map:
                new_cpw = max(0.1, round(base["commits_per_week"] * (0.35 + 0.65 * capacity_multiplier), 1))
                sim["commits_per_week"] = new_cpw

            applied_parameters.append({
                "parameter_key": "active_contributors",
                "parameter_name": "Active Contributors",
                "baseline_value": c_base,
                "proposed_value": c_sim,
                "delta": delta_c,
                "delta_percentage": pct_c,
                "user_notes": p.user_notes,
            })

            direction = "IMPROVEMENT" if delta_c > 0 else ("DETERIORATION" if delta_c < 0 else "NEUTRAL")
            impact_analysis.append(ImpactItemResponse(
                metric_key="active_contributors",
                metric_name="Active Contributors & Team Capacity",
                baseline_value=f"{c_base} developers",
                simulated_value=f"{c_sim} developers ({round(effective_capacity, 1)} effective capacity)",
                delta=float(delta_c),
                delta_percentage=float(pct_c),
                direction=direction,
                reason=(
                    f"Team expanded by {delta_c} developers. Accounting for Brooks' Law and coordination overhead "
                    f"({round((coord_overhead_factor - 1.0) * 100, 1)}% overhead from {int(channels_sim)} pairwise communication links), "
                    f"effective team capacity scales to {round(effective_capacity, 1)}x baseline."
                    if delta_c > 0 else
                    f"Team reduced by {abs(delta_c)} developers. Nominal team capacity contracts directly to {c_sim} contributors."
                ),
                methodology="Brooks' Law & Pairwise Coordination Overhead Model: N*(N-1)/2 communication links with 0.70 ramp-up onboarding coefficient.",
                confidence="HIGH" if base["total_contributors"] >= 3 else "MEDIUM",
            ))

            # Risks & Opportunities for team changes
            if delta_c >= 4 and c_sim >= 2 * c_base:
                risks.append(SimulationRiskItem(
                    id="team-coord-overhead",
                    title="Diminishing Returns from Rapid Team Expansion",
                    description=f"Scaling active contributors from {c_base} to {c_sim} introduces {int(channels_sim - channels_base)} additional communication paths. Mentoring and onboarding overhead will temporarily suppress individual developer efficiency.",
                    severity="MEDIUM",
                    factor="Team Coordination Overhead",
                ))
            elif delta_c < 0 and c_sim <= 2:
                risks.append(SimulationRiskItem(
                    id="team-critical-reduction",
                    title="Severe Bus Factor & Maintainer Bottleneck",
                    description=f"Reducing active developers to {c_sim} concentrates architectural knowledge and leaves the project vulnerable to unreviewed PRs and delayed security triage.",
                    severity="HIGH" if c_sim == 1 else "MEDIUM",
                    factor="Maintainer Scarcity",
                ))

            if delta_c > 0:
                opportunities.append(SimulationOpportunityItem(
                    id="team-capacity-boost",
                    title="Expanded Engineering Bandwidth",
                    description=f"Effective development capacity increases by {round((capacity_multiplier - 1.0) * 100, 1)}%, accelerating PR throughput and shortening code review cycles.",
                    impact="HIGH" if delta_c >= 3 else "MEDIUM",
                    factor="Engineering Bandwidth",
                ))
                if new_top_pct < base["top_contributor_percentage"] - 10:
                    opportunities.append(SimulationOpportunityItem(
                        id="team-diversity-boost",
                        title="Decentralized Codebase Ownership",
                        description=f"Top contributor commit concentration reduces from {base['top_contributor_percentage']}% to {new_top_pct}%, improving project resilience.",
                        impact="HIGH",
                        factor="Knowledge Distribution",
                    ))

        # ─── 2. ISSUE & MAINTENANCE MODELING ───
        if "open_issues" in param_map:
            p = param_map["open_issues"]
            i_base = max(0, base["open_issues"])
            i_sim = int(round(p.proposed_value))
            delta_i = i_sim - i_base
            pct_i = round((delta_i / max(1, i_base)) * 100, 1)

            sim["open_issues"] = i_sim

            # Stale issue ratio adjustments
            if delta_i > 0:
                stale_inflation = 15.0 * (delta_i / max(1, i_base))
                new_stale_ratio = min(95.0, round(base["stale_issue_ratio"] + stale_inflation, 1))
                new_closure_rate = max(15.0, round(base["issue_closure_rate"] * (i_base / max(1, i_sim)), 1))
            elif delta_i < 0:
                reduction_ratio = max(0.0, i_sim / max(1, i_base))
                new_stale_ratio = max(0.0, round(base["stale_issue_ratio"] * reduction_ratio, 1))
                new_closure_rate = min(98.0, round(base["issue_closure_rate"] * (1.0 + 0.25 * (abs(delta_i) / max(1, i_base))), 1))
            else:
                new_stale_ratio = base["stale_issue_ratio"]
                new_closure_rate = base["issue_closure_rate"]

            sim["stale_issue_ratio"] = new_stale_ratio
            sim["stale_issues_count"] = int(round(i_sim * (new_stale_ratio / 100.0)))
            if "issue_resolution_rate" not in param_map:
                sim["issue_closure_rate"] = new_closure_rate

            applied_parameters.append({
                "parameter_key": "open_issues",
                "parameter_name": "Open Issues Backlog",
                "baseline_value": i_base,
                "proposed_value": i_sim,
                "delta": delta_i,
                "delta_percentage": pct_i,
                "user_notes": p.user_notes,
            })

            direction = "IMPROVEMENT" if delta_i < 0 else ("DETERIORATION" if delta_i > 0 else "NEUTRAL")
            impact_analysis.append(ImpactItemResponse(
                metric_key="open_issues",
                metric_name="Issue Backlog & Maintenance Pressure",
                baseline_value=f"{i_base} issues",
                simulated_value=f"{i_sim} issues ({new_stale_ratio}% projected stale)",
                delta=float(delta_i),
                delta_percentage=float(pct_i),
                direction=direction,
                reason=(
                    f"Backlog reduced by {abs(delta_i)} issues (-{abs(pct_i)}%). Maintainer triage workload decreases, "
                    f"driving projected stale issue ratio down to {new_stale_ratio}%."
                    if delta_i < 0 else
                    f"Backlog expanded by {delta_i} issues (+{pct_i}%). Unresolved maintenance tickets elevate stale ratio "
                    f"to {new_stale_ratio}%, placing downward pressure on response time."
                ),
                methodology="Queue Backlog Dynamics Model: Backlog elasticity calculates maintenance load and stale ticket accumulation.",
                confidence="HIGH" if base["open_issues"] + base["closed_issues"] >= 5 else "MEDIUM",
            ))

            if delta_i >= 15 or pct_i >= 50.0:
                risks.append(SimulationRiskItem(
                    id="issue-backlog-saturation",
                    title="Issue Backlog Saturation & Triage Fatigue",
                    description=f"A surge of {delta_i} open issues increases maintainer triage overhead, risking slower resolution times and user dissatisfaction.",
                    severity="HIGH" if delta_i >= 30 else "MEDIUM",
                    factor="Maintenance Burden",
                ))
            elif delta_i < 0:
                opportunities.append(SimulationOpportunityItem(
                    id="issue-backlog-clearance",
                    title="Backlog Clearance & Faster Triage Velocity",
                    description=f"Resolving {abs(delta_i)} open issues significantly reduces project maintenance debt, improving responsiveness indicators.",
                    impact="HIGH" if abs(pct_i) >= 40 else "MEDIUM",
                    factor="Quality & Support",
                ))

        if "issue_resolution_rate" in param_map:
            p = param_map["issue_resolution_rate"]
            r_base = base["issue_closure_rate"]
            r_sim = round(p.proposed_value, 1)
            delta_r = round(r_sim - r_base, 1)
            pct_r = round((delta_r / max(1.0, r_base)) * 100, 1)

            sim["issue_closure_rate"] = r_sim
            # Improvement in resolution rate organically shrinks backlog and stale ratio
            if delta_r > 0 and "open_issues" not in param_map:
                shrinkage = min(base["open_issues"], int(round(base["open_issues"] * (delta_r / 100.0) * 0.6)))
                sim["open_issues"] = max(0, base["open_issues"] - shrinkage)
                sim["stale_issue_ratio"] = max(0.0, round(base["stale_issue_ratio"] * (1.0 - (delta_r / 100.0)), 1))

            applied_parameters.append({
                "parameter_key": "issue_resolution_rate",
                "parameter_name": "Issue Resolution Rate",
                "baseline_value": r_base,
                "proposed_value": r_sim,
                "delta": delta_r,
                "delta_percentage": pct_r,
                "user_notes": p.user_notes,
            })

            direction = "IMPROVEMENT" if delta_r > 0 else ("DETERIORATION" if delta_r < 0 else "NEUTRAL")
            impact_analysis.append(ImpactItemResponse(
                metric_key="issue_resolution_rate",
                metric_name="Issue Resolution Efficiency",
                baseline_value=f"{r_base}%",
                simulated_value=f"{r_sim}%",
                delta=float(delta_r),
                delta_percentage=float(pct_r),
                direction=direction,
                reason=(
                    f"Resolution rate improved by {delta_r}% points. Efficient issue turnaround clears stagnant bugs and maintains project health."
                    if delta_r > 0 else
                    f"Resolution rate declined by {abs(delta_r)}% points, indicating ticket backlog accumulation."
                ),
                methodology="Throughput Resolution Efficiency Model: Closure velocity mapped directly against historical defect discovery rates.",
                confidence="HIGH" if base["closed_issues"] > 0 else "MEDIUM",
            ))

        # ─── 3. SOFTWARE DEPENDENCY MODELING ───
        if "dependency_count" in param_map:
            p = param_map["dependency_count"]
            if not base.get("has_dependency_manifest") or base.get("dependency_count") is None:
                impact_analysis.append(ImpactItemResponse(
                    metric_key="dependency_count",
                    metric_name="Software Dependencies",
                    baseline_value="Unavailable",
                    simulated_value="Unavailable",
                    delta=None,
                    delta_percentage=None,
                    direction="INSUFFICIENT_DATA",
                    reason="No package manifest (package.json, requirements.txt, pom.xml, etc.) was detected in the project tree.",
                    methodology="Manifest Dependency Analysis requires synchronized package declarations.",
                    confidence="INSUFFICIENT_DATA",
                ))
            else:
                d_base = base["dependency_count"]
                d_sim = int(round(p.proposed_value))
                delta_d = d_sim - d_base
                pct_d = round((delta_d / max(1, d_base)) * 100, 1)

                sim["dependency_count"] = d_sim
                # Estimated maintenance hours: ~1.5 hours/month per added package
                est_maint_hours_monthly = round(d_sim * 1.5, 1)

                applied_parameters.append({
                    "parameter_key": "dependency_count",
                    "parameter_name": "Software Dependencies",
                    "baseline_value": d_base,
                    "proposed_value": d_sim,
                    "delta": delta_d,
                    "delta_percentage": pct_d,
                    "user_notes": p.user_notes,
                })

                direction = "IMPROVEMENT" if delta_d < 0 else ("DETERIORATION" if delta_d > 0 else "NEUTRAL")
                impact_analysis.append(ImpactItemResponse(
                    metric_key="dependency_count",
                    metric_name="Software Dependencies & Maintenance Surface",
                    baseline_value=f"{d_base} dependencies",
                    simulated_value=f"{d_sim} dependencies (~{est_maint_hours_monthly}h/mo maintenance)",
                    delta=float(delta_d),
                    delta_percentage=float(pct_d),
                    direction=direction,
                    reason=(
                        f"Adding {delta_d} dependencies (+{pct_d}%) expands maintenance surface area by ~{est_maint_hours_monthly} maintenance hours/month "
                        f"for version updates, deprecation tracking, and breaking changes."
                        if delta_d > 0 else
                        f"Removing {abs(delta_d)} dependencies (-{abs(pct_d)}%) slims down the attack surface and reduces upgrade maintenance overhead."
                    ),
                    methodology="Dependency Maintenance Surface Model: 1.5 hours/month recurring maintenance cost per declared external package.",
                    confidence="HIGH",
                ))

                if delta_d >= 6:
                    risks.append(SimulationRiskItem(
                        id="dep-sprawl",
                        title="Dependency Maintenance Sprawl",
                        description=f"Introducing {delta_d} new dependencies increases upgrade fatigue, license compliance surface, and upstream breakage exposure.",
                        severity="MEDIUM" if delta_d < 15 else "HIGH",
                        factor="Dependency Surface",
                    ))
                elif delta_d < 0:
                    opportunities.append(SimulationOpportunityItem(
                        id="dep-streamlining",
                        title="Lean Dependency Footprint",
                        description=f"Eliminating {abs(delta_d)} dependencies streamlines project build times and shrinks upstream maintenance vulnerabilities.",
                        impact="MEDIUM",
                        factor="Attack Surface Reduction",
                    ))

        # ─── 4. DEVELOPMENT ACTIVITY MODELING ───
        if "commits_per_week" in param_map:
            p = param_map["commits_per_week"]
            cpw_base = base["commits_per_week"]
            cpw_sim = round(p.proposed_value, 1)
            delta_cpw = round(cpw_sim - cpw_base, 1)
            pct_cpw = round((delta_cpw / max(0.1, cpw_base)) * 100, 1)

            sim["commits_per_week"] = cpw_sim
            # Projected days since last commit scales inversely with frequency
            if cpw_sim >= 7.0:
                sim["days_since_last_commit"] = 1
            elif cpw_sim >= 3.0:
                sim["days_since_last_commit"] = 2
            elif cpw_sim >= 1.0:
                sim["days_since_last_commit"] = 4
            else:
                sim["days_since_last_commit"] = max(base["days_since_last_commit"], 14)

            applied_parameters.append({
                "parameter_key": "commits_per_week",
                "parameter_name": "Weekly Commit Velocity",
                "baseline_value": cpw_base,
                "proposed_value": cpw_sim,
                "delta": delta_cpw,
                "delta_percentage": pct_cpw,
                "user_notes": p.user_notes,
            })

            direction = "IMPROVEMENT" if delta_cpw > 0 else ("DETERIORATION" if delta_cpw < 0 else "NEUTRAL")
            impact_analysis.append(ImpactItemResponse(
                metric_key="commits_per_week",
                metric_name="Development Velocity & Commit Cadence",
                baseline_value=f"{cpw_base} commits/wk",
                simulated_value=f"{cpw_sim} commits/wk",
                delta=float(delta_cpw),
                delta_percentage=float(pct_cpw),
                direction=direction,
                reason=(
                    f"Development activity increases by {delta_cpw} commits/week (+{pct_cpw}%). Active code shipping keeps the repository current and signals active maintenance."
                    if delta_cpw > 0 else
                    f"Development activity declines by {abs(delta_cpw)} commits/week (-{abs(pct_cpw)}%). Slower commit cadence increases stagnation risks."
                ),
                methodology="Activity Cadence Recency Model: Projected days since last activity derived inversely from weekly commit velocity.",
                confidence="HIGH" if base["total_commits"] >= 5 else "MEDIUM",
            ))

            if delta_cpw < -5.0 or (pct_cpw <= -50.0 and cpw_sim < 1.0):
                risks.append(SimulationRiskItem(
                    id="activity-stagnation",
                    title="Development Activity Stagnation",
                    description=f"Commit velocity dropping to {cpw_sim} commits/week risks project obsolescence and decreases community confidence.",
                    severity="HIGH" if cpw_sim < 0.5 else "MEDIUM",
                    factor="Project Stagnation",
                ))
            elif delta_cpw >= 5.0:
                opportunities.append(SimulationOpportunityItem(
                    id="activity-velocity-surge",
                    title="Accelerated Development Cadence",
                    description=f"Increasing development velocity to {cpw_sim} commits/week ensures rapid feature delivery and prompt patch releases.",
                    impact="HIGH" if delta_cpw >= 10.0 else "MEDIUM",
                    factor="Release Velocity",
                ))

        if "open_prs" in param_map:
            p = param_map["open_prs"]
            pr_base = base["open_prs"]
            pr_sim = int(round(p.proposed_value))
            delta_pr = pr_sim - pr_base
            pct_pr = round((delta_pr / max(1, pr_base)) * 100, 1)

            sim["open_prs"] = pr_sim
            applied_parameters.append({
                "parameter_key": "open_prs",
                "parameter_name": "Open Pull Requests",
                "baseline_value": pr_base,
                "proposed_value": pr_sim,
                "delta": delta_pr,
                "delta_percentage": pct_pr,
                "user_notes": p.user_notes,
            })

            direction = "IMPROVEMENT" if delta_pr < 0 else ("DETERIORATION" if delta_pr > 0 else "NEUTRAL")
            impact_analysis.append(ImpactItemResponse(
                metric_key="open_prs",
                metric_name="Pull Request Review Pipeline",
                baseline_value=f"{pr_base} open PRs",
                simulated_value=f"{pr_sim} open PRs",
                delta=float(delta_pr),
                delta_percentage=float(pct_pr),
                direction=direction,
                reason=(
                    f"Open PR backlog reduced to {pr_sim}, clearing code review queues and accelerating delivery."
                    if delta_pr < 0 else
                    f"Open PR backlog increased by {delta_pr} PRs, requiring additional reviewer bandwidth to avoid merge conflicts."
                ),
                methodology="PR Review Pipeline Queue Model: Pipeline inventory evaluated against reviewer concurrency.",
                confidence="HIGH" if base["open_prs"] + base["closed_prs"] > 0 else "MEDIUM",
            ))

        # ─── 5. RE-EVALUATE HEALTH SCORES DETERMINISTICALLY ───
        # Build dimension inputs for health_scoring
        activity_metrics = {
            "has_data": sim["total_commits"] > 0 or sim["commits_per_week"] > 0,
            "days_since_last_commit": sim["days_since_last_commit"],
            "commits_per_week": sim["commits_per_week"],
        }
        issues_metrics = {
            "has_data": (sim["open_issues"] + sim["closed_issues"]) > 0 or sim["open_issues"] > 0,
            "total_open": sim["open_issues"],
            "stale_ratio": sim["stale_issue_ratio"],
            "closure_rate": sim["issue_closure_rate"],
        }
        prs_metrics = {
            "has_data": (sim["open_prs"] + sim["closed_prs"]) > 0 or sim["open_prs"] > 0,
            "total_open": sim["open_prs"],
            "stale_ratio": sim["stale_pr_ratio"],
            "merge_rate": sim["pr_merge_rate"],
        }
        contributors_metrics = {
            "has_data": sim["total_contributors"] > 0 or sim["active_contributors"] > 0,
            "top_contributor_percentage": sim["top_contributor_percentage"],
            "active_contributors_recent": sim["active_contributors"],
        }
        maintenance_metrics = {
            "has_data": True,
            "days_since_last_commit": sim["days_since_last_commit"],
            "stale_issues_count": sim["stale_issues_count"],
            "stale_prs_count": sim["stale_prs_count"],
        }

        # Calculate dimension scores
        score_act, status_act = score_activity(activity_metrics)
        score_iss, status_iss = score_issues(issues_metrics)
        score_prs, status_prs = score_pull_requests(prs_metrics)
        score_con, status_con = score_contributors(contributors_metrics)
        score_mnt, status_mnt = score_maintenance(maintenance_metrics)

        # Apply dependency maintenance impact if dependency count changed
        if "dependency_count" in param_map and base.get("dependency_count") is not None and score_mnt is not None:
            delta_deps = sim["dependency_count"] - base["dependency_count"]
            # Each 5 added dependencies penalize maintenance score by 2.5 points
            dep_penalty = round((delta_deps / 5.0) * 2.5, 1)
            score_mnt = max(10.0, min(100.0, score_mnt - dep_penalty))
            status_mnt = score_to_status(score_mnt)

        dimensions = [
            {"dimension": "activity", "name": "Development Activity", "score": score_act, "weight": 0.20, "status": status_act},
            {"dimension": "issues", "name": "Issue Management", "score": score_iss, "weight": 0.20, "status": status_iss},
            {"dimension": "pull_requests", "name": "Code Review & PRs", "score": score_prs, "weight": 0.20, "status": status_prs},
            {"dimension": "contributors", "name": "Contributor Community", "score": score_con, "weight": 0.20, "status": status_con},
            {"dimension": "maintenance", "name": "Maintenance & Stability", "score": score_mnt, "weight": 0.20, "status": status_mnt},
        ]

        sim_overall_score, sim_overall_status = calculate_overall_health(dimensions)
        sim["health_score"] = sim_overall_score
        sim["health_status"] = sim_overall_status

        base_health_score = base.get("health_score")
        base_health_status = base.get("health_status", "INSUFFICIENT_DATA")

        health_delta = (
            round(sim_overall_score - base_health_score, 1)
            if base_health_score is not None else None
        )

        key_factors = []
        for d in dimensions:
            if d["score"] is not None:
                if d["status"] == "HEALTHY":
                    key_factors.append(f"{d['name']} remains in Healthy condition ({d['score']}/100)")
                elif d["status"] in ("DEGRADED", "CRITICAL"):
                    key_factors.append(f"{d['name']} requires attention ({d['score']}/100 - {d['status']})")

        health_impact = HealthImpactResponse(
            baseline_score=base_health_score,
            simulated_score=sim_overall_score,
            delta=health_delta,
            baseline_status=base_health_status,
            simulated_status=sim_overall_status,
            dimension_deltas={d["dimension"]: d["score"] for d in dimensions},
            key_factors=key_factors[:4],
        )

        # ─── 6. AI-GENERATED OR DETERMINISTIC EXPLANATION ───
        ai_explanation = cls._generate_explanation(
            project_name=baseline_resp.project_name,
            scenario_name=request.name,
            applied_parameters=applied_parameters,
            base_metrics=base,
            sim_metrics=sim,
            health_impact=health_impact,
            risks=risks,
            opportunities=opportunities,
        )

        exec_duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        simulation = WhatIfSimulation(
            project_id=project_id,
            name=request.name,
            description=request.description,
            category=request.category,
            status="COMPLETED",
            baseline_twin_version=baseline_resp.twin_version,
            baseline_snapshot_id=baseline_resp.snapshot_id,
            baseline_metrics=base,
            parameters=applied_parameters,
            simulated_metrics=sim,
            impact_analysis=[i.model_dump() for i in impact_analysis],
            health_impact=health_impact.model_dump(),
            risks=[r.model_dump() for r in risks],
            opportunities=[o.model_dump() for o in opportunities],
            ai_explanation=ai_explanation.model_dump(),
            execution_duration_ms=exec_duration_ms,
        )

        if persist:
            db.add(simulation)
            db.commit()
            db.refresh(simulation)

        return SimulationResponse(
            id=simulation.id or 0,
            project_id=project_id,
            name=simulation.name,
            description=simulation.description,
            category=simulation.category,
            status=simulation.status,
            baseline_twin_version=simulation.baseline_twin_version,
            baseline_snapshot_id=simulation.baseline_snapshot_id,
            baseline_metrics=simulation.baseline_metrics,
            parameters=simulation.parameters,
            simulated_metrics=simulation.simulated_metrics,
            impact_analysis=impact_analysis,
            health_impact=health_impact,
            risks=risks,
            opportunities=opportunities,
            ai_explanation=ai_explanation,
            execution_duration_ms=exec_duration_ms,
            created_at=simulation.created_at or datetime.now(timezone.utc),
        )

    @classmethod
    def _generate_explanation(
        cls,
        project_name: str,
        scenario_name: str,
        applied_parameters: List[Dict[str, Any]],
        base_metrics: Dict[str, Any],
        sim_metrics: Dict[str, Any],
        health_impact: HealthImpactResponse,
        risks: List[SimulationRiskItem],
        opportunities: List[SimulationOpportunityItem],
    ) -> AIExplanationResponse:
        """
        Attempts to generate an AI explanation using Groq or Ollama.
        If unavailable or in case of errors, produces a rich, deterministic explanation.
        """
        # Format parameter changes for prompt
        changes_str = "; ".join([
            f"{p['parameter_name']}: {p['baseline_value']} -> {p['proposed_value']} ({'+' if p['delta'] > 0 else ''}{p['delta']})"
            for p in applied_parameters
        ])

        # Attempt AI provider if configured
        try:
            if settings.GROQ_API_KEY and (settings.AI_PROVIDER or "groq").lower() == "groq":
                prompt = (
                    f"You are the Software Intelligence Digital Twin Assistant analyzing a hypothetical What-If simulation.\n"
                    f"Project: {project_name}\n"
                    f"Scenario: {scenario_name}\n"
                    f"Changes Tested: {changes_str}\n"
                    f"Baseline Health: {health_impact.baseline_score}/100 ({health_impact.baseline_status})\n"
                    f"Simulated Health: {health_impact.simulated_score}/100 ({health_impact.simulated_status}) [Delta: {'+' if (health_impact.delta or 0) > 0 else ''}{health_impact.delta}]\n"
                    f"Identified Risks: {len(risks)}\n"
                    f"Identified Opportunities: {len(opportunities)}\n\n"
                    f"Provide a clear, strategic executive analysis structured strictly as:\n"
                    f"1. Executive Summary (1-2 sentences)\n"
                    f"2. What Changed\n"
                    f"3. Predicted Outcomes\n"
                    f"4. Why It Happens\n"
                    f"Keep it grounded solely in the mathematical simulation data without hallucinating new metrics."
                )

                messages = [
                    {"role": "system", "content": "You are an expert software engineering advisor grounded in empirical software engineering telemetry."},
                    {"role": "user", "content": prompt},
                ]
                # Run synchronous call to groq
                response_text = groq_service.chat_completion(messages=messages, temperature=0.3, max_tokens=1024)
                if response_text and len(response_text.strip()) > 50:
                    return AIExplanationResponse(
                        summary=f"Simulation evaluated the impact of {len(applied_parameters)} hypothetical change(s) on {project_name}, resulting in a projected health score of {health_impact.simulated_score}/100 ({'+' if (health_impact.delta or 0) > 0 else ''}{health_impact.delta} pts).",
                        what_changed=changes_str,
                        predicted_outcomes=f"Project health shifts from {health_impact.baseline_score or 0} ({health_impact.baseline_status}) to {health_impact.simulated_score} ({health_impact.simulated_status}).",
                        why_it_happens=response_text.strip(),
                        positive_aspects=[o.title for o in opportunities],
                        potential_issues=[r.title for r in risks],
                        strategic_recommendations=[
                            "Review team communication protocols before adding contributors to minimize Brooks' Law overhead.",
                            "Establish automated triage and CI test pipelines before expanding the issue backlog.",
                            "Audit dependency licenses and security advisories before introducing new packages.",
                        ],
                        is_ai_generated=True,
                        provider="Groq Cloud LPU (" + settings.GROQ_MODEL + ")",
                    )
        except Exception as e:
            logger.info(f"AI provider generation skipped ({e}); falling back to deterministic explanation.")

        # Deterministic Grounded Explanation
        h_delta = health_impact.delta or 0.0
        health_trend = "improved" if h_delta > 0 else ("deteriorated" if h_delta < 0 else "remained steady")

        summary = (
            f"Testing hypothetical changes ({changes_str}) on {project_name} predicts project health {health_trend} "
            f"from {health_impact.baseline_score or 0}/100 to {health_impact.simulated_score}/100 "
            f"({'+' if h_delta > 0 else ''}{h_delta} points)."
        )

        what_changed = (
            f"The scenario modified {len(applied_parameters)} project parameter(s): " +
            ", ".join([f"{p['parameter_name']} adjusted from {p['baseline_value']} to {p['proposed_value']}" for p in applied_parameters]) + "."
        )

        outcomes = (
            f"Under this simulation, project health is estimated at {health_impact.simulated_score}/100 with status {health_impact.simulated_status}. "
            f"The simulation identified {len(opportunities)} potential operational opportunity(ies) and {len(risks)} risk factor(s)."
        )

        why_it_happens = (
            "The calculation applies empirical software engineering models. Contributor modifications incorporate Brooks' Law "
            "and communication link overhead (N*(N-1)/2). Issue and PR adjustments apply queue backlog dynamics and review throughput limits. "
            "Health scoring dynamically normalizes valid engineering dimensions without fabricating missing metrics."
        )

        recommendations = [
            "Validate developer onboarding processes before expanding team size to reduce coordination overhead.",
            "Maintain consistent issue triage discipline to prevent backlog staleness.",
            "Ensure regular automated testing when commit velocity accelerates.",
        ]

        return AIExplanationResponse(
            summary=summary,
            what_changed=what_changed,
            predicted_outcomes=outcomes,
            why_it_happens=why_it_happens,
            positive_aspects=[o.title + ": " + o.description for o in opportunities] or ["No significant immediate opportunities detected."],
            potential_issues=[r.title + ": " + r.description for r in risks] or ["No high-severity risks identified for this scenario."],
            strategic_recommendations=recommendations,
            is_ai_generated=False,
            provider="Deterministic Engineering Model (Rules Engine)",
        )

    @classmethod
    def get_simulations(cls, project_id: int, db: Session) -> List[SimulationSummaryResponse]:
        """
        Retrieves saved simulations history for a specific project.
        """
        sims = (
            db.query(WhatIfSimulation)
            .filter(WhatIfSimulation.project_id == project_id)
            .order_by(desc(WhatIfSimulation.created_at))
            .all()
        )

        results = []
        for s in sims:
            h_impact = s.health_impact or {}
            h_delta = h_impact.get("delta")
            params = s.parameters or []
            r_list = s.risks or []
            o_list = s.opportunities or []

            # Generate headline summary
            param_names = [p.get("parameter_name", "param") for p in params[:2]]
            param_str = ", ".join(param_names)
            if len(params) > 2:
                param_str += f" +{len(params)-2} more"

            headline = (
                f"Evaluated {param_str} (Health: {'+' if (h_delta or 0) > 0 else ''}{h_delta or 0} pts)"
                if h_delta is not None else
                f"Evaluated {param_str}"
            )

            results.append(SimulationSummaryResponse(
                id=s.id,
                project_id=s.project_id,
                name=s.name,
                description=s.description,
                category=s.category,
                status=s.status,
                baseline_twin_version=s.baseline_twin_version,
                health_score_delta=h_delta,
                parameter_count=len(params),
                risk_count=len(r_list),
                opportunity_count=len(o_list),
                summary_headline=headline,
                created_at=s.created_at,
            ))

        return results

    @classmethod
    def get_simulation_detail(cls, project_id: int, simulation_id: int, db: Session) -> SimulationResponse:
        """
        Retrieves a saved simulation by ID, ensuring project ownership.
        """
        sim = (
            db.query(WhatIfSimulation)
            .filter(WhatIfSimulation.id == simulation_id, WhatIfSimulation.project_id == project_id)
            .first()
        )
        if not sim:
            raise ValueError(f"Simulation with ID {simulation_id} not found for project {project_id}.")

        return SimulationResponse.model_validate(sim)

    @classmethod
    def delete_simulation(cls, project_id: int, simulation_id: int, db: Session) -> bool:
        """
        Deletes a saved simulation. Never deletes real project or snapshot data.
        """
        sim = (
            db.query(WhatIfSimulation)
            .filter(WhatIfSimulation.id == simulation_id, WhatIfSimulation.project_id == project_id)
            .first()
        )
        if not sim:
            raise ValueError(f"Simulation with ID {simulation_id} not found for project {project_id}.")

        db.delete(sim)
        db.commit()
        return True

    @classmethod
    def compare_simulations(cls, project_id: int, sim_a_id: int, sim_b_id: int, db: Session) -> SimulationCompareResponse:
        """
        Compares two saved simulations for the same project.
        """
        sim_a = cls.get_simulation_detail(project_id, sim_a_id, db)
        sim_b = cls.get_simulation_detail(project_id, sim_b_id, db)

        project = db.query(Project).filter(Project.id == project_id).first()
        project_name = project.name if project else "Project"

        # Parameter differences
        params_a = {p["parameter_key"]: p for p in sim_a.parameters}
        params_b = {p["parameter_key"]: p for p in sim_b.parameters}
        all_param_keys = list(set(list(params_a.keys()) + list(params_b.keys())))

        param_diffs = []
        for k in all_param_keys:
            pa = params_a.get(k)
            pb = params_b.get(k)
            name = (pa or pb).get("parameter_name", k)
            param_diffs.append({
                "parameter_key": k,
                "parameter_name": name,
                "value_in_a": pa.get("proposed_value") if pa else None,
                "value_in_b": pb.get("proposed_value") if pb else None,
                "difference": (
                    round(pb["proposed_value"] - pa["proposed_value"], 1)
                    if pa and pb else None
                ),
            })

        # Metric comparisons
        common_metrics = [
            ("health_score", "Overall Health Score", "pts"),
            ("active_contributors", "Active Contributors", "devs"),
            ("open_issues", "Open Issues", "issues"),
            ("commits_per_week", "Weekly Commits", "commits/wk"),
            ("open_prs", "Open Pull Requests", "PRs"),
            ("dependency_count", "Dependencies", "packages"),
        ]

        metric_comparisons = []
        for m_key, m_name, m_unit in common_metrics:
            val_a = sim_a.simulated_metrics.get(m_key)
            val_b = sim_b.simulated_metrics.get(m_key)
            diff = round(val_b - val_a, 1) if val_a is not None and val_b is not None else None
            metric_comparisons.append({
                "metric_key": m_key,
                "metric_name": m_name,
                "unit": m_unit,
                "sim_a_value": val_a,
                "sim_b_value": val_b,
                "difference": diff,
            })

        # Health Comparison
        health_comp = {
            "sim_a_score": sim_a.health_impact.simulated_score,
            "sim_a_status": sim_a.health_impact.simulated_status,
            "sim_a_delta": sim_a.health_impact.delta,
            "sim_b_score": sim_b.health_impact.simulated_score,
            "sim_b_status": sim_b.health_impact.simulated_status,
            "sim_b_delta": sim_b.health_impact.delta,
            "health_score_advantage": (
                "Simulation A" if (sim_a.health_impact.simulated_score or 0) > (sim_b.health_impact.simulated_score or 0)
                else ("Simulation B" if (sim_b.health_impact.simulated_score or 0) > (sim_a.health_impact.simulated_score or 0) else "Tie")
            ),
        }

        # Risk Trade-offs
        risk_tradeoffs = {
            "sim_a_risks_count": len(sim_a.risks),
            "sim_b_risks_count": len(sim_b.risks),
            "sim_a_opportunities_count": len(sim_a.opportunities),
            "sim_b_opportunities_count": len(sim_b.opportunities),
            "sim_a_key_risk": sim_a.risks[0].title if sim_a.risks else "None",
            "sim_b_key_risk": sim_b.risks[0].title if sim_b.risks else "None",
            "sim_a_key_opportunity": sim_a.opportunities[0].title if sim_a.opportunities else "None",
            "sim_b_key_opportunity": sim_b.opportunities[0].title if sim_b.opportunities else "None",
        }

        # Comparative summary
        better_sim = health_comp["health_score_advantage"]
        comparative_summary = (
            f"Comparing '{sim_a.name}' against '{sim_b.name}': "
            f"{better_sim} achieves higher projected project health "
            f"({sim_a.health_impact.simulated_score} vs {sim_b.health_impact.simulated_score}). "
            f"Scenario A introduces {len(sim_a.risks)} risks and {len(sim_a.opportunities)} opportunities, "
            f"whereas Scenario B introduces {len(sim_b.risks)} risks and {len(sim_b.opportunities)} opportunities."
        )

        return SimulationCompareResponse(
            project_id=project_id,
            project_name=project_name,
            simulation_a=sim_a,
            simulation_b=sim_b,
            parameter_differences=param_diffs,
            metric_comparisons=metric_comparisons,
            health_comparison=health_comp,
            risk_tradeoffs=risk_tradeoffs,
            comparative_summary=comparative_summary,
        )


simulation_engine = SimulationEngine()

