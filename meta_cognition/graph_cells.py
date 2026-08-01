"""
图细胞 v2 — 具身学习 + 结构共振

一个细胞:
  1. 位置 (因果图上的节点)
  2. 感知 (局部拓扑)
  3. 学习 (沿已验证边行走, 积累路径记忆)
  4. 行动 (基于记忆提出假说)
  5. 复制 (分裂到邻居节点)

核心改变: 细胞不再随机猜边, 而是先遍历已知物理结构,
把走过的因果链内化成记忆。记忆积累到一定量后,
基于"这个模式我以前见过"来提出新边。

殖民地结构自然共振物理知识结构:
  - 连接度高的节点聚集更多细胞 (力/能量/作用量)
  - 走过相似路径的细胞形成相似分化
  - 细胞分布本身就是物理知识的活地图
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import time, random


# 记忆条目: (src_node, law_name, dst_node, domain)
MemoryEntry = Tuple[str, str, str, str]


class GraphCell:
    """因果图上的一个细胞 — 带记忆和学习能力"""

    LEARN_UNTIL_AGE = 10       # 前N代主要学习
    MEMORY_FOR_PROPOSAL = 5    # 至少积累这么多记忆才能提出假说
    MAX_MEMORY = 50            # 记忆容量上限

    def __init__(self, node_id: str, graph: Dict, board: 'Blackboard'):
        self.node = node_id
        self.graph = graph
        self.board = board
        self.age = 0
        self.specialization = None
        self.action_history: List[str] = []
        self.contributions = 0
        self.last_contributed_at = 0
        # 记忆: 走过的因果路径
        self.memory: List[MemoryEntry] = []
        # 当前正在学习的路径 (未完成的遍历)
        self._current_path: List[str] = []  # 节点序列

    # ── 感知 ──

    def perceive(self) -> Dict:
        """感知局部环境"""
        node = self.graph.get(self.node, {"causes": [], "effects": []})
        in_deg = len(node["causes"])
        out_deg = len(node["effects"])

        has_sym_source = any(
            any(kw in c[0].lower() for kw in ("symmetry", "gauge", "invariance", "noether"))
            for c in node["causes"]
        )
        is_conserved = self.node in {"energy", "momentum", "charge", "angular_momentum"}
        out_domains = {d for _, _, d in node["effects"]}
        in_domains = {d for _, _, d in node["causes"]}

        # 已验证边 (非 emergence 域)
        verified_effects = [(name, dst, dom) for name, dst, dom in node["effects"]
                           if dom != "emergence"]
        verified_causes = [(src, name, dom) for src, name, dom in node["causes"]
                          if name != "emergence"]

        return {
            "node": self.node,
            "in_deg": in_deg,
            "out_deg": out_deg,
            "verified_out": len(verified_effects),
            "verified_effects": verified_effects,
            "verified_causes": verified_causes,
            "is_orphan": in_deg == 0 and out_deg > 0,
            "is_dead_end": out_deg == 0 and in_deg > 0,
            "is_isolated": in_deg == 0 and out_deg == 0,
            "has_sym_source": has_sym_source,
            "is_conserved": is_conserved,
            "conserved_no_sym": is_conserved and in_deg > 0 and not has_sym_source,
            "cross_domain": len(out_domains) >= 2,
            "in_domains": in_domains,
            "out_domains": out_domains,
            "memory_size": len(self.memory),
        }

    # ── 行动 (主入口) ──

    def act(self) -> Dict:
        """根据年龄和感知选择行动"""
        env = self.perceive()

        # 年轻细胞: 优先学习
        if self.age < self.LEARN_UNTIL_AGE and env["verified_out"] > 0:
            return self._act_learn(env)

        # 年老细胞: 基于记忆行动
        if env["conserved_no_sym"]:
            self.specialization = "audit"
            return self._act_audit(env)
        elif env["is_orphan"]:
            self.specialization = "bridge"
            return self._act_bridge_from_memory(env)
        elif env["is_dead_end"]:
            self.specialization = "extend"
            return self._act_extend_from_memory(env)
        elif env["cross_domain"]:
            self.specialization = "analogy"
            return self._act_analogy(env)
        else:
            # 健康节点: 有经验→回顾/教学, 否则→继续学习 (不空转)
            if len(self.memory) >= self.MEMORY_FOR_PROPOSAL:
                r = random.random()
                if r < 0.15:
                    return self._act_review(env)
                elif r < 0.25:
                    return self._act_teach()
                elif env["verified_out"] > 0:
                    return self._act_learn(env)
                elif env["verified_causes"]:
                    return self._act_learn(env)  # 回溯也是学习
            elif env["verified_out"] > 0:
                return self._act_learn(env)
            elif env["verified_causes"]:
                return self._act_learn(env)
            return {"type": "observe", "node": self.node,
                    "detail": f"孤立节点, 记忆{len(self.memory)}条"}

    # ── 学习行为 ──

    def _act_learn(self, env) -> Dict:
        """沿已验证边行走一步。梯度跟随: 优先走向未探索边多的节点。
        不随机跳跃——每一步都是有向的知识获取。"""
        verified_out = env["verified_effects"]
        verified_in = env["verified_causes"]

        # 如果没有出边, 沿入边回溯
        if not verified_out:
            if verified_in:
                src, law_name, domain = random.choice(verified_in)
                self.memory.append((src, law_name, self.node, domain))
                if len(self.memory) > self.MAX_MEMORY:
                    self.memory = self.memory[-self.MAX_MEMORY:]
                old = self.node
                self.node = src
                return {"type": "learn_backward", "from": old, "to": src,
                        "via": law_name}
            return {"type": "observe", "node": self.node, "detail": "汇节点"}

        # 梯度跟随: 每个目标节点计算"学习价值"
        # 价值 = 未走过的出边数 + 跨域奖励
        scored = []
        known_dsts = {m[2] for m in self.memory if m[0] == self.node}
        for law_name, dst_node, domain in verified_out:
            dst_node_data = self.graph.get(dst_node, {"causes": [], "effects": []})
            # 目标节点的总出边数
            total_out = len(dst_node_data["effects"])
            # 已知的目标节点出边 (从记忆中)
            known_out = len({m[2] for m in self.memory if m[0] == dst_node})
            # 未探索边数 = 价值
            unexplored = max(0, total_out - known_out)
            # 跨域奖励: 如果目标节点在不同域
            cross_bonus = 1.5 if domain not in {m[3] for m in self.memory[-10:]} else 0
            score = 1.0 + unexplored * 0.5 + cross_bonus
            scored.append((score, law_name, dst_node, domain))

        # 加权随机选择 (不总是选最高分, 保留一定探索性)
        total = sum(s[0] for s in scored)
        r = random.random() * total
        cumulative = 0
        for score, law_name, dst_node, domain in scored:
            cumulative += score
            if r <= cumulative:
                break
        else:
            _, law_name, dst_node, domain = scored[-1]

        self.memory.append((self.node, law_name, dst_node, domain))
        if len(self.memory) > self.MAX_MEMORY:
            self.memory = self.memory[-self.MAX_MEMORY:]

        old = self.node
        self.node = dst_node

        # 弱信号注册 (按边分散)
        edge_key = f"{old}->{dst_node}"
        self.board.register_expectation(
            f"learn:{edge_key}",
            f"学习: {old} --[{law_name}]--> {dst_node}",
            importance=0.1,
            location=edge_key,
        )

        return {"type": "learn", "from": old, "to": dst_node,
                "via": law_name, "domain": domain,
                "memory": len(self.memory)}

    # ── 回顾行为 ──

    def _act_teach(self) -> Dict:
        """年老细胞分享最独特的记忆给黑板, 让同节点细胞学习。
        独特记忆 = 自己走过但黑板上很少出现的边。"""
        if len(self.memory) < 3:
            return {"type": "observe", "node": self.node, "detail": "无可教"}

        # 找到最罕见的记忆 (在最近黑板预期中出现次数最少的)
        from collections import Counter
        board_ids = Counter(e["id"] for e in self.board.expectations[-100:])

        rarest = None
        rarest_count = float("inf")
        for m in self.memory:
            edge_id = f"teach:{m[0]}->{m[2]}"
            count = board_ids.get(edge_id, 0)
            if count < rarest_count:
                rarest_count = count
                rarest = m

        if rarest:
            src, law, dst, dom = rarest
            self.board.register_expectation(
                f"teach:{src}->{dst}",
                f"教学: {src} --[{law}]--> {dst} ({dom})",
                importance=0.5,
                location=src,
            )
            return {"type": "teach", "from": src, "to": dst, "domain": dom}

        return {"type": "observe", "node": self.node, "detail": "无新知识可教"}

    # ── 回顾行为 (修正版) ──

    def _act_review(self, env) -> Dict:
        """有经验的细胞回顾记忆, 注册发现的模式。
        比如: '我走过 action→force→acceleration→velocity 好几次了, 
        这个模式值得注意'"""
        if len(self.memory) < 3:
            return {"type": "observe", "node": self.node, "detail": "记忆不足"}

        # 统计记忆中最常见的因果对
        from collections import Counter
        pair_counts = Counter((m[0], m[2]) for m in self.memory)
        most_common = pair_counts.most_common(3)

        results = []
        for (src, dst), count in most_common:
            if count >= 2 and src != dst:  # 跳过自环
                domains = {m[3] for m in self.memory if m[0] == src and m[2] == dst}
                self.board.register_expectation(
                    f"review:{src}->{dst}",
                    f"回顾发现: {src}→{dst} 常见 ({count}次, 域{domains})",
                    importance=0.2 + count * 0.05,  # 弱信号, 不主导共识
                    location=src,  # 注册在模式起源节点, 分散热度
                )
                results.append(f"{src}→{dst}")

        if results:
            return {"type": "review", "node": self.node, "patterns": results}
        return {"type": "observe", "node": self.node, "detail": "无显著模式"}

    # ── 基于记忆的桥接 ──

    def _act_bridge_from_memory(self, env) -> Dict:
        """孤岛节点: 从记忆中找结构相似的已连接节点"""
        if len(self.memory) < self.MEMORY_FOR_PROPOSAL:
            return self._act_bridge(env)  # 降级到旧逻辑

        # 从记忆中提取: 见过哪些 (src → dst) 模式
        patterns = defaultdict(list)
        for src, law, dst, dom in self.memory:
            patterns[src].append((dst, law, dom))

        # 当前节点是孤岛 (无 causes), 找记忆中哪些 src 也是"后来才有来源"的
        for mem_src, mem_dsts in patterns.items():
            mem_node = self.graph.get(mem_src, {"causes": [], "effects": []})
            # 如果记忆中的 src 现在已经有 causes (说明它后来被桥接了)
            # 而且它的 effects 和当前节点相似
            if len(mem_node["causes"]) > 0:
                my_effects = {e[1] for e in self.graph.get(self.node, {}).get("effects", [])}
                mem_effects = {e[1] for e in mem_node["effects"]}
                overlap = len(my_effects & mem_effects)
                if overlap > 0:
                    # 找到给 mem_src 提供 causes 的那些节点
                    mem_sources = [c[0] for c in mem_node["causes"]]
                    for potential_src in mem_sources:
                        if potential_src in self.graph:
                            self.board.register_expectation(
                                f"membridge:{potential_src}->{self.node}",
                                f"记忆类比: {potential_src}→{self.node} (参考{potential_src}→{mem_src})",
                                importance=1.0 + overlap * 0.2,
                                location=self.node,
                            )
                            return {"type": "memory_bridge", "from": potential_src,
                                    "to": self.node, "reference": mem_src}

        return self._act_bridge(env)

    # ── 基于记忆的扩展 ──

    def _act_extend_from_memory(self, env) -> Dict:
        """死胡同节点: 从记忆中找同类节点的下游"""
        if len(self.memory) < self.MEMORY_FOR_PROPOSAL:
            return self._act_extend(env)

        # 找记忆中与当前节点同域的节点, 看它们的下游是什么
        in_doms = env["in_domains"]
        candidates = defaultdict(float)

        for src, law, dst, dom in self.memory:
            if dom in in_doms and src != self.node and dst != src:  # 排除自环
                # 检查 dst 是否在当前图中存在
                if dst in self.graph:
                    candidates[dst] += 1.0

        if candidates:
            best = max(candidates, key=candidates.get)
            # 排除自环
            if best == self.node:
                del candidates[best]
                if not candidates:
                    return self._act_extend(env)
                best = max(candidates, key=candidates.get)
            score = candidates[best]
            self.board.register_expectation(
                f"memextend:{self.node}->{best}",
                f"记忆延伸: {self.node}→{best} (同域{in_doms}, 得分{score:.1f})",
                importance=min(1.0 + score * 0.5, 5.0),
                location=self.node,
            )
            return {"type": "memory_extend", "from": self.node, "to": best,
                    "score": score}

        return self._act_extend(env)

    # ── 原有行为 (降级后备) ──

    def _act_bridge(self, env) -> Dict:
        """旧桥接逻辑"""
        my_effects = {e[1] for e in self.graph.get(self.node, {}).get("effects", [])}
        best, best_sim = None, 0
        for var, node in self.graph.items():
            if var == self.node: continue
            if not node["causes"]: continue
            var_effects = {e[1] for e in node["effects"]}
            sim = len(my_effects & var_effects)
            if sim > best_sim:
                best_sim, best = sim, var
        if best and best_sim > 0:
            self.board.register_expectation(
                f"bridge:{best}->{self.node}",
                f"孤岛 {self.node} 可能桥接到 {best} (共享{best_sim}效应)",
                importance=0.5 + best_sim * 0.1,
                location=self.node,
            )
            return {"type": "bridge", "from": best, "to": self.node, "sim": best_sim}
        return {"type": "observe", "node": self.node, "detail": "无桥接候选"}

    def _act_extend(self, env) -> Dict:
        """旧扩展逻辑"""
        return {"type": "observe", "node": self.node, "detail": "需要学习更多"}

    def _act_audit(self, env) -> Dict:
        """审计: 守恒量无对称来源"""
        expected_sym = {"energy": "time_translation", "momentum": "space_translation",
                        "charge": "U1_gauge", "angular_momentum": "rotation"}
        sym = expected_sym.get(self.node, "unknown_symmetry")
        self.board.register_expectation(
            f"sym_source:{self.node}",
            f"{self.node} 应该有对称来源 '{sym}'",
            importance=2.0,
            location=self.node,
        )
        return {"type": "audit", "node": self.node,
                "detail": f"注册预期: {sym} → {self.node}"}

    def _act_analogy(self, env) -> Dict:
        """类比: 跨域结构同构"""
        my_structure = (env["in_deg"], env["out_deg"])
        for var, node in self.graph.items():
            if var == self.node: continue
            var_env = {"in_deg": len(node["causes"]), "out_deg": len(node["effects"])}
            if (var_env["in_deg"], var_env["out_deg"]) == my_structure:
                self.board.register_expectation(
                    f"analogy:{self.node}↔{var}",
                    f"{self.node} 与 {var} 结构同构",
                    importance=0.5,
                    location=self.node,
                )
                return {"type": "analogy", "with": var, "node": self.node}
        return {"type": "observe", "node": self.node, "detail": "无同构匹配"}

    # ── 复制 ──

    def replicate(self) -> List[GraphCell]:
        """复制: 只往知识稀疏的邻居分裂。
        优先: 细胞密度低 + 域新颖 + 问题评分高。
        不往细胞已经密集的节点繁殖——那是癌症。"""
        node = self.graph.get(self.node, {"causes": [], "effects": []})
        neighbors = set()
        for _, dst, _ in node["effects"]:
            neighbors.add(dst)
        for _, src, _ in node["causes"]:
            neighbors.add(src)

        if not neighbors:
            return []

        children = []
        for nb in neighbors:
            nb_node = self.graph.get(nb, {"causes": [], "effects": []})
            in_d = len(nb_node["causes"])
            out_d = len(nb_node["effects"])
            is_conserved = nb in {"energy", "momentum", "charge", "angular_momentum"}
            has_sym = any(any(kw in c[0].lower()
                             for kw in ("symmetry", "gauge", "noether"))
                          for c in nb_node["causes"])

            # 问题评分 + 基础繁殖权 (健康节点也能低速繁殖, 维持种群)
            problem_score = 1.0
            if in_d == 0: problem_score += 2.0
            if out_d == 0: problem_score += 2.0
            if is_conserved and in_d > 0 and not has_sym: problem_score += 3.0

            prob = min(0.10 * problem_score + 0.05, 0.80)  # 基础5% + 问题加成
            if random.random() < prob:
                child = GraphCell(nb, self.graph, self.board)
                child.specialization = self.specialization
                child.memory = self.memory[-5:].copy()
                children.append(child)

        return children[:3]  # 限制每代最多3个


