"""
前沿地图 — 标注未知边界，引导自主探索方向

三个维度:
  1. 稀疏区 — 变量在哪些领域缺席
  2. 断头路 — chain 传播在哪里停止
  3. 尺度裂缝 — 不同物理尺度间的缺失桥接

与 dissonance 的区别:
  dissonance 检测已知定律间的张力 (已知的矛盾)
  frontier 标注未知的空白 (未知的边界)
"""

from __future__ import annotations
from typing import Dict, List, Set, Tuple
from collections import defaultdict


class FrontierMap:
    """PhysCausal 的前沿地图 — 告诉 agent 哪里最值得探索"""

    # 尺度映射
    SCALE_MAP = {
        "mechanics": "classical", "electromagnetism": "classical",
        "thermodynamics": "classical", "fluids": "classical",
        "optics": "classical", "acoustics": "classical",
        "modern": "classical",
        "quantum": "quantum",
        "general_relativity": "relativistic",
    }

    # 基础变量 — 跨域出现越多越重要
    FUNDAMENTAL = {"mass", "energy", "time", "force", "velocity",
                   "temperature", "momentum", "wavelength", "frequency",
                   "pressure", "volume", "charge"}

    def __init__(self):
        self.coverage: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.variable_frequency: Dict[str, int] = defaultdict(int)
        self.domain_list: List[str] = []
        self._built = False

    def build(self):
        """从定律库构建覆盖矩阵"""
        from physics.laws import library

        self.coverage.clear()
        self.variable_frequency.clear()
        domains_seen = set()

        for law in library.list_all():
            domain = law.domain
            if domain in ("unknown", "auto", "unification"):
                continue
            domains_seen.add(domain)
            for var in law.inputs + law.outputs:
                self.coverage[var][domain] += 1
                self.variable_frequency[var] += 1

        self.domain_list = sorted(domains_seen)
        self._built = True

    # ═══ 稀疏区 ═══

    def sparse_zones(self, min_domains: int = 3) -> List[Dict]:
        """
        找出在 ≥ min_domains 个领域出现, 但缺席某些领域的变量。
        """
        if not self._built:
            self.build()

        zones = []
        for var, freq in self.variable_frequency.items():
            domains_present = set(self.coverage[var].keys())
            n_present = len(domains_present)

            if n_present < min_domains:
                continue

            domains_absent = [d for d in self.domain_list if d not in domains_present]
            if not domains_absent:
                continue

            # 只在基础变量或高频变量中找
            is_fundamental = var in self.FUNDAMENTAL
            if not is_fundamental and freq < 4:
                continue

            # ── 本体论加权: 基础变量缺席 > 几何变量缺席 > 派生变量缺席 ──
            from physics.laws import classify_variable
            cat = classify_variable(var)
            cat_multiplier = {"fundamental": 2.0, "geometric": 1.5, "quantum": 1.3, "derived": 0.8}
            base_score = len(domains_absent) * cat_multiplier.get(cat, 0.8)
            if is_fundamental:
                base_score *= 1.5

            zones.append({
                "type": "sparse_zone",
                "variable": var,
                "frequency": freq,
                "domains_present": sorted(domains_present),
                "domains_absent": domains_absent,
                "fundamental": is_fundamental,
                "score": round(base_score, 1),
            })

        return sorted(zones, key=lambda z: z["score"], reverse=True)

    # ═══ 断头路 ═══

    def dead_ends(self, max_per_var: int = 3) -> List[Dict]:
        """
        从高频变量出发传播 chain, 记录在哪里停止。
        停不是因为 max_depth, 而是因为没有下游定律。
        """
        if not self._built:
            self.build()

        from inference.counterfactual_chain import propagate, build_dependency_graph

        graph = build_dependency_graph()
        dead = []

        # 从频率最高的变量开始
        top_vars = sorted(self.variable_frequency.items(),
                          key=lambda x: x[1], reverse=True)[:max_per_var * 3]

        for var, freq in top_vars[:max_per_var * 3]:
            chain = propagate(var, "变化", max_depth=6)
            if not chain or "error" in chain[0]:
                continue

            # 找 chain 中的终点: effect_variable 在 graph 中没有 as_input
            for step in chain:
                effect = step.get("effect_variable", "")
                depth = step.get("depth", 0)

                if effect not in graph or not graph[effect].get("as_input"):
                    # 断头: effect 没有下游
                    dead.append({
                        "type": "dead_end",
                        "start_variable": var,
                        "dead_variable": effect,
                        "depth": depth,
                        "domain": step.get("domain", "unknown"),
                        "law": step.get("law", ""),
                        "score": 0.5 + depth * 0.3,
                    })

        # 去重 + 排序
        seen = set()
        unique = []
        for d in sorted(dead, key=lambda x: x["score"], reverse=True):
            key = (d["start_variable"], d["dead_variable"])
            if key not in seen:
                seen.add(key)
                unique.append(d)

        return unique[:max_per_var * 3]

    # ═══ 尺度裂缝 ═══

    def scale_gaps(self) -> List[Dict]:
        """
        找出不同物理尺度间共享变量但无桥接定律的位置。
        只在 classical↔quantum, classical↔relativistic, quantum↔relativistic 之间检测。
        """
        if not self._built:
            self.build()

        from physics.laws import library

        # 按尺度分组变量
        scale_vars: Dict[str, Set[str]] = defaultdict(set)
        scale_laws: Dict[str, List] = defaultdict(list)

        for law in library.list_all():
            scale = self.SCALE_MAP.get(law.domain, law.domain)
            if scale in ("unknown", "auto", "unification"):
                continue
            for var in law.inputs + law.outputs:
                scale_vars[scale].add(var)
            scale_laws[scale].append(law)

        scales = sorted(scale_vars.keys())
        gaps = []

        for i, s1 in enumerate(scales):
            for s2 in scales[i + 1:]:
                shared = scale_vars[s1] & scale_vars[s2]
                if not shared:
                    continue

                # 找在 s1 和 s2 都出现但没有直接桥接的基础变量
                for var in sorted(shared):
                    if var not in self.FUNDAMENTAL:
                        continue

                    # 检查是否已有跨尺度定律连接这个变量
                    bridged = False
                    for law in library.list_all():
                        law_scale = self.SCALE_MAP.get(law.domain, law.domain)
                        # 定律在 s1 域, 变量是 output, 且在 s2 域有定律以此为 input
                        if law_scale == s1 and var in law.outputs:
                            # 查找 s2 域中使用 var 作为 input 的定律
                            for law2 in scale_laws.get(s2, []):
                                if var in law2.inputs:
                                    bridged = True
                                    break
                        if bridged:
                            break
                        if law_scale == s2 and var in law.outputs:
                            for law2 in scale_laws.get(s1, []):
                                if var in law2.inputs:
                                    bridged = True
                                    break
                        if bridged:
                            break

                    if not bridged:
                        gaps.append({
                            "type": "scale_gap",
                            "scale_a": s1,
                            "scale_b": s2,
                            "variable": var,
                            "score": 2.0,  # 尺度裂缝最重要
                        })

        return sorted(gaps, key=lambda g: g["score"], reverse=True)

    # ═══ 汇总 ═══

    def top_frontiers(self, n: int = 10) -> List[Dict]:
        """返回最有希望的前沿, 按综合得分排序"""
        all_frontiers = []
        all_frontiers.extend(self.sparse_zones())
        all_frontiers.extend(self.dead_ends())
        all_frontiers.extend(self.scale_gaps())
        return sorted(all_frontiers, key=lambda f: f["score"], reverse=True)[:n]

    def report(self) -> str:
        """人类可读的前沿报告"""
        lines = ["=== PhysCausal 前沿地图 ==="]
        lines.append("")

        sparse = self.sparse_zones()
        dead = self.dead_ends()
        gaps = self.scale_gaps()

        if sparse:
            lines.append(f"稀疏区 ({len(sparse)}):")
            for z in sparse[:5]:
                star = "★" if z["fundamental"] else "·"
                lines.append(f"  {star} {z['variable']} 缺席 {z['domains_absent']}")
                lines.append(f"    已覆盖: {z['domains_present']}")
            lines.append("")

        if dead:
            lines.append(f"断头路 ({len(dead)}):")
            for d in dead[:5]:
                lines.append(f"  → {d['start_variable']} ...→ {d['dead_variable']} [depth={d['depth']}]")
                lines.append(f"    停在 {d['law']} ({d['domain']}), 无下游")
            lines.append("")

        if gaps:
            lines.append(f"尺度裂缝 ({len(gaps)}):")
            for g in gaps[:5]:
                lines.append(f"  ⚡ {g['scale_a']} ↔ {g['scale_b']}: {g['variable']} 无桥接")

        if not sparse and not dead and not gaps:
            lines.append("  定律库覆盖完整, 未发现明显前沿。")

        return "\n".join(lines)
