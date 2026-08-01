"""
本体觉 — 脑感受自己的 emergent 结构统计

不告诉细胞去哪，只给气味场。细胞自己根据气味调整策略。

气味场每 N 代更新一次 (PROPRIOCEPTION_INTERVAL)，注入到细胞环境。
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from collections import Counter
import json, os, time, math


class Proprioception:
    """费曼脑的本体觉 — 感受自己内部的 emergent 结构"""

    # 更新频率
    INTERVAL = 10  # 每 10 代刷新一次
    # 衰减因子 (EWMA)
    ALPHA = 0.3

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        self.data_dir = data_dir
        self.last_update_gen = 0
        self.field: Dict = {}          # 当前气味场
        self._prev_field: Dict = {}    # 上一轮 (用于 EWMA)

    # ═══ 主接口 ═══

    def maybe_update(self, colony, force: bool = False) -> Dict:
        """每 N 代更新一次气味场。返回当前场。"""
        gen = colony.generation
        if not force and gen - self.last_update_gen < self.INTERVAL:
            return self.field
        # 只用快照数据 (O(1) 访问突触层激活)
        raw = self._compute_raw(colony)
        # EWMA 平滑
        field = {}
        for key, val in raw.items():
            prev = self._prev_field.get(key)
            if prev is not None and isinstance(val, (int, float)):
                field[key] = prev * (1 - self.ALPHA) + val * self.ALPHA
            else:
                field[key] = val
        self._prev_field = field
        self.field = field
        self.last_update_gen = gen
        self._save(field, gen)
        return field

    def _compute_raw(self, colony) -> Dict:
        """计算原始统计量 — 只读突触层，不做全图遍历"""
        acts = colony.synapse.activations  # Dict[(src, dst), {s, c, ...}]
        graph = colony.graph

        # ── emergent 边按域分布 ──
        em_by_domain: Dict[str, int] = Counter()
        total_em = 0
        for (src, dst), v in acts.items():
            s = v.get("s", 0)
            if s < 0.01:
                continue
            # 从图取域 (两端取并集)
            src_data = graph.get(src, {})
            dst_data = graph.get(dst, {})
            effects = src_data.get("effects", [])
            for eff in effects:
                if isinstance(eff, (list, tuple)) and len(eff) >= 3 and eff[1] == dst:
                    dom = eff[2]
                    if dom == "emergent":
                        total_em += 1
                        # 从节点名推断域 (fallback)
                        d = _infer_domain(src) or _infer_domain(dst) or "unknown"
                        em_by_domain[d] += 1
                    break

        # ── s 值分布 (用分位数逼近) ──
        s_vals = sorted([v.get("s", 0) for v in acts.values() if v.get("s", 0) > 0.001])
        n_s = len(s_vals)
        s_stats = {}
        if n_s >= 10:
            p10 = s_vals[n_s // 10]
            p50 = s_vals[n_s // 2]
            p90 = s_vals[n_s * 9 // 10]
            head = sum(1 for x in s_vals if x >= 0.5)
            s_stats = {
                "p10": round(p10, 3),
                "p50": round(p50, 3),
                "p90": round(p90, 3),
                "head_ratio": round(head / n_s, 3),     # 强壮突触占比
                "tail_ratio": round(sum(1 for x in s_vals if x < 0.05) / n_s, 3),  # 弱突触占比
                "total_active": n_s,
            }

        # ── 跨域桥接节点 Top-5 ──
        node_domains: Dict[str, set] = {}
        for node_name, nd in graph._cache.items() if hasattr(graph, '_cache') else graph.items():
            if not isinstance(nd, dict):
                continue
            doms = set()
            for eff in nd.get("effects", []):
                if isinstance(eff, (list, tuple)) and len(eff) >= 3:
                    doms.add(eff[2])
            for cause in nd.get("causes", []):
                if isinstance(cause, (list, tuple)) and len(cause) >= 3:
                    doms.add(cause[2])
            if len(doms) >= 3:
                node_domains[node_name] = doms

        bridge_nodes = sorted(node_domains.items(), key=lambda x: -len(x[1]))[:5]
        bridges = [{"node": n, "domains": list(d), "count": len(d)} for n, d in bridge_nodes]

        # ── coincidence 热点 ──
        coinc = getattr(colony, "_coincidence", {})
        hot_pairs = sorted(coinc.items(), key=lambda x: -x[1])[:5]
        hotspots = [{"pair": f"{a}↔{b}", "count": c} for (a, b), c in hot_pairs]

        # ── 全局指标 ──
        return {
            "total_cells": len(colony.cells),
            "total_synapses": len(acts),
            "generation": colony.generation,
            "emergent_edges": total_em,
            "em_by_domain": dict(em_by_domain),
            "s_distribution": s_stats,
            "bridge_nodes": bridges,
            "coincidence_hotspots": hotspots,
            "sleep_pressure": getattr(colony, "_sleep_pressure", 0),
        }

    # ═══ 细胞感知接口 ═══

    def smell(self, node_name: str) -> Dict:
        """一个细胞在给定节点上闻到的气味。

        返回轻量 Dict, 可直接合并到 cell.perceive() 的结果中。
        """
        f = self.field
        if not f:
            return {"proprioception": "no_data"}

        # 节点所在域的 emergent 密度
        dom = _infer_domain(node_name)
        em_density = f.get("em_by_domain", {}).get(dom, 0)
        total_em = max(f.get("emergent_edges", 0), 1)
        em_density_norm = em_density / total_em

        # 该节点是否是桥接节点
        bridges = {b["node"] for b in f.get("bridge_nodes", [])}
        is_bridge = node_name in bridges

        # s 分布参考
        s_dist = f.get("s_distribution", {})

        return {
            "_proprio_em_density": round(em_density_norm, 3),
            "_proprio_domain": dom,
            "_proprio_is_bridge": is_bridge,
            "_proprio_s_head_ratio": s_dist.get("head_ratio", 0),
            "_proprio_global_em": total_em,
            "_proprio_gen": f.get("generation", 0),
        }

    # ═══ 持久化 ═══

    def _save(self, field: Dict, gen: int):
        try:
            path = os.path.join(self.data_dir, "proprioception.json")
            out = {"generation": gen, "timestamp": time.time(), "field": field}
            with open(path, "w") as f:
                json.dump(out, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    @classmethod
    def load(cls, data_dir: str = None) -> Optional[Dict]:
        """从磁盘读最近的本体觉数据"""
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        try:
            path = os.path.join(data_dir, "proprioception.json")
            with open(path) as f:
                return json.load(f)
        except Exception:
            return None


# ═══ 辅助 ═══

def _infer_domain(name: str) -> str:
    """从概念名推断物理域"""
    name_lower = name.lower()
    mappings = [
        ("mechanics", ["force", "mass", "energy", "acceleration", "momentum", "velocity", "kinetic"]),
        ("electromagnetism", ["current", "voltage", "charge", "field", "electric", "magnetic", "lorentz"]),
        ("thermodynamics", ["temperature", "entropy", "heat", "thermal"]),
        ("quantum", ["quantum", "wavefunction", "spin", "planck", "photon", "probability"]),
        ("general_relativity", ["spacetime", "curvature", "gravitational", "black_hole", "geodesic", "relativistic"]),
        ("optics", ["wavelength", "frequency", "optical", "refractive", "diffraction", "interference"]),
        ("gauge_geometry", ["gauge", "connection", "curvature", "fiber", "bundle", "chern", "yang_mills"]),
        ("condensed_matter", ["band", "fermi", "phonon", "conductivity", "magnetization"]),
    ]
    for domain, keywords in mappings:
        for kw in keywords:
            if kw in name_lower:
                return domain
    return "unknown"
