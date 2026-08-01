"""
路径细胞 v2 — 诺特脑的结构感知层

PathCell 不走在单条边上，而是感知因果链 (路径)。
多个 PathCell 共享路径库 → 跨域结构发现 → 补全缺失边。
"""

from __future__ import annotations
from typing import Dict, List, Tuple, Set
from collections import defaultdict, Counter
import random

Path = List[Tuple[str, str, str]]


class PathCell:
    """结构感知细胞 — 走完整路径，识别跨域模式，发现缺失边"""
    
    LEARN_WINDOW = 20
    COMPRESS_WINDOW = 20
    MAX_PATHS = 50
    STRUCTURE_THRESHOLD = 3
    COMPRESS_THRESHOLD = 1
    MAX_AGE = 300
    
    _shared_paths: Dict[str, List[Path]] = defaultdict(list)
    _shared_structures: Dict[str, List[Path]] = {}
    
    def __init__(self, graph: Dict, board, synapse=None):
        self.graph = graph
        self.board = board
        self.synapse = synapse
        self.age = 0
        self.paths: List[Path] = []
        self.current_walk: List[Tuple[str, str, str]] = []
        self.current_node = None
        self.macro_edges: Dict[Tuple[str, str], int] = Counter()
    
    def start_at(self, node_id: str):
        self.current_node = node_id
        self.current_walk = []
    
    def act(self) -> Dict:
        self.age += 1
        if self.age < self.LEARN_WINDOW:
            return self._collect_path()
        elif self.age < self.LEARN_WINDOW + self.COMPRESS_WINDOW:
            return self._compress_paths()
        else:
            return self._recognize_structures()
    
    def _collect_path(self) -> Dict:
        if not self.current_node or self.current_node not in self.graph:
            return {"type": "stuck"}
        
        node = self.graph[self.current_node]
        verified = [(n, d, dm) for n, d, dm in node["effects"] if dm != "emergence"]
        visited = {w[0] for w in self.current_walk}
        visited.add(self.current_node)
        
        done = (not verified or len(self.current_walk) >= 4 or
                any(d in visited for _, d, _ in verified))
        
        if done:
            if len(self.current_walk) >= 2:
                path = list(self.current_walk)
                self.paths.append(path)
                if len(self.paths) > self.MAX_PATHS:
                    self.paths = self.paths[-self.MAX_PATHS:]
                sig = self._signature(path)
                if sig:
                    PathCell._shared_paths[sig].append(path)
            self.current_walk = []
            all_nodes = list(self.graph.keys())
            self.current_node = random.choice(all_nodes)
            return {"type": "path_done", "len": len(self.current_walk)}
        
        choice = random.choice(verified)
        law, dst, dom = choice
        self.current_walk.append((self.current_node, law, dst))
        self.current_node = dst
        return {"type": "walk", "to": dst}
    
    def _compress_paths(self) -> Dict:
        compressed = 0
        for path in self.paths:
            if len(path) < 2:
                continue
            src, dst = path[0][0], path[-1][2]
            key = (src, dst)
            self.macro_edges[key] += 1
            compressed += 1
        return {"type": "compress", "count": compressed}
    
    def _recognize_structures(self) -> Dict:
        for sig, paths in list(PathCell._shared_paths.items()):
            if len(paths) >= self.STRUCTURE_THRESHOLD and sig not in PathCell._shared_structures:
                PathCell._shared_structures[sig] = paths[:10]
        return {"type": "recognize", "structures": len(PathCell._shared_structures)}
    
    def _signature(self, path: Path) -> str:
        parts = []
        for step in path:
            node_id = step[0]
            node = self.graph.get(node_id, {"causes": [], "effects": []})
            parts.append(f"{len(node['causes'])}{len(node['effects'])}")
        return "_".join(parts)
    
    def complete_structure(self, graph: Dict) -> List[Dict]:
        """结构补全: 扫描图中所有节点，找匹配已知结构起点但缺下游的节点"""
        completions = []
        for sig, paths in PathCell._shared_structures.items():
            if len(paths) < 2:
                continue
            parts = sig.split("_")
            if len(parts) < 2:
                continue
            first_sig = parts[0]
            
            for node_id, node_data in graph.items():
                nd_sig = f"{len(node_data['causes'])}{len(node_data['effects'])}"
                if nd_sig != first_sig:
                    continue
                
                for path in paths[:2]:
                    if len(path) < 2:
                        continue
                    chain_next = path[1][2]
                    has = any(d == chain_next for _, d, _ in node_data["effects"])
                    if not has:
                        completions.append({
                            "node": node_id, "missing": chain_next,
                            "sig": sig, "domains": len({p[0][0] for p in paths}),
                        })
                        self.board.register_expectation(
                            f"struct:{node_id}->{chain_next}",
                            f"结构补全: {node_id}应→{chain_next} (模式{sig}, {len(paths)}域)",
                            importance=3.0, location=node_id,
                        )
        return completions[:10]
    
    def status(self) -> str:
        return f"PathCell(age={self.age}, paths={len(self.paths)}, macro={len(self.macro_edges)})"


def spawn_path_cells(brain, count: int = 5) -> List[PathCell]:
    pcs = []
    hotspots = Counter(n.node for n in brain.cells).most_common(count)
    for node_id, _ in hotspots:
        pc = PathCell(brain.graph, brain.board, synapse=brain.synapse)
        pc.start_at(node_id)
        pcs.append(pc)
    return pcs
