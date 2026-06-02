"""
特征谱 — 信息的空间架构与重要性度量

元物理层模块 4/4。

核心洞察:
  本征向量 = 信息空间的「骨架方向」
  本征值   = 每个方向上的「重要性」

  感知层输出高维特征 → 特征分解 → 降维 + 重要性排序 → 因果层

应用链:
  PCA:          协方差矩阵的特征分解 → 数据的主成分方向
  SVD:          任意矩阵的奇异值分解 → 隐语义空间 (NLP/CV 的核心)
  Quantum:      可观测量的本征值 = 测量结果, 本征态 = 坍缩后的状态
  Spectral Graph: 拉普拉斯矩阵的特征分解 → 图的聚类结构
  Koopman:      非线性动力学的线性化 → 发现隐式因果结构
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np
from scipy import linalg


# ═══════════════════════════════════════════════════════════════
# Core: EigenDecomposition
# ═══════════════════════════════════════════════════════════════

@dataclass
class EigenResult:
    """特征分解结果"""
    eigenvalues: np.ndarray          # 降序排列
    eigenvectors: np.ndarray         # 列 = 本征向量
    explained_variance_ratio: np.ndarray  # 每个成分的解释方差比例
    cumulative_variance: np.ndarray      # 累积解释方差
    n_components: int
    effective_rank: int              # 有效秩 (95% 方差需要的成分数)


@dataclass
class SpectralGraph:
    """图的谱表示"""
    adjacency: np.ndarray
    laplacian: np.ndarray
    eigenvalues: np.ndarray
    eigenvectors: np.ndarray
    algebraic_connectivity: float    # λ₂ — 图的连通性度量
    spectral_gap: float              # λ_{k+1} - λ_k — 最优聚类数信号


class SpectralDecomposer:
    """
    特征谱分解器 — 从数据中提取「什么重要」和「如何组织」。

    这是感知层和因果层之间的认知压缩桥梁:
      高维感知 → 特征分解 → 低维因果变量

    三个核心操作:
      1. PCA: 找到方差最大的方向 (主成分)
      2. SVD: 找到矩阵的低秩近似
      3. Spectral Graph: 找到图的聚类结构
    """

    def __init__(self, variance_threshold: float = 0.95):
        self.variance_threshold = variance_threshold

    def pca(self, data: np.ndarray) -> EigenResult:
        """
        主成分分析 — 协方差矩阵的特征分解。

        数据矩阵 X (n_samples × n_features):
          Σ = (1/n) X^T X  (协方差矩阵)
          Σ v_i = λ_i v_i
          
          λ_i 降序排列: λ₁ ≥ λ₂ ≥ ... ≥ λ_d
          v_i: 数据变化最大的方向
        """
        n, d = data.shape
        centered = data - data.mean(axis=0)
        cov = (centered.T @ centered) / (n - 1)

        eigenvalues, eigenvectors = np.linalg.eigh(cov)
        # eigh 返回升序 → 反转为降序
        eigenvalues = eigenvalues[::-1]
        eigenvectors = eigenvectors[:, ::-1]

        total_var = eigenvalues.sum()
        explained = eigenvalues / total_var if total_var > 0 else eigenvalues
        cumulative = np.cumsum(explained)

        # 有效秩: 达到 variance_threshold 所需的最少成分数
        effective_rank = int(np.searchsorted(cumulative, self.variance_threshold) + 1)
        effective_rank = min(effective_rank, d)

        return EigenResult(
            eigenvalues=eigenvalues,
            eigenvectors=eigenvectors,
            explained_variance_ratio=explained,
            cumulative_variance=cumulative,
            n_components=d,
            effective_rank=effective_rank,
        )

    def svd_low_rank(self, data: np.ndarray,
                     k: Optional[int] = None) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        奇异值分解 — 矩阵的低秩近似。

        数据矩阵 X (n × d):
          X = U Σ V^T
          
          U: 左奇异向量 (样本空间)
          Σ: 奇异值 (每个潜在维度的强度)
          V^T: 右奇异向量 (特征空间)

        k-rank 近似 = 保留前 k 个奇异值 → 最佳低秩近似 (Eckart-Young)
        """
        if k is None:
            result = self.pca(data)
            k = result.effective_rank

        U, S, Vt = np.linalg.svd(data, full_matrices=False)
        S_k = np.zeros_like(S)
        S_k[:k] = S[:k]

        return U[:, :k], S_k[:k], Vt[:k, :]

    def spectral_graph_analysis(self, adjacency: np.ndarray) -> SpectralGraph:
        """
        图的谱分析 — 拉普拉斯矩阵的特征分解。

        拉普拉斯矩阵 L = D - A:
          - λ₁ = 0 (总是), v₁ = 1 (全连接分量)
          - λ₂ (代数连通度): 越大 → 图越连通
          - λ₂ 的谱间隙: 指示最优聚类数

        应用:
          - 因果图中哪些变量聚类在一起？
          - 图的全局连通性如何？
        """
        n = adjacency.shape[0]
        degrees = adjacency.sum(axis=1)
        D = np.diag(degrees)
        L = D - adjacency

        eigenvalues, eigenvectors = np.linalg.eigh(L)

        algebraic_connectivity = eigenvalues[1] if n > 1 else 0.0

        # 谱间隙: 相邻特征值的最大跳跃
        gaps = np.diff(eigenvalues)
        spectral_gap = float(np.max(gaps)) if len(gaps) > 0 else 0.0

        return SpectralGraph(
            adjacency=adjacency,
            laplacian=L,
            eigenvalues=eigenvalues,
            eigenvectors=eigenvectors,
            algebraic_connectivity=algebraic_connectivity,
            spectral_gap=spectral_gap,
        )

    def importance_ranking(self, data: np.ndarray,
                           feature_names: List[str]) -> List[Tuple[str, float]]:
        """
        特征重要性排序 — 基于本征值的特征选择。

        对每个特征，计算它在主成分中的加权贡献:
          importance(f_j) = Σ_i |λ_i| · |v_{i,j}|
          
        含义: 在变化最大的方向上贡献越大的特征越重要。
        """
        result = self.pca(data)
        lam = np.abs(result.eigenvalues)
        V = np.abs(result.eigenvectors)

        # 加权重要性
        importance = V @ lam
        importance = importance / importance.sum() if importance.sum() > 0 else importance

        ranked = sorted(
            zip(feature_names, importance),
            key=lambda x: x[1], reverse=True
        )
        return ranked

    def dimension_reduction(self, data: np.ndarray,
                            method: str = "pca") -> Tuple[np.ndarray, EigenResult]:
        """
        降维 — 将高维感知数据压缩到有效维度。

        Returns:
          reduced_data: (n_samples × effective_rank) 
          result: 完整的特征分解结果
        """
        if method == "pca":
            result = self.pca(data)
            centered = data - data.mean(axis=0)
            reduced = centered @ result.eigenvectors[:, :result.effective_rank]
            return reduced, result
        else:
            raise ValueError(f"Unknown method: {method}")


