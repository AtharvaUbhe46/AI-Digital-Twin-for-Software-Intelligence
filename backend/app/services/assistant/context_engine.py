import os
import re
import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.project import Project, Issue, PullRequest, Commit, Contributor, Release, Branch
from app.models.digital_twin import DigitalTwin, DigitalTwinSnapshot, DigitalTwinChange, RepositoryFile
from app.models.architecture import ArchitectureAnalysis, GraphNode, GraphEdge
from app.models.health import SoftwareHealthSnapshot, HealthDimensionResult
from app.models.risk import SoftwareRisk
from app.models.evolution import (
    EvolutionSnapshot,
    ChangeHotspot,
    TechnicalDebtIndicator,
    DependencyManifest,
    DependencyItem,
)
from app.schemas.assistant import AssistantSourceItem
from app.services.architecture.architecture_service import architecture_service
from app.services.health.health_service import health_service
from app.services.risk.risk_service import risk_service

logger = logging.getLogger("digital_twin.assistant.context_engine")


class ProjectContextEngine:
    """
    Retrieves, correlates, and filters verified repository intelligence from
    Phases 1–6 to provide grounded context for Qwen.
    """

    def is_general_programming_question(self, question: str) -> bool:
        """
        Distinguishes general programming, language, syntax, or algorithmic questions
        from project-specific software intelligence questions.
        """
        q = question.strip().lower()

        # Explicit repository / project referents indicate project-specific inquiry
        project_indicators = [
            "this project", "the project", "this repo", "the repo", "this repository", "the repository",
            "our repo", "our project", "in this app", "in the app", "in this codebase", "the codebase",
            "health score", "digital twin", "twin", "architecture", "circular dependenc", "cycle",
            "hotspot", "bottleneck", "endpoint", "api route", "api endpoint", "routes in",
            "controllers", "database entit", "schema", "recent change", "detected change",
            "contributor", "pull request", "pr ", "prs", "issues in", "open issue",
            "tech debt", "technical debt", "code churn", "blast radius", "manifest",
            "where is", "which file", "locate", "who wrote", "when was", "overview of",
            "dependenc", "package", "module"
        ]
        if any(ind in q for ind in project_indicators):
            return False

        # Conceptual / generic programming question patterns
        general_patterns = [
            r"^(what is|what are|explain|how to|how do i|how does|write|create|implement|difference between)\b.*(in python|in javascript|in typescript|in java|in c\+\+|in c#|in go|in rust|in html|in css|in sql|in react|in angular|in vue|in node|in docker|in git\b)",
            r"^(what is|explain)\s+(an?\s+)?(event loop|closure|hoisting|promise|async/await|generator|recursion|binary search|quicksort|merge sort|linked list|stack|queue|binary tree|hash table|solid principle|design pattern|monad|currying|polymorphism|inheritance|encapsulation|dependency injection|memoization|virtual dom|regex|garbage collection)",
            r"^(how to|how do i)\s+(reverse a string|sort a list|find duplicates|flatten an array|parse json|read a file in python|write a test in jest|center a div)",
            r"^(difference between|compare)\s+(\w+)\s+and\s+(\w+)",
        ]
        for pat in general_patterns:
            if re.search(pat, q):
                return True

        generic_starters = [
            "how do i use", "how to use", "what is the syntax for", "example of a", "example of an",
            "how does garbage collection work", "why use typescript over javascript", "what is restful"
        ]
        if any(q.startswith(gs) for gs in generic_starters) and not any(ind in q for ind in project_indicators):
            return True

        return False

    def analyze_intent(self, question: str) -> Dict[str, Any]:
        """
        Determines the primary and secondary intent categories for a question.
        Categories:
        - 'architecture': structure, modules, components, layering, design, cycles
        - 'endpoints': api routes, endpoints, controllers, http methods, handlers
        - 'dependencies': depends on, blast radius, dependents, imports, package removal
        - 'risks': risky, hazards, bugs, vulnerabilities, risk score
        - 'health': health score, quality, test status, release health, activity
        - 'debt_hotspots': technical debt, refactoring, hotspots, churn, backlog
        - 'twin_changes': digital twin versions, detected changes, snapshots
        - 'git_activity': commits, PRs, issues, contributors
        - 'files': where is, which file, file structure, path, location
        - 'component': what is X, tell me about X, what does X do
        - 'general': overview, summary, introduction
        """
        q = question.lower()

        intents = []
        if any(w in q for w in ["endpoint", "api", "route", "handler", "controller", "rest", "http", "fastapi"]):
            intents.append("endpoints")

        if any(w in q for w in ["twin", "version", "changes", "detected changes", "snapshot"]):
            intents.append("twin_changes")

        if any(w in q for w in ["commit", "pr ", "pull request", "contributor", "recent work"]):
            intents.append("git_activity")

        if any(w in q for w in ["architect", "structure", "module", "layer", "overview of project", "high level"]):
            intents.append("architecture")

        if any(w in q for w in ["depend", "import", "require", "used by", "blast radius", "remove", "package", "dependency"]):
            intents.append("dependencies")

        if any(w in q for w in ["risk", "threat", "vulnerab", "critical", "warning", "severity"]):
            intents.append("risks")

        if any(w in q for w in ["health", "score", "healthy", "quality", "activity", "throughput"]):
            intents.append("health")

        if any(w in q for w in ["debt", "hotspot", "churn", "backlog", "refactor", "improve", "fix first", "smell"]):
            intents.append("debt_hotspots")

        if any(w in q for w in ["where is", "which file", "locate", "filepath", "code for", "implement"]):
            intents.append("files")

        if any(w in q for w in ["what does", "what is", "tell me about", "explain the component", "function of"]):
            intents.append("component")

        primary = intents[0] if intents else "general"
        return {
            "primary": primary,
            "all_intents": intents if intents else ["general"],
        }

    def extract_entity_candidate(self, question: str, previous_entity: Optional[str] = None) -> Optional[str]:
        """
        Extracts potential entity, module, or package names mentioned in the question.
        If the question contains referential pronouns ("it", "this", "that component"),
        resolves to the previous entity.
        """
        q_clean = question.strip()

        # Check for referential pronouns
        lower = q_clean.lower()
        pronoun_match = bool(re.search(r"\b(it|this|that|the component|this component|that component|the module)\b", lower))
        if pronoun_match and previous_entity:
            return previous_entity

        # Look for quoted strings: "PaymentService", '@babel/core'
        quoted = re.findall(r"['\"`]([^'\"`]+)['\"`]", q_clean)
        if quoted:
            return quoted[0].strip()

        # Look for scoped package names like @babel/core
        scoped_pkg = re.search(r"@[\w\-\.]+/[\w\-\.]+", q_clean)
        if scoped_pkg:
            return scoped_pkg.group(0).strip()

        # Look for CamelCase or PascalCase names (e.g. PaymentService, OrderController, ReactCompiler)
        stopwords = {
            "what", "which", "where", "when", "why", "how", "tell", "explain",
            "does", "can", "could", "should", "would", "show", "list", "give",
            "find", "have", "has", "are", "were", "will", "the", "this", "that"
        }
        camel_candidates = re.findall(r"\b[A-Z][a-zA-Z0-9_]{2,}\b", q_clean)
        for cand in camel_candidates:
            if cand.lower() not in stopwords:
                return cand

        # Look for path-like package names or module paths (e.g. facebook/react)
        path_pkg = re.search(r"\b([\w\-\.]+/[\w\-\.]+)\b", q_clean)
        if path_pkg and not path_pkg.group(1).startswith("http"):
            return path_pkg.group(1).strip()

        # Look for file path pattern (e.g. app/main.py, package.json, server.ts)
        file_match = re.search(r"\b([\w\-/\\]+\.(?:py|js|ts|tsx|jsx|json|toml|md|yml|yaml))\b", q_clean, re.I)
        if file_match:
            return file_match.group(1).strip()

        return None

    def build_project_context(
        self,
        project_id: int,
        question: str,
        db: Session,
        previous_entity: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Assembles a verified, focused context payload based on user question and project data.
        Returns:
            {
                "context_text": str,
                "sources": List[AssistantSourceItem],
                "related_components": List[str],
                "related_risks": List[str],
                "resolved_entity": Optional[str],
                "is_general": bool,
                "intent": str
            }
        """
        # Check if question is a purely conceptual or generic programming query
        if self.is_general_programming_question(question):
            return {
                "context_text": (
                    "This is a general programming, algorithmic, or software engineering question not specific to the local repository.\n"
                    "Provide a clear, accurate, structured explanation with code examples and best practices. "
                    "Do not invent fictitious repository files or claim that the local repository contains files it does not."
                ),
                "sources": [],
                "related_components": [],
                "related_risks": [],
                "resolved_entity": None,
                "is_general": True,
                "intent": "general_programming",
            }

        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return {
                "context_text": "Project not found in system.",
                "sources": [],
                "related_components": [],
                "related_risks": [],
                "resolved_entity": None,
                "is_general": False,
                "intent": "general",
            }

        intent_info = self.analyze_intent(question)
        entity_candidate = self.extract_entity_candidate(question, previous_entity)
        sources: List[AssistantSourceItem] = []
        related_components: List[str] = []
        related_risks: List[str] = []

        context_sections = []

        # 1. Project High-Level Overview & README Documentation
        context_sections.append(
            f"PROJECT METADATA:\n"
            f"- Repository: {project.full_name}\n"
            f"- Name: {project.name}\n"
            f"- Primary Language: {project.language or 'Unknown'}\n"
            f"- Default Branch: {project.default_branch or 'main'}\n"
            f"- Total Open Issues: {project.open_issues_count}\n"
            f"- Total Open PRs: {project.open_prs_count}\n"
            f"- Health Score: {project.health_score if project.health_score is not None else 'Uncalculated'}/100\n"
        )
        sources.append(AssistantSourceItem(
            type="metric",
            name=f"Project: {project.name}",
            path=None,
            detail=f"Overall health score: {project.health_score}/100"
        ))

        # Retrieve README or project documentation
        self._retrieve_readme_context(project, context_sections, sources)

        # 2. Specific Entity/Component Intelligence (if detected)
        matched_node = None
        if entity_candidate:
            matched_node = self._retrieve_component_context(
                project_id=project_id,
                entity_name=entity_candidate,
                db=db,
                context_sections=context_sections,
                sources=sources,
                related_components=related_components
            )

        intents = set(intent_info["all_intents"])

        # 3. Knowledge Graph Endpoints & Database Schemas
        if "endpoints" in intents:
            self._retrieve_endpoints_and_database_context(
                project_id=project_id,
                db=db,
                context_sections=context_sections,
                sources=sources
            )

        # 4. Architecture & Dependency Intelligence
        if "architecture" in intents or "dependencies" in intents or ("general" in intents and not matched_node):
            self._retrieve_architecture_context(
                project_id=project_id,
                db=db,
                context_sections=context_sections,
                sources=sources,
                related_components=related_components
            )

        # 5. Software Health Intelligence
        if "health" in intents or ("general" in intents and "architecture" not in intents and not matched_node):
            self._retrieve_health_context(
                project_id=project_id,
                db=db,
                context_sections=context_sections,
                sources=sources
            )

        # 6. Software Risk Intelligence
        if "risks" in intents or "debt_hotspots" in intents:
            self._retrieve_risks_context(
                project_id=project_id,
                db=db,
                context_sections=context_sections,
                sources=sources,
                related_risks=related_risks
            )

        # 7. Technical Debt, Evolution & Change Hotspots Intelligence
        if "debt_hotspots" in intents:
            self._retrieve_technical_debt_context(
                project_id=project_id,
                db=db,
                context_sections=context_sections,
                sources=sources
            )

        # 8. Digital Twin Version & Detected Changes
        if "twin_changes" in intents:
            self._retrieve_digital_twin_changes_context(
                project_id=project_id,
                db=db,
                context_sections=context_sections,
                sources=sources
            )

        # 9. Recent Git Activity (Commits, PRs, Issues)
        if "git_activity" in intents:
            self._retrieve_git_activity_context(
                project_id=project_id,
                db=db,
                context_sections=context_sections,
                sources=sources
            )

        # 10. File / Structure Intelligence (if searching for files or implementation)
        if "files" in intents:
            self._retrieve_file_context(
                project_id=project_id,
                query=question,
                entity_candidate=entity_candidate,
                db=db,
                context_sections=context_sections,
                sources=sources
            )

        context_text = "\n\n".join(context_sections)

        # Deduplicate sources and components
        unique_sources = []
        seen_source_keys = set()
        for s in sources:
            key = (s.type, s.name, s.path)
            if key not in seen_source_keys:
                seen_source_keys.add(key)
                unique_sources.append(s)

        unique_components = list(dict.fromkeys(related_components))
        unique_risks = list(dict.fromkeys(related_risks))

        return {
            "context_text": context_text,
            "sources": unique_sources[:8],
            "related_components": unique_components[:6],
            "related_risks": unique_risks[:6],
            "resolved_entity": entity_candidate,
            "is_general": False,
            "intent": intent_info["primary"],
        }

    def _retrieve_component_context(
        self,
        project_id: int,
        entity_name: str,
        db: Session,
        context_sections: List[str],
        sources: List[AssistantSourceItem],
        related_components: List[str]
    ) -> Optional[GraphNode]:
        """Looks up a specific component, module, or package in the Knowledge Graph and dependency manifests."""
        analysis = db.query(ArchitectureAnalysis).filter(
            ArchitectureAnalysis.project_id == project_id,
            ArchitectureAnalysis.status == "COMPLETED"
        ).order_by(desc(ArchitectureAnalysis.analyzed_at)).first()

        clean_name = entity_name.strip("'\"`")
        node = None

        if analysis:
            # Try exact match, then case-insensitive / partial match
            node = db.query(GraphNode).filter(
                GraphNode.analysis_id == analysis.id,
                GraphNode.name == clean_name
            ).first()

            if not node:
                node = db.query(GraphNode).filter(
                    GraphNode.analysis_id == analysis.id,
                    GraphNode.name.ilike(f"%{clean_name}%")
                ).first()

            if not node:
                # Try by file path match
                node = db.query(GraphNode).filter(
                    GraphNode.analysis_id == analysis.id,
                    GraphNode.file_path.ilike(f"%{clean_name}%")
                ).first()

        # Also check dependency manifest items (e.g. @babel/core, axios, react)
        dep_items = db.query(DependencyItem).join(DependencyManifest).filter(
            DependencyManifest.project_id == project_id,
            DependencyItem.name.ilike(f"%{clean_name}%")
        ).all()

        if node:
            related_components.append(node.name)
            # Find incoming edges (dependents - who relies on this node)
            incoming = db.query(GraphEdge).filter(
                GraphEdge.analysis_id == analysis.id,
                GraphEdge.target_id == node.id
            ).all()

            # Find outgoing edges (dependencies - what does this node rely on)
            outgoing = db.query(GraphEdge).filter(
                GraphEdge.analysis_id == analysis.id,
                GraphEdge.source_id == node.id
            ).all()

            dependent_node_ids = [e.source_id for e in incoming]
            dependent_nodes = db.query(GraphNode).filter(
                GraphNode.analysis_id == analysis.id,
                GraphNode.id.in_(dependent_node_ids)
            ).limit(10).all() if dependent_node_ids else []

            dependency_node_ids = [e.target_id for e in outgoing]
            dependency_nodes = db.query(GraphNode).filter(
                GraphNode.analysis_id == analysis.id,
                GraphNode.id.in_(dependency_node_ids)
            ).limit(10).all() if dependency_node_ids else []

            dependent_names = [dn.name for dn in dependent_nodes]
            dependency_names = [dn.name for dn in dependency_nodes]

            for dn in dependent_names[:4]:
                related_components.append(dn)

            section = (
                f"COMPONENT INTELLIGENCE FOR '{node.name}':\n"
                f"- Entity Type: {node.node_type}\n"
                f"- Defined in File: {node.file_path or 'External / Package'}\n"
                f"- Module: {node.module or 'root'}\n"
                f"- Direct Dependents Count (Impact/Blast Radius): {len(incoming)}\n"
                f"- Direct Dependents: {', '.join(dependent_names) if dependent_names else 'None'}\n"
                f"- Direct Dependencies Count: {len(outgoing)}\n"
                f"- Direct Dependencies: {', '.join(dependency_names) if dependency_names else 'None'}\n"
            )
            context_sections.append(section)

            sources.append(AssistantSourceItem(
                type="component",
                name=node.name,
                path=node.file_path,
                detail=f"Type: {node.node_type}, Module: {node.module or 'root'}, {len(incoming)} dependents"
            ))
            if node.file_path:
                sources.append(AssistantSourceItem(
                    type="file",
                    name=node.file_path.split("/")[-1],
                    path=node.file_path,
                    detail=f"Defines {node.name}"
                ))
            return node

        elif dep_items:
            first_dep = dep_items[0]
            manifest = first_dep.manifest
            related_components.append(first_dep.name)
            section = (
                f"PACKAGE DEPENDENCY FOR '{first_dep.name}':\n"
                f"- Declared in Manifest: {manifest.file_path} ({manifest.manifest_type})\n"
                f"- Version Constraint: {first_dep.version_spec or 'any'}\n"
                f"- Dev Dependency: {'Yes' if first_dep.is_dev_dependency else 'No'}\n"
            )
            # Check if any graph nodes reference this package
            if analysis:
                ref_edges = db.query(GraphEdge).filter(
                    GraphEdge.analysis_id == analysis.id,
                    GraphEdge.target_id.ilike(f"%{clean_name}%")
                ).all()
                if ref_edges:
                    section += f"- Direct Graph Dependents: {len(ref_edges)} components import or depend on this package.\n"

            context_sections.append(section)
            sources.append(AssistantSourceItem(
                type="dependency",
                name=first_dep.name,
                path=manifest.file_path,
                detail=f"Ecosystem: {manifest.manifest_type}, Version: {first_dep.version_spec or 'unspecified'}"
            ))
            return None

        return None

    def _retrieve_architecture_context(
        self,
        project_id: int,
        db: Session,
        context_sections: List[str],
        sources: List[AssistantSourceItem],
        related_components: List[str]
    ) -> None:
        """Retrieves module architecture, circular dependencies, hotspots, and coupling."""
        analysis = db.query(ArchitectureAnalysis).filter(
            ArchitectureAnalysis.project_id == project_id,
            ArchitectureAnalysis.status == "COMPLETED"
        ).order_by(desc(ArchitectureAnalysis.analyzed_at)).first()

        if not analysis or not analysis.metrics:
            context_sections.append(
                "ARCHITECTURE INTELLIGENCE:\n"
                "- Architecture analysis has not been calculated yet for this project."
            )
            return

        m = analysis.metrics
        modules = m.get("modules", [])
        cycles = analysis.cycles or []
        hotspots = m.get("hotspots", [])
        bottlenecks = m.get("bottlenecks", [])

        top_modules = []
        for mod in modules[:6]:
            mod_name = mod.get("name", "unknown")
            top_modules.append(f"{mod_name} (internal: {mod.get('internal_components', 0)}, fan-in: {mod.get('fan_in', 0)}, fan-out: {mod.get('fan_out', 0)})")
            related_components.append(mod_name)

        cycle_descriptions = []
        for c in cycles[:3]:
            cycle_nodes = c.get("nodes", c) if isinstance(c, dict) else c
            if isinstance(cycle_nodes, list):
                cycle_descriptions.append(" -> ".join(cycle_nodes[:4]))

        section = (
            f"ARCHITECTURE INTELLIGENCE:\n"
            f"- Total Files Tracked: {m.get('total_files', 0)}\n"
            f"- Total Modules: {m.get('total_modules', 0)}\n"
            f"- Total Classes: {m.get('total_classes', 0)}\n"
            f"- Total Functions/Methods: {m.get('total_functions', 0)}\n"
            f"- Total Internal Dependencies: {m.get('internal_dependencies', 0)}\n"
            f"- Circular Dependency Cycles Detected: {len(cycles)}\n"
        )
        if cycle_descriptions:
            section += f"  - Detected Cycles: {'; '.join(cycle_descriptions)}\n"
        if top_modules:
            section += f"- Major Architectural Modules: {'; '.join(top_modules)}\n"
        if hotspots:
            h_names = [h.get("module_name", h.get("name", "unknown")) for h in hotspots[:4] if isinstance(h, dict)]
            section += f"- Coupling Hotspots: {', '.join(h_names)}\n"
        if bottlenecks:
            b_names = [b.get("name", "unknown") for b in bottlenecks[:4] if isinstance(b, dict)]
            section += f"- Architectural Bottlenecks: {', '.join(b_names)}\n"

        context_sections.append(section)
        sources.append(AssistantSourceItem(
            type="component",
            name="Architecture Graph",
            path=None,
            detail=f"{m.get('total_modules', 0)} modules, {m.get('total_files', 0)} files, {len(cycles)} cycles"
        ))

    def _retrieve_health_context(
        self,
        project_id: int,
        db: Session,
        context_sections: List[str],
        sources: List[AssistantSourceItem]
    ) -> None:
        """Retrieves latest Software Health snapshot and dimension results."""
        latest = db.query(SoftwareHealthSnapshot).filter(
            SoftwareHealthSnapshot.project_id == project_id
        ).order_by(desc(SoftwareHealthSnapshot.calculated_at)).first()

        if not latest:
            context_sections.append("SOFTWARE HEALTH INTELLIGENCE:\n- No health calculation available.")
            return

        dimensions = db.query(HealthDimensionResult).filter(
            HealthDimensionResult.snapshot_id == latest.id
        ).all()

        dim_summaries = []
        for d in dimensions:
            score_str = f"{d.score:.1f}" if d.score is not None else "N/A"
            dim_summaries.append(f"{d.name}: {score_str}/100 ({d.status})")

        explanations = latest.explanations or []

        section = (
            f"SOFTWARE HEALTH EVALUATION:\n"
            f"- Overall Health Score: {latest.overall_score:.1f}/100 ({latest.overall_status})\n"
            f"- Dimension Breakdown: {', '.join(dim_summaries)}\n"
        )
        if explanations:
            section += "- Evaluated Signals:\n"
            for expl in explanations[:4]:
                section += f"  * {expl}\n"

        context_sections.append(section)
        sources.append(AssistantSourceItem(
            type="health",
            name=f"Health: {latest.overall_score:.1f}/100",
            path=None,
            detail=f"Status: {latest.overall_status}. Dimensions: {len(dimensions)} tracked"
        ))

    def _retrieve_risks_context(
        self,
        project_id: int,
        db: Session,
        context_sections: List[str],
        sources: List[AssistantSourceItem],
        related_risks: List[str]
    ) -> None:
        """Retrieves active Software Risks, severities, and affected entities."""
        risks = db.query(SoftwareRisk).filter(
            SoftwareRisk.project_id == project_id,
            SoftwareRisk.status.in_(["OPEN", "ACKNOWLEDGED"])
        ).order_by(desc(SoftwareRisk.detected_at)).limit(6).all()

        if not risks:
            context_sections.append("ACTIVE RISKS:\n- No critical or open software risks currently detected.")
            return

        risk_bullets = []
        for r in risks:
            related_risks.append(r.title)
            risk_bullets.append(f"[{r.severity}] {r.title}: {r.description}")
            sources.append(AssistantSourceItem(
                type="risk",
                name=f"Risk: {r.title}",
                path=None,
                detail=f"Severity: {r.severity}, Rule: {r.detection_rule}"
            ))

        section = "ACTIVE RISKS DETECTED IN REPOSITORY:\n"
        for rb in risk_bullets:
            section += f"- {rb}\n"

        context_sections.append(section)

    def _retrieve_technical_debt_context(
        self,
        project_id: int,
        db: Session,
        context_sections: List[str],
        sources: List[AssistantSourceItem]
    ) -> None:
        """Retrieves Technical Debt indicators and active change hotspots."""
        debt_indicators = db.query(TechnicalDebtIndicator).filter(
            TechnicalDebtIndicator.project_id == project_id
        ).all()

        hotspots = db.query(ChangeHotspot).filter(
            ChangeHotspot.project_id == project_id
        ).order_by(desc(ChangeHotspot.churn)).limit(5).all()

        manifests = db.query(DependencyManifest).filter(
            DependencyManifest.project_id == project_id
        ).all()

        debt_summaries = []
        for td in debt_indicators:
            debt_summaries.append(f"{td.indicator_name or td.indicator_type}: {td.severity} (score {td.score:.1f})")

        hotspot_summaries = []
        for hs in hotspots:
            hotspot_summaries.append(f"{hs.path} (churn: {hs.churn}, commits: {hs.change_count})")
            sources.append(AssistantSourceItem(
                type="hotspot",
                name=hs.path.split("/")[-1],
                path=hs.path,
                detail=f"High churn: {hs.churn} lines, {hs.change_count} commits"
            ))

        manifest_summaries = []
        for man in manifests:
            manifest_summaries.append(f"{man.file_path} ({man.manifest_type}, {man.dependency_count} dependencies declared)")

        section = "TECHNICAL DEBT & CODE CHURN TELEMETRY:\n"
        if debt_summaries:
            section += f"- Heuristic Debt Indicators: {', '.join(debt_summaries)}\n"
        if hotspot_summaries:
            section += f"- Top Active Change Hotspots: {', '.join(hotspot_summaries)}\n"
        if manifest_summaries:
            section += f"- Dependency Manifests Tracked: {', '.join(manifest_summaries)}\n"

        if debt_summaries or hotspot_summaries or manifest_summaries:
            context_sections.append(section)

    def _retrieve_file_context(
        self,
        project_id: int,
        query: str,
        entity_candidate: Optional[str],
        db: Session,
        context_sections: List[str],
        sources: List[AssistantSourceItem]
    ) -> None:
        """Searches repository file tree for paths relevant to the user query."""
        keywords = [w for w in re.findall(r"\w+", query.lower()) if len(w) > 3 and w not in {"where", "which", "files", "project", "code", "explain", "implement"}]
        if entity_candidate:
            keywords.append(entity_candidate.lower())

        if not keywords:
            return

        matching_files = []
        for kw in keywords[:3]:
            files = db.query(RepositoryFile).filter(
                RepositoryFile.project_id == project_id,
                RepositoryFile.path.ilike(f"%{kw}%")
            ).limit(4).all()
            for f in files:
                if f.path not in matching_files:
                    matching_files.append(f.path)

        if matching_files:
            section = "RELEVANT REPOSITORY FILES:\n"
            for mf in matching_files[:6]:
                section += f"- {mf}\n"
                sources.append(AssistantSourceItem(
                    type="file",
                    name=mf.split("/")[-1],
                    path=mf,
                    detail="Repository source file"
                ))
            context_sections.append(section)

    def _retrieve_readme_context(
        self,
        project: Project,
        context_sections: List[str],
        sources: List[AssistantSourceItem]
    ) -> None:
        """Reads project README or description to give architectural and functional orientation."""
        readme_text = None
        try:
            safe_name = f"{project.github_owner}_{project.github_repo}".replace("/", "_").replace("\\", "_")
            candidate_dirs = [
                os.path.join(architecture_service.storage_dir, safe_name).replace("\\", "/"),
            ]
            if project.github_owner == "test" or project.full_name in ("test/digital-twin", "AtharvaUbhe46/AI-Digital-Twin-for-Software-Intelligence"):
                candidate_dirs.append(architecture_service.default_workspace)

            for target_dir in candidate_dirs:
                if os.path.isdir(target_dir):
                    for candidate in ["README.md", "readme.md", "README.rst", "README.txt", "README"]:
                        p = os.path.join(target_dir, candidate)
                        if os.path.isfile(p):
                            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                                raw = f.read(2500)
                                lines = [ln for ln in raw.splitlines() if not ln.strip().startswith("[!") and not ln.strip().startswith("<img")][:25]
                                readme_text = "\n".join(lines).strip()
                                sources.append(AssistantSourceItem(
                                    type="documentation",
                                    name="README.md",
                                    path=candidate,
                                    detail="Project documentation"
                                ))
                                break
                    if readme_text:
                        break
        except Exception as e:
            logger.debug(f"Could not read README from disk: {e}")

        if not readme_text and project.description:
            readme_text = f"Repository Description: {project.description}"

        if readme_text:
            context_sections.append(
                f"PROJECT DOCUMENTATION & OVERVIEW:\n{readme_text}"
            )

    def _retrieve_endpoints_and_database_context(
        self,
        project_id: int,
        db: Session,
        context_sections: List[str],
        sources: List[AssistantSourceItem]
    ) -> None:
        """Retrieves Knowledge Graph extracted API endpoints, database entities, and layered call relationships."""
        analysis = db.query(ArchitectureAnalysis).filter(
            ArchitectureAnalysis.project_id == project_id,
            ArchitectureAnalysis.status == "COMPLETED"
        ).order_by(desc(ArchitectureAnalysis.analyzed_at)).first()

        if not analysis:
            return

        endpoint_nodes = db.query(GraphNode).filter(
            GraphNode.analysis_id == analysis.id,
            GraphNode.node_type.in_(["api_endpoint", "endpoint"])
        ).limit(10).all()

        db_nodes = db.query(GraphNode).filter(
            GraphNode.analysis_id == analysis.id,
            GraphNode.node_type.in_(["database_entity", "model", "schema"])
        ).limit(6).all()

        endpoint_lines = []
        for ep in endpoint_nodes:
            meta = ep.node_metadata or {}
            method = meta.get("http_method", "")
            route = meta.get("route_path", ep.name)
            handler = meta.get("handler_function", "")
            framework = meta.get("framework", "")
            desc_str = f"{method} {route}".strip()
            if handler:
                desc_str += f" (handler: {handler})"
            if ep.file_path:
                desc_str += f" in `{ep.file_path}`"
            endpoint_lines.append(desc_str)
            sources.append(AssistantSourceItem(
                type="endpoint",
                name=f"{method} {route}".strip(),
                path=ep.file_path,
                detail=f"Handler: {handler or 'N/A'}, Framework: {framework or 'N/A'}"
            ))

        db_lines = []
        for d in db_nodes:
            meta = d.node_metadata or {}
            table = meta.get("table_name", d.name)
            desc_str = f"{d.name} (table: {table})"
            if d.file_path:
                desc_str += f" in `{d.file_path}`"
            db_lines.append(desc_str)
            sources.append(AssistantSourceItem(
                type="database",
                name=d.name,
                path=d.file_path,
                detail=f"Table: {table}"
            ))

        layered_edges = db.query(GraphEdge).filter(
            GraphEdge.analysis_id == analysis.id,
            GraphEdge.relationship_type.in_(["CALLS", "HANDLED_BY", "BELONGS_TO", "ACCESSES"])
        ).limit(8).all()

        edge_lines = []
        for edge in layered_edges:
            s_name = edge.source_id.split(":")[-1] if ":" in edge.source_id else edge.source_id
            t_name = edge.target_id.split(":")[-1] if ":" in edge.target_id else edge.target_id
            edge_lines.append(f"{s_name} --[{edge.relationship_type}]--> {t_name}")

        section = "KNOWLEDGE GRAPH ENDPOINTS & DATABASE SCHEMAS:\n"
        if endpoint_lines:
            section += f"- Extracted API Endpoints ({len(endpoint_nodes)}):\n  * " + "\n  * ".join(endpoint_lines) + "\n"
        if db_lines:
            section += f"- Extracted Database Entities ({len(db_nodes)}):\n  * " + "\n  * ".join(db_lines) + "\n"
        if edge_lines:
            section += f"- Verified Architecture Call Chains:\n  * " + "\n  * ".join(edge_lines) + "\n"

        if endpoint_lines or db_lines or edge_lines:
            context_sections.append(section)

    def _retrieve_digital_twin_changes_context(
        self,
        project_id: int,
        db: Session,
        context_sections: List[str],
        sources: List[AssistantSourceItem]
    ) -> None:
        """Retrieves Digital Twin versions, fidelity score, and recently detected state changes."""
        twin = db.query(DigitalTwin).filter(DigitalTwin.project_id == project_id).first()
        if not twin:
            return

        latest_snapshot = db.query(DigitalTwinSnapshot).filter(
            DigitalTwinSnapshot.digital_twin_id == twin.id
        ).order_by(desc(DigitalTwinSnapshot.version)).first()

        recent_changes = db.query(DigitalTwinChange).filter(
            DigitalTwinChange.digital_twin_id == twin.id
        ).order_by(desc(DigitalTwinChange.detected_at)).limit(5).all()

        section = (
            f"DIGITAL TWIN STATE & VERSION INTELLIGENCE:\n"
            f"- Twin Status: {twin.status}\n"
            f"- Current Twin Version: v{twin.current_version}\n"
            f"- Fidelity Score: {twin.fidelity_score:.1f}/100\n"
        )
        if latest_snapshot and latest_snapshot.summary:
            section += f"- Latest Snapshot Summary: {latest_snapshot.summary}\n"

        if recent_changes:
            change_bullets = []
            for chg in recent_changes:
                summary = chg.change_summary or f"{chg.change_type} {chg.entity_type} {chg.entity_id}"
                change_bullets.append(f"[{chg.change_type}] {summary}")
            section += f"- Recently Detected State Changes:\n  * " + "\n  * ".join(change_bullets) + "\n"
            sources.append(AssistantSourceItem(
                type="twin",
                name=f"Digital Twin v{twin.current_version}",
                path=None,
                detail=f"Status: {twin.status}, {len(recent_changes)} recent changes tracked"
            ))

        context_sections.append(section)

    def _retrieve_git_activity_context(
        self,
        project_id: int,
        db: Session,
        context_sections: List[str],
        sources: List[AssistantSourceItem]
    ) -> None:
        """Retrieves recent commits, open PRs, and tracked issues for project activity context."""
        commits = db.query(Commit).filter(
            Commit.project_id == project_id
        ).order_by(desc(Commit.committed_at)).limit(5).all()

        prs = db.query(PullRequest).filter(
            PullRequest.project_id == project_id,
            PullRequest.state == "open"
        ).order_by(desc(PullRequest.created_at)).limit(3).all()

        issues = db.query(Issue).filter(
            Issue.project_id == project_id,
            Issue.state == "open"
        ).order_by(desc(Issue.created_at)).limit(3).all()

        if not commits and not prs and not issues:
            return

        section = "RECENT REPOSITORY ACTIVITY & COMMITS:\n"
        if commits:
            commit_lines = []
            for c in commits:
                sha_short = (c.sha or "")[:7]
                first_line = (c.message or "").splitlines()[0] if c.message else "No commit message"
                author = c.author_name or "Unknown"
                commit_lines.append(f"{sha_short} ({author}): {first_line}")
                sources.append(AssistantSourceItem(
                    type="commit",
                    name=f"Commit {sha_short}",
                    path=None,
                    detail=f"By {author}: {first_line[:60]}"
                ))
            section += "- Recent Git Commits:\n  * " + "\n  * ".join(commit_lines) + "\n"

        if prs:
            pr_lines = [f"#{pr.number}: {pr.title} (by {pr.user_login or 'unknown'})" for pr in prs]
            section += "- Active Open Pull Requests:\n  * " + "\n  * ".join(pr_lines) + "\n"

        if issues:
            issue_lines = [f"#{iss.number}: {iss.title}" for iss in issues]
            section += "- Open Issues:\n  * " + "\n  * ".join(issue_lines) + "\n"

        context_sections.append(section)


context_engine = ProjectContextEngine()
