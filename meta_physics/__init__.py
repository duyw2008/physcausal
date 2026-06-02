"""
元物理层 (Meta-Physics) — 世界运行的底层逻辑

物理定律告诉你「世界怎么运转」。
元物理规律告诉你「为什么世界只能这样运转」和「规律本身何时会变」。

五条第一性原理 (当前实现: 5/5):

  Tier 0 — 生成性原理:
    ① 最小作用量 δS=0  — 所有动力学从此导出 (least_action.py) ✅
    ② 对称性 → 守恒    — Noether 定理 (symmetry.py) ✅

  Tier 1 — 过程约束:
    ③ 熵增 ΔS≥0        — 第二定律, 因果箭头 (entropy.py) ✅
    ④ 局域因果         — 因果在光锥内 (locality.py) ✅

  Tier 2 — 信息边界:
    ⑤ 信息边界         — 获取信息改变系统 (measurement.py) ✅
                        量子坍缩 / 经典条件化 / 因果 do() / Landauer 极限
                        本质: 从可能性空间中投影到子空间

  横切基础设施:
    特征谱 (spectral.py) — 所有元物理原则的数学语言
    本征向量 = 信息空间骨架, 本征值 = 重要性度量 ✅

当前模块:
  symmetry.py   — 对称性 → 守恒律 (Noether 定理) + 对称性破缺检测
  entropy.py    — 熵增 → 因果箭头 (多项式残差 + 熵信息增益)
  measurement.py — 观测坍缩 → do() 干预 + 多世界反事实
  spectral.py   — 特征谱: PCA/SVD/谱图论/Koopman 分解 (横切层)

后续扩展方向:
  - 最小作用量原理 (δS=0 → 最优因果路径)
  - 局域因果显式化 (光锥验证 + 时空标签)
  - 规范不变性 (规范对称 → 相互作用的形式约束)
  - 重整化群 (尺度依赖 → 不同尺度下的有效因果定律)
  - 涨落-耗散定理 (噪声 ↔ 阻尼的关系)
  - 自由能原理 (最小化自由能 = 最优因果决策)
  - 退相干 (环境诱导的坍缩 → 因果箭头从量子到经典的过渡)
"""

from meta_physics.symmetry import (
    SymmetryType,
    ConservationLaw,
    Symmetry,
    SymmetryDetector,
    SymmetryBreakingDetector,
)

from meta_physics.least_action import (
    Lagrangian,
    ActionResult,
    ActionPrinciple,
    NoetherBridge,
    CausalPathValidator,
    simple_pendulum,
    harmonic_oscillator,
    free_particle,
    kepler_system,
)

from meta_physics.locality import (
    SpacetimeEvent,
    LocalityReport,
    LocalityValidator,
    TemporalOrder,
    CausalLocalityBridge,
)

from meta_physics.entropy import (
    EntropyAnalysis,
    EntropyArrow,
    IrreversibilityDetector,
)

from meta_physics.measurement import (
    PossibilitySpace,
    InformationAcquisition,
    MeasurementBasis,
    CollapseEvent,
    MeasurementCollapse,
    InformationBoundary,
    WorldBranch,
    MultiWorldCounterfactual,
)

__all__ = [
    # Symmetry
    "SymmetryType", "ConservationLaw", "Symmetry",
    "SymmetryDetector", "SymmetryBreakingDetector",
    # Least Action
    "Lagrangian", "ActionResult", "ActionPrinciple",
    "NoetherBridge", "CausalPathValidator",
    "simple_pendulum", "harmonic_oscillator", "free_particle", "kepler_system",
    # Locality
    "SpacetimeEvent", "LocalityReport", "LocalityValidator",
    "TemporalOrder", "CausalLocalityBridge",
    # Entropy
    "EntropyAnalysis", "EntropyArrow", "IrreversibilityDetector",
    # Measurement / Information Boundary
    "PossibilitySpace", "InformationAcquisition",
    "MeasurementBasis", "CollapseEvent", "MeasurementCollapse",
    "InformationBoundary", "WorldBranch", "MultiWorldCounterfactual",
]
