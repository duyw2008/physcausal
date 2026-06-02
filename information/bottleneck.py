"""
信息瓶颈 — 感知压缩的数学基础

信息瓶颈理论 (Tishby et al.):
  给定 X (原始信号) 和 Y (相关目标),
  找到一个压缩表示 T, 使得:
    - I(T;X) 尽可能小 (压缩)
    - I(T;Y) 尽可能大 (保留相关信息)

这直接对应 PhysCausal 中的感知层架构:
  X = 原始像素
  T = 感知层提取的 Scene 特征
  Y = 因果推理需要的变量
"""

from __future__ import annotations
from typing import Optional, Tuple
import numpy as np

from information.shannon import ShannonEntropy


class InformationBottleneck:
    """
    信息瓶颈 — 感知压缩的核心理论。

    在 PhysCausal 中的应用:
      感知层输出 Scene (高维特征) →
      信息瓶颈找到最优压缩 T (因果变量)

    Lagrangian: L = I(T;X) - β I(T;Y)

    β → 0: 最大压缩 (只保留与 Y 最相关的)
    β → ∞: 无损保留
    """

    def __init__(self, beta: float = 1.0):
        self.beta = beta

    def compute_compression_bound(self,
                                   x_data: np.ndarray,
                                   y_data: np.ndarray,
                                   n_components: int = 10) -> Tuple[float, float]:
        """
        计算数据的信息瓶颈边界。

        Returns:
          (I(T;X), I(T;Y)) — 压缩量与保留信息量

        当前实现: PCA 近似 (线性瓶颈)
        未来: 变分信息瓶颈 (神经网络)
        """
        from spectral.spectral import SpectralDecomposer

        decomp = SpectralDecomposer(variance_threshold=0.95)
        result = decomp.pca(x_data)

        # I(T;X) ≈ Σ log(1 + λ_i) for Gaussian
        kept_lambdas = result.eigenvalues[:n_components]
        tx = 0.5 * np.sum(np.log(1 + kept_lambdas))

        # I(T;Y) ≈ 互信息 in compressed space
        reduced, _ = decomp.dimension_reduction(x_data)
        ty = ShannonEntropy.mutual_information(
            reduced[:, 0], y_data
        ) if reduced.shape[1] > 0 else 0.0

        return float(tx), float(ty)

    def optimal_beta_range(self,
                           x_data: np.ndarray,
                           y_data: np.ndarray) -> Dict:
        """扫描 β 值, 找到压缩-保真权衡曲线上的关键区间"""
        betas = [0.01, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
        curve = []

        for b in betas:
            self.beta = b
            tx, ty = self.compute_compression_bound(x_data, y_data)
            curve.append({"beta": b, "compression": tx, "relevance": ty})

        # 找 elbow point (压缩 vs 保真的最佳折中)
        # 简单启发式: 选使得 I(T;X) / I(T;Y) 在 0.3-1.0 之间的 β
        best = None
        best_score = float("inf")
        for p in curve:
            if p["relevance"] > 0:
                ratio = abs(p["compression"] / p["relevance"] - 0.5)
                if ratio < best_score:
                    best_score = ratio
                    best = p

        return {
            "curve": curve,
            "suggested_beta": best["beta"] if best else 1.0,
        }

    def relevance_score(self,
                        feature: np.ndarray,
                        target: np.ndarray) -> float:
        """
        单个特征与目标的「相关性得分」。

        I(feature; target) / H(feature) — 归一化互信息
        """
        mi = ShannonEntropy.mutual_information(feature, target)
        h_feat = ShannonEntropy.entropy(feature)
        if h_feat > 1e-10:
            return float(mi / h_feat)
        return 0.0


class CompressionReport:
    """压缩报告 — 从原始信号到因果变量的信息流追踪"""

    def __init__(self):
        self.stages: List[Dict] = []

    def add_stage(self, name: str, n_input: int, n_output: int,
                  entropy_in: float, entropy_out: float):
        self.stages.append({
            "stage": name,
            "dim_in": n_input,
            "dim_out": n_output,
            "entropy_in": round(entropy_in, 4),
            "entropy_out": round(entropy_out, 4),
            "compression_ratio": round(n_output / n_input, 4) if n_input else 0,
            "information_loss": round(
                max(0, entropy_in - entropy_out) / (entropy_in + 1e-10), 4
            ),
        })

    def summary(self) -> str:
        lines = ["=== Information Flow Report ==="]
        for s in self.stages:
            lines.append(
                f"  {s['stage']}: {s['dim_in']} → {s['dim_out']} dims, "
                f"H: {s['entropy_in']:.2f} → {s['entropy_out']:.2f} nats, "
                f"loss: {s['information_loss']:.1%}"
            )
        return "\n".join(lines)
