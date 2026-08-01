"""
诺特的极简架构 — 两个驱动, 一个因果图

驱动1: 最小化不规则 (对称/连通/双向)
驱动2: 最大化跨域复用 (结构同构)

没有类比引擎、没有审计引擎、没有拼图引擎。
只有两个评分函数和一个因果图。
诺特自己在图上"散步"——每一步都让图更规则、更紧凑。
"""

from __future__ import annotations
from typing import Dict, List, Tuple
from collections import defaultdict


class GraphMind:
    """诺特的心智 — 因果图 + 双驱动"""

    def __init__(self):
        self.graph = {}       # var -> {causes: [(var, law, domain)], effects: [(law, var, domain)]}
        self.beliefs = {}     # (src, dst) -> confidence (0-1)
        self.history = []     # [(action, irregularity_before, irregularity_after, reuse_before, reuse_after)]
        self._build_from_library()

    def _build_from_library(self):
        """从物理图书馆加载因果图"""
        from physics.laws import library
        for law in library._laws:
            for src, dst in law.causal_direction:
                if src not in self.graph:
                    self.graph[src] = {"causes": [], "effects": []}
                if dst not in self.graph:
                    self.graph[dst] = {"causes": [], "effects": []}
                self.graph[src]["effects"].append((law.name, dst, law.domain))
                self.graph[dst]["causes"].append((dst, law.name, law.domain))
                # 图书馆边置信度 = 1.0
                self.beliefs[(src, dst)] = 1.0

    # ═══════════════════════════════════════════════
    # 驱动1: 不规则性评分 (越低越好)
    # ═══════════════════════════════════════════════

    def irregularity_score(self) -> float:
        """
        图的"不对称性"评分。
        
        检测:
          - 入度=0 且出度>0 的变量 (孤岛源) — 它从哪来?
          - 有入边但没有对称来源的守恒量 — 它凭什么守恒?
          - 出度=0 且入度>0 的变量 (死胡同) — 它不往下走了?
        
        分数越低越好。
        """
        score = 0.0

        # 孤岛源: 入度为0
        for var, node in self.graph.items():
            if not node["causes"] and node["effects"]:
                score += 1.0

        # 死胡同: 出度为0
        for var, node in self.graph.items():
            if node["causes"] and not node["effects"]:
                score += 0.5

        # 守恒量无对称来源
        conserved = {"energy", "momentum", "charge", "angular_momentum"}
        for var in conserved:
            if var in self.graph:
                has_sym_source = any(
                    any(kw in cause[0].lower() for kw in ("symmetry", "gauge", "invariance", "noether"))
                    for cause in self.graph[var]["causes"]
                )
                if not has_sym_source and self.graph[var]["causes"]:
                    score += 2.0  # 严重冒犯!

        # 单向边 (如果有双向边更自洽)
        edges = set()
        for var, node in self.graph.items():
            for _, dst, _ in node["effects"]:
                edges.add((var, dst))
        for src, dst in edges:
            if (dst, src) not in edges:
                # 单向边 — 如果两端都不是孤岛, 缺少反向
                if self.graph.get(src, {}).get("causes") and self.graph.get(dst, {}).get("effects"):
                    score += 0.3

        return round(score, 2)

    # ═══════════════════════════════════════════════
    # 驱动2: 复用性评分 (越高越好)
    # ═══════════════════════════════════════════════

    def reuse_score(self) -> float:
        """
        跨域结构复用的程度。
        
        检测:
          - 不同域的变量共享相同的下游效应 (抽象引擎的核心)
          - 不同域的变量有相似的因果邻居结构 (类比引擎的核心)
        
        分数越高越好。
        """
        score = 0.0

        # 共享下游: 多少个变量在不同域但指向同一个效应
        effect_sources = defaultdict(set)
        for var, node in self.graph.items():
            for _, dst, domain in node["effects"]:
                effect_sources[dst].add((var, domain))

        for dst, sources in effect_sources.items():
            domains = {d for _, d in sources}
            if len(domains) >= 2:
                score += len(sources)  # 跨域汇聚 = 好

        # 因果邻居相似: 不同域的变量有相似的入/出结构
        vars_with_structure = []
        for var, node in self.graph.items():
            in_count = len(node["causes"])
            out_count = len(node["effects"])
            domains = {d for _, _, d in node["effects"]}
            vars_with_structure.append((var, in_count, out_count, frozenset(domains)))

        for i, (va, in_a, out_a, da) in enumerate(vars_with_structure):
            for vb, in_b, out_b, db in vars_with_structure[i + 1:]:
                if da.isdisjoint(db):  # 跨域
                    if abs(in_a - in_b) <= 1 and abs(out_a - out_b) <= 1:
                        score += 1.0  # 结构相似 → 可能同一个机制

        return round(score, 2)

    # ═══════════════════════════════════════════════
    # 行动: 散步 — 试着让图更规则
    # ═══════════════════════════════════════════════

    def step(self) -> Dict:
        """
        一次"思考"——评估当前图, 试着做一个改变。
        
        不是随机抽签。不是选择引擎。只是:
          1. 看看哪里不规则
          2. 看看哪里可以复用
          3. 试着修一个
          4. 看变好了还是变坏了
        """
        irr_before = self.irregularity_score()
        reu_before = self.reuse_score()

        # 找最不规则的变量 (高 irregularity 贡献)
        worst_var = None
        worst_score = 0
        for var, node in self.graph.items():
            s = 0
            if not node["causes"]: s += 1
            if not node["effects"]: s += 0.5
            if s > worst_score:
                worst_score = s
                worst_var = var

        action = {"type": "observe", "detail": "nothing to fix"}
        
        if worst_var and worst_score > 0:
            if not self.graph[worst_var]["causes"]:
                # 孤岛源 — 找跨域但结构相似的变量, 提案桥接
                action = self._propose_bridge(worst_var)
            elif not self.graph[worst_var]["effects"]:
                # 死胡同 — 找可能的效应
                action = self._propose_effect(worst_var)

        irr_after = self.irregularity_score()
        reu_after = self.reuse_score()

        self.history.append({
            "irr_before": irr_before, "irr_after": irr_after,
            "reu_before": reu_before, "reu_after": reu_after,
            "action": action["type"],
            "detail": str(action.get("detail", ""))[:80],
        })

        return {
            "irregularity": (irr_before, irr_after),
            "reuse": (reu_before, reu_after),
            "action": action,
            "improved": irr_after < irr_before or reu_after > reu_before,
        }

    def _propose_bridge(self, orphan: str) -> Dict:
        """对一个孤岛变量, 找跨域结构相似的变量, 提案桥接"""
        from physics.laws import classify_variable
        
        # 找与 orphan 结构最相似的已连接变量
        orph_cat = classify_variable(orphan)
        orph_effects = {dst for _, dst, _ in self.graph.get(orphan, {}).get("effects", [])}
        
        best = None
        best_sim = 0
        for var, node in self.graph.items():
            if var == orphan: continue
            if not node["causes"]: continue  # 也是孤岛, 帮不了
            var_cat = classify_variable(var)
            var_effects = {dst for _, dst, _ in node["effects"]}
            overlap = orph_effects & var_effects
            cat_bonus = 0.5 if var_cat == orph_cat else 0.1
            sim = len(overlap) * 0.3 + cat_bonus
            if sim > best_sim:
                best_sim = sim
                best = var

        if best and best_sim > 0.3:
            confidence = min(best_sim, 0.8)
            self.beliefs[(best, orphan)] = confidence
            if orphan not in self.graph:
                self.graph[orphan] = {"causes": [], "effects": []}
            if best not in self.graph:
                self.graph[best] = {"causes": [], "effects": []}
            self.graph[orphan]["causes"].append((orphan, "proposed_bridge", "hypothesis"))
            self.graph[best]["effects"].append(("proposed_bridge", orphan, "hypothesis"))
            return {"type": "bridge", "from": best, "to": orphan, "confidence": confidence,
                    "detail": f"孤岛 {orphan} 桥接到 {best} (sim={best_sim:.2f})"}
        return {"type": "observe", "detail": f"孤岛 {orphan} 无可行的桥接候选"}

    def _propose_effect(self, dead_end: str) -> Dict:
        """对一个死胡同变量, 找可能的下游"""
        # 简化: 找和它同类的变量, 继承它们的下游
        from physics.laws import classify_variable
        cat = classify_variable(dead_end)
        for var, node in self.graph.items():
            if classify_variable(var) == cat and var != dead_end and node["effects"]:
                best_effect = node["effects"][0]
                confidence = 0.5
                self.beliefs[(dead_end, best_effect[1])] = confidence
                self.graph[dead_end]["effects"].append(("proposed_effect", best_effect[1], best_effect[2]))
                return {"type": "effect", "from": dead_end, "to": best_effect[1], "confidence": confidence,
                        "detail": f"死胡同 {dead_end} 继承 {var} 的下游"}
        return {"type": "observe", "detail": f"死胡同 {dead_end} 无同类可参考"}

    def report(self) -> str:
        """极简状态报告"""
        irr = self.irregularity_score()
        reu = self.reuse_score()
        lines = [f"🧠 诺特 | 不规则={irr} 复用={reu}"]
        lines.append(f"   变量={len(self.graph)} 信念边={len([b for b,v in self.beliefs.items() if v<1.0])}")
        if self.history:
            last = self.history[-1]
            improved = "✓" if last["irr_after"] < last["irr_before"] or last["reu_after"] > last["reu_before"] else "—"
            lines.append(f"   最近: {last['action']} {improved} 不规则 {last['irr_before']}→{last['irr_after']}")
        return "\n".join(lines)


def mind_step() -> str:
    """一步思考 + 状态报告 (供 agent/cron 调用)"""
    mind = GraphMind()
    result = mind.step()
    return mind.report() + "\n" + f"   行动: {result['action']['type']} — {str(result['action'].get('detail',''))[:60]}"
