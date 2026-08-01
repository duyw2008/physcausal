"""
sympy 推导感知 — coincidence 热点自动触发数学推导

定位: 推导是工具不是裁判，derived 边以低 s 注入
     成功靠细胞 walk 验证, 失败有冷却机制
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import random


class DerivePerception:
    """每 N 代从 coincidence 热点 + emergent hot nodes 选取候选对，调用 sympy 推导"""

    MAX_DERIVES_PER_CYCLE = 3
    MIN_COINCIDENCE = 10
    MIN_COINCIDENCE_BRIDGE = 3
    DERIVED_INITIAL_S = 0.3

    def __init__(self):
        self._last_derive_gen: int = 0
        self._failed_pairs: Dict[tuple, int] = {}   # (src,dst) → 失败次数
        self._failed_gen: Dict[tuple, int] = {}      # (src,dst) → 最近失败代数
        self._derive_history: List[Dict] = []

    def try_derive_from_hotspots(self, colony, force: bool = False) -> int:
        gen = getattr(colony, 'generation', 0)
        if not force and gen - self._last_derive_gen < 5:
            return 0
        self._last_derive_gen = gen

        # 确保本体觉数据是最新的
        colony.proprioception.maybe_update(colony, force=(gen - colony.proprioception.last_update_gen >= 5))

        candidates = self._collect_candidates(colony)
        if not candidates:
            return 0

        print(f"  [DERIVE] {len(candidates)} candidates @ gen {gen}")

        successes = 0
        for src, dst, coinc_count in candidates[:self.MAX_DERIVES_PER_CYCLE]:
            key = (src, dst)
            fail_count = self._failed_pairs.get(key, 0)
            last_fail_gen = self._failed_gen.get(key, 0)
            if fail_count > 0 and gen - last_fail_gen < 20:
                continue

            result = self._do_derive(src, dst)
            if result and result.get("success"):
                relation = str(result.get("relation", f"{src}→{dst}"))
                law_name = f"derive:{src[:20]}→{dst[:20]}"
                colony.feed_queue.feed_edge(
                    src, dst,
                    law=law_name,
                    source="derive",
                    domain="math_verified",
                    initial_s=self.DERIVED_INITIAL_S,
                )
                colony._coincidence[(src, dst)] = colony._coincidence.get((src, dst), 0) + 5
                successes += 1
                self._derive_history.append({
                    "gen": gen, "src": src, "dst": dst,
                    "relation": relation,
                    "confidence": result.get("confidence", 0),
                })
                if len(self._derive_history) > 20:
                    self._derive_history = self._derive_history[-20:]
                print(f"  [DERIVE] ✅ {src}→{dst}: {relation[:60]}")
            else:
                if key in colony._coincidence:
                    colony._coincidence[key] = max(1, colony._coincidence[key] - 3)
                self._failed_pairs[key] = fail_count + 1
                self._failed_gen[key] = gen

        if successes > 0:
            print(f"  [DERIVE] +{successes} math_verified edges (gen {gen})")
        return successes

    def _collect_candidates(self, colony) -> List[Tuple[str, str, int]]:
        from physics.math_derive import get_symbol

        def is_simple_concept(name: str) -> bool:
            # 只要 sympy 能解析到符号就放过，不管名字多长/几个下划线
            return get_symbol(name) is not None

        candidates = []

        # 来源1: coincidence 热点
        coinc = getattr(colony, "_coincidence", {})
        for (a, b), count in coinc.items():
            if count >= self.MIN_COINCIDENCE and is_simple_concept(a) and is_simple_concept(b):
                candidates.append((a, b, count))

        # 来源2: proprioception hotspots
        field = colony.proprioception.field
        seen = {(a, b) for a, b, _ in candidates}
        for h in field.get("coincidence_hotspots", []):
            pair_str = h.get("pair", "")
            if "↔" in pair_str:
                parts = pair_str.split("↔")
                if len(parts) == 2:
                    a, b = parts[0].strip(), parts[1].strip()
                    if (a, b) not in seen and (b, a) not in seen:
                        count = h.get("count", 0)
                        if count >= self.MIN_COINCIDENCE and is_simple_concept(a) and is_simple_concept(b):
                            candidates.append((a, b, count))
                            seen.add((a, b))

        # 来源3: 桥接节点间配对
        bridges = [b["node"] for b in field.get("bridge_nodes", [])
                   if is_simple_concept(b["node"])]
        for i, a in enumerate(bridges):
            for b_node in bridges[i+1:]:
                if (a, b_node) not in seen and (b_node, a) not in seen:
                    candidates.append((a, b_node, 15))
                    seen.add((a, b_node))

        # 来源4: emergent hot nodes — 脑自己涌现的重要概念
        hot_nodes = self._get_emergent_hot_nodes(colony, min_edges=3)
        for i, a in enumerate(hot_nodes):
            for b_node in hot_nodes[i+1:]:
                if (a, b_node) not in seen and (b_node, a) not in seen:
                    candidates.append((a, b_node, 10))
                    seen.add((a, b_node))

        candidates.sort(key=lambda x: -x[2])
        return candidates

    def _do_derive(self, src: str, dst: str) -> Optional[Dict]:
        from physics.math_derive import derive as math_derive
        try:
            return math_derive(src, dst)
        except Exception:
            return None

    def _get_emergent_hot_nodes(self, colony, min_edges: int = 3) -> List[str]:
        """从 emergent edges 中提取出现频率最高的概念节点"""
        try:
            import json, os
            path = os.path.join(colony.data_dir, "emergent_edges.json")
            if not os.path.exists(path):
                return []
            with open(path) as f:
                edges = json.load(f)
            from collections import Counter
            node_counts = Counter()
            for e in edges:
                if len(e) >= 3 and e[0] != e[2]:
                    node_counts[e[0]] += 1
                    node_counts[e[2]] += 1
            hot = [n for n, c in node_counts.most_common(16) if c >= min_edges]
            return hot[:8]
        except Exception:
            return []

    def history(self) -> List[Dict]:
        return self._derive_history[-10:]
