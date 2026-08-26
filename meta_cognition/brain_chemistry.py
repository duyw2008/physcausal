"""
诺特脑化学层 — 多巴胺/注意力/惊奇/抑制/共识

所有化学信号在此集中定义。evo_colony 只负责收集事件，调用本模块评估，
然后应用返回的信号到细胞。

设计原则：
  - 不碰细胞代码，只在奖励层决定给多少多巴胺
  - 系数、阈值、surge 条件全在这里，调参只改一个文件
  - 无状态机，纯函数式评估
"""

from __future__ import annotations
from typing import Dict, List, Set, Tuple, Optional
from collections import Counter


# ═══════ 全局参数 (调参只改这里) ═══════

class ChemistryParams:
    """所有化学系数的单点定义"""

    # ── 多巴胺: 路径发现 ──
    DOPAMINE_PATH_LENGTH_EXPONENT = 1.5   # base = 1.0 × length^exponent
    DOPAMINE_CROSS_DOMAIN_PER_EXTRA = 3.0  # ↑2.0→3.0: 跨域更值钱
    DOPAMINE_CREATIVE_LEAP_MULT = 2.0      # 创意跳跃翻倍
    DOPAMINE_NOVELTY_NEW = 0.8             # 新路径基线reward (探索行为值得奖, 非惩罚; 深耕仍更高)
    DOPAMINE_NOVELTY_KNOWN = 1.5           # 已知路径高reward (预测命中→模型对)
    PREDICTION_SURPRISE_DRIVE = 0.5        # 惊奇→提升curiosity探索驱动
    REGISTRATION_BONUS = 0.4               # 首次注册路径的激励 (非reward, 促进建模)

    # ── Eureka 爆发 ──
    EUREKA_MIN_LENGTH = 5                  # 最少跳数
    EUREKA_MIN_DOMAINS = 3                 # 最少的域数
    EUREKA_MULTIPLIER = 4.0                # ↑3.0→4.0: Eureka更猛烈

    # ── 惊奇: 新路到熟地 ──
    SURPRISE_MULTIPLIER = 0.5              # 基础奖励×此倍数
    SURPRISE_HOT_THRESHOLD = 15            # coincidence≥此数算"热门边"
    SURPRISE_HUB_MIN_EDGES = 3             # 涉及热门边≥此数=hot hub

    # ── 深耕 (注意力机制) ──
    DEEPEN_PER_STREAK = 0.7                # ↑0.5→0.7: 深耕更值钱
    DEEPEN_CAP = 4.0                       # ↑3.0→4.0
    DEEPEN_MASTERY_STREAK = 10
    DEEPEN_MASTERY_BONUS = 4.0             # ↑3.0→4.0
    DEEPEN_OVERLAP_MIN = 2                 # 子图重叠节点≥此数=同一区域

    # ── 共识共振 ──
    CONSENSUS_HOT_MIN = 5                  # coincidence≥此数算"共识对"
    CONSENSUS_PER_PAIR_MULT = 0.05         # ↑0.03→0.05: 共识更值钱
    CONSENSUS_PER_PAIR_CAP = 0.5
    CONSENSUS_TOTAL_CAP = 4.0              # ↑3.0→4.0
    BREAKTHROUGH_THRESHOLD = 50
    BREAKTHROUGH_BONUS = 5.0
    DIRECTION_RATIO_MIN = 2.0           # 正向/反向≥此数才认因果方向

    # ── 探索基础 ──
    EXPLORE_BASE = 0.3                     # 基础探索奖励
    EXPLORE_DEAD_END_BONUS = 0.4           # 碰壁加成
    EXPLORE_GAP_ORPHAN = 0.15              # ↓0.3→0.15: 继续压边爆炸
    EXPLORE_GAP_DEAD_END = 0.15            # ↓0.3→0.15
    EXPLORE_GAP_ASYMMETRY_MULT = 0.10      # ↓0.2→0.10
    EXPLORE_GAP_CONSERVED_NO_SYM = 0.2     # ↓0.4→0.2

    # ── 低保 ──
    WELFARE_MARK = 0.15                    # mark低保
    WELFARE_ECHO = 0.15                    # echo低保
    WELFARE_RESONANCE = 0.3                # 黑板共振
    WELFARE_REST = 0.25                    # 记忆巩固

    # ── 路径合成 ──
    COMPOSE_PER_PATH = 0.5                 # 每条合成路径奖励
    COMPOSE_ORIGIN_PER_SAME = 0.5          # 同源对比每条

    # ── 抑制 (GABA) ──
    INHIBITION_PER_DEAD_END = 1.0          # 每次碰壁累积抑制分
    INHIBITION_DECAY_RATE = 0.1            # 每50代衰减比例
    INHIBITION_BLOCK_THRESHOLD = 3.0       # 抑制分≥此数 → 拦截边
    INHIBITION_BROADCAST_RADIUS = 1        # 广播: 同节点其他出边也受影响 (0=不广播)

    # ── 情感信号 ──
    EMOTION_FEAR = 0.3                     # 死路→恐惧 (额外多巴胺)
    EMOTION_ANXIETY = 0.2                  # 缺口→焦虑 (引力加成)
    EMOTION_EUPHORIA = 2.0                 # Eureka→欣快 (额外爆发)


