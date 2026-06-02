"""
对称性 — Noether 定理 + 守恒律作为因果约束

元物理层核心模块 1/3。

核心洞察:
  每个连续对称性 ⇒ 一个守恒量 (Noether 1918)
  守恒量 ⇒ 因果模型的硬约束 (反事实不能违反守恒律)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Dict, List, Optional, Tuple
import numpy as np


# ═══════════════════════════════════════════════════════════════
# Symmetry Type
# ═══════════════════════════════════════════════════════════════

class SymmetryType(Enum):
    TIME_TRANSLATION = auto()     # t → t + δt  → 能量守恒
    SPACE_TRANSLATION = auto()    # x → x + δx  → 动量守恒
    ROTATION = auto()             # θ → θ + δθ  → 角动量守恒
    GAUGE = auto()                # 规范变换     → 电荷守恒
    SCALE = auto()                # 标度变换 (无守恒量，但约束形式)
    PARITY = auto()               # 宇称 (离散对称)


# ═══════════════════════════════════════════════════════════════
# Conservation Law
# ═══════════════════════════════════════════════════════════════

@dataclass
class ConservationLaw:
    """Noether 定理导出的守恒律"""
    name: str
    symmetry: SymmetryType
    conserved_quantity: str          # 守恒量的变量名
    formula: Callable[..., float]    # 计算守恒量的函数
    variables: List[str]             # 参与守恒的变量
    tolerance: float = 0.02

    def compute(self, values: Dict[str, float]) -> float:
        """从变量字典计算守恒量"""
        args = {v: values.get(v, 0.0) for v in self.variables}
        return self.formula(**args)

    def is_conserved(self, before: Dict[str, float],
                     after: Dict[str, float]) -> bool:
        """验证前后守恒量是否一致"""
        val_before = self.compute(before)
        val_after = self.compute(after)
        if val_before == 0.0:
            return abs(val_after) < self.tolerance
        return abs(val_before - val_after) / abs(val_before) < self.tolerance


# ═══════════════════════════════════════════════════════════════
# Symmetry Detector
# ═══════════════════════════════════════════════════════════════

@dataclass
class Symmetry:
    """检测到的对称性"""
    symmetry_type: SymmetryType
    confidence: float               # 0-1, 对称性成立的可信度
    conserved_law: Optional[ConservationLaw] = None
    variables_involved: List[str] = field(default_factory=list)
    notes: str = ""


class SymmetryDetector:
    """
    对称性检测器。

    检测数据中是否存在某种对称性，并自动生成对应的守恒律。

    当前实现: 启发式检测 (基于变量名和数值模式)
    未来扩展: 学习式检测 (从轨迹数据中学习不变性)
    """

    def __init__(self):
        self._builtin_laws = self._define_conservation_laws()

    def _define_conservation_laws(self) -> Dict[str, ConservationLaw]:
        """预定义的守恒律库"""
        return {
            "energy_kinetic": ConservationLaw(
                name="Kinetic Energy Conservation",
                symmetry=SymmetryType.TIME_TRANSLATION,
                conserved_quantity="kinetic_energy",
                formula=lambda m, v: 0.5 * m * v * v,
                variables=["mass", "velocity"],
            ),
            "energy_mechanical": ConservationLaw(
                name="Mechanical Energy Conservation",
                symmetry=SymmetryType.TIME_TRANSLATION,
                conserved_quantity="mechanical_energy",
                formula=lambda m, v, h: 0.5 * m * v * v + m * 9.81 * h,
                variables=["mass", "velocity", "height"],
            ),
            "momentum": ConservationLaw(
                name="Momentum Conservation",
                symmetry=SymmetryType.SPACE_TRANSLATION,
                conserved_quantity="momentum",
                formula=lambda m1, m2, v1, v2: m1 * v1 + m2 * v2,
                variables=["m1", "m2", "v1", "v2"],
            ),
            "momentum_single": ConservationLaw(
                name="Momentum Conservation (single body)",
                symmetry=SymmetryType.SPACE_TRANSLATION,
                conserved_quantity="momentum",
                formula=lambda m, v: m * v,
                variables=["mass", "velocity"],
            ),
            "angular_momentum": ConservationLaw(
                name="Angular Momentum Conservation",
                symmetry=SymmetryType.ROTATION,
                conserved_quantity="angular_momentum",
                formula=lambda m, v, r: m * v * r,
                variables=["mass", "velocity", "radius"],
            ),
        }

    def detect(self, variable_names: List[str]) -> List[Symmetry]:
        """
        检测哪些对称性可能适用于给定的变量集合。

        方法: 基于变量名启发式匹配。
        """
        detected = []
        vset = set(variable_names)

        # 能量守恒检测
        if {"mass", "velocity"} <= vset:
            if "height" in vset:
                detected.append(Symmetry(
                    symmetry_type=SymmetryType.TIME_TRANSLATION,
                    confidence=0.9,
                    conserved_law=self._builtin_laws["energy_mechanical"],
                    variables_involved=["mass", "velocity", "height"],
                    notes="机械能守恒 (动能 + 重力势能)"
                ))
            else:
                detected.append(Symmetry(
                    symmetry_type=SymmetryType.TIME_TRANSLATION,
                    confidence=0.85,
                    conserved_law=self._builtin_laws["energy_kinetic"],
                    variables_involved=["mass", "velocity"],
                    notes="动能守恒 (弹性碰撞)"
                ))

        # 动量守恒检测
        momentum_vars = {"m1", "m2", "v1", "v2"}
        if momentum_vars <= vset or (
            all(any(f"m{i}" in vset for v in vset) for i in [1, 2]) and
            all(any(f"v{i}" in vset for v in vset) for i in [1, 2])
        ):
            detected.append(Symmetry(
                symmetry_type=SymmetryType.SPACE_TRANSLATION,
                confidence=0.9,
                conserved_law=self._builtin_laws["momentum"],
                variables_involved=["m1", "m2", "v1", "v2"],
                notes="动量守恒 (两体碰撞)"
            ))
        elif {"mass", "velocity"} <= vset:
            detected.append(Symmetry(
                symmetry_type=SymmetryType.SPACE_TRANSLATION,
                confidence=0.7,
                conserved_law=self._builtin_laws["momentum_single"],
                variables_involved=["mass", "velocity"],
                notes="动量守恒 (单体, 无外力时)"
            ))

        # 角动量守恒
        if {"mass", "velocity", "radius"} <= vset:
            detected.append(Symmetry(
                symmetry_type=SymmetryType.ROTATION,
                confidence=0.8,
                conserved_law=self._builtin_laws["angular_momentum"],
                variables_involved=["mass", "velocity", "radius"],
                notes="角动量守恒 (有心力场)"
            ))

        return detected

    def validate_conservation(self, before: Dict[str, float],
                              after: Dict[str, float],
                              variable_names: List[str]) -> Dict[str, bool]:
        """
        验证反事实结果是否违反守恒律。

        Returns:
            {"energy": True, "momentum": False, ...}
            True = 守恒成立, False = 违反
        """
        symmetries = self.detect(variable_names)
        results = {}
        for sym in symmetries:
            if sym.conserved_law:
                law = sym.conserved_law
                ok = law.is_conserved(before, after)
                results[law.name] = ok
        return results


# ═══════════════════════════════════════════════════════════════
# Symmetry Breaking Detector
# ═══════════════════════════════════════════════════════════════

class SymmetryBreakingDetector:
    """
    对称性破缺检测器。

    检测系统何时经历对称性破缺 → 新因果变量涌现。

    启发式:
      1. 观测某变量的方差突然增大 → 可能接近相变点
      2. 新变量在某个阈值后突然出现 → 对称性破缺
      3. 因果图的边在时间窗口间发生拓扑变化 → 结构断点
    """

    def detect_phase_transition(self, data: np.ndarray,
                                variable_names: List[str],
                                window_size: int = 50) -> List[Dict]:
        """
        检测时间序列中的相变点。

        Returns:
            [{"time": 150, "new_variables": ["magnetization"], 
              "broken_symmetry": "rotation", "confidence": 0.82}, ...]
        """
        n = len(data)
        if n < 2 * window_size:
            return []

        transitions = []
        for t in range(window_size, n - window_size, window_size):
            before = data[t - window_size:t]
            after = data[t:t + window_size]

            # 简单启发式: 方差突变检测
            for i, name in enumerate(variable_names):
                var_before = np.var(before[:, i])
                var_after = np.var(after[:, i])
                if var_before > 1e-10:
                    ratio = var_after / var_before
                    if ratio > 5.0 or ratio < 0.2:
                        transitions.append({
                            "time": t,
                            "variable": name,
                            "var_ratio": ratio,
                            "interpretation": (
                                "方差跳变 — 可能为对称性破缺点"
                                if ratio > 5.0 else
                                "方差骤降 — 可能为对称性恢复"
                            )
                        })

        return transitions
