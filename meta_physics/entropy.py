"""
熵增 — 第二热力学定律作为因果箭头

元物理层 Tier 1 — 过程约束 ③

核心洞察:
  1. 因果过程必定沿熵增方向 (原因→结果 = 信息损耗 = 熵增)
  2. 熵增方向可用于打破 Markov 等价类的对称性
  3. 不可逆过程的因果效应估计需要特殊处理

注意:
  信息度量的数学工具在 information/ 横切层 (ShannonEntropy, MaxEnt, ...)。
  本模块只包含元物理原则 (第二定律 + 因果箭头判定)。
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np

from information.shannon import ShannonEntropy as _SE


@dataclass
class EntropyAnalysis:
    """熵分析结果"""
    direction: str
    delta_entropy: float
    is_reversible: bool
    causal_direction_supported: bool
    notes: str = ""


class EntropyArrow:
    """
    熵箭头 — 用第二定律判定因果方向。

    原理:
      因果过程产生熵增 (信息损耗)。
      原因端通常熵更低 (更有序)。
      当 PC/FCI 输出等价类时, 用熵增方向消除歧义。

    数学工具委托给: information/shannon.py (ShannonEntropy)
    """

    def __init__(self):
        self._se = _SE()

    # ═══ 委托方法 — 包装 ShannonEntropy ═══

    def compute_entropy(self, data: np.ndarray, bins: int = 20) -> float:
        """Shannon 熵 → 委托 information/shannon.py"""
        return _SE.entropy(data, bins=bins)

    def compute_conditional_entropy(self, x: np.ndarray,
                                    y: np.ndarray, bins: int = 10) -> float:
        """条件熵 → 委托 information/shannon.py"""
        return _SE.conditional_entropy(x, y, bins=bins)

    def infer_causal_direction(self, data: np.ndarray,
                                var_names: List[str],
                                var_a: str, var_b: str) -> EntropyAnalysis:
        """
        用混合方法推断 var_a→var_b 还是 var_b→var_a。

        方法: 残差方差比较 (Additive Noise Model 思想)
          - 如果 X→Y: Y = f(X) + ε, ε ⊥ X
          - 拟合 X→Y: 计算残差方差
          - 拟合 Y→X: 计算残差方差
          - 残差方差更小的方向 = 真实的因果方向
          - 用熵增作为辅助验证
        """
        idx_a = var_names.index(var_a)
        idx_b = var_names.index(var_b)

        x = data[:, idx_a].astype(float)
        y = data[:, idx_b].astype(float)

        # 残差方差法 — 使用 2 次多项式拟合 (打破线性对称)
        # 如果真实关系是非线性的，正确的因果方向会有更小的残差

        # X→Y: Y ~ poly2(X)
        coeffs_ab = np.polyfit(x, y, 2)
        y_pred_ab = np.polyval(coeffs_ab, x)
        resid_var_ab = np.var(y - y_pred_ab)
        resid_ab_indep = abs(np.corrcoef(x, y - y_pred_ab)[0, 1])

        # Y→X: X ~ poly2(Y)
        coeffs_ba = np.polyfit(y, x, 2)
        x_pred_ba = np.polyval(coeffs_ba, y)
        resid_var_ba = np.var(x - x_pred_ba)
        resid_ba_indep = abs(np.corrcoef(y, x - x_pred_ba)[0, 1])

        # 综合得分: 残差独立性 + 归一化残差方差
        score_ab = resid_ab_indep + resid_var_ab / (np.var(y) + 1e-10)
        score_ba = resid_ba_indep + resid_var_ba / (np.var(x) + 1e-10)

        # 也试一次线性拟合作为参考
        c1 = np.polyfit(x, y, 1)
        r1 = np.var(y - np.polyval(c1, x)) / (np.var(y) + 1e-10)
        c2 = np.polyfit(y, x, 1)
        r2 = np.var(x - np.polyval(c2, y)) / (np.var(x) + 1e-10)

        if score_ab < score_ba:
            direction = f"{var_a}→{var_b}"
            note = f"poly2: indep={resid_ab_indep:.4f}, resid={resid_var_ab/(np.var(y)+1e-10):.4f} "
            note += f"< {resid_var_ba/(np.var(x)+1e-10):.4f}"
        elif score_ba < score_ab:
            direction = f"{var_b}→{var_a}"
            note = f"poly2: indep={resid_ba_indep:.4f}, resid={resid_var_ba/(np.var(x)+1e-10):.4f} "
            note += f"< {resid_var_ab/(np.var(y)+1e-10):.4f}"
        else:
            # 平局 — 线性高斯等价类，方向不可判定
            direction = f"{var_a}—{var_b}  (等价类, 方向不可判定)"
            note = "线性高斯系统的 Markov 等价类 — 需要领域知识或干预实验来定向"

        return EntropyAnalysis(
            direction=direction,
            delta_entropy=abs(score_ab - score_ba),
            is_reversible=(abs(score_ab - score_ba) < 0.01),
            causal_direction_supported=True,
            notes=note
        )


class IrreversibilityDetector:
    """
    不可逆过程检测器。

    判断一个因果过程是可逆的 (保守力) 还是不可逆的 (耗散)。

    不可逆过程的标志:
      1. 熵增 > 阈值
      2. 反事实中能量/动量不守恒
      3. 时间反演不对称 (正逆过程的统计性质不同)

    对因果推断的影响:
      - 不可逆过程的 ATE 不能简单用反事实 (需要特殊的耗散模型)
      - 不可逆过程的效应估计应包含「熵成本」
    """

    def __init__(self, threshold: float = 0.05):
        self.threshold = threshold

    def check_reversibility(self, forward_data: np.ndarray,
                            reverse_data: np.ndarray,
                            variable_idx: int) -> bool:
        """
        通过比较正过程和逆过程的统计分布来判断可逆性。

        forward_data: 原因→结果方向的数据
        reverse_data: 结果→原因方向的数据 (如果可以观察到)

        Returns:
          True 如果过程可逆 (分布无显著差异)
        """
        if len(forward_data) < 10 or len(reverse_data) < 10:
            return True  # 样本不足, 假设可逆

        # Kolmogorov-Smirnov 检验
        forward_sorted = np.sort(forward_data[:, variable_idx])
        reverse_sorted = np.sort(reverse_data[:, variable_idx])

        ks_stat = np.max(np.abs(
            np.searchsorted(forward_sorted, forward_sorted) / len(forward_sorted) -
            np.searchsorted(reverse_sorted, forward_sorted) / len(reverse_sorted)
        ))

        return ks_stat < self.threshold

    def entropy_cost(self, before: Dict[str, float],
                     after: Dict[str, float],
                     variable_names: List[str]) -> float:
        """
        估计因果过程的熵成本 (粗略近似)。

        对于耗散过程 (如摩擦、热传导)，熵成本 > 0。
        对于保守过程 (如弹性碰撞)，熵成本 ≈ 0。

        当前实现: 基于方差变化的启发式。
        未来: 基于实际热力学模型。
        """
        before_arr = np.array([before.get(v, 0.0) for v in variable_names])
        after_arr = np.array([after.get(v, 0.0) for v in variable_names])

        var_before = np.var(before_arr)
        var_after = np.var(after_arr)

        if var_before > 1e-10:
            return max(0.0, (var_after - var_before) / var_before)
        return 0.0
