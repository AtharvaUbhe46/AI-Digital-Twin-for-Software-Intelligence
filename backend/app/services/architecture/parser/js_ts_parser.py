import os
import re
import logging
from typing import List, Tuple, Dict, Any, Optional
from app.services.architecture.parser.base import BaseParser, ParsedEntity, ParsedRelation

logger = logging.getLogger("digital_twin.parser.jsts")


class JSTypeScriptParser(BaseParser):
    SUPPORTED_EXTENSIONS = (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")

    def supports(self, file_path: str) -> bool:
        return any(file_path.endswith(ext) for ext in self.SUPPORTED_EXTENSIONS)

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

        file_id = f"file:{norm_path}"
        module_name = self._path_to_module(norm_path)
        language = "TypeScript" if norm_path.endswith((".ts", ".tsx")) else "JavaScript"

        lines = content.splitlines()
        loc = len(lines)

        # 1. File entity
        entities.append(
            ParsedEntity(
                id=file_id,
                name=os.path.basename(norm_path),
                entity_type="file",
                file_path=norm_path,
                line_number=1,
                language=language,
                module=module_name,
                metadata={"loc": loc, "extension": os.path.splitext(norm_path)[1], "module": module_name}
            )
        )

        # 2. Extract Imports
        # import { a, b } from './path' or import Foo from 'package' or const x = require('...')
        import_es_pattern = re.compile(
            r"""import\s+(?:(?:\*\s+as\s+(\w+)|([\w\s{},*]+))\s+from\s+)?['"]([^'"]+)['"]""",
            re.MULTILINE
        )
        require_pattern = re.compile(r"""(?:const|let|var)\s+([\w\s{},:]+)\s*=\s*require\s*\(\s*['"]([^'"]+)['"]\s*\)""")

        for lineno, line in enumerate(lines, 1):
            # ES imports
            for match in import_es_pattern.finditer(line):
                star_alias, named_imports, target_path = match.groups()
                symbols = []
                if named_imports:
                    symbols = [s.strip() for s in named_imports.replace("{", "").replace("}", "").split(",") if s.strip()]
                elif star_alias:
                    symbols = [f"* as {star_alias}"]

                is_internal = target_path.startswith(".") or target_path.startswith("@/")
                target_id = f"mod:{target_path}" if is_internal else f"pkg:{target_path}"

                relations.append(
                    ParsedRelation(
                        source_id=file_id,
                        target_id=target_id,
                        rel_type="IMPORTS",
                        confidence=1.0,
                        metadata={
                            "import_path": target_path,
                            "symbols": symbols,
                            "line_number": lineno,
                            "is_internal": is_internal,
                        }
                    )
                )

            # CommonJS requires
            for match in require_pattern.finditer(line):
                assigned_var, target_path = match.groups()
                is_internal = target_path.startswith(".") or target_path.startswith("@/")
                target_id = f"mod:{target_path}" if is_internal else f"pkg:{target_path}"

                relations.append(
                    ParsedRelation(
                        source_id=file_id,
                        target_id=target_id,
                        rel_type="IMPORTS",
                        confidence=0.9,
                        metadata={
                            "import_path": target_path,
                            "assigned_var": assigned_var.strip(),
                            "line_number": lineno,
                            "is_internal": is_internal,
                        }
                    )
                )

        # 3. Extract Classes & Interfaces
        class_pattern = re.compile(r"""export\s+(?:default\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?""")
        plain_class_pattern = re.compile(r"""class\s+(\w+)(?:\s+extends\s+(\w+))?""")
        interface_pattern = re.compile(r"""export\s+(?:default\s+)?interface\s+(\w+)(?:\s+extends\s+(\w+))?""")

        found_classes = set()
        for lineno, line in enumerate(lines, 1):
            # Classes
            for match in class_pattern.finditer(line):
                cls_name, base_name = match.groups()
                if cls_name and cls_name not in found_classes:
                    found_classes.add(cls_name)
                    cls_id = f"class:{norm_path}:{cls_name}"
                    entities.append(
                        ParsedEntity(
                            id=cls_id,
                            name=cls_name,
                            entity_type="class",
                            file_path=norm_path,
                            line_number=lineno,
                            language=language,
                            module=module_name,
                            metadata={"base": base_name, "is_exported": True}
                        )
                    )
                    relations.append(ParsedRelation(source_id=file_id, target_id=cls_id, rel_type="CONTAINS"))
                    relations.append(ParsedRelation(source_id=file_id, target_id=cls_id, rel_type="EXPORTS"))
                    if base_name:
                        relations.append(ParsedRelation(source_id=cls_id, target_id=f"class:{base_name}", rel_type="EXTENDS"))

            for match in plain_class_pattern.finditer(line):
                cls_name, base_name = match.groups()
                if cls_name and cls_name not in found_classes:
                    found_classes.add(cls_name)
                    cls_id = f"class:{norm_path}:{cls_name}"
                    entities.append(
                        ParsedEntity(
                            id=cls_id,
                            name=cls_name,
                            entity_type="class",
                            file_path=norm_path,
                            line_number=lineno,
                            language=language,
                            module=module_name,
                            metadata={"base": base_name, "is_exported": False}
                        )
                    )
                    relations.append(ParsedRelation(source_id=file_id, target_id=cls_id, rel_type="CONTAINS"))
                    if base_name:
                        relations.append(ParsedRelation(source_id=cls_id, target_id=f"class:{base_name}", rel_type="EXTENDS"))

            # TypeScript Interfaces
            for match in interface_pattern.finditer(line):
                iface_name, base_name = match.groups()
                iface_id = f"interface:{norm_path}:{iface_name}"
                entities.append(
                    ParsedEntity(
                        id=iface_id,
                        name=iface_name,
                        entity_type="class",
                        file_path=norm_path,
                        line_number=lineno,
                        language=language,
                        module=module_name,
                        metadata={"is_interface": True, "base": base_name}
                    )
                )
                relations.append(ParsedRelation(source_id=file_id, target_id=iface_id, rel_type="DEFINES"))

        # 4. Extract Functions / React Components
        func_patterns = [
            # export const Name: React.FC<Props> = ... or export const name = (...) =>
            (re.compile(r"""export\s+const\s+(\w+)\s*(?::\s*[\w.<>]+)?\s*=\s*(?:async\s*)?\("""), True),
            # const Name: React.FC<Props> = ... or const name = (...) =>
            (re.compile(r"""(?:const|let|var)\s+(\w+)\s*(?::\s*[\w.<>]+)?\s*=\s*(?:async\s*)?\("""), False),
            # export function name(...)
            (re.compile(r"""export\s+(?:default\s+)?(?:async\s+)?function\s+(\w+)\s*\("""), True),
            # function name(...)
            (re.compile(r"""(?:async\s+)?function\s+(\w+)\s*\("""), False),
        ]

        found_funcs = set()
        for lineno, line in enumerate(lines, 1):
            for pattern, is_exported in func_patterns:
                for match in pattern.finditer(line):
                    func_name = match.group(1)
                    if func_name and func_name not in found_funcs and func_name not in found_classes:
                        # Exclude common JS keywords
                        if func_name in ("if", "for", "while", "switch", "catch", "return"):
                            continue
                        found_funcs.add(func_name)
                        is_component = func_name[0].isupper() and (norm_path.endswith((".tsx", ".jsx")) or "React" in line)
                        func_id = f"func:{norm_path}:{func_name}"
                        entities.append(
                            ParsedEntity(
                                id=func_id,
                                name=func_name,
                                entity_type="function",
                                file_path=norm_path,
                                line_number=lineno,
                                language=language,
                                module=module_name,
                                metadata={
                                    "is_component": is_component,
                                    "is_exported": is_exported,
                                }
                            )
                        )
                        relations.append(ParsedRelation(source_id=file_id, target_id=func_id, rel_type="CONTAINS"))
                        if is_exported:
                            relations.append(ParsedRelation(source_id=file_id, target_id=func_id, rel_type="EXPORTS"))

        # 5. Extract API client calls (e.g., apiClient.get('/health'), fetch('/api/...'))
        api_call_pattern = re.compile(r"""(?:apiClient|axios|client)\.(get|post|put|delete|patch)\s*(?:<[^>]+>)?\s*\(\s*[`'"]([^`'"]+)[`'"]""")
        for lineno, line in enumerate(lines, 1):
            for match in api_call_pattern.finditer(line):
                method, endpoint_path = match.groups()
                endpoint_id = f"endpoint:{method.upper()}:{endpoint_path}"
                relations.append(
                    ParsedRelation(
                        source_id=file_id,
                        target_id=endpoint_id,
                        rel_type="CALLS",
                        confidence=0.85,
                        metadata={"http_method": method.upper(), "path": endpoint_path, "line_number": lineno}
                    )
                )

        return entities, relations

    @staticmethod
    def _path_to_module(path: str) -> str:
        # e.g., "frontend/src/services/api.ts" -> "src.services.api"
        base, _ = os.path.splitext(path)
        parts = base.split("/")
        if parts and parts[0] in ("frontend", "client"):
            parts = parts[1:]
        return ".".join(parts)
