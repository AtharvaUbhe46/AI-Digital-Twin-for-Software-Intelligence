import logging
from typing import Dict, List, Set, Any, Tuple
from collections import defaultdict
from app.services.architecture.parser.base import ParsedEntity, ParsedRelation

logger = logging.getLogger("digital_twin.architecture.engine")


class ArchitectureEngine:
    """
    Computes module-level architecture graphs, coupling metrics (Afferent/Efferent/Instability),
    dependency hotspots, architectural bottlenecks, and unused dependencies.
    """

    @staticmethod
    def analyze_architecture(
        nodes: Dict[str, ParsedEntity],
        edges: List[ParsedRelation],
    ) -> Dict[str, Any]:
        # 1. Map files to modules
        file_to_module: Dict[str, str] = {}
        module_files: Dict[str, Set[str]] = defaultdict(set)

        for n_id, n in nodes.items():
            if n.entity_type == "file":
                mod = n.module or "root"
                file_to_module[n_id] = mod
                module_files[mod].add(n_id)

        # 2. Compute dependencies between files and modules
        file_incoming: Dict[str, Set[str]] = defaultdict(set)
        file_outgoing: Dict[str, Set[str]] = defaultdict(set)
        module_incoming: Dict[str, Set[str]] = defaultdict(set)
        module_outgoing: Dict[str, Set[str]] = defaultdict(set)

        internal_dep_count = 0
        external_dep_count = 0

        # Track which external packages are imported
        imported_packages: Set[str] = set()

        for edge in edges:
            src = edge.source_id
            tgt = edge.target_id

            # External package dependency
            if tgt.startswith("pkg:"):
                external_dep_count += 1
                pkg_name = tgt[4:].lower()
                imported_packages.add(pkg_name)
                continue

            # Internal file/module dependency
            if edge.rel_type in ("IMPORTS", "CALLS", "EXTENDS", "DEPENDS_ON"):
                src_file = src if src.startswith("file:") else (nodes[src].file_path and f"file:{nodes[src].file_path}")
                tgt_file = tgt if tgt.startswith("file:") else (nodes.get(tgt) and nodes[tgt].file_path and f"file:{nodes[tgt].file_path}")

                if src_file and tgt_file and src_file != tgt_file:
                    internal_dep_count += 1
                    file_outgoing[src_file].add(tgt_file)
                    file_incoming[tgt_file].add(src_file)

                    src_mod = file_to_module.get(src_file, "unknown")
                    tgt_mod = file_to_module.get(tgt_file, "unknown")
                    if src_mod != tgt_mod:
                        module_outgoing[src_mod].add(tgt_mod)
                        module_incoming[tgt_mod].add(src_mod)

        # 3. Calculate Module Coupling Metrics
        # Ca = Afferent Coupling (incoming, fan-in)
        # Ce = Efferent Coupling (outgoing, fan-out)
        # I  = Ce / (Ca + Ce) (0 = maximum stability, 1 = maximum instability)
        all_modules = sorted(list(set(list(module_files.keys()) + list(module_outgoing.keys()) + list(module_incoming.keys()))))
        module_metrics: List[Dict[str, Any]] = []

        for mod in all_modules:
            if not mod or mod in ("root", "unknown"):
                continue
            ca = len(module_incoming[mod])
            ce = len(module_outgoing[mod])
            total_coupling = ca + ce
            instability = round(ce / total_coupling, 2) if total_coupling > 0 else 0.0

            module_metrics.append({
                "module": mod,
                "afferent_coupling": ca,
                "efferent_coupling": ce,
                "instability": instability,
                "total_files": len(module_files[mod]),
                "dependents": sorted(list(module_incoming[mod])),
                "dependencies": sorted(list(module_outgoing[mod])),
            })

        # 4. Identify Hotspots and Bottlenecks
        # Hotspot: high fan-out (many dependencies, fragile)
        # Bottleneck: high fan-in (many modules depend on it, high blast radius)
        hotspots = []
        bottlenecks = []

        for m in module_metrics:
            if m["efferent_coupling"] >= 4 or (m["instability"] >= 0.8 and m["efferent_coupling"] >= 3):
                hotspots.append({
                    "module": m["module"],
                    "reason": f"High fan-out ({m['efferent_coupling']} outgoing dependencies). High instability ({m['instability']}).",
                    "severity": "HIGH" if m["efferent_coupling"] >= 6 else "MEDIUM",
                    "metric_value": m["efferent_coupling"],
                })
            if m["afferent_coupling"] >= 4:
                bottlenecks.append({
                    "module": m["module"],
                    "reason": f"Architectural critical path ({m['afferent_coupling']} incoming dependents). Changes risk cascading effects.",
                    "severity": "CRITICAL" if m["afferent_coupling"] >= 8 else "HIGH",
                    "metric_value": m["afferent_coupling"],
                })

        # 5. Identify Declared Packages and Unused Packages
        package_items = []
        unused_packages_count = 0

        for n_id, n in nodes.items():
            if n.entity_type == "package":
                pkg_name = n.name.lower()
                # Check if any file imports this package
                files_using = [
                    edge.source_id[5:] for edge in edges
                    if edge.target_id == n_id and edge.source_id.startswith("file:")
                ]
                # Also check normalized name in imported_packages
                is_used = len(files_using) > 0 or pkg_name in imported_packages or pkg_name.replace("-", "_") in imported_packages
                is_unused = not is_used and n.metadata.get("dep_type") != "dev"

                if is_unused:
                    unused_packages_count += 1

                package_items.append({
                    "name": n.name,
                    "version": n.metadata.get("version"),
                    "declared_in": n.metadata.get("declared_in", "manifest"),
                    "files_using": files_using,
                    "usage_count": len(files_using),
                    "is_unused": is_unused,
                })

        # Sort modules by total connections
        sorted_by_total = sorted(module_metrics, key=lambda x: (x["afferent_coupling"] + x["efferent_coupling"]), reverse=True)
        sorted_by_depended = sorted(module_metrics, key=lambda x: x["afferent_coupling"], reverse=True)

        return {
            "modules": module_metrics,
            "bottlenecks": bottlenecks,
            "hotspots": hotspots,
            "packages": package_items,
            "unused_packages_count": unused_packages_count,
            "internal_dependencies_count": internal_dep_count,
            "external_dependencies_count": external_dep_count,
            "file_incoming": {k: list(v) for k, v in file_incoming.items()},
            "file_outgoing": {k: list(v) for k, v in file_outgoing.items()},
            "most_connected_modules": [
                {"module": m["module"], "connections": m["afferent_coupling"] + m["efferent_coupling"]}
                for m in sorted_by_total[:5]
            ],
            "most_depended_modules": [
                {"module": m["module"], "dependents": m["afferent_coupling"]}
                for m in sorted_by_depended[:5]
            ],
        }
