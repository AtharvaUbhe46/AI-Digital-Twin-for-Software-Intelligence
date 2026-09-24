import hashlib
from typing import List, Dict, Set, Any
from collections import defaultdict


class CycleDetector:
    """
    Detects circular dependencies in directed dependency graphs.
    Uses DFS-based cycle extraction on Strongly Connected Components (SCC).
    """

    @staticmethod
    def detect_cycles(
        adjacency_list: Dict[str, Set[str]],
        max_cycles: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Finds circular dependencies given an adjacency list of source_id -> set of target_ids.
        Returns a list of cycle dictionaries with participants, path, and severity.
        """
        cycles: List[Dict[str, Any]] = []
        visited_cycles = set()

        # Step 1: Tarjan's algorithm for Strongly Connected Components (SCCs)
        sccs = CycleDetector._tarjan_scc(adjacency_list)

        # Step 2: For each SCC with > 1 node, extract elementary cycles
        for scc in sccs:
            if len(scc) < 2:
                # Check for direct self-loop
                node = next(iter(scc))
                if node in adjacency_list.get(node, set()):
                    path = [node, node]
                    cycle_sig = f"{node}->{node}"
                    if cycle_sig not in visited_cycles:
                        visited_cycles.add(cycle_sig)
                        cycles.append(CycleDetector._format_cycle(path))
                continue

            # Subgraph for this SCC
            subgraph = {u: adjacency_list.get(u, set()) & scc for u in scc}
            scc_nodes = sorted(list(scc))

            # Simple DFS cycle finder within this SCC
            for start_node in scc_nodes:
                if len(cycles) >= max_cycles:
                    break
                path = [start_node]
                visited = {start_node}
                CycleDetector._dfs_find_cycles(
                    curr=start_node,
                    start=start_node,
                    subgraph=subgraph,
                    path=path,
                    visited=visited,
                    cycles=cycles,
                    visited_cycles=visited_cycles,
                    max_cycles=max_cycles,
                    max_depth=12,
                )

        # Sort cycles by length (shortest/tightest circular deps first)
        cycles.sort(key=lambda x: (x["length"], x["severity"]))
        return cycles

    @staticmethod
    def _dfs_find_cycles(
        curr: str,
        start: str,
        subgraph: Dict[str, Set[str]],
        path: List[str],
        visited: Set[str],
        cycles: List[Dict[str, Any]],
        visited_cycles: Set[str],
        max_cycles: int,
        max_depth: int
    ):
        if len(cycles) >= max_cycles or len(path) > max_depth:
            return

        for neighbor in sorted(list(subgraph.get(curr, set()))):
            if neighbor == start and len(path) >= 2:
                cycle_path = path + [start]
                # Canonical representation of cycle
                cycle_nodes = sorted(path)
                cycle_sig = ":".join(cycle_nodes)
                if cycle_sig not in visited_cycles:
                    visited_cycles.add(cycle_sig)
                    cycles.append(CycleDetector._format_cycle(cycle_path))
                    if len(cycles) >= max_cycles:
                        return
            elif neighbor not in visited:
                visited.add(neighbor)
                path.append(neighbor)
                CycleDetector._dfs_find_cycles(
                    curr=neighbor,
                    start=start,
                    subgraph=subgraph,
                    path=path,
                    visited=visited,
                    cycles=cycles,
                    visited_cycles=visited_cycles,
                    max_cycles=max_cycles,
                    max_depth=max_depth
                )
                path.pop()
                visited.remove(neighbor)

    @staticmethod
    def _tarjan_scc(adj: Dict[str, Set[str]]) -> List[Set[str]]:
        """Finds all strongly connected components using Tarjan's algorithm."""
        index = 0
        indices = {}
        lowlinks = {}
        on_stack = set()
        stack = []
        sccs = []

        all_nodes = set(adj.keys())
        for targets in adj.values():
            all_nodes.update(targets)

        def strongconnect(v):
            nonlocal index
            indices[v] = index
            lowlinks[v] = index
            index += 1
            stack.append(v)
            on_stack.add(v)

            for w in adj.get(v, set()):
                if w not in indices:
                    strongconnect(w)
                    lowlinks[v] = min(lowlinks[v], lowlinks[w])
                elif w in on_stack:
                    lowlinks[v] = min(lowlinks[v], indices[w])

            if lowlinks[v] == indices[v]:
                scc = set()
                while True:
                    w = stack.pop()
                    on_stack.remove(w)
                    scc.add(w)
                    if w == v:
                        break
                sccs.append(scc)

        for node in all_nodes:
            if node not in indices:
                strongconnect(node)

        return sccs

    @staticmethod
    def _format_cycle(path: List[str]) -> Dict[str, Any]:
        unique_nodes = path[:-1]
        length = len(unique_nodes)

        # Calculate severity based on cycle tightness
        if length <= 2:
            severity = "CRITICAL"
        elif length == 3:
            severity = "HIGH"
        elif length <= 5:
            severity = "MEDIUM"
        else:
            severity = "LOW"

        # Extract file paths if prefixed with "file:"
        affected_files = []
        for n in unique_nodes:
            if n.startswith("file:"):
                affected_files.append(n[5:])
            elif n.startswith("mod:"):
                affected_files.append(n[4:])
            else:
                affected_files.append(n)

        # Deterministic ID
        cycle_sig = "->".join(sorted(unique_nodes))
        cycle_id = hashlib.sha256(cycle_sig.encode()).hexdigest()[:12]

        explanation = (
            f"Circular dependency detected between {length} entities: "
            + " → ".join(affected_files[:4])
            + ("..." if len(affected_files) > 4 else "")
            + f" → {affected_files[0]}. "
            + "This causes tight architectural coupling, prevents modular compilation, and can cause runtime recursion."
        )

        return {
            "cycle_id": f"cycle_{cycle_id}",
            "length": length,
            "nodes": unique_nodes,
            "path": path,
            "affected_files": affected_files,
            "severity": severity,
            "explanation": explanation,
        }