# ═══════════════════════════════════════════════════════════════
# Quantum Connection: 观测 = 特征分解
# ═══════════════════════════════════════════════════════════════

@dataclass
class ObservableMeasurement:
    """
    量子可观测量测量 — 特征分解视角。

    量子:  可观测量 = Hermitian 算符 Â
           本征值 λ_i = 可能的测量结果
           本征态 |φ_i⟩ = 测量后的状态
           P(λ_i) = |⟨φ_i|ψ⟩|²  (Born 规则)

    AI 对应:
           数据矩阵 X^T X  = "可观测量"
           本征值 λ_i = 每个模式的强度 (方差)
           本征向量 v_i = "主成分方向"
           投影 x·v_i = 样本在该方向上的得分
    """

    def __init__(self):
        pass

    def measure(self, state_vector: np.ndarray,
                covariance: np.ndarray) -> List[Tuple[float, float, np.ndarray]]:
        """
        "测量"数据 → 本征值 (可能结果) + 本征向量 (坍缩方向) + 概率 (解释方差比)。

        Returns:
          [(eigenvalue, probability, eigenvector), ...]
        """
        eigenvalues, eigenvectors = np.linalg.eigh(covariance)
        eigenvalues = eigenvalues[::-1]
        eigenvectors = eigenvectors[:, ::-1]

        total = eigenvalues.sum()
        probs = eigenvalues / total if total > 0 else eigenvalues

        results = []
        for i in range(len(eigenvalues)):
            results.append((eigenvalues[i], probs[i], eigenvectors[:, i]))

        return results

    def collapse(self, state: np.ndarray,
                 measurement_basis: np.ndarray) -> np.ndarray:
        """
        向测量基坍缩 — 投影到本征向量方向。

        类似于: 测量使叠加态坍缩到一个本征态。
        在数据中: 将数据投影到主成分方向。
        """
        return state @ measurement_basis


