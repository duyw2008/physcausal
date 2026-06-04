"""
对称性破缺 — 结构涌现的物理机制

位置: physics/ (物理层, 和 23 定律平级)

对称性破缺 = 世界多样性的来源:
  1. 水结冰: 旋转对称性破缺 → 晶体结构涌现
  2. 铁磁体: 自旋对称性破缺 → 磁畴涌现
  3. Higgs 机制: 规范对称性破缺 → 质量涌现
  4. 因果推断: 相变点 = 新因果变量涌现

与元物理对称性的关系:
  meta_physics/symmetry.py — Noether: 对称性 → 守恒律 (元原则)
  physics/symmetry_breaking.py — 何时/如何破缺 (物理机制)

自组织是破缺后的第二步 — 差异被放大和稳定化。
"""

from __future__ import annotations
from typing import List, Dict
import numpy as np


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
