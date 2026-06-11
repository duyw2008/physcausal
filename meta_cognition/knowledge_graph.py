"""
知识网络 — Noether 的统一知识图谱

8 个散落的 JSON → 一个有类型的知识网络。
为图感知 RL 和未来 GNN 提供数据基础。
"""

from __future__ import annotations
from typing import Dict, List, Set, Tuple, Optional
import json, os, time
from collections import defaultdict
from data_paths import data_path

_KG_FILE = data_path("knowledge_graph.json")


class KnowledgeGraph:
    """Noether 的知识网络"""

    def __init__(self):
        self.nodes: Dict[str, Dict] = {}   # node_id → {type, data}
        self.edges: List[Tuple[str, str, str]] = []  # (src, dst, type)
        self._load()

    def __len__(self):
        return len(self.nodes)

    # ── 存储 ──

    def _load(self):
        try:
            with open(_KG_FILE) as f:
                data = json.load(f)
                self.nodes = data.get("nodes", {})
                self.edges = data.get("edges", [])
        except:
            pass

    def save(self):
        with open(_KG_FILE, "w") as f:
            json.dump({"nodes": self.nodes, "edges": self.edges}, f, ensure_ascii=False, indent=2)

    # ── 节点 ──

    def add_node(self, node_id: str, node_type: str, data: Dict = None):
        self.nodes[node_id] = {"type": node_type, "data": data or {}, "added": time.time()}

    def get_node(self, node_id: str) -> Optional[Dict]:
        return self.nodes.get(node_id)

    def nodes_of_type(self, node_type: str) -> List[str]:
        return [nid for nid, nd in self.nodes.items() if nd["type"] == node_type]

    # ── 边 ──

    def add_edge(self, src: str, dst: str, edge_type: str):
        if (src, dst, edge_type) not in self.edges:
            self.edges.append((src, dst, edge_type))

    def neighbors(self, node_id: str, direction: str = "both") -> List[Tuple[str, str]]:
        """查询邻居: out(出边), in(入边), both(全部)"""
        results = []
        for src, dst, etype in self.edges:
            if direction in ("out", "both") and src == node_id:
                results.append((dst, etype))
            if direction in ("in", "both") and dst == node_id:
                results.append((src, etype))
        return results

    def query(self, node_id: str) -> Dict:
        """查询一个节点的完整上下文"""
        node = self.get_node(node_id)
        if not node:
            return {"error": f"节点 {node_id} 不存在"}

        in_edges = [(s, t) for s, d, t in self.edges if d == node_id]
        out_edges = [(d, t) for s, d, t in self.edges if s == node_id]

        return {
            "node": {"id": node_id, "type": node["type"], "data": node["data"]},
            "incoming": len(in_edges),
            "outgoing": len(out_edges),
            "in_edges": in_edges[:20],
            "out_edges": out_edges[:20],
        }

    # ── 统计 ──

    def stats(self) -> Dict:
        type_counts = defaultdict(int)
        for nd in self.nodes.values():
            type_counts[nd["type"]] += 1
        edge_counts = defaultdict(int)
        for _, _, etype in self.edges:
            edge_counts[etype] += 1
        return {
            "nodes": len(self.nodes),
            "edges": len(self.edges),
            "node_types": dict(type_counts),
            "edge_types": dict(edge_counts),
        }

    # ── 导出 ──

    def to_adjacency(self) -> Tuple[List[str], List[Tuple[int, int]]]:
        """导出邻接表 (给 GNN)"""
        node_list = list(self.nodes.keys())
        node_idx = {n: i for i, n in enumerate(node_list)}
        adj = [(node_idx[s], node_idx[d]) for s, d, _ in self.edges]
        return node_list, adj


# ── 全局单例 ──

kg = KnowledgeGraph()