# ═══════════════════════════════════════════════════════════════
# Koopman Operator: 非线性动力学的谱分解
# ═══════════════════════════════════════════════════════════════

class KoopmanSpectral:
    """
    Koopman 算子谱分析 — 在无限维函数空间中线性化非线性动力学。

    核心思想:
      非线性动力学:  x_{t+1} = f(x_t)   (难以分析)
      Koopman 提升:  g(x_{t+1}) = K g(x_t)  (线性! 但在函数空间)

      K 是一个无限维线性算子。其特征分解:
        K φ_k = μ_k φ_k

        μ_k = 本征值 (频率和衰减率)
        φ_k = 本征函数 (相干结构 / 模式)

    在因果推断中的应用:
      - 发现隐式因果结构 (Koopman 模式 = 因果变量)
      - 预测长期演化 (通过本征值指数)
      - 分离快慢动力学 (不同本征值对应不同时间尺度)
    """

    def __init__(self, n_delays: int = 10):
        """
        Args:
            n_delays: Hankel 矩阵的时间延迟嵌入维度
        """
        self.n_delays = n_delays

    def fit(self, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        用 DMD (Dynamic Mode Decomposition) 近似 Koopman 算子。

        data: (n_timesteps × n_features)

        Returns:
          eigenvalues: Koopman 本征值 (复数, 模长=增长率, 幅角=频率)
          modes: Koopman 模式 (每个模式对应一个相干结构)
        """
        # 构造快照矩阵
        X = data[:-1].T    # (n_features × n_timesteps-1)
        Y = data[1:].T     # (n_features × n_timesteps-1)

        # DMD: 寻找 A 使得 Y ≈ A X
        # A = Y X^+  (X^+ = X 的伪逆)
        U, S, Vt = np.linalg.svd(X, full_matrices=False)

        # 截断: 保留 99% 的奇异值能量
        energy = np.cumsum(S) / S.sum()
        r = int(np.searchsorted(energy, 0.99) + 1)
        r = min(r, len(S))

        U_r = U[:, :r]
        S_r = np.diag(S[:r])
        V_r = Vt[:r, :].T.conj()

        # A 的低秩近似在 r 维子空间中
        A_tilde = U_r.T.conj() @ Y @ V_r @ np.linalg.inv(S_r)

        # 特征分解
        eigenvalues, eigenvectors = np.linalg.eig(A_tilde)

        # 重构高维模式
        modes = Y @ V_r @ np.linalg.inv(S_r) @ eigenvectors

        return eigenvalues, modes

    def predict(self, eigenvalues: np.ndarray, modes: np.ndarray,
                x0: np.ndarray, n_steps: int) -> np.ndarray:
        """
        利用 Koopman 模式预测未来。

        x(t) ≈ Σ b_k · φ_k · μ_k^t

        其中 b_k 是初始条件在模式上的投影。
        """
        # 计算初始条件在模式上的投影权重
        b = np.linalg.lstsq(modes, x0, rcond=None)[0]

        predictions = np.zeros((n_steps, len(x0)), dtype=complex)
        for t in range(n_steps):
            predictions[t] = modes @ (b * eigenvalues ** t)

        return predictions.real

    def mode_decomposition(self, data: np.ndarray) -> List[Dict]:
        """
        将时间序列分解为 Koopman 模式。

        Returns:
          [{"eigenvalue": μ, "frequency": f, "growth_rate": g, 
            "mode": φ, "amplitude": a}, ...]
        """
        eigenvalues, modes = self.fit(data)

        result = []
        for i in range(len(eigenvalues)):
            mu = eigenvalues[i]
            phi = modes[:, i]

            freq = np.abs(np.angle(mu)) / (2 * np.pi) if abs(mu) > 1e-10 else 0.0
            growth = np.log(np.abs(mu) + 1e-15)

            mode_type = "oscillatory" if abs(np.imag(mu)) > 1e-6 else "real"
            if growth > 0.01:
                stability = "unstable"
            elif growth < -0.01:
                stability = "decaying"
            else:
                stability = "neutral"

            result.append({
                "eigenvalue": mu,
                "frequency": freq,
                "growth_rate": growth,
                "mode": phi,
                "stability": stability,
                "type": mode_type,
            })

        return result