class Blackboard:
    """共享黑板 — 细胞注册预期, 共振触发啊哈"""

    def __init__(self):
        self.expectations = []
        self.signals = []
        self.threshold = 2.0    # 降低共识阈值

    def register_expectation(self, eid: str, desc: str,
                             importance: float, location: str):
        self.expectations.append({
            "id": eid, "desc": desc, "importance": importance,
            "location": location, "time": time.time(),
        })

    def detect_resonance(self) -> List[Dict]:
        by_location = defaultdict(float)
        for exp in self.expectations[-100:]:
            by_location[exp["location"]] += exp["importance"]

        signals = []
        for loc, total in sorted(by_location.items(), key=lambda x: -x[1]):
            if total >= self.threshold:
                related = [e for e in self.expectations if e["location"] == loc]
                signals.append({
                    "location": loc,
                    "importance": round(total, 1),
                    "cells_agreed": len(related),
                    "top_expectation": related[0]["desc"] if related else "",
                    "top_id": related[0]["id"] if related else "",
                })

        self.signals = signals
        return signals


def _count_specs(cells: List[GraphCell]) -> Dict:
    from collections import Counter
    return dict(Counter(c.specialization for c in cells if c.specialization))


def simulate_cycle(graph: Dict = None, cycles: int = 10) -> Dict:
    from physics.laws import library
    if graph is None:
        graph = {}
        for law in library._laws:
            for src, dst in law.causal_direction:
                if src not in graph:
                    graph[src] = {"causes": [], "effects": []}
                if dst not in graph:
                    graph[dst] = {"causes": [], "effects": []}
                graph[src]["effects"].append((law.name, dst, law.domain))
                graph[dst]["causes"].append((dst, law.name, law.domain))

    board = Blackboard()
    cells = []
    for node_id, node in graph.items():
        in_d = len(node["causes"])
        out_d = len(node["effects"])
        is_conserved = node_id in {"energy", "momentum", "charge", "angular_momentum"}
        has_sym = any(any(kw in c[0].lower()
                         for kw in ("symmetry", "gauge", "noether"))
                      for c in node["causes"])
        if in_d == 0 or out_d == 0 or (is_conserved and in_d > 0 and not has_sym):
            cell = GraphCell(node_id, graph, board)
            cells.append(cell)
    cells = cells[:20]

    results = []
    for _ in range(cycles):
        new_cells = []
        for cell in cells:
            cell.age += 1
            result = cell.act()
            results.append(result)
            children = cell.replicate()
            new_cells.extend(children)
        cells = cells[:15] + new_cells
        cells = cells[:30]

    signals = board.detect_resonance()
    return {
        "cycles": cycles,
        "total_cells": len(cells),
        "specializations": _count_specs(cells),
        "expectations": len(board.expectations),
        "resonance": len(signals),
        "top_signals": signals[:5],
        "actions": len(results),
    }


def cell_report() -> str:
    r = simulate_cycle(cycles=10)
    lines = ["══════ 细胞模拟 v2 (具身学习) ══════"]
    lines.append(f"  周期: {r['cycles']} | 细胞: {r['total_cells']}")
    lines.append(f"  分化: {r['specializations']}")
    lines.append(f"  预期: {r['expectations']} | 共振: {r['resonance']}")
    if r["top_signals"]:
        lines.append("")
        lines.append("  共识发现:")
        for s in r["top_signals"]:
            lines.append(f"    ✨ {s['location']}: {s['top_expectation'][:60]}")
            lines.append(f"       {s['cells_agreed']}细胞共识, 重要性={s['importance']}")
    return "\n".join(lines)
