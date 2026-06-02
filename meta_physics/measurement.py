"""
信息边界 — 获取信息必然改变系统

元物理层 Tier 2 — 信息边界 ⑤

核心原则:
  获取关于系统的信息 = 从可能性空间中选出一个子空间。
  这个操作在不同尺度有不同名字，但数学上是同一种操作。

尺度对应:
  量子: |ψ⟩ = Σ c_i |φ_i⟩  →  测量 →  |φ_k⟩        「波函数坍缩」
  经典: 52! 种排列          →  翻开一张 →  51! 种可能 「信息获取」
  统计: P(Y) = Σ_x P(Y|x)P(x) → 观测 X=x_k → P(Y|x_k)  「条件化」
  因果: E[Y]               →  do(X=x) →  E[Y|do(x)] 「干预」
  信息: kT ln 2            ←  获取 1 bit 的最低能量代价   「Landauer 极限」

共同数学结构:
  大的可能性空间 S → 获取信息 I → 投影到子空间 S|I
  信息获取不是被动的「知道了什么」，
  而是主动的「排除了其他可能性」。

在因果推断中的应用:
  - 每次数据收集 = 一次 do() 操作 (从可能世界集合中选出一个)
  - 观测不是被动的记录, 而是主动的干预
  - Pearl 三步反事实 = 量子测量三阶段:
      Abduction  ≡ 态制备    (反推 U / 反推 |ψ⟩)
      Action     ≡ 选择测量基 (do() / 选择可观测量)
      Prediction ≡ 空间投影  (得到确定结果 / 得到本征值)

  反事实推理的本质:
    "如果当初观测到的是另一个值..."
    = 在当时那个可能性空间中, 选另一个子空间
    = 需要知道坍缩前的「完整可能性空间」(U / |ψ⟩)

与其他元物理模块的关系:
  information ← least_action:  最小作用量定义了「物理上可行的可能性空间」
  information ← symmetry:      对称性定义了可能性空间的结构
  information ← entropy:       熵度量了可能性空间的「大小」
  information ← locality:      光锥限制了信息获取的空间范围
  information ← spectral:      特征分解 = 可能性空间的「骨架」
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


class PossibilitySpace(Enum):
    """可能性空间的类型 — 对应不同尺度的信息获取"""
    QUANTUM = auto()        # Hilbert 空间 → 本征态投影
    CLASSICAL = auto()      # 经典概率空间 → 条件化
    CAUSAL = auto()         # 因果模型 → do() 干预
    STATISTICAL = auto()    # 统计推断 → 条件分布


@dataclass
class InformationAcquisition:
    """
    一次信息获取事件。

    在不同尺度有不同的物理表现，但数学结构相同:
      pre_space: 获取信息前的可能性空间
      acquired_info: 获取了什么信息
      post_space: 获取信息后的子空间
      entropy_cost: 信息获取的熵成本

    量子坍缩只是这类事件在 Hilbert 空间的特例。
    """
    space_type: PossibilitySpace
    pre_space_description: str
    acquired_info: str
    post_space_description: str
    entropy_change: float = 0.0
    notes: str = ""


# ═══════════════════════════════════════════════════════════════
# Measurement — 量子尺度的信息获取 (保留原名兼容)
# ═══════════════════════════════════════════════════════════════

class MeasurementBasis(Enum):
    """测量基 — 对应因果模型中的干预变量"""
    STANDARD = auto()
    INTERVENTION = auto()
    COUNTERFACTUAL = auto()


@dataclass
class CollapseEvent:
    """坍缩事件 — 一次观测/干预的记录 (量子表述)"""
    measurement_basis: MeasurementBasis
    pre_collapse_state: Dict[str, Any]
    chosen_branch: Dict[str, float]
    excluded_branches: List[Dict[str, float]]
    entropy_change: float = 0.0


class MeasurementCollapse:
    """
    信息获取的量子表述 — 波函数坍缩 = 可能性空间投影。

    在因果推断中:
      do() 操作 = 主动选择测量基
      反事实    = 在另一个分支中做测量
    """

    def __init__(self):
        pass

    def collapse_continuous(self, values: np.ndarray,
                            n_branches: int = 5) -> CollapseEvent:
        mean = np.mean(values)
        std = np.std(values) if np.std(values) > 1e-10 else 1.0
        branches = []
        for i in range(n_branches):
            branches.append({"value": mean + (i - n_branches // 2) * std})
        observed = np.mean(values)
        chosen_idx = np.argmin([abs(b["value"] - observed) for b in branches])
        chosen = branches[chosen_idx]
        excluded = [b for i, b in enumerate(branches) if i != chosen_idx]
        return CollapseEvent(
            measurement_basis=MeasurementBasis.STANDARD,
            pre_collapse_state={"mean": mean, "std": std, "n_branches": n_branches},
            chosen_branch=chosen,
            excluded_branches=excluded,
            entropy_change=-np.log(1.0 / n_branches) if n_branches > 0 else 0.0,
        )

    def intervention_as_measurement(self, intervention_var: str,
                                    intervention_value: float,
                                    possible_values: List[float]) -> CollapseEvent:
        excluded = [{"value": v} for v in possible_values
                    if abs(v - intervention_value) > 1e-10]
        return CollapseEvent(
            measurement_basis=MeasurementBasis.INTERVENTION,
            pre_collapse_state={"possible_values": possible_values},
            chosen_branch={intervention_var: intervention_value},
            excluded_branches=excluded,
            entropy_change=-np.log(1.0 / len(possible_values)) if possible_values else 0.0,
        )

    def counterfactual_branches(self, scm_variables: List[str],
                                observed: Dict[str, float],
                                interventions: List[Dict[str, float]]) -> List[CollapseEvent]:
        events = []
        for intv in interventions:
            chosen = dict(observed)
            chosen.update(intv)
            excluded = [{"world": "original", "values": observed}]
            events.append(CollapseEvent(
                measurement_basis=MeasurementBasis.COUNTERFACTUAL,
                pre_collapse_state={"variables": scm_variables},
                chosen_branch=chosen,
                excluded_branches=excluded,
            ))
        return events


# ═══════════════════════════════════════════════════════════════
# Information Boundary — 普适信息边界层
# ═══════════════════════════════════════════════════════════════

class InformationBoundary:
    """
    信息边界 — 获取信息必然改变系统。

    这是五条元物理原则中 Tier 2 的核心。
    不依赖量子力学 — 在经典世界同样成立。

    三种等价表述:
      1. 物理: Landauer 极限 — 获取 1 bit 最少消耗 kT ln 2 能量
      2. 统计: 条件化 — P(Y|X=x) 是对 P(Y) 的投影
      3. 因果: do() — do(X=x) 是对观测分布 P(Y|X) 的收缩
    """

    def __init__(self):
        pass

    def landauer_limit(self, temperature: float = 300.0) -> float:
        """
        Landauer 极限: 获取 1 bit 信息的最低能量代价。

        E_min = kT ln 2

        室温 (300K): ≈ 2.9 × 10⁻²¹ J ≈ 0.018 eV

        含义:
          - 信息不是免费的 — 每次观测都消耗能量
          - 你不可能在不改变系统的情况下获取信息
          - 这是经典世界的信息边界, 不需要量子力学
        """
        k_B = 1.380649e-23  # Boltzmann 常数
        return k_B * temperature * np.log(2)

    def information_cost(self, n_bits: float, temperature: float = 300.0) -> float:
        """获取 n bits 信息的最低能量成本"""
        return n_bits * self.landauer_limit(temperature)

    def conditionalization_as_projection(self,
                                         prior_probs: Dict[str, float],
                                         evidence: str) -> Dict[str, float]:
        """
        条件化 = 可能性空间的投影。

        P(H|E) = P(H ∩ E) / P(E)

        在信息边界视角下:
          prior_probs: 投影前的可能性空间
          evidence:    获取的信息
          结果:        投影后的子空间 (重新归一化)
        """
        posterior = dict(prior_probs)
        total = sum(posterior.values()) if posterior else 1.0
        if total > 0:
            posterior = {k: v / total for k, v in posterior.items()}
        return posterior

    def intervention_as_information_acquisition(self,
                                                variable: str,
                                                value: float) -> InformationAcquisition:
        """
        因果干预 = 信息获取 = 可能性空间投影。

        do(X=x) 相当于:
          1. 获取信息: "X 的值是 x"
          2. 系统投影到 X=x 的子空间
          3. 其他变量按 SCM 重新计算
        """
        return InformationAcquisition(
            space_type=PossibilitySpace.CAUSAL,
            pre_space_description=f"X 的所有可能取值",
            acquired_info=f"X = {value}",
            post_space_description=f"X = {value} 的子空间 (do干预)",
            notes="干预 = 主动信息获取 — 从被动观测变为主动控制"
        )


# ═══════════════════════════════════════════════════════════════
# Multi-World Counterfactual — 跨分支推理
# ═══════════════════════════════════════════════════════════════

class WorldBranch:
    """世界分支 — 可能性空间中的一个投影子空间"""
    def __init__(self, branch_id: str,
                 intervention: Dict[str, float],
                 parent_branch: Optional[str] = None):
        self.branch_id = branch_id
        self.intervention = intervention
        self.parent_branch = parent_branch
        self.variables: Dict[str, float] = {}

    def set_variables(self, values: Dict[str, float]):
        self.variables = dict(values)

    def compare_to(self, other: "WorldBranch") -> Dict[str, float]:
        diffs = {}
        for var in set(self.variables) | set(other.variables):
            diffs[var] = self.variables.get(var, 0.0) - other.variables.get(var, 0.0)
        return diffs


class MultiWorldCounterfactual:
    """
    多世界反事实引擎。

    将 Pearl 三步反事实嵌入「可能性空间投影」框架。

    实际世界 = 可能性空间投影到「我们观测到的分支」
    反事实世界 = 可能性空间投影到「不同的分支」
    因果效应 = 两个分支之间的差异

    注意: 这不是量子多世界解释, 而是说:
    「在观测之前, 很多结果都是可能的。
      观测选出了一个。反事实问的是: 如果选了另一个呢？」
    """

    def __init__(self):
        self.branches: Dict[str, WorldBranch] = {}
        self.counter = 0

    def create_actual_world(self, observed: Dict[str, float]) -> str:
        branch_id = "world_actual"
        branch = WorldBranch(branch_id, intervention={})
        branch.set_variables(observed)
        self.branches[branch_id] = branch
        return branch_id

    def create_counterfactual_world(self, intervention: Dict[str, float],
                                    parent: str = "world_actual",
                                    label: str = "") -> str:
        self.counter += 1
        branch_id = f"world_cf_{label}" if label else f"world_cf_{self.counter}"
        branch = WorldBranch(branch_id, intervention, parent_branch=parent)
        self.branches[branch_id] = branch
        return branch_id

    def compute_causal_effect(self, actual: str, cf: str,
                              outcome: str) -> float:
        a = self.branches.get(actual)
        b = self.branches.get(cf)
        if not a or not b:
            return 0.0
        return b.compare_to(a).get(outcome, 0.0)

    def all_branches_report(self, outcome_variable: str) -> str:
        actual = self.branches.get("world_actual")
        if not actual:
            return "No actual world recorded."
        lines = ["=== Multi-World Counterfactual Report ==="]
        lines.append(f"\nActual world: {outcome_variable} = "
                     f"{actual.variables.get(outcome_variable, 'N/A')}")
        for bid, branch in self.branches.items():
            if bid == "world_actual":
                continue
            effect = self.compute_causal_effect("world_actual", bid, outcome_variable)
            cf_val = branch.variables.get(outcome_variable, "N/A")
            intv = ", ".join(f"{k}={v}" for k, v in branch.intervention.items())
            lines.append(f"\n  {bid}: do({intv})")
            lines.append(f"    {outcome_variable} = {cf_val}")
            lines.append(f"    Causal effect = {effect:+.4f}")
        return "\n".join(lines)

