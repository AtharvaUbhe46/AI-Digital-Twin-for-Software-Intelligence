import ast
import os
import logging
from typing import List, Tuple, Dict, Any, Optional
from app.services.architecture.parser.base import BaseParser, ParsedEntity, ParsedRelation

logger = logging.getLogger("digital_twin.parser.python")


class PythonASTParser(BaseParser):
    def supports(self, file_path: str) -> bool:
        return file_path.endswith(".py")

    def parse_file(
        self,
        file_path: str,
        content: str,
        project_root: str = ""
    ) -> Tuple[List[ParsedEntity], List[ParsedRelation]]:
        entities: List[ParsedEntity] = []
        relations: List[ParsedRelation] = []

        # Normalize file path
        norm_path = file_path.replace("\\", "/").strip("/")
        if project_root:
            norm_root = project_root.replace("\\", "/").strip("/")
            if norm_path.startswith(norm_root):
                norm_path = norm_path[len(norm_root):].strip("/")

        file_id = f"file:{norm_path}"
        module_name = self._path_to_module(norm_path)

        # 1. File entity
        line_count = len(content.splitlines())
        entities.append(
            ParsedEntity(
                id=file_id,
                name=os.path.basename(norm_path),
                entity_type="file",
                file_path=norm_path,
                line_number=1,
                language="Python",
                module=module_name,
                metadata={
                    "loc": line_count,
                    "extension": ".py",
                    "module": module_name,
                }
            )
        )

        try:
            tree = ast.parse(content, filename=norm_path)
        except SyntaxError as e:
            logger.warning(f"Syntax error parsing {norm_path} at line {e.lineno}: {e.msg}")
            entities[0].metadata["parse_error"] = str(e)
            return entities, relations
        except Exception as e:
            logger.warning(f"Failed to parse AST for {norm_path}: {e}")
            entities[0].metadata["parse_error"] = str(e)
            return entities, relations

        # Walk AST
        visitor = _PythonVisitor(file_id=file_id, file_path=norm_path, module_name=module_name)
        visitor.visit(tree)

        entities.extend(visitor.entities)
        relations.extend(visitor.relations)

        return entities, relations

    @staticmethod
    def _path_to_module(path: str) -> str:
        # e.g., "backend/app/api/v1/endpoints/projects.py" -> "app.api.v1.endpoints.projects"
        cleaned = path.replace(".py", "")
        parts = cleaned.split("/")
        # If starts with backend/ or src/, trim for canonical module name
        if parts and parts[0] in ("backend", "src", "lib"):
            parts = parts[1:]
        return ".".join(parts)


