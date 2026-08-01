"""
细胞殖民地 — 诺特的自组织心智 (持久版)

殖民地是活的:
  - 初始只有一个细胞
  - 每次 breathe() 让所有细胞呼吸一次 (感知→行动→复制→老化→死亡)
  - 细胞数量自然增长, 直到达到环境容量
  - 保存到 data/cell_colony.json
"""

from __future__ import annotations
import json, os, time, random
from typing import Dict, List, Tuple
from meta_cognition.graph_cells import GraphCell, Blackboard


COLONY_PATH = None


def _colony_path() -> str:
    global COLONY_PATH
    if COLONY_PATH is None:
        COLONY_PATH = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "cell_colony.json"
        )
    return COLONY_PATH


def _build_graph():
    """构建因果图"""
    from physics.laws import library
    graph = {}
    for law in library._laws:
        for src, dst in law.causal_direction:
            if src not in graph: graph[src] = {"causes": [], "effects": []}
            if dst not in graph: graph[dst] = {"causes": [], "effects": []}
            graph[src]["effects"].append((law.name, dst, law.domain))
            graph[dst]["causes"].append((dst, law.name, law.domain))
    return graph


class Colony:
    """活细胞殖民地"""

    MAX_CELLS = 500          # 硬上限
    SOFT_CAP = 350           # 软上限: 超过后密度致死率上升
    MAX_AGE = 200            # 细胞最大寿命 (避免年龄同步坍塌)
    STARVATION_WINDOW = 999  # 暂时关闭饥饿
    REDUNDANCY_LIMIT = 20    # 同节点同分化超过此数 → 淘汰
    UNDIFF_DEADLINE = 60     # 超过此年龄未分化 → 凋亡
    EDGE_DECAY_RATE = 0.1    # 每代衰减
    EDGE_PRUNE_THRESHOLD = 1.0  # 低于此值 → 修剪
    BREATHE_INTERVAL = 30    # 呼吸间隔 (秒) — 用于计算代际

    def __init__(self):
        self.graph = _build_graph()
        self.board = Blackboard()
        self.cells: List[GraphCell] = []
        self.generation = 0
        self.total_actions = 0
        self.total_discoveries = 0
        self.birth_time = time.time()
        # 生物调控
        self._edge_strengths: Dict[str, float] = {}  # edge_name → strength
        self._death_stats = {"age": 0, "starvation": 0, "redundancy": 0,
                            "undifferentiated": 0, "density": 0}
        self._pruned_log: List[dict] = []  # 被修剪的边记录
        self._gap_queue: List[dict] = []  # 待文献验证的缺口
        self._load()

    def _load(self):
        path = _colony_path()
        if os.path.exists(path):
            try:
                with open(path) as f:
                    state = json.load(f)
                self.generation = state.get("generation", 0)
                self.total_actions = state.get("total_actions", 0)
                self.total_discoveries = state.get("discoveries", 0)
                self.birth_time = state.get("birth_time", time.time())
                self.board.threshold = state.get("threshold", 3.0)
                self.grown_edges = state.get("grown_edges", 0)
                self._edge_strengths = state.get("edge_strengths", {})
                self._rejected_edges = state.get("rejected_edges", [])
                self._immune_memory = set(tuple(p) for p in state.get("immune_memory", []))
                self._pruned_log = state.get("pruned_log", [])
                self._gap_queue = state.get("gap_queue", [])
                self._death_stats = state.get("death_stats",
                    {"age": 0, "starvation": 0, "redundancy": 0,
                     "undifferentiated": 0, "density": 0})
                self._recent_growth = []
                # 恢复预期
                for exp in state.get("expectations", []):
                    self.board.expectations.append(exp)
                # 恢复共识
                for sig in state.get("signals", []):
                    self.board.signals.append(sig)
                print(f"殖民地恢复: 世代{self.generation}, {len(self.board.expectations)}预期")
            except: pass

        # 如果没有细胞, 播种初始细胞
        if not self.cells:
            self._seed()

    def _save(self):
        path = _colony_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        state = {
            "generation": self.generation,
            "total_actions": self.total_actions,
            "discoveries": self.total_discoveries,
            "birth_time": self.birth_time,
            "cell_count": len(self.cells),
            "threshold": self.board.threshold,
            "expectations": self.board.expectations[-200:],
            "signals": self.board.signals[-50:],
            "specializations": _count_specs(self.cells),
            "grown_edges": getattr(self, 'grown_edges', 0),
            "edge_strengths": getattr(self, '_edge_strengths', {}),
            "rejected_edges": getattr(self, '_rejected_edges', [])[-20:],
            "immune_memory": list(getattr(self, '_immune_memory', set())),
            "pruned_log": getattr(self, '_pruned_log', [])[-30:],
            "gap_queue": getattr(self, '_gap_queue', []),
            "death_stats": getattr(self, '_death_stats', {}),
        }
        with open(path, "w") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def _seed(self):
        """播种: 在问题最多的节点放初始细胞"""
        candidates = []
        for node_id, node in self.graph.items():
            in_d = len(node["causes"])
            out_d = len(node["effects"])
            is_conserved = node_id in {"energy", "momentum", "charge", "angular_momentum"}
            has_sym = any(any(kw in c[0].lower() for kw in ("symmetry", "gauge", "noether"))
                          for c in node["causes"])
            problem_score = 0
            if in_d == 0: problem_score += 1
            if out_d == 0: problem_score += 0.5
            if is_conserved and in_d > 0 and not has_sym: problem_score += 2
            if problem_score > 0:
                candidates.append((node_id, problem_score))

        # 集中播种: 5个关键节点 × 各3个细胞 (密度>广度, 初始就能共振)
        candidates.sort(key=lambda x: -x[1])
        seeds = []
        for node_id, score in candidates[:5]:
            for _ in range(3):  # 每个节点3个种子
                seeds.append((node_id, score))
        # 再加5个随机节点各1个 (探索)
        all_nodes = list(self.graph.keys())
        random.shuffle(all_nodes)
        extra = 0
        for node_id in all_nodes:
            if extra >= 5: break
            if node_id not in {s[0] for s in seeds}:
                seeds.append((node_id, 1.0))
                extra += 1
        
        for i, (node_id, _) in enumerate(seeds):
            cell = GraphCell(node_id, self.graph, self.board)
            cell.age = i * 5  # 错开年龄, 避免同步坍塌
            cell.last_contributed_at = self.generation
            self.cells.append(cell)

    def breathe(self, steps: int = 3) -> Dict:
        """一次呼吸: 行动 → 凋亡 → 繁殖 → 修剪 → 共识 → 生长。
        完整的生物周期。"""
        deaths_by_cause = {"age": 0, "starvation": 0, "redundancy": 0,
                          "undifferentiated": 0, "density": 0}

        for _ in range(steps):
            self.generation += 1

            # ── 1. 所有细胞行动 ──
            for cell in self.cells:
                cell.age += 1
                result = cell.act()
                self.total_actions += 1

            # ── 2. 凋亡 (在繁殖之前, 只有适者能繁殖) ──
            survivors, cause_counts = self._apoptosis()
            for k, v in cause_counts.items():
                deaths_by_cause[k] += v

            # ── 3. 繁殖 (幸存者才有资格) ──
            new_cells = []
            for cell in survivors:
                # 有空间 + 概率繁殖
                space_left = self.SOFT_CAP - len(survivors) - len(new_cells)
                if space_left > 0 and random.random() < 0.45:
                    children = cell.replicate()
                    for child in children:
                        child.last_contributed_at = self.generation  # 新生儿宽限期
                    new_cells.extend(children[:min(len(children), space_left)])

            survivors.extend(new_cells)
            self.cells = survivors

            # ── 4. 边衰减 ──
            self._decay_edges()

            # ── 5. 突触修剪 ──
            pruned = self._prune_edges()
            if pruned:
                self._pruned_log.extend(pruned)
                if len(self._pruned_log) > 50:
                    self._pruned_log = self._pruned_log[-50:]

            # ── 6. 共识检测 ──
            signals = self.board.detect_resonance()
            if signals:
                self.total_discoveries += len(signals)
                # 给所有在共识位置上的细胞更新贡献
                resonant_locations = {s["location"] for s in signals}
                for cell in self.cells:
                    if cell.node in resonant_locations:
                        cell.contributions += 1
                        cell.last_contributed_at = self.generation

            # ── 7. 共识材料化 (通过验证闸门) ──
            self._materialize_signals(signals)

        # 更新累计
        for k, v in deaths_by_cause.items():
            self._death_stats[k] += v

        self._save()

        return {
            "generation": self.generation,
            "cells": len(self.cells),
            "deaths": deaths_by_cause,
            "pruned": sum(1 for p in self._pruned_log[-steps:]),
            "expectations": len(self.board.expectations),
            "specs": _count_specs(self.cells),
        }

    def _apoptosis(self) -> Tuple[List[GraphCell], Dict[str, int]]:
        """程序性细胞死亡: 年龄/饥饿/冗余/未分化/密度。
        返回 (幸存者列表, 死因统计)"""
        counts = {"age": 0, "starvation": 0, "redundancy": 0,
                  "undifferentiated": 0, "density": 0}
        survivors = []

        # 按节点+分化分组 (用于冗余检查)
        from collections import defaultdict
        by_node_spec = defaultdict(list)
        for i, cell in enumerate(self.cells):
            key = (cell.node, cell.specialization)
            by_node_spec[key].append(i)

        total = len(self.cells)

        for i, cell in enumerate(self.cells):
            dead = False

            # 年龄死亡
            if cell.age > self.MAX_AGE:
                counts["age"] += 1
                dead = True

            # 饥饿死亡: N代无贡献
            elif (self.generation - cell.last_contributed_at > self.STARVATION_WINDOW
                  and random.random() < 0.08):  # 8% 概率 (温和)
                counts["starvation"] += 1
                dead = True

            # 冗余死亡: 同节点同分化超过限制 → 保留记忆最独特的
            elif not dead:
                key = (cell.node, cell.specialization)
                same_group = by_node_spec.get(key, [])
                if len(same_group) > self.REDUNDANCY_LIMIT:
                    # 计算群体中每个细胞的记忆独特性
                    group_cells = [self.cells[j] for j in same_group]
                    # 记忆重叠度: 对每个细胞, 计算与其他细胞的 Jaccard 相似度均值
                    mem_sets = []
                    for gc in group_cells:
                        mem_sets.append({(m[0], m[2]) for m in gc.memory})
                    
                    overlap_scores = []
                    for i, ms in enumerate(mem_sets):
                        if not ms:
                            overlap_scores.append((1.0, i))  # 无记忆=最该淘汰
                            continue
                        total_sim = 0.0
                        for j, ms2 in enumerate(mem_sets):
                            if i == j: continue
                            if not ms2: continue
                            union = len(ms | ms2)
                            inter = len(ms & ms2)
                            total_sim += inter / max(union, 1)
                        avg_sim = total_sim / max(len(mem_sets) - 1, 1)
                        overlap_scores.append((avg_sim, i))
                    
                    # 按重叠度降序 (最重叠的排前面, 先杀)
                    overlap_scores.sort(key=lambda x: -x[0])
                    to_kill = len(group_cells) - self.REDUNDANCY_LIMIT
                    kill_indices = {overlap_scores[k][1] for k in range(to_kill)}
                    
                    if group_cells.index(cell) in kill_indices:
                        counts["redundancy"] += 1
                        dead = True

            # 未分化死亡
            if not dead and cell.age > self.UNDIFF_DEADLINE and not cell.specialization:
                if random.random() < 0.35:
                    counts["undifferentiated"] += 1
                    dead = True

            # 密度死亡: 超过软上限
            if not dead and total > self.SOFT_CAP:
                excess_ratio = (total - self.SOFT_CAP) / (self.MAX_CELLS - self.SOFT_CAP)
                if random.random() < excess_ratio * 0.3:
                    counts["density"] += 1
                    dead = True

            if not dead:
                survivors.append(cell)

        return survivors, counts

    def status(self) -> str:
        age_sec = time.time() - self.birth_time
        age_str = f"{int(age_sec//3600)}h{int((age_sec%3600)//60)}m"
        signals = self.board.detect_resonance()
        specs = _count_specs(self.cells)
        grown = getattr(self, 'grown_edges', 0)
        rejected = getattr(self, '_rejected_edges', [])
        strengths = getattr(self, '_edge_strengths', {})
        deaths = getattr(self, '_death_stats', {})
        pruned_log = getattr(self, '_pruned_log', [])
        
        # 记忆统计
        cells_with_mem = sum(1 for c in self.cells if c.memory)
        total_mem = sum(len(c.memory) for c in self.cells)
        avg_mem = total_mem / max(len(self.cells), 1)
        # 学习 vs 提议: 年轻细胞(<10代)=学习, 有记忆的老年细胞=提议
        from meta_cognition.graph_cells import GraphCell
        learning = sum(1 for c in self.cells if c.age < GraphCell.LEARN_UNTIL_AGE)
        proposing = sum(1 for c in self.cells
                       if c.age >= GraphCell.LEARN_UNTIL_AGE and len(c.memory) >= GraphCell.MEMORY_FOR_PROPOSAL)
        
        lines = [f"🧫 诺特殖民地 | 世代{self.generation} | 年龄{age_str}"]
        lines.append(f"   细胞: {len(self.cells)}/{self.MAX_CELLS} (软上限{self.SOFT_CAP})"
                     f" | 预期: {len(self.board.expectations)}")
        lines.append(f"   分化: {specs} | 学习:{learning} 提议:{proposing}"
                     f" | 记忆: {total_mem}条(均{avg_mem:.1f})"
                     f" | 生长边: {grown} | 拒绝: {len(rejected)}")
        lines.append(f"   行动: {self.total_actions} | 发现: {self.total_discoveries}")
        # 死亡统计
        if deaths:
            total_deaths = sum(deaths.values())
            if total_deaths > 0:
                cause_str = " ".join(f"{k}:{v}" for k, v in sorted(deaths.items()) if v > 0)
                lines.append(f"   💀 累计死亡 {total_deaths} ({cause_str})")
        # 边强度分布
        if strengths:
            strong = sum(1 for v in strengths.values() if v >= 5.0)
            weak = sum(1 for v in strengths.values() if 1.0 <= v < 5.0)
            lines.append(f"   🔗 边强度: 强{strong} 弱{weak} | 已修剪: {len(pruned_log)}")
        # 最近被修剪的边
        if pruned_log:
            for p in pruned_log[-2:]:
                lines.append(f"   ✂ 已修剪 {p['edge']} @代{p['generation']}")
        # 最近的生长边
        if hasattr(self, '_recent_growth') and self._recent_growth:
            for g in self._recent_growth[-2:]:
                lines.append(f"   🌱 {g}")
        # 被拒绝的边
        if rejected:
            lines.append(f"   ❌ 被物理验证拒绝:")
            for r in rejected[-2:]:
                lines.append(f"      {r['src']} → {r['dst']}: {r['reason']}")
        # 缺口队列
        gaps = getattr(self, '_gap_queue', [])
        if gaps:
            unresolved = [g for g in gaps if not g.get("resolved")]
            if unresolved:
                lines.append(f"   🔬 待验证缺口 ({len(unresolved)}):")
                for g in unresolved[-3:]:
                    lines.append(f"      {g['src']} → {g['dst']} "
                                 f"(共识{g['consensus']}, {g['cells']}细胞)")
        if signals:
            lines.append(f"   最新共识:")
            for s in signals[:2]:
                lines.append(f"     ✨ {s['location']}: {s['top_expectation'][:50]}")
                lines.append(f"        {s['cells_agreed']}细胞共识")
        return "\n".join(lines)

    def _decay_edges(self):
        """所有殖民地生长的边每代衰减"""
        for name in list(self._edge_strengths.keys()):
            self._edge_strengths[name] = max(0, self._edge_strengths[name] - self.EDGE_DECAY_RATE)

    def _prune_edges(self) -> List[dict]:
        """突触修剪: 删除强度低于阈值的边。返回被修剪的边列表。"""
        pruned = []
        for name in list(self._edge_strengths.keys()):
            if self._edge_strengths[name] < self.EDGE_PRUNE_THRESHOLD:
                # 找到并删除图中的边
                edge_parts = name.split("_", 1)  # "grown_N"
                for node_id, node in self.graph.items():
                    # 从 effects 中删除
                    old_len = len(node["effects"])
                    node["effects"] = [e for e in node["effects"]
                                       if e[0] != name]
                    if len(node["effects"]) < old_len:
                        removed_dst = None
                        # 也需要从目标的 causes 中删除
                        # (在 effects 循环中我们不知道目标是谁)
                        pass
                # 从 causes 中删除
                for node_id, node in self.graph.items():
                    node["causes"] = [c for c in node["causes"]
                                      if c[1] != name]

                del self._edge_strengths[name]
                self.grown_edges -= 1
                pruned.append({
                    "edge": name,
                    "final_strength": round(self._edge_strengths.get(name, 0), 2),
                    "generation": self.generation
                })
        return pruned

    def _validate_edge(self, src: str, dst: str) -> Tuple[bool, str]:
        """物理验证: 检查殖民地的边是否违反已知物理定律。
        返回 (pass, reason)"""
        from physics.constraints import PhysicsConstrainedDAG

        # 1. 基本合理性
        if src == dst:
            return False, "self-loop"

        all_vars = list(self.graph.keys())
        constraint = PhysicsConstrainedDAG(all_vars)

        # 2. 直接 forbidden 检查
        for f_src, f_dst in constraint.forbidden_edges:
            if f_src == src and f_dst == dst:
                return False, f"forbidden: {f_src} → {f_dst}"

        # 3. 连通性检查: 已验证图中 src→dst 有无已知路径?
        #    如果没有, 说明这两个概念属于完全不相连的物理领域,
        #    殖民地的模式匹配大概率是假关联
        verified_path = self._path_exists(src, dst, exclude_emergence=True)
        if not verified_path:
            # 反向也检查 (A→B不存在但B→A存在? 方向错了?)
            reverse_path = self._path_exists(dst, src, exclude_emergence=True)
            if reverse_path:
                return False, f"reverse_only: 已验证图有 {dst}→{src}, 非 {src}→{dst}"
            return False, f"no_path: {src}和{dst}在已验证图中无连通路径"

        return True, "pass"

    def _path_exists(self, src: str, dst: str, exclude_emergence: bool = True,
                     max_depth: int = 8) -> bool:
        """BFS: src 到 dst 在已验证图中是否有路径。
        exclude_emergence=True 时忽略殖民地自己长的边。"""
        if src not in self.graph or dst not in self.graph:
            return False
        visited = {src}
        frontier = [src]
        for _ in range(max_depth):
            if not frontier:
                break
            node = frontier.pop(0)
            for edge_name, neighbor, domain in self.graph[node]["effects"]:
                if exclude_emergence and domain == "emergence":
                    continue
                if neighbor == dst:
                    return True
                if neighbor not in visited:
                    visited.add(neighbor)
                    frontier.append(neighbor)
        return False

    def _materialize_signals(self, signals):
        """共识成熟: 把高重要性信号变成真实的因果边。
        所有殖民地生成的边标记为 tier 4 (探索性, 未验证)"""
        import re
        if not hasattr(self, 'grown_edges'):
            self.grown_edges = 0
            self._recent_growth = []
            self._rejected_edges = []  # 被物理验证拒绝的边
            self._immune_memory = set()  # 已拒绝的 (src, dst) 对, 不再重试

        for sig in signals:
            if sig["importance"] < 3.0:  # 记忆提议阈值 (比随机更低)
                continue

            loc = sig["location"]
            top_exp = sig["top_expectation"]

            # 解析预期类型
            src = dst = None
            eid = sig.get("top_id", "")
            if "memextend:" in eid or "memextend:" in top_exp:
                # 记忆延伸: "lorentz_force→acceleration"
                m = re.search(r'(\w+)\s*→\s*(\w+)', top_exp)
                if m:
                    src, dst = m.group(1), m.group(2)
            elif "membridge:" in eid:
                m = re.search(r'(\w+)\s*→\s*(\w+)', top_exp)
                if m:
                    src, dst = m.group(1), m.group(2)
            elif "bridge:" in top_exp or "孤岛" in top_exp:
                m = re.search(r'桥接到 (\w+)', top_exp)
                if m:
                    src = m.group(1)
                    dst = loc
            elif "扩展" in top_exp or "下游" in top_exp:
                m = re.search(r'下游 (\w+)', top_exp)
                if m:
                    src = loc
                    dst = m.group(1)

            if src and dst and src in self.graph and dst in self.graph:
                # 免疫记忆: 已拒绝的边不再重试
                if (src, dst) in self._immune_memory:
                    continue
                # 检查是否已存在
                existing = any(e[1] == dst for e in self.graph[src]["effects"])
                if not existing:
                    # === 物理验证闸门 ===
                    valid, reason = self._validate_edge(src, dst)
                    if not valid:
                        self._rejected_edges.append({
                            "src": src, "dst": dst,
                            "consensus": sig["importance"],
                            "reason": reason,
                            "expectation": top_exp[:100]
                        })
                        self._immune_memory.add((src, dst))
                        # 高共识 no_path → 进入缺口队列 (待文献验证)
                        if reason.startswith("no_path") and sig["importance"] > 5.0:
                            self._gap_queue.append({
                                "src": src, "dst": dst,
                                "consensus": round(sig["importance"], 1),
                                "cells": sig["cells_agreed"],
                                "generation": self.generation,
                                "source": "colony",
                            })
                        continue
                    # === 通过验证, 标记 tier 4 ===
                    edge_name = "grown_" + str(self.grown_edges)
                    self.graph[src]["effects"].append((edge_name, dst, "emergence"))
                    self.graph[dst]["causes"].append((dst, edge_name, "emergence"))
                    self._edge_strengths[edge_name] = sig["importance"]  # 初始强度=共识
                    self.grown_edges += 1
                    self._recent_growth.append(
                        f"⚠ tier4 {src} → {dst} (共识={sig['importance']:.0f})"
                    )
                    if len(self._recent_growth) > 20:
                        self._recent_growth = self._recent_growth[-20:]


def _count_specs(cells):
    from collections import Counter
    return dict(Counter(c.specialization for c in cells if c.specialization))


# 全局殖民地实例
_colony_instance = None

def get_colony() -> Colony:
    global _colony_instance
    if _colony_instance is None:
        _colony_instance = Colony()
    return _colony_instance

def colony_breathe(steps: int = 3) -> str:
    colony = get_colony()
    result = colony.breathe(steps)
    return colony.status()

def colony_status() -> str:
    return get_colony().status()
