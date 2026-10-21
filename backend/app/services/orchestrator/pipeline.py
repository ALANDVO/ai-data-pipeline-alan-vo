import logging
from typing import List, Dict, Any, Optional, Set
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

class DAGValidator:
    '''Validates pipeline DAGs: checks for cycles, orphaned nodes, and produces topological order.'''

    def validate(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> Dict[str, Any]:
        errors: List[str] = []
        node_ids = {n["id"] for n in nodes}

        for e in edges:
            if e["source"] not in node_ids:
                errors.append(f"Edge {e['id']} references unknown source node {e['source']}")
            if e["target"] not in node_ids:
                errors.append(f"Edge {e['id']} references unknown target node {e['target']}")

        indegree = defaultdict(int)
        adj: Dict[str, List[str]] = defaultdict(list)
        for e in edges:
            if e["source"] in node_ids and e["target"] in node_ids:
                adj[e["source"]].append(e["target"])
                indegree[e["target"]] += 1

        for nid in node_ids:
            if indegree[nid] == 0 and nid not in adj:
                pass
            elif nid not in indegree and nid not in adj:
                errors.append(f"Node {nid} is isolated (no incoming or outgoing edges)")

        topo = self._topological_sort(node_ids, adj, indegree)
        if topo is None:
            errors.append("DAG contains a cycle")
            return {"valid": False, "errors": errors, "topological_order": [], "topological_levels": []}

        levels = self.get_execution_groups(nodes, edges)
        return {"valid": len(errors) == 0, "errors": errors, "topological_order": topo, "topological_levels": levels}

    def _topological_sort(self, node_ids: Set[str], adj: Dict[str, List[str]], indegree: Dict[str, int]) -> Optional[List[str]]:
        queue = deque([n for n in node_ids if indegree.get(n, 0) == 0])
        order: List[str] = []
        while queue:
            node = queue.popleft()
            order.append(node)
            for neighbor in adj.get(node, []):
                indegree[neighbor] -= 1
                if indegree[neighbor] == 0:
                    queue.append(neighbor)
        if len(order) != len(node_ids):
            return None
        return order

    def get_execution_groups(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> List[List[str]]:
        '''Returns levels of nodes that can execute in parallel.'''
        indegree = defaultdict(int)
        adj: Dict[str, List[str]] = defaultdict(list)
        node_ids = {n["id"] for n in nodes}
        for e in edges:
            if e["source"] in node_ids and e["target"] in node_ids:
                adj[e["source"]].append(e["target"])
                indegree[e["target"]] += 1
        for nid in node_ids:
            indegree.setdefault(nid, 0)

        levels: List[List[str]] = []
        current = [n for n in node_ids if indegree[n] == 0]
        visited: Set[str] = set()
        while current:
            levels.append(sorted(current))
            visited.update(current)
            next_level: List[str] = []
            for node in current:
                for neighbor in adj.get(node, []):
                    indegree[neighbor] -= 1
                    if indegree[neighbor] == 0 and neighbor not in visited:
                        next_level.append(neighbor)
            current = next_level
        return levels
