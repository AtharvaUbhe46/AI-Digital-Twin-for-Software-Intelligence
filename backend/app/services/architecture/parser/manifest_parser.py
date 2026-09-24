import json
import os
import re
import logging
from typing import List, Tuple, Dict, Any
from app.services.architecture.parser.base import BaseParser, ParsedEntity, ParsedRelation

logger = logging.getLogger("digital_twin.parser.manifest")


class ManifestParser(BaseParser):
    SUPPORTED_FILES = ("package.json", "requirements.txt", "pyproject.toml", "setup.py")

    def supports(self, file_path: str) -> bool:
        filename = os.path.basename(file_path).lower()
        return filename in self.SUPPORTED_FILES or filename.startswith("requirements") and filename.endswith(".txt")

    def parse_file(
        self,
        file_path: str,
        content: str,
        project_root: str = ""
    ) -> Tuple[List[ParsedEntity], List[ParsedRelation]]:
        entities: List[ParsedEntity] = []
        relations: List[ParsedRelation] = []

        norm_path = file_path.replace("\\", "/").strip("/")
        if project_root:
            norm_root = project_root.replace("\\", "/").strip("/")
            if norm_path.startswith(norm_root):
                norm_path = norm_path[len(norm_root):].strip("/")

        filename = os.path.basename(norm_path).lower()
        file_id = f"file:{norm_path}"

        # 1. Manifest file entity
        entities.append(
            ParsedEntity(
                id=file_id,
                name=os.path.basename(norm_path),
                entity_type="file",
                file_path=norm_path,
                line_number=1,
                language="Manifest",
                module="manifest",
                metadata={"is_manifest": True}
            )
        )

        if filename == "package.json":
            self._parse_package_json(norm_path, file_id, content, entities, relations)
        elif "requirements" in filename and filename.endswith(".txt"):
            self._parse_requirements_txt(norm_path, file_id, content, entities, relations)
        elif filename == "pyproject.toml":
            self._parse_pyproject_toml(norm_path, file_id, content, entities, relations)

        return entities, relations

    def _parse_package_json(
        self,
        norm_path: str,
        file_id: str,
        content: str,
        entities: List[ParsedEntity],
        relations: List[ParsedRelation]
    ):
        try:
            data = json.loads(content)
        except Exception as e:
            logger.warning(f"Failed to parse package.json at {norm_path}: {e}")
            return

        pkg_groups = [
            ("dependencies", "runtime"),
            ("devDependencies", "dev"),
            ("peerDependencies", "peer"),
        ]

        for key, dep_type in pkg_groups:
            deps = data.get(key, {})
            if isinstance(deps, dict):
                for pkg_name, ver in deps.items():
                    pkg_id = f"pkg:{pkg_name}"
                    entities.append(
                        ParsedEntity(
                            id=pkg_id,
                            name=pkg_name,
                            entity_type="package",
                            file_path=norm_path,
                            language="JavaScript/TypeScript",
                            module="external",
                            metadata={
                                "version": str(ver),
                                "dep_type": dep_type,
                                "manager": "npm",
                                "declared_in": norm_path,
                            }
                        )
                    )
                    relations.append(
                        ParsedRelation(
                            source_id=file_id,
                            target_id=pkg_id,
                            rel_type="DEPENDS_ON",
                            confidence=1.0,
                            metadata={"dep_type": dep_type, "version": str(ver)}
                        )
                    )

    def _parse_requirements_txt(
        self,
        norm_path: str,
        file_id: str,
        content: str,
        entities: List[ParsedEntity],
        relations: List[ParsedRelation]
    ):
        for lineno, line in enumerate(content.splitlines(), 1):
            cleaned = line.strip()
            # Skip comments and flags
            if not cleaned or cleaned.startswith("#") or cleaned.startswith("-"):
                continue

            # e.g., fastapi>=0.110.0 or uvicorn[standard]>=0.28.0 or requests
            match = re.match(r"^([a-zA-Z0-9_\-\.]+)(?:\[[^\]]+\])?\s*([<>=!~]+.*)?$", cleaned)
            if match:
                pkg_name = match.group(1).lower()
                version_spec = match.group(2) or "any"
                pkg_id = f"pkg:{pkg_name}"

                entities.append(
                    ParsedEntity(
                        id=pkg_id,
                        name=pkg_name,
                        entity_type="package",
                        file_path=norm_path,
                        line_number=lineno,
                        language="Python",
                        module="external",
                        metadata={
                            "version": version_spec.strip(),
                            "dep_type": "runtime",
                            "manager": "pip",
                            "declared_in": norm_path,
                        }
                    )
                )
                relations.append(
                    ParsedRelation(
                        source_id=file_id,
                        target_id=pkg_id,
                        rel_type="DEPENDS_ON",
                        confidence=1.0,
                        metadata={"version": version_spec.strip(), "line_number": lineno}
                    )
                )

    def _parse_pyproject_toml(
        self,
        norm_path: str,
        file_id: str,
        content: str,
        entities: List[ParsedEntity],
        relations: List[ParsedRelation]
    ):
        # Basic regex parsing of dependencies in pyproject.toml without requiring tomli
        dep_section = False
        for lineno, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("["):
                dep_section = "dependencies" in stripped.lower()
                continue
            if dep_section and stripped and not stripped.startswith("#"):
                match = re.match(r"""^['"]?([a-zA-Z0-9_\-\.]+)['"]?\s*=\s*['"]?([^'",]+)['"]?""", stripped)
                if match:
                    pkg_name = match.group(1).lower()
                    ver = match.group(2)
                    pkg_id = f"pkg:{pkg_name}"
                    entities.append(
                        ParsedEntity(
                            id=pkg_id,
                            name=pkg_name,
                            entity_type="package",
                            file_path=norm_path,
                            line_number=lineno,
                            language="Python",
                            module="external",
                            metadata={"version": ver, "manager": "pyproject", "declared_in": norm_path}
                        )
                    )
                    relations.append(
                        ParsedRelation(
                            source_id=file_id,
                            target_id=pkg_id,
                            rel_type="DEPENDS_ON",
                            confidence=1.0,
                            metadata={"version": ver}
                        )
                    )
