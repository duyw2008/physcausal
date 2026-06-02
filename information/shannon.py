"""
Shannon 信息论 — 数学基础工具

横切层: information/ (与 spectral/ 平级)

提供:
  - Shannon 熵 H(X) = -Σ p(x) log p(x)
  - 联合熵 H(X,Y)
  - 条件熵 H(Y|X)
  - 互信息 I(X;Y) = H(X) + H(Y) - H(X,Y)
  - KL 散度 D_KL(P||Q)
  - 交叉熵 H(P,Q)
  - Jensen-Shannon 散度

所有需要信息度量的模块 (meta_physics/entropy, causal/discovery, ...)
都从这个模块获取数学工具，而不是各自实现。
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


class ShannonEntropy:
    """Shannon 信息论的静态工具集"""

    @staticmethod
    def entropy(data: np.ndarray, bins: int = 20,
                method: str = "histogram") -> float:
        """
        Shannon 熵: H(X) = -Σ p(x) log p(x)

        Args:
            data: 一维数据
            bins: 直方图分桶数 (method="histogram")
            method: "histogram" 或 "knn" (k近邻估计)

        Returns:
            H(X) in nats (natural log)
        """
        if len(data) < 2:
            return 0.0

        if method == "histogram":
            hist, _ = np.histogram(data, bins=bins)
            hist = hist[hist > 0]
            p = hist / hist.sum()
            return float(-np.sum(p * np.log(p)))

        elif method == "knn":
            # Kozachenko-Leonenko 估计
            n = len(data)
            k = max(1, int(np.sqrt(n)))
            data_sorted = np.sort(data)
            ent = 0.0
            for i in range(n):
                left = max(0, i - k)
                right = min(n - 1, i + k)
                rho = (data_sorted[right] - data_sorted[left]) / 2
                if rho > 1e-15:
                    ent += np.log(2 * k / (n * rho + 1e-15))
            return max(0.0, ent / n + np.euler_gamma)

        else:
            raise ValueError(f"Unknown method: {method}")

    @staticmethod
    def joint_entropy(x: np.ndarray, y: np.ndarray,
                      bins: int = 10) -> float:
        """联合熵 H(X,Y)"""
        if len(x) != len(y) or len(x) < 2:
            return 0.0

        hist, _, _ = np.histogram2d(x, y, bins=bins)
        hist = hist[hist > 0]
        p = hist / hist.sum()
        return float(-np.sum(p * np.log(p)))

    @staticmethod
    def conditional_entropy(x: np.ndarray, y: np.ndarray,
                            bins: int = 10) -> float:
        """
        条件熵: H(Y|X) = H(X,Y) - H(X)

        给定 X 后 Y 的剩余不确定性。
        """
        h_xy = ShannonEntropy.joint_entropy(x, y, bins)
        h_x = ShannonEntropy.entropy(x, bins=bins)
        return max(0.0, h_xy - h_x)

    @staticmethod
    def mutual_information(x: np.ndarray, y: np.ndarray,
                           bins: int = 10) -> float:
        """
        互信息: I(X;Y) = H(X) + H(Y) - H(X,Y)

        X 和 Y 共享的信息量。
        I(X;Y) = 0 如果 X ⊥ Y
        """
        h_x = ShannonEntropy.entropy(x, bins=bins)
        h_y = ShannonEntropy.entropy(y, bins=bins)
        h_xy = ShannonEntropy.joint_entropy(x, y, bins)
        return max(0.0, h_x + h_y - h_xy)

    @staticmethod
    def kl_divergence(p: np.ndarray, q: np.ndarray) -> float:
        """
        KL 散度: D_KL(P||Q) = Σ p(x) log(p(x)/q(x))

        从 Q 到 P 的「信息增益」。
        """
        p = np.asarray(p, dtype=float)
        q = np.asarray(q, dtype=float)
        p = p / p.sum()
        q = q / q.sum()

        mask = (p > 0) & (q > 0)
        return float(np.sum(p[mask] * np.log(p[mask] / q[mask])))

    @staticmethod
    def cross_entropy(p: np.ndarray, q: np.ndarray) -> float:
        """交叉熵: H(P,Q) = H(P) + D_KL(P||Q)"""
        p = np.asarray(p, dtype=float)
        q = np.asarray(q, dtype=float)
        p = p / p.sum()
        q = q / q.sum()
        q = np.clip(q, 1e-15, None)
        return float(-np.sum(p * np.log(q)))

    @staticmethod
    def js_divergence(p: np.ndarray, q: np.ndarray) -> float:
        """
        Jensen-Shannon 散度 — KL 的对称版本。

        JSD(P||Q) = ½ D_KL(P||M) + ½ D_KL(Q||M)
        其中 M = ½(P+Q)

        范围: [0, ln 2]
        """
        p = np.asarray(p, dtype=float)
        q = np.asarray(q, dtype=float)
        p = p / p.sum()
        q = q / q.sum()
        m = (p + q) / 2

        mask_p = p > 0
        mask_q = q > 0
        jsd = 0.0
        if mask_p.any():
            jsd += 0.5 * np.sum(p[mask_p] * np.log(p[mask_p] / (m[mask_p] + 1e-15)))
        if mask_q.any():
            jsd += 0.5 * np.sum(q[mask_q] * np.log(q[mask_q] / (m[mask_q] + 1e-15)))
        return float(jsd)

    @staticmethod
    def entropy_rate(time_series: np.ndarray, order: int = 1) -> float:
        """
        熵率 — 时间序列的每步平均不确定性。

        h = lim_{n→∞} H(X₁,...,Xₙ) / n

        近似: h ≈ H(X_{t+1} | X_t, ..., X_{t-order+1})
        """
        n = len(time_series)
        if n <= order:
            return ShannonEntropy.entropy(time_series)

        # 构建滞后矩阵
        X = np.zeros((n - order, order + 1))
        for i in range(order + 1):
            X[:, i] = time_series[i:n - order + i]

        return ShannonEntropy.conditional_entropy(
            X[:, :order].flatten(),
            X[:, order],
        )

    @staticmethod
    def transfer_entropy(source: np.ndarray,
                         target: np.ndarray,
                         lag: int = 1) -> float:
        """
        传递熵 — 从 source 到 target 的信息流。

        TE(source → target) = I(target_t ; source_{t-lag} | target_{t-lag})

        这是 Wiener-Granger 因果的信息论版本。
        TE > 0 意味着 source 的过去提供了关于 target 未来的信息，
        即使已经知道了 target 的过去。
        """
        n = len(source)
        if n <= lag:
            return 0.0

        # target_{t-lag} 和 target_t
        past_target = target[:n - lag]
        future_target = target[lag:]
        past_source = source[:n - lag]

        # H(target_t | target_{t-lag})
        h_cond_target = ShannonEntropy.conditional_entropy(
            past_target, future_target
        )

        # H(target_t | target_{t-lag}, source_{t-lag})
        joint_past = np.column_stack([past_target, past_source])
        h_cond_joint = ShannonEntropy.conditional_entropy(
            joint_past.flatten(), future_target
        )

        return max(0.0, h_cond_target - h_cond_joint)


# ═══════════════════════════════════════════════════════════════
# Bridge: Boltzmann → Shannon
# ═══════════════════════════════════════════════════════════════

class BoltzmannBridge:
    """连接热力学熵和 Shannon 熵"""

    k_B = 1.380649e-23  # Boltzmann 常数 (J/K)

    @staticmethod
    def boltzmann_to_shannon(thermodynamic_entropy: float,
                             temperature: float = 300.0) -> float:
        """
        热力学熵 → Shannon 信息熵。

        S_thermo = k_B · H_shannon (乘以 k_B, 除以 ln 2 可选)

        Returns:
            Shannon 熵 in nats
        """
        return thermodynamic_entropy / BoltzmannBridge.k_B

    @staticmethod
    def shannon_to_boltzmann(shannon_entropy: float) -> float:
        """Shannon 熵 → 热力学熵 (J/K)"""
        return shannon_entropy * BoltzmannBridge.k_B

    @staticmethod
    def landauer_bound(bits: float, temperature: float = 300.0) -> float:
        """
        Landauer 极限: 擦除 1 bit 信息的最小热力学成本。

        E_min = k_B T ln 2

        Args:
            bits: 要擦除的信息量 (bit)
            temperature: 温度 (K)

        Returns:
            最低能量消耗 (J)
        """
        return bits * BoltzmannBridge.k_B * temperature * np.log(2)