# ═══════ 化学引擎 ═══════

class BrainChemistry:
    """无状态的化学信号评估器

    所有方法接收事件输入，返回信号字典。
    evo_colony 负责收集事件、调用评估、应用信号。
    """

    def __init__(self, params: ChemistryParams = None):
        self.p = params or ChemistryParams()
        # 抑制分: (src, dst) → cumulative_inhibition
        self._edge_inhibition: Dict[Tuple[str, str], float] = {}

    # ── 多巴胺: 路径发现 ──

    def eval_mark(self, walk: List, path_key: str, known_paths: Set[str],
                  hot_hubs: Set[str], coincidence: Dict) -> dict:
        """评估 mark 行为的化学信号

        Returns:
            {
                "dopamine": base + bonuses,
                "eureka": bool,
                "surprise_bonus": float,
                "novelty_mult": float,
                "domains_seen": set,
                "has_leap": bool,
                "subgraph": set,
            }
        """
        if len(walk) < 2:
            return {"dopamine": 0.0}

        length = len(walk)

        # 1. 非线性长度
        base = 1.0 * (length ** self.p.DOPAMINE_PATH_LENGTH_EXPONENT)

        # 2. 跨域
        domains_seen = set()
        for step in walk:
            if len(step) >= 4:
                domains_seen.add(step[3])
        cross = max(0, (len(domains_seen) - 1) * self.p.DOPAMINE_CROSS_DOMAIN_PER_EXTRA)

        # 3. 创意跳跃
        has_leap = any(w[1] == "creative_leap" for w in walk)

        # 4. 新颖度
        is_new_path = path_key not in known_paths
        if is_new_path:
            novelty_mult = self.p.DOPAMINE_NOVELTY_NEW
            registration_bonus = self.p.REGISTRATION_BONUS  # 首次注册→激励建模
        else:
            novelty_mult = self.p.DOPAMINE_NOVELTY_KNOWN
            registration_bonus = 0.0

        reward = (base + cross) * (self.p.DOPAMINE_CREATIVE_LEAP_MULT if has_leap else 1.0) * novelty_mult

        # 5. Eureka: 预测命中的长跨域路径 → 大奖励 (模型正确)
        is_eureka = (length >= self.p.EUREKA_MIN_LENGTH and
                     len(domains_seen) >= self.p.EUREKA_MIN_DOMAINS and
                     novelty_mult == self.p.DOPAMINE_NOVELTY_KNOWN)
        if is_eureka:
            reward *= self.p.EUREKA_MULTIPLIER

        # 6. 惊奇 → 学习驱动 (不是reward): 新路到熟地 = 预期落空 → 该探索
        surprise_bonus = 0.0
        surprise_drive = 0.0
        dest_node = walk[-1][2] if len(walk) >= 2 else None
        if dest_node and novelty_mult == self.p.DOPAMINE_NOVELTY_NEW and hot_hubs and dest_node in hot_hubs:
            surprise_drive = self.p.PREDICTION_SURPRISE_DRIVE  # 提升curiosity,不是reward

        # 7. 子图
        subgraph = set(w[2] for w in walk) | {w[0] for w in walk}

        return {
            "dopamine": round(reward, 2),
            "eureka": is_eureka,
            "surprise_bonus": round(surprise_bonus, 2),
            "surprise_drive": round(surprise_drive, 2),
            "registration_bonus": round(registration_bonus, 2),
            "novelty_mult": novelty_mult,
            "domains_seen": domains_seen,
            "has_leap": has_leap,
            "subgraph": subgraph,
            "dest_node": dest_node,
        }

    # ── 注意力: 深耕 ──

    def eval_deepen(self, cell, subgraph: Set[str]) -> dict:
        """评估深耕信号 — 连续在同一子图标记

        使用 cell._deepen_nodes 和 cell._deepen_streak 追踪状态。
        返回: {"deepen_bonus": float, "mastery_bonus": float}
        """
        if not hasattr(cell, '_deepen_nodes'):
            cell._deepen_nodes = set()
            cell._deepen_streak = 0

        overlap = len(subgraph & cell._deepen_nodes)

        if overlap >= self.p.DEEPEN_OVERLAP_MIN:
            cell._deepen_streak += 1
            deepen_bonus = min(cell._deepen_streak * self.p.DEEPEN_PER_STREAK,
                               self.p.DEEPEN_CAP)
            mastery_bonus = self.p.DEEPEN_MASTERY_BONUS if cell._deepen_streak == self.p.DEEPEN_MASTERY_STREAK else 0.0
        else:
            cell._deepen_streak = max(0, cell._deepen_streak - 1)
            deepen_bonus = 0.0
            mastery_bonus = 0.0

        cell._deepen_nodes = subgraph

        return {"deepen_bonus": deepen_bonus, "mastery_bonus": mastery_bonus}

    # ── 共识共振 ──

    def eval_consensus(self, seen_pairs: Set[Tuple], coincidence: Dict,
                       breakthrough_pairs: Set[Tuple]) -> dict:
        """评估共识共振 — 你的路径强化了别人也在用的 coincidence

        breakthrough_pairs: 已触发过突破的对 (避免重复奖励)
        """
        consensus_score = 0.0
        breakthrough_bonus = 0.0

        for pair in seen_pairs:
            hot = coincidence.get(pair, 0)
            if hot >= self.p.CONSENSUS_HOT_MIN:
                # 方向闸门: 正向必须≥2倍反向，否则只是随机共现
                rev = coincidence.get((pair[1], pair[0]), 0)
                if rev > 0 and hot / max(rev, 1) < self.p.DIRECTION_RATIO_MIN:
                    continue
                consensus_score += min(hot * self.p.CONSENSUS_PER_PAIR_MULT,
                                       self.p.CONSENSUS_PER_PAIR_CAP)

            # 首次突破50
            if hot == self.p.BREAKTHROUGH_THRESHOLD and pair not in breakthrough_pairs:
                breakthrough_pairs.add(pair)
                breakthrough_bonus += self.p.BREAKTHROUGH_BONUS

        consensus_bonus = min(consensus_score, self.p.CONSENSUS_TOTAL_CAP)
        return {
            "consensus_bonus": round(consensus_bonus, 2),
            "breakthrough_bonus": round(breakthrough_bonus, 2),
        }

    # ── 探索奖励 (含缺口引力 + 死路有用) ──

    def eval_explore(self, cell, graph: Dict) -> float:
        """评估探索行为的化学信号

        基础 + 死路测绘 + 缺口引力
        """
        reward = self.p.EXPLORE_BASE

        # 死路有用
        res = getattr(cell, '_last_result', {})
        if isinstance(res, dict) and res.get("result") in ("dead_end", "orphan"):
            reward += self.p.EXPLORE_DEAD_END_BONUS

        # 缺口引力
        node_data = graph.get(cell.node, {"causes": [], "effects": []})
        in_d = len(node_data["causes"])
        out_d = len(node_data["effects"])
        gap_score = 0.0

        if in_d == 0 and out_d > 0:
            gap_score = self.p.EXPLORE_GAP_ORPHAN
        elif out_d == 0 and in_d > 0:
            gap_score = self.p.EXPLORE_GAP_DEAD_END
        elif in_d > 0 and out_d > 0:
            asymmetry = abs(in_d - out_d) / (in_d + out_d)
            gap_score = asymmetry * self.p.EXPLORE_GAP_ASYMMETRY_MULT

        if cell.node in {"energy", "momentum", "charge", "angular_momentum"}:
            has_sym = any("symmetry" in c[0].lower() or "gauge" in c[0].lower()
                         or "noether" in c[0].lower() for c in node_data["causes"])
            if not has_sym:
                gap_score = max(gap_score, self.p.EXPLORE_GAP_CONSERVED_NO_SYM)

        return round(reward + gap_score, 2)

    # ── 低保 ──

    def eval_welfare(self, cell, rewarded: bool, signals: list) -> float:
        """低保信号 — 确保所有行为都有基本价值"""
        if rewarded:
            return 0.0

        if signals:
            resonant_locations = {s["location"] for s in signals}
            if cell.node in resonant_locations:
                return self.p.WELFARE_RESONANCE

        if cell.last_action in ("step_forward", "step_backward"):
            return 0.0  # explore 已经单独处理
        if cell.last_action == "mark":
            return self.p.WELFARE_MARK
        if cell.last_action == "echo":
            return self.p.WELFARE_ECHO

        return 0.0

    # ── 热门枢纽缓存 ──

    @staticmethod
    def compute_hot_hubs(coincidence: Dict,
                         hot_threshold: int = None,
                         hub_min_edges: int = None) -> Set[str]:
        """从 coincidence 池计算热门枢纽 (静态方法, 可缓存)

        热门枢纽 = 被 ≥hub_min_edges 条 ≥hot_threshold 的 pair 涉及的节点
        """
        if hot_threshold is None:
            hot_threshold = ChemistryParams.SURPRISE_HOT_THRESHOLD
        if hub_min_edges is None:
            hub_min_edges = ChemistryParams.SURPRISE_HUB_MIN_EDGES

        hub_counter = Counter()
        for pair, count in coincidence.items():
            if count >= hot_threshold:
                hub_counter[pair[0]] += 1
                hub_counter[pair[1]] += 1
        return {node for node, cnt in hub_counter.items()
                if cnt >= hub_min_edges}

    # ── 抑制通道 (GABA) ──

    def record_dead_end(self, src: str, dst: str):
        """记录碰壁 — 在边 (src→dst) 上累积抑制分"""
        key = (src, dst)
        self._edge_inhibition[key] = self._edge_inhibition.get(key, 0.0) + self.p.INHIBITION_PER_DEAD_END

    def decay_inhibition(self):
        """定期衰减所有抑制分 (每50代调用)"""
        for key in list(self._edge_inhibition.keys()):
            self._edge_inhibition[key] *= (1.0 - self.p.INHIBITION_DECAY_RATE)
            if self._edge_inhibition[key] < 0.01:
                del self._edge_inhibition[key]

    def get_blocked_edges(self) -> Set[Tuple[str, str]]:
        """返回抑制分超过拦截阈值的边集合 — 这些边应该被暂时隐藏"""
        return {key for key, score in self._edge_inhibition.items()
                if score >= self.p.INHIBITION_BLOCK_THRESHOLD}

    def broadcast_to_neighbors(self, blocked: Set[Tuple[str, str]], graph: Dict) -> Set[Tuple[str, str]]:
        """广播抑制到邻居边: 如果 A→B 被封，A 的其他出边也受影响"""
        if self.p.INHIBITION_BROADCAST_RADIUS <= 0:
            return blocked
        expanded = set(blocked)
        for src, dst in blocked:
            node_data = graph.get(src, {})
            for law, neighbor, domain in node_data.get("effects", []):
                if neighbor != dst:
                    expanded.add((src, neighbor))
        return expanded


# ═══════ 全局单例 ═══════

chemistry = BrainChemistry()
