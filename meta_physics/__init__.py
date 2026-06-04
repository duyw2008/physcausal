"""
元物理层 (Meta-Physics) — 世界运行的底层逻辑

物理定律告诉你「世界怎么运转」。
元物理规律告诉你「为什么世界只能这样运转」和「规律本身何时会变」。

三条第一性原理 (3/3):

  Tier 0 — 生成性原理:
    1. 最小作用量 delta S = 0 — 所有动力学从此导出 (least_action.py)
    2. 对称性 -> 守恒 — Noether 定理 (symmetry.py)

  Tier 1 — 过程约束:
    3. 熵增 delta S >= 0 — 第二定律, 因果箭头 (entropy.py)

注意:
  局域因果 (光速限制) — 这是物理定律, 不是元规律
    Newton 力学中因果是瞬时的。局域因果只在 SR/GR 中成立。
    已移至 physics/laws.py — 和 Newton, Maxwell 平级。

  信息边界 — 获取信息改变系统 — 这是认识论
    在量子/经典/因果层有不同表达。属于横切概念。
"""

from meta_physics.symmetry import (
    SymmetryType, ConservationLaw, Symmetry,
    SymmetryDetector,
)

from meta_physics.least_action import (
    Lagrangian, ActionResult, ActionPrinciple,
    NoetherBridge, CausalPathValidator,
    simple_pendulum, harmonic_oscillator, free_particle, kepler_system,
)

from meta_physics.entropy import (
    EntropyAnalysis, EntropyArrow, IrreversibilityDetector,
)

from meta_physics.measurement import (
    PossibilitySpace, InformationAcquisition,
    MeasurementBasis, CollapseEvent, MeasurementCollapse,
    InformationBoundary, WorldBranch, MultiWorldCounterfactual,
)

__all__ = [
    # Symmetry
    "SymmetryType", "ConservationLaw", "Symmetry",
    "SymmetryDetector",
    # Least Action
    "Lagrangian", "ActionResult", "ActionPrinciple",
    "NoetherBridge", "CausalPathValidator",
    "simple_pendulum", "harmonic_oscillator", "free_particle", "kepler_system",
    # Entropy
    "EntropyAnalysis", "EntropyArrow", "IrreversibilityDetector",
    # Measurement / Information Boundary
    "PossibilitySpace", "InformationAcquisition",
    "MeasurementBasis", "CollapseEvent", "MeasurementCollapse",
    "InformationBoundary", "WorldBranch", "MultiWorldCounterfactual",
]
