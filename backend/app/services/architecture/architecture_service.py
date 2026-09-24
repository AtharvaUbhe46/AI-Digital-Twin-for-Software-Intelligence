import os
import shutil
import zipfile
import tempfile
import subprocess
import urllib.request
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.config import settings
from app.models.project import Project
from app.models.digital_twin import DigitalTwin, RepositoryFile
from app.models.architecture import ArchitectureAnalysis, GraphNode, GraphEdge
from app.services.architecture.parser import parser_engine, ParsedEntity, ParsedRelation
from app.services.architecture.graph.graph_builder import KnowledgeGraphBuilder
from app.services.architecture.graph.cycle_detector import CycleDetector
from app.services.architecture.graph.architecture_engine import ArchitectureEngine

logger = logging.getLogger("digital_twin.architecture.service")


class ArchitectureService:
    def __init__(self):
        # Default workspace root if none provided
        self.default_workspace = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
        ).replace("\\", "/")
        # Storage location for cloned/downloaded repositories
        self.storage_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "repos")
        ).replace("\\", "/")

    def get_latest_analysis(self, project_id: int, db: Session) -> Optional[ArchitectureAnalysis]:
        analysis = (
            db.query(ArchitectureAnalysis)
            .filter(ArchitectureAnalysis.project_id == project_id)
            .order_by(desc(ArchitectureAnalysis.analyzed_at))
            .first()
        )
        if analysis and analysis.metrics:
            project = db.query(Project).filter(Project.id == project_id).first()
            if project and analysis.metrics.get("repo_full_name") and analysis.metrics.get("repo_full_name") != project.full_name:
                # Analysis was performed for a different project, consider stale
                return None
        return analysis

    def analyze_project(
        self,
        project_id: int,
        db: Session,
        repo_path: Optional[str] = None,
        force_refresh: bool = False
    ) -> ArchitectureAnalysis:
        """
        Executes static analysis for a project, constructing its Knowledge Graph,
        architecture metrics, and cycle analysis. Persists results to DB.
        """
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project {project_id} not found.")

        # Check existing analysis if not forcing refresh
        existing = self.get_latest_analysis(project_id, db)
        if existing and existing.status == "COMPLETED" and not force_refresh:
            if existing.metrics and existing.metrics.get("repo_full_name") == project.full_name:
                return existing

        # Locate source directory safely (cloning/downloading repository if remote GitHub link)
        target_dir = self._resolve_target_dir(project, repo_path)
        logger.info(f"Starting architecture analysis for project {project.full_name} at {target_dir}")

        # Clean previous analyses for this project to maintain a clean, high-performance state
        prev_analyses = db.query(ArchitectureAnalysis).filter(ArchitectureAnalysis.project_id == project_id).all()
        for prev in prev_analyses:
            db.delete(prev)
        db.commit()

        twin = db.query(DigitalTwin).filter(DigitalTwin.project_id == project_id).first()
        twin_version = twin.current_version if twin else 1

        # Create or update analysis record
        analysis = ArchitectureAnalysis(
            project_id=project_id,
            twin_version=twin_version,
            status="ANALYZING",
            analyzed_at=datetime.now(timezone.utc),
            analysis_version="1.0.0",
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)

        try:
            # 1. Parse repository source files
            parsed_entities, parsed_relations = parser_engine.parse_directory(
                target_dir,
                repo_display_name=project.name or project.full_name
            )

            # 2. Build and deduplicate Knowledge Graph
            node_map, resolved_relations = KnowledgeGraphBuilder.build_graph(
                entities=parsed_entities,
                relations=parsed_relations,
                project_id=project_id,
            )

            # 3. Detect Circular Dependencies
            adjacency: Dict[str, set] = {}
            for rel in resolved_relations:
                if rel.rel_type in ("IMPORTS", "DEPENDS_ON", "CALLS"):
                    adjacency.setdefault(rel.source_id, set()).add(rel.target_id)

            detected_cycles = CycleDetector.detect_cycles(adjacency)

            # 4. Architecture and Coupling Metrics
            arch_summary = ArchitectureEngine.analyze_architecture(
                nodes=node_map,
                edges=resolved_relations,
            )

            # Compute entity counts
            type_counts = {}
            for n in node_map.values():
                type_counts[n.entity_type] = type_counts.get(n.entity_type, 0) + 1

            total_files = type_counts.get("file", 0)
            total_classes = type_counts.get("class", 0)
            total_functions = type_counts.get("function", 0) + type_counts.get("method", 0)
            total_modules = len(arch_summary.get("modules", []))

            metrics_payload = {
                "repo_full_name": project.full_name,
                "analyzed_dir": target_dir,
                "total_files": total_files,
                "total_modules": total_modules,
                "total_classes": total_classes,
                "total_functions": total_functions,
                "total_dependencies": len(resolved_relations),
                "internal_dependencies": arch_summary.get("internal_dependencies_count", 0),
                "external_dependencies": arch_summary.get("external_dependencies_count", 0),
                "circular_dependencies": len(detected_cycles),
                "architecture_hotspots": len(arch_summary.get("hotspots", [])),
                "node_type_counts": type_counts,
                "most_connected_modules": arch_summary.get("most_connected_modules", []),
                "most_depended_modules": arch_summary.get("most_depended_modules", []),
                "modules": arch_summary.get("modules", []),
                "bottlenecks": arch_summary.get("bottlenecks", []),
                "hotspots": arch_summary.get("hotspots", []),
                "packages": arch_summary.get("packages", []),
                "unused_packages_count": arch_summary.get("unused_packages_count", 0),
            }

            analysis.status = "COMPLETED"
            analysis.metrics = metrics_payload
            analysis.cycles = detected_cycles
            analysis.summary = (
                f"Analysis complete for {project.full_name}: {total_files} files, {total_modules} modules, {total_classes} classes, "
                f"{total_functions} functions. Detected {len(detected_cycles)} cycles, "
                f"{len(arch_summary.get('hotspots', []))} architectural hotspots."
            )

            # Persist nodes and edges in batch
            db_nodes = []
            for n in node_map.values():
                db_nodes.append(
                    GraphNode(
                        id=n.id,
                        analysis_id=analysis.id,
                        project_id=project_id,
                        node_type=n.entity_type,
                        name=n.name,
                        file_path=n.file_path,
                        line_number=n.line_number,
                        language=n.language,
                        module=n.module,
                        node_metadata=n.metadata,
                    )
                )

            db_edges = []
            for r in resolved_relations:
                db_edges.append(
                    GraphEdge(
                        analysis_id=analysis.id,
                        project_id=project_id,
                        source_id=r.source_id,
                        target_id=r.target_id,
                        relationship_type=r.rel_type,
                        confidence=r.confidence,
                        edge_metadata=r.metadata,
                    )
                )

            # Clear older nodes/edges for this project if replacing
            db.bulk_save_objects(db_nodes)
            db.bulk_save_objects(db_edges)
            db.commit()
            db.refresh(analysis)

            logger.info(f"Successfully finished architecture analysis for {project.full_name}. Saved {len(db_nodes)} nodes and {len(db_edges)} edges.")
            return analysis

        except Exception as exc:
            db.rollback()
            analysis.status = "FAILED"
            analysis.error_message = str(exc)
            try:
                db.commit()
            except Exception:
                pass
            logger.error(f"Architecture analysis failed for project {project_id}: {exc}", exc_info=True)
            raise

    def get_knowledge_graph(
        self,
        project_id: int,
        db: Session,
        node_type: Optional[str] = None,
        relationship_type: Optional[str] = None,
        module: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 500
    ) -> Dict[str, Any]:
        analysis = self.get_latest_analysis(project_id, db)
        if not analysis:
            analysis = self.analyze_project(project_id, db)

        node_query = db.query(GraphNode).filter(GraphNode.analysis_id == analysis.id)
        if node_type:
            node_query = node_query.filter(GraphNode.node_type == node_type)
        if module:
            node_query = node_query.filter(GraphNode.module == module)
        if search:
            node_query = node_query.filter(GraphNode.name.ilike(f"%{search}%"))

        nodes = node_query.limit(limit).all()
        node_ids = {n.id for n in nodes}

        # Query edges connecting retrieved nodes
        edge_query = db.query(GraphEdge).filter(GraphEdge.analysis_id == analysis.id)
        if relationship_type:
            edge_query = edge_query.filter(GraphEdge.relationship_type == relationship_type)

        edges = [
            e for e in edge_query.all()
            if e.source_id in node_ids or e.target_id in node_ids
        ]

        # Calculate type summaries
        metrics = analysis.metrics or {}
        type_counts = metrics.get("node_type_counts", {})
        rel_counts = {}
        for e in edges:
            rel_counts[e.relationship_type] = rel_counts.get(e.relationship_type, 0) + 1

        return {
            "nodes": nodes,
            "edges": edges,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "node_type_counts": type_counts,
            "relationship_type_counts": rel_counts,
            "filtered_by": {
                "node_type": node_type,
                "relationship_type": relationship_type,
                "module": module,
                "search": search,
            }
        }

    def get_node_detail(self, project_id: int, node_id: str, db: Session) -> Dict[str, Any]:
        analysis = self.get_latest_analysis(project_id, db)
        if not analysis:
            analysis = self.analyze_project(project_id, db)

        node = db.query(GraphNode).filter(
            GraphNode.analysis_id == analysis.id,
            GraphNode.id == node_id
        ).first()

        if not node:
            raise ValueError(f"Node '{node_id}' not found in project {project_id}.")

        incoming_edges = db.query(GraphEdge).filter(
            GraphEdge.analysis_id == analysis.id,
            GraphEdge.target_id == node_id
        ).all()

        outgoing_edges = db.query(GraphEdge).filter(
            GraphEdge.analysis_id == analysis.id,
            GraphEdge.source_id == node_id
        ).all()

        dep_ids = {e.target_id for e in outgoing_edges}
        dep_node_objs = db.query(GraphNode).filter(
            GraphNode.analysis_id == analysis.id,
            GraphNode.id.in_(dep_ids)
        ).all() if dep_ids else []

        dependent_ids = {e.source_id for e in incoming_edges}
        dependent_node_objs = db.query(GraphNode).filter(
            GraphNode.analysis_id == analysis.id,
            GraphNode.id.in_(dependent_ids)
        ).all() if dependent_ids else []

        return {
            "node": node,
            "incoming_edges": incoming_edges,
            "outgoing_edges": outgoing_edges,
            "dependencies": dep_node_objs,
            "dependents": dependent_node_objs,
            "metrics": {
                "incoming_count": len(incoming_edges),
                "outgoing_count": len(outgoing_edges),
            }
        }

    def _resolve_target_dir(self, project: Project, custom_path: Optional[str]) -> str:
        """
        Safely verifies, downloads/clones, and resolves the source directory
        for the given project.
        """
        # 1. Custom explicit path takes precedence if provided and valid
        if custom_path:
            norm_custom = os.path.abspath(custom_path).replace("\\", "/")
            if os.path.isdir(norm_custom):
                return norm_custom
            logger.warning(f"Provided path '{custom_path}' not a valid directory. Attempting repository resolution.")

        # 2. Test / local development safety fallback
        if project.github_owner == "test" or project.full_name in ("test/digital-twin", "AtharvaUbhe46/AI-Digital-Twin-for-Software-Intelligence"):
            return self.default_workspace

        # 3. Dedicated cloned/downloaded repository directory for this project
        os.makedirs(self.storage_dir, exist_ok=True)
        safe_name = f"{project.github_owner}_{project.github_repo}".replace("/", "_").replace("\\", "_")
        target_dir = os.path.join(self.storage_dir, safe_name).replace("\\", "/")

        # Check if already cloned and has files
        if os.path.isdir(target_dir):
            contents = [f for f in os.listdir(target_dir) if f != ".git"]
            if contents:
                logger.info(f"Using cached repository directory for {project.full_name} at {target_dir}")
                return target_dir

        # 4. Clone or download the remote GitHub repository
        success = self._fetch_remote_repository(project, target_dir)
        if success and os.path.isdir(target_dir) and any(f for f in os.listdir(target_dir) if f != ".git"):
            return target_dir

        # 5. Fallback: synthesize directory from RepositoryFile records in DB
        synth_success = self._synthesize_from_db_files(project, target_dir)
        if synth_success and os.path.isdir(target_dir) and any(f for f in os.listdir(target_dir) if f != ".git"):
            return target_dir

        logger.warning(f"Could not clone or synthesize repo for {project.full_name}. Falling back to default workspace.")
        return self.default_workspace

    def _fetch_remote_repository(self, project: Project, target_dir: str) -> bool:
        """
        Attempts to shallow clone the GitHub repository using git,
        falling back to downloading the zipball archive.
        """
        owner = project.github_owner
        repo = project.github_repo
        branch = project.default_branch or "main"

        # 1. Try git shallow clone
        try:
            token = settings.GITHUB_TOKEN
            if token and token.strip():
                clone_url = f"https://x-access-token:{token.strip()}@github.com/{owner}/{repo}.git"
            else:
                clone_url = f"https://github.com/{owner}/{repo}.git"

            os.makedirs(target_dir, exist_ok=True)
            logger.info(f"Cloning GitHub repository {owner}/{repo} (branch: {branch}) into {target_dir}...")

            cmd = ["git", "clone", "--depth", "1", "--single-branch"]
            if branch:
                cmd.extend(["--branch", branch])
            cmd.extend([clone_url, target_dir])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0 and os.path.isdir(target_dir) and os.listdir(target_dir):
                logger.info(f"Successfully shallow-cloned {owner}/{repo} into {target_dir}")
                return True
            else:
                logger.warning(f"git clone failed for {owner}/{repo} (exit {result.returncode}): {result.stderr.strip()[:200]}")
        except Exception as exc:
            logger.warning(f"git clone error for {owner}/{repo}: {exc}")

        # 2. Try downloading zip archive from GitHub
        zip_urls = [
            f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip",
            f"https://github.com/{owner}/{repo}/archive/refs/heads/master.zip",
            f"https://github.com/{owner}/{repo}/archive/refs/heads/main.zip",
            f"https://api.github.com/repos/{owner}/{repo}/zipball/{branch}",
        ]

        headers = {
            "User-Agent": "AIDigitalTwin-SoftwareIntelligence/1.0",
        }
        if settings.GITHUB_TOKEN and settings.GITHUB_TOKEN.strip():
            headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN.strip()}"

        for zip_url in zip_urls:
            try:
                logger.info(f"Attempting zipball download from {zip_url}...")
                req = urllib.request.Request(zip_url, headers=headers)
                with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_zip:
                    tmp_zip_path = tmp_zip.name

                with urllib.request.urlopen(req, timeout=30) as response, open(tmp_zip_path, "wb") as out_f:
                    out_f.write(response.read())

                if os.path.getsize(tmp_zip_path) > 0:
                    with tempfile.TemporaryDirectory() as tmp_extract:
                        with zipfile.ZipFile(tmp_zip_path, "r") as zf:
                            zf.extractall(tmp_extract)

                        extracted_items = os.listdir(tmp_extract)
                        # GitHub zip archives have a root folder like repo-main/
                        if len(extracted_items) == 1 and os.path.isdir(os.path.join(tmp_extract, extracted_items[0])):
                            source_inner = os.path.join(tmp_extract, extracted_items[0])
                        else:
                            source_inner = tmp_extract

                        os.makedirs(target_dir, exist_ok=True)
                        for item in os.listdir(source_inner):
                            s = os.path.join(source_inner, item)
                            d = os.path.join(target_dir, item)
                            if os.path.isdir(s):
                                shutil.copytree(s, d, dirs_exist_ok=True)
                            else:
                                shutil.copy2(s, d)

                    try:
                        os.remove(tmp_zip_path)
                    except Exception:
                        pass

                    if os.path.isdir(target_dir) and os.listdir(target_dir):
                        logger.info(f"Successfully extracted zipball for {owner}/{repo} into {target_dir}")
                        return True
            except Exception as e:
                logger.warning(f"Zip download from {zip_url} failed: {e}")
                if 'tmp_zip_path' in locals() and os.path.exists(tmp_zip_path):
                    try:
                        os.remove(tmp_zip_path)
                    except Exception:
                        pass

        return False

    def _synthesize_from_db_files(self, project: Project, target_dir: str) -> bool:
        """
        Synthesizes repository directory from RepositoryFile entries already in DB,
        downloading raw content for key manifest files (package.json, requirements.txt).
        """
        from app.core.database import SessionLocal
        db = SessionLocal()
        try:
            repo_files = db.query(RepositoryFile).filter(RepositoryFile.project_id == project.id).all()
            if not repo_files:
                return False

            os.makedirs(target_dir, exist_ok=True)
            headers = {"User-Agent": "AIDigitalTwin/1.0"}
            if settings.GITHUB_TOKEN and settings.GITHUB_TOKEN.strip():
                headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN.strip()}"

            branch = project.default_branch or "main"
            manifest_names = {"package.json", "requirements.txt", "pyproject.toml", "setup.py", "Pipfile", "pom.xml"}

            for rf in repo_files[:600]:
                if not rf.path:
                    continue
                file_full_path = os.path.join(target_dir, rf.path).replace("\\", "/")
                os.makedirs(os.path.dirname(file_full_path), exist_ok=True)

                # If it's a key manifest file, attempt to fetch raw contents
                content = ""
                if rf.filename in manifest_names:
                    raw_url = f"https://raw.githubusercontent.com/{project.github_owner}/{project.github_repo}/{branch}/{rf.path}"
                    try:
                        req = urllib.request.Request(raw_url, headers=headers)
                        with urllib.request.urlopen(req, timeout=5) as resp:
                            content = resp.read().decode("utf-8", errors="replace")
                    except Exception:
                        content = ""

                try:
                    with open(file_full_path, "w", encoding="utf-8", errors="replace") as f:
                        f.write(content)
                except Exception:
                    pass

            return True
        except Exception as exc:
            logger.warning(f"Could not synthesize repo files from DB for {project.full_name}: {exc}")
            return False
        finally:
            db.close()


architecture_service = ArchitectureService()
