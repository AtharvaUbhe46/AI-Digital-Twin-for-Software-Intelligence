"""
Dependency detection service for Phase 6 Technical Debt Intelligence.

Scans known manifest file paths in a GitHub repository, parses declared dependencies,
and persists results to PostgreSQL. Read-only access is provided for the API layer.
"""

import logging
import json
import base64
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.project import Project
from app.models.evolution import DependencyManifest, DependencyItem

logger = logging.getLogger("digital_twin.dependency_service")

# Known dependency manifest paths and their ecosystem types
MANIFEST_DEFINITIONS = [
    {"path": "package.json",      "type": "npm"},
    {"path": "requirements.txt",  "type": "pip"},
    {"path": "Pipfile",           "type": "pip"},
    {"path": "setup.py",          "type": "pip"},
    {"path": "pyproject.toml",    "type": "pip"},
    {"path": "pom.xml",           "type": "maven"},
    {"path": "build.gradle",      "type": "gradle"},
    {"path": "Cargo.toml",        "type": "cargo"},
    {"path": "Gemfile",           "type": "gem"},
    {"path": "go.mod",            "type": "go"},
    {"path": "composer.json",     "type": "composer"},
]


def _parse_npm_deps(content: str) -> List[Dict[str, Any]]:
    """Parse package.json and return list of dependency dicts."""
    try:
        data = json.loads(content)
        deps = []
        for name, ver in data.get("dependencies", {}).items():
            deps.append({"name": name, "version_spec": str(ver), "is_dev": False})
        for name, ver in data.get("devDependencies", {}).items():
            deps.append({"name": name, "version_spec": str(ver), "is_dev": True})
        return deps
    except Exception:
        return []


def _parse_pip_requirements(content: str) -> List[Dict[str, Any]]:
    """Parse requirements.txt style file."""
    deps = []
    for line in content.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("-"):
            # Remove extras and environment markers
            name_ver = line.split(";")[0].strip()
            parts = name_ver.replace("==", ">=").split(">=")
            name = parts[0].strip()
            ver = parts[1].strip() if len(parts) > 1 else None
            if name:
                deps.append({"name": name, "version_spec": ver, "is_dev": False})
    return deps


def _parse_cargo_toml(content: str) -> List[Dict[str, Any]]:
    """Very simple TOML dependency parser for Cargo.toml."""
    deps = []
    in_deps = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped in ("[dependencies]", "[dev-dependencies]"):
            in_deps = True
            continue
        if stripped.startswith("[") and stripped not in ("[dependencies]", "[dev-dependencies]"):
            in_deps = False
        if in_deps and "=" in stripped and not stripped.startswith("#"):
            parts = stripped.split("=", 1)
            name = parts[0].strip()
            ver = parts[1].strip().strip('"').strip("'")
            deps.append({"name": name, "version_spec": ver, "is_dev": False})
    return deps


def _parse_generic(content: str, manifest_type: str) -> List[Dict[str, Any]]:
    """Fallback: return a count placeholder."""
    lines = [l.strip() for l in content.splitlines() if l.strip() and not l.strip().startswith("#")]
    return [{"name": f"{manifest_type}_dep_{i}", "version_spec": None, "is_dev": False}
            for i, _ in enumerate(lines[:50])]


def _parse_content(content: str, manifest_type: str) -> List[Dict[str, Any]]:
    if manifest_type == "npm":
        return _parse_npm_deps(content)
    elif manifest_type in ("pip",):
        return _parse_pip_requirements(content)
    elif manifest_type == "cargo":
        return _parse_cargo_toml(content)
    return _parse_generic(content, manifest_type)


class DependencyService:
    """
    Retrieves and persists dependency manifests and declared dependencies.
    Vulnerability analysis requires an external CVE/OSV database (not included).
    """

    @staticmethod
    async def scan_and_save_dependencies(project_id: int, db: Session) -> None:
        """
        Scans known manifest paths in the repository via GitHub API and persists results.
        Called during sync. Imports github_service lazily to avoid circular imports.
        """
        from app.services.github_service import github_service
        from app.models.project import Project

        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return

        owner = project.github_owner
        repo = project.github_repo

        # Clear existing manifests for this project
        db.query(DependencyManifest).filter(DependencyManifest.project_id == project_id).delete()

        now = datetime.now(timezone.utc)
        found_any = False

        for manifest_def in MANIFEST_DEFINITIONS:
            path = manifest_def["path"]
            mtype = manifest_def["type"]
            try:
                file_data = await github_service.get_file_content(owner, repo, path)
                if not file_data:
                    continue

                # GitHub API returns base64-encoded content
                raw_b64 = file_data.get("content", "")
                raw_bytes = base64.b64decode(raw_b64.replace("\n", ""))
                raw_content = raw_bytes.decode("utf-8", errors="replace")[:65536]

                parsed_deps = _parse_content(raw_content, mtype)

                manifest_obj = DependencyManifest(
                    project_id=project_id,
                    manifest_type=mtype,
                    file_path=path,
                    raw_content=raw_content[:4096],  # Store first 4KB only
                    detected_at=now,
                    dependency_count=len(parsed_deps),
                )
                db.add(manifest_obj)
                db.flush()  # Get the manifest ID

                for dep in parsed_deps:
                    item_obj = DependencyItem(
                        manifest_id=manifest_obj.id,
                        name=dep["name"][:255],
                        version_spec=str(dep["version_spec"])[:100] if dep["version_spec"] else None,
                        is_dev_dependency=dep.get("is_dev", False),
                    )
                    db.add(item_obj)

                found_any = True
                logger.info(f"Detected {len(parsed_deps)} dependencies in {path} ({mtype}) for {owner}/{repo}")

            except Exception as e:
                # Individual manifest failures are non-fatal
                logger.debug(f"Manifest {path} not found or could not be parsed for {owner}/{repo}: {e}")
                continue

        if found_any:
            try:
                db.commit()
            except Exception as e:
                db.rollback()
                logger.warning(f"Could not persist dependency manifests for project {project_id}: {e}")

    @staticmethod
    def get_project_dependencies(project_id: int, db: Session) -> Dict[str, Any]:
        """
        Returns all detected dependency manifests and their declared dependencies.
        """
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project with ID {project_id} not found.")

        manifests = (
            db.query(DependencyManifest)
            .filter(DependencyManifest.project_id == project_id)
            .all()
        )

        manifest_data: List[Dict[str, Any]] = []
        total_deps = 0

        for m in manifests:
            items = (
                db.query(DependencyItem)
                .filter(DependencyItem.manifest_id == m.id)
                .all()
            )
            item_data = [
                {
                    "name": item.name,
                    "version_spec": item.version_spec,
                    "is_dev_dependency": item.is_dev_dependency,
                }
                for item in items
            ]
            total_deps += len(item_data)
            manifest_data.append(
                {
                    "manifest_type": m.manifest_type,
                    "file_path": m.file_path,
                    "dependency_count": m.dependency_count or len(item_data),
                    "detected_at": m.detected_at.isoformat() if m.detected_at else None,
                    "items": item_data,
                }
            )

        return {
            "project_id": project_id,
            "has_sufficient_data": len(manifest_data) > 0,
            "total_manifests": len(manifest_data),
            "total_declared_dependencies": total_deps,
            "manifests": manifest_data,
            "limitation_notice": (
                "Dependencies are detected from known manifest file paths "
                "(package.json, requirements.txt, Pipfile, pom.xml, build.gradle, Cargo.toml, Gemfile, etc.). "
                "Vulnerability analysis requires an external CVE/OSV database and is not performed here."
            ),
        }


dependency_service = DependencyService()
