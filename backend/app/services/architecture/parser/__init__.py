import os
import logging
from typing import List, Tuple, Dict, Any, Optional
from app.services.architecture.parser.base import BaseParser, ParsedEntity, ParsedRelation
from app.services.architecture.parser.python_parser import PythonASTParser
from app.services.architecture.parser.js_ts_parser import JSTypeScriptParser
from app.services.architecture.parser.manifest_parser import ManifestParser

logger = logging.getLogger("digital_twin.parser")


class RepositoryParserEngine:
    DEFAULT_EXCLUDES = {
        ".git",
        "node_modules",
        "venv",
        ".venv",
        "env",
        "__pycache__",
        ".pytest_cache",
        "dist",
        "build",
        ".next",
        "coverage",
        ".idea",
        ".vscode",
    }

    def __init__(self):
        self.parsers: List[BaseParser] = [
            PythonASTParser(),
            JSTypeScriptParser(),
            ManifestParser(),
        ]

    def parse_file(
        self,
        file_path: str,
        content: str,
        project_root: str = ""
    ) -> Tuple[List[ParsedEntity], List[ParsedRelation]]:
        """Finds matching parser and extracts entities and relations."""
        for parser in self.parsers:
            if parser.supports(file_path):
                return parser.parse_file(file_path, content, project_root=project_root)
        return [], []

    def parse_directory(
        self,
        dir_path: str,
        max_files: int = 1500,
        exclude_dirs: Optional[set] = None,
        repo_display_name: Optional[str] = None
    ) -> Tuple[List[ParsedEntity], List[ParsedRelation]]:
        """
        Statically analyzes a local directory tree.
        Extracts repository, directory, and file nodes, plus AST entities and relations.
        """
        excludes = exclude_dirs or self.DEFAULT_EXCLUDES
        all_entities: List[ParsedEntity] = []
        all_relations: List[ParsedRelation] = []

        norm_root = os.path.abspath(dir_path).replace("\\", "/")
        repo_name = repo_display_name or os.path.basename(norm_root)
        repo_id = f"repo:{repo_name}"

        # Repository node
        all_entities.append(
            ParsedEntity(
                id=repo_id,
                name=repo_name,
                entity_type="repository",
                file_path="",
                language="Multi-language",
                module="root",
                metadata={"root_path": norm_root}
            )
        )

        seen_dirs = set()
        file_count = 0

        for root, dirs, files in os.walk(norm_root):
            # Prune excluded directories safely
            dirs[:] = [d for d in dirs if d not in excludes and not d.startswith(".")]

            rel_dir = os.path.relpath(root, norm_root).replace("\\", "/").strip("./")
            if rel_dir and rel_dir != ".":
                dir_id = f"dir:{rel_dir}"
                if dir_id not in seen_dirs:
                    seen_dirs.add(dir_id)
                    parent_rel = os.path.dirname(rel_dir)
                    parent_id = f"dir:{parent_rel}" if parent_rel and parent_rel != "." else repo_id
                    all_entities.append(
                        ParsedEntity(
                            id=dir_id,
                            name=os.path.basename(rel_dir),
                            entity_type="directory",
                            file_path=rel_dir,
                            module=rel_dir.replace("/", "."),
                            metadata={"dir_path": rel_dir}
                        )
                    )
                    all_relations.append(
                        ParsedRelation(source_id=parent_id, target_id=dir_id, rel_type="CONTAINS")
                    )

            for file in files:
                if file_count >= max_files:
                    logger.warning(f"Analysis file limit reached ({max_files}). Halting directory walk.")
                    break

                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, norm_root).replace("\\", "/")

                # Check if supported
                if not any(p.supports(file) for p in self.parsers):
                    continue

                # Safely read content
                try:
                    with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                except Exception as e:
                    logger.warning(f"Could not read {full_path}: {e}")
                    continue

                parsed_ents, parsed_rels = self.parse_file(rel_path, content, project_root=norm_root)
                if parsed_ents:
                    file_count += 1
                    file_id = f"file:{rel_path}"
                    parent_dir_rel = os.path.dirname(rel_path)
                    parent_dir_id = f"dir:{parent_dir_rel}" if parent_dir_rel and parent_dir_rel != "." else repo_id
                    all_relations.append(
                        ParsedRelation(source_id=parent_dir_id, target_id=file_id, rel_type="CONTAINS")
                    )
                    all_entities.extend(parsed_ents)
                    all_relations.extend(parsed_rels)

        return all_entities, all_relations


parser_engine = RepositoryParserEngine()

__all__ = [
    "BaseParser",
    "ParsedEntity",
    "ParsedRelation",
    "PythonASTParser",
    "JSTypeScriptParser",
    "ManifestParser",
    "RepositoryParserEngine",
    "parser_engine",
]
