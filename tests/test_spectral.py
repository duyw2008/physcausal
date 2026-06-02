"""
特征谱模块测试 — SpectralDecomposer + ObservableMeasurement + KoopmanSpectral
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from spectral.spectral import (
    SpectralDecomposer, ObservableMeasurement, KoopmanSpectral
)


class TestSpectralDecomposer:

    def setup_method(self):
        self.decomp = SpectralDecomposer(variance_threshold=0.95)

    def test_pca_basic(self):
        """PCA: 基本特征分解"""
        np.random.seed(42)
        n = 500
        # 生成 2D 数据，沿 [1, 1] 方向方差大，沿 [-1, 1] 方差小
        v1 = np.array([1.0, 1.0]) / np.sqrt(2)
        v2 = np.array([-1.0, 1.0]) / np.sqrt(2)
        scores = np.column_stack([
            np.random.normal(0, 3, n),   # PC1: σ=3
            np.random.normal(0, 0.5, n), # PC2: σ=0.5
        ])
        data = scores @ np.vstack([v1, v2])

        result = self.decomp.pca(data)

        # 第一个本征值应远大于第二个
        assert result.eigenvalues[0] > result.eigenvalues[1] * 5, \
            f"λ₁={result.eigenvalues[0]:.3f} should >> λ₂={result.eigenvalues[1]:.3f}"
        assert result.effective_rank <= 2
        assert abs(result.explained_variance_ratio.sum() - 1.0) < 1e-10

    def test_pca_effective_rank(self):
        """PCA: 有效秩检测"""
        np.random.seed(42)
        n = 300
        # 3D 数据，但只有 2 维有信号
        data = np.column_stack([
            np.random.normal(0, 3, n),
            np.random.normal(0, 1, n),
            np.random.normal(0, 0.01, n),  # 几乎无信号
        ])

        result = self.decomp.pca(data)
        assert result.effective_rank <= 2, \
            f"Effective rank should be ≤ 2, got {result.effective_rank}"

    def test_importance_ranking(self):
        """特征重要性排序"""
        np.random.seed(42)
        n = 500
        # x1 是强信号, x2 是弱信号
        x1 = np.random.normal(0, 5, n)
        x2 = np.random.normal(0, 0.5, n)
        data = np.column_stack([x1, x2])

        ranked = self.decomp.importance_ranking(data, ["x1", "x2"])
        assert ranked[0][0] == "x1", \
            f"x1 should be most important, got {ranked[0]}"

    def test_dimension_reduction(self):
        """PCA 降维"""
        np.random.seed(42)
        n = 200
        # 10 维，只有 3 维有信号
        data = np.random.randn(n, 10)
        data[:, :3] *= 10  # 前三列方差大

        reduced, result = self.decomp.dimension_reduction(data)
        assert reduced.shape[1] <= 3, \
            f"Should reduce to ≤ 3 dims, got {reduced.shape[1]}"
        assert reduced.shape[0] == n


class TestObservableMeasurement:

    def setup_method(self):
        self.obs = ObservableMeasurement()

    def test_measure_returns_eigenspectrum(self):
        """测量应返回完整的特征谱"""
        np.random.seed(42)
        data = np.random.randn(100, 5)
        cov = data.T @ data / 99

        results = self.obs.measure(data[0], cov)
        assert len(results) == 5
        # 概率应归一化
        total_prob = sum(p for _, p, _ in results)
        assert abs(total_prob - 1.0) < 1e-10

    def test_collapse_project(self):
        """坍缩: 投影到本征基"""
        x = np.array([3.0, 4.0])
        basis = np.eye(2)
        result = self.obs.collapse(x, basis)
        assert np.allclose(result, x)


class TestKoopmanSpectral:

    def setup_method(self):
        self.koopman = KoopmanSpectral(n_delays=5)

    def test_fit_simple_oscillator(self):
        """DMD: 简谐振子"""
        t = np.linspace(0, 10, 200)
        x = np.sin(2 * np.pi * 0.5 * t)  # 频率 0.5 Hz
        data = np.column_stack([x])

        eigenvalues, modes = self.koopman.fit(data)
        # 至少应提取出一个模式
        assert len(eigenvalues) > 0

    def test_mode_decomposition(self):
        """模式分解: 混合信号"""
        t = np.linspace(0, 10, 200)
        # 两个频率混合
        x1 = np.sin(2 * np.pi * 0.5 * t)
        x2 = 0.5 * np.sin(2 * np.pi * 1.2 * t)
        data = np.column_stack([x1 + x2])

        modes = self.koopman.mode_decomposition(data)
        assert len(modes) > 0, "Should find at least one mode"
        # DMD modes may have near-zero imaginary part — this is OK

    def test_predict_oscillation(self):
        """预测: 简谐振动外推"""
        t = np.linspace(0, 5, 100)
        x = np.sin(2 * np.pi * 0.3 * t)
        data = np.column_stack([x])

        eigenvalues, modes = self.koopman.fit(data)
        pred = self.koopman.predict(eigenvalues, modes, data[-1], 20)

        assert pred.shape == (20, 1)
