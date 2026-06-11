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

    # ── 层4: 推理 — 路径查找 ──

    def upstream(self, node_id: str, max_depth: int = 3) -> List[List[str]]:
        """查找上游路径: 什么导致这个变量?"""
        paths = []
        visited = set()

        def dfs(current, path, depth):
            if depth > max_depth:
                return
            visited.add(current)
            for src, dst, etype in self.edges:
                if dst == current and src not in visited:
                    new_path = path + [f"{src}({etype})"]
                    paths.append(new_path)
                    dfs(src, new_path, depth + 1)
            visited.discard(current)

        dfs(node_id, [node_id], 1)
        return paths

    def downstream(self, node_id: str, max_depth: int = 3) -> List[List[str]]:
        """查找下游路径: 这个变量导致什么?"""
        paths = []
        visited = set()

        def dfs(current, path, depth):
            if depth > max_depth:
                return
            visited.add(current)
            for src, dst, etype in self.edges:
                if src == current and dst not in visited:
                    new_path = path + [f"{dst}({etype})"]
                    paths.append(new_path)
                    dfs(dst, new_path, depth + 1)
            visited.discard(current)

        dfs(node_id, [node_id], 1)
        return paths

    def connect(self, node_a: str, node_b: str, max_depth: int = 3) -> List[List[str]]:
        """查找两个节点之间的所有路径"""
        paths = []

        def dfs(current, path, depth):
            if depth > max_depth:
                return
            if current == node_b and len(path) > 1:
                paths.append(path[:])
                return
            for src, dst, _ in self.edges:
                if src == current and dst not in path:
                    dfs(dst, path + [dst], depth + 1)
                if dst == current and src not in path:  # 也走反向
                    dfs(src, path + [src], depth + 1)

        dfs(node_a, [node_a], 1)
        return paths

    # ── 层5: 矛盾检测 ──

    def detect_contradictions(self) -> List[Dict]:
        """检测图中的矛盾"""
        contradictions = []

        # 1. 同一变量对的相反因果方向
        seen_pairs = {}
        for src, dst, etype in self.edges:
            if etype in ("has_input", "has_output"):
                pair = (src, dst)
                reverse = (dst, src)
                if reverse in seen_pairs:
                    contradictions.append({
                        "type": "reverse_causality",
                        "pair": (src, dst),
                        "message": f"{src} 和 {dst} 存在双向因果边, 可能冲突",
                    })
                seen_pairs[pair] = etype

        # 2. 论文断言 vs 已有定律冲突
        for src, dst, etype in self.edges:
            if etype == "discovered_in":
                # 检查这条定律的因果方向是否和已有定律反向
                law_node = self.get_node(src)
                if law_node:
                    inputs = law_node["data"].get("inputs", [])
                    outputs = law_node["data"].get("outputs", [])
                    for i in inputs:
                        for o in outputs:
                            reverse_key = (f"var:{o}", f"var:{i}")
                            if reverse_key in seen_pairs:
                                contradictions.append({
                                    "type": "paper_vs_law",
                                    "paper_law": src,
                                    "existing_law": seen_pairs[reverse_key],
                                    "message": f"论文 {src} 的因果方向与已有定律冲突: {o}→{i}",
                                })

        # 3. 孤儿变量: 只有入边没有出边, 或只有出边没有人边
        for nid, nd in self.nodes.items():
            if nd["type"] == "variable":
                in_edges = [e for e in self.edges if e[1] == nid]
                out_edges = [e for e in self.edges if e[0] == nid]
                if in_edges and not out_edges:
                    contradictions.append({
                        "type": "sink_variable",
                        "variable": nid,
                        "message": f"{nid} 只被使用, 不产生任何东西 (纯消耗)",
                    })
                elif out_edges and not in_edges:
                    contradictions.append({
                        "type": "source_variable",
                        "variable": nid,
                        "message": f"{nid} 只有产出, 没有来源 (根变量)",
                    })

        return contradictions


# ── 全局单例 ──

kg = KnowledgeGraph()
