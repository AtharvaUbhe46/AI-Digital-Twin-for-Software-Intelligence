import logging
from typing import List, Dict, Set, Tuple, Any, Optional
from app.services.architecture.parser.base import ParsedEntity, ParsedRelation

logger = logging.getLogger("digital_twin.graph.builder")


class KnowledgeGraphBuilder:
    """
    Assembles raw ParsedEntity and ParsedRelation objects into a clean,
    resolved, and cross-referenced Knowledge Graph.
    """

    @staticmethod
    def build_graph(
        entities: List[ParsedEntity],
        relations: List[ParsedRelation],
        project_id: int
    ) -> Tuple[Dict[str, ParsedEntity], List[ParsedRelation]]:
        """
        Deduplicates entities, resolves relative and module import targets,
        and ensures edge integrity.
        """
        node_map: Dict[str, ParsedEntity] = {}
        for entity in entities:
            if entity.id not in node_map:
                node_map[entity.id] = entity

        # Index existing files for resolving imports
        file_paths = {e.file_path: e.id for e in entities if e.entity_type == "file" and e.file_path}
        module_to_file = {}
        for f_path, f_id in file_paths.items():
            # Derive various module representations
            # e.g., "backend/app/api/v1/router.py" -> "app.api.v1.router", "backend.app.api.v1.router"
            parts = f_path.replace(".py", "").replace(".ts", "").replace(".tsx", "").replace(".js", "").split("/")
            dot_path = ".".join(parts)
            module_to_file[dot_path] = f_id
            if len(parts) > 1 and parts[0] in ("backend", "frontend", "src", "app"):
                module_to_file[".".join(parts[1:])] = f_id
                if len(parts) > 2 and parts[1] == "app":
                    module_to_file[".".join(parts[2:])] = f_id

        resolved_relations: List[ParsedRelation] = []
        seen_edges = set()

        for rel in relations:
            target_id = rel.target_id

            # If target is a module import, attempt resolution to existing file
            if target_id.startswith("mod:"):
                raw_mod = target_id[4:]
                resolved_file_id = KnowledgeGraphBuilder._resolve_module(raw_mod, rel.source_id, module_to_file, file_paths)
                if resolved_file_id:
                    target_id = resolved_file_id

            # Ensure target node exists or create a synthetic stub node
            if target_id not in node_map:
                node_map[target_id] = KnowledgeGraphBuilder._create_stub_node(target_id)

            edge_key = (rel.source_id, target_id, rel.rel_type)
            if edge_key not in seen_edges and rel.source_id != target_id:
                seen_edges.add(edge_key)
                resolved_relations.append(
                    ParsedRelation(
                        source_id=rel.source_id,
                        target_id=target_id,
                        rel_type=rel.rel_type,
                        confidence=rel.confidence,
                        metadata=rel.metadata,
                    )
                )

        return node_map, resolved_relations

    @staticmethod
    def _resolve_module(
        raw_mod: str,
        source_id: str,
        module_to_file: Dict[str, str],
        file_paths: Dict[str, str]
    ) -> Optional[str]:
        # Direct module lookup
        if raw_mod in module_to_file:
            return module_to_file[raw_mod]

        # Handle relative imports: e.g., source="file:backend/app/api/v1/health.py", raw_mod="..core.database"
        if raw_mod.startswith(".") and source_id.startswith("file:"):
            source_file = source_id[5:]
            source_dir = "/".join(source_file.split("/")[:-1])
            # Count leading dots
            level = len(raw_mod) - len(raw_mod.lstrip("."))
            mod_part = raw_mod.lstrip(".")
            dir_parts = source_dir.split("/") if source_dir else []
            if len(dir_parts) >= level:
                target_dir = "/".join(dir_parts[:len(dir_parts) - level + 1])
                candidate_rel = f"{target_dir}/{mod_part.replace('.', '/')}"
                for ext in (".py", ".ts", ".tsx", ".js", "/__init__.py", "/index.ts"):
                    candidate = f"{candidate_rel}{ext}".strip("/")
                    if candidate in file_paths:
                        return file_paths[candidate]

        # Try matching base names
        mod_tail = raw_mod.split(".")[-1]
        for f_path, f_id in file_paths.items():
            base_no_ext = f_path.split("/")[-1].split(".")[0]
            if base_no_ext == mod_tail and raw_mod.replace(".", "/") in f_path:
                return f_id

        return None

    @staticmethod
    def _create_stub_node(node_id: str) -> ParsedEntity:
        """Creates a synthetic placeholder node for external or unresolved dependencies."""
        if node_id.startswith("pkg:"):
            pkg_name = node_id[4:]
            return ParsedEntity(
                id=node_id,
                name=pkg_name,
                entity_type="package",
                file_path="",
                module="external",
                metadata={"is_external": True, "name": pkg_name}
            )
        elif node_id.startswith("class:"):
            class_name = node_id.split(":")[-1]
            return ParsedEntity(
                id=node_id,
                name=class_name,
                entity_type="class",
                file_path="",
                module="external_or_builtin",
                metadata={"is_stub": True}
            )
        elif node_id.startswith("mod:"):
            mod_name = node_id[4:]
            return ParsedEntity(
                id=node_id,
                name=mod_name,
                entity_type="module",
                file_path="",
                module=mod_name,
                metadata={"is_external": True}
            )
        else:
            return ParsedEntity(
                id=node_id,
                name=node_id.split(":")[-1],
                entity_type="entity",
                file_path="",
                metadata={"is_stub": True}
            )