class _PythonVisitor(ast.NodeVisitor):
    def __init__(self, file_id: str, file_path: str, module_name: str):
        self.file_id = file_id
        self.file_path = file_path
        self.module_name = module_name

        self.entities: List[ParsedEntity] = []
        self.relations: List[ParsedRelation] = []

        self.current_class: Optional[str] = None
        self.current_class_id: Optional[str] = None
        self.current_function: Optional[str] = None
        self.current_function_id: Optional[str] = None

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            imported_mod = alias.name
            target_id = f"mod:{imported_mod}"
            self.relations.append(
                ParsedRelation(
                    source_id=self.file_id,
                    target_id=target_id,
                    rel_type="IMPORTS",
                    confidence=1.0,
                    metadata={
                        "imported_name": imported_mod,
                        "alias": alias.asname,
                        "line_number": node.lineno,
                        "is_internal": imported_mod.startswith("app") or imported_mod.startswith(self.module_name.split(".")[0]),
                    }
                )
            )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        mod_prefix = node.module or ""
        # Handle relative imports
        if node.level > 0:
            rel_dots = "." * node.level
            imported_mod = f"{rel_dots}{mod_prefix}"
        else:
            imported_mod = mod_prefix

        symbols = [alias.name for alias in node.names]
        target_id = f"mod:{imported_mod}"

        is_internal = (
            node.level > 0 or
            imported_mod.startswith("app") or
            imported_mod.startswith(self.module_name.split(".")[0])
        )

        self.relations.append(
            ParsedRelation(
                source_id=self.file_id,
                target_id=target_id,
                rel_type="IMPORTS",
                confidence=1.0,
                metadata={
                    "module": imported_mod,
                    "symbols": symbols,
                    "level": node.level,
                    "line_number": node.lineno,
                    "is_internal": is_internal,
                }
            )
        )
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        class_id = f"class:{self.file_path}:{node.name}"
        docstring = ast.get_docstring(node)

        # Base classes (inheritance)
        base_names = []
        for b in node.bases:
            if isinstance(b, ast.Name):
                base_names.append(b.id)
            elif isinstance(b, ast.Attribute):
                base_names.append(f"{self._get_attribute_name(b)}")

        class_entity = ParsedEntity(
            id=class_id,
            name=node.name,
            entity_type="class",
            file_path=self.file_path,
            line_number=node.lineno,
            language="Python",
            module=self.module_name,
            metadata={
                "bases": base_names,
                "docstring": docstring[:200] if docstring else None,
                "end_line": getattr(node, "end_lineno", node.lineno),
            }
        )
        self.entities.append(class_entity)

        # File CONTAINS Class
        self.relations.append(
            ParsedRelation(
                source_id=self.file_id,
                target_id=class_id,
                rel_type="CONTAINS",
                confidence=1.0,
            )
        )

        # Inheritance: Class EXTENDS Base
        for b_name in base_names:
            self.relations.append(
                ParsedRelation(
                    source_id=class_id,
                    target_id=f"class:{b_name}",
                    rel_type="EXTENDS",
                    confidence=0.9,
                    metadata={"base_name": b_name}
                )
            )

        prev_class = self.current_class
        prev_class_id = self.current_class_id
        self.current_class = node.name
        self.current_class_id = class_id

        self.generic_visit(node)

        self.current_class = prev_class
        self.current_class_id = prev_class_id

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._handle_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._handle_function(node, is_async=True)

    def _handle_function(self, node, is_async: bool):
        params = [arg.arg for arg in node.args.args]
        docstring = ast.get_docstring(node)

        if self.current_class:
            entity_type = "method"
            func_id = f"method:{self.file_path}:{self.current_class}.{node.name}"
            parent_id = self.current_class_id
        else:
            entity_type = "function"
            func_id = f"func:{self.file_path}:{node.name}"
            parent_id = self.file_id

        func_entity = ParsedEntity(
            id=func_id,
            name=node.name,
            entity_type=entity_type,
            file_path=self.file_path,
            line_number=node.lineno,
            language="Python",
            module=self.module_name,
            metadata={
                "parameters": params,
                "is_async": is_async,
                "class_name": self.current_class,
                "docstring": docstring[:200] if docstring else None,
                "end_line": getattr(node, "end_lineno", node.lineno),
            }
        )
        self.entities.append(func_entity)

        # Parent CONTAINS Function/Method
        self.relations.append(
            ParsedRelation(
                source_id=parent_id,
                target_id=func_id,
                rel_type="CONTAINS",
                confidence=1.0,
            )
        )

        # Check for API Route decorators (e.g., @router.get("/path"), @app.post("/path"))
        for decorator in node.decorator_list:
            route_info = self._extract_route_info(decorator)
            if route_info:
                http_method, route_path = route_info
                endpoint_id = f"endpoint:{http_method}:{route_path}"

                # API endpoint entity
                endpoint_entity = ParsedEntity(
                    id=endpoint_id,
                    name=f"{http_method} {route_path}",
                    entity_type="api_endpoint",
                    file_path=self.file_path,
                    line_number=node.lineno,
                    language="Python",
                    module=self.module_name,
                    metadata={
                        "http_method": http_method,
                        "path": route_path,
                        "handler": node.name,
                    }
                )
                self.entities.append(endpoint_entity)

                # Endpoint ROUTES_TO handler function
                self.relations.append(
                    ParsedRelation(
                        source_id=endpoint_id,
                        target_id=func_id,
                        rel_type="ROUTES_TO",
                        confidence=1.0,
                        metadata={"http_method": http_method, "path": route_path}
                    )
                )
                # File EXPOSES Endpoint
                self.relations.append(
                    ParsedRelation(
                        source_id=self.file_id,
                        target_id=endpoint_id,
                        rel_type="EXPOSES",
                        confidence=1.0,
                    )
                )

        prev_func = self.current_function
        prev_func_id = self.current_function_id
        self.current_function = node.name
        self.current_function_id = func_id

        self.generic_visit(node)

        self.current_function = prev_func
        self.current_function_id = prev_func_id

    def visit_Call(self, node: ast.Call):
        # Detect function calls
        callee_name = None
        if isinstance(node.func, ast.Name):
            callee_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            callee_name = node.func.attr

        if callee_name and self.current_function_id:
            # Skip built-in language primitives for cleaner graph
            if callee_name not in ("print", "len", "range", "isinstance", "int", "str", "list", "dict", "set", "super"):
                target_id = f"call:{callee_name}"
                self.relations.append(
                    ParsedRelation(
                        source_id=self.current_function_id,
                        target_id=target_id,
                        rel_type="CALLS",
                        confidence=0.8,
                        metadata={
                            "callee": callee_name,
                            "line_number": node.lineno,
                        }
                    )
                )
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        # Extract top-level module constants/variables
        if self.current_class is None and self.current_function is None:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    var_name = target.id
                    if var_name.isupper() or var_name in ("router", "api_router", "settings", "engine"):
                        var_id = f"var:{self.file_path}:{var_name}"
                        self.entities.append(
                            ParsedEntity(
                                id=var_id,
                                name=var_name,
                                entity_type="variable",
                                file_path=self.file_path,
                                line_number=node.lineno,
                                language="Python",
                                module=self.module_name,
                                metadata={"is_constant": var_name.isupper()}
                            )
                        )
                        self.relations.append(
                            ParsedRelation(
                                source_id=self.file_id,
                                target_id=var_id,
                                rel_type="DEFINES",
                                confidence=1.0,
                            )
                        )
        self.generic_visit(node)

    def _extract_route_info(self, decorator: ast.AST) -> Optional[Tuple[str, str]]:
        """
        Detects route decorators:
        @router.get('/path')
        @app.post('/path')
        @api_router.delete('/path')
        """
        if isinstance(decorator, ast.Call):
            func = decorator.func
            if isinstance(func, ast.Attribute):
                attr_name = func.attr.upper()
                if attr_name in ("GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"):
                    # Check first arg for route path
                    if decorator.args and isinstance(decorator.args[0], ast.Constant) and isinstance(decorator.args[0].value, str):
                        return attr_name, decorator.args[0].value
        return None

    def _get_attribute_name(self, node: ast.Attribute) -> str:
        parts = []
        curr = node
        while isinstance(curr, ast.Attribute):
            parts.append(curr.attr)
            curr = curr.value
        if isinstance(curr, ast.Name):
            parts.append(curr.id)
        return ".".join(reversed(parts))
