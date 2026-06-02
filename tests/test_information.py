"""
信息层测试 — ShannonEntropy + InformationBottleneck + MaxEnt
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from information.shannon import ShannonEntropy, BoltzmannBridge
from information.bottleneck import InformationBottleneck, CompressionReport
from information.jaynes import MaxEnt


class TestShannonEntropy:

    def test_basic_entropy(self):
        data = np.array([0, 0, 0, 1, 1, 1])
        h = ShannonEntropy.entropy(data, bins=5)
        assert h >= 0

    def test_deterministic_is_zero(self):
        data = np.ones(100)
        h = ShannonEntropy.entropy(data, bins=10)
        assert h < 0.1  # near zero for constant

    def test_random_is_high(self):
        data = np.random.randn(1000)
        h = ShannonEntropy.entropy(data, bins=30)
        assert h > 0.5

    def test_joint_entropy(self):
        x = np.random.randn(200)
        y = 2 * x + np.random.randn(200) * 0.1
        h_xy = ShannonEntropy.joint_entropy(x, y, bins=10)
        h_x = ShannonEntropy.entropy(x, bins=10)
        assert h_xy >= h_x  # joint >= marginal

    def test_mutual_information(self):
        np.random.seed(42)
        x = np.random.randn(500)
        y = 3 * x + np.random.randn(500) * 0.1  # strong dependence
        mi = ShannonEntropy.mutual_information(x, y, bins=15)
        assert mi > 0.5, f"MI should be > 0.5, got {mi:.3f}"

    def test_independent_zero_mi(self):
        np.random.seed(42)
        x = np.random.randn(500)
        y = np.random.randn(500)
        mi = ShannonEntropy.mutual_information(x, y, bins=15)
        assert mi < 0.3, f"MI of independent vars should be low, got {mi:.3f}"

    def test_kl_divergence(self):
        p = np.array([0.7, 0.2, 0.1])
        q = np.array([0.33, 0.33, 0.34])
        kl = ShannonEntropy.kl_divergence(p, q)
        assert kl > 0

    def test_kl_self_is_zero(self):
        p = np.array([0.5, 0.3, 0.2])
        kl = ShannonEntropy.kl_divergence(p, p)
        assert abs(kl) < 1e-10

    def test_js_divergence(self):
        p = np.array([0.8, 0.2])
        q = np.array([0.2, 0.8])
        js = ShannonEntropy.js_divergence(p, q)
        assert 0 < js < np.log(2)

    def test_transfer_entropy(self):
        np.random.seed(42)
        n = 300
        source = np.random.randn(n)
        target = 0.5 * np.roll(source, 1) + np.random.randn(n) * 0.2
        target[0] = 0
        te = ShannonEntropy.transfer_entropy(source, target, lag=1)
        assert te >= 0, f"TE should be ≥ 0, got {te:.3f}"


class TestBoltzmannBridge:

    def test_landauer_bound(self):
        cost = BoltzmannBridge.landauer_bound(1.0, 300.0)
        assert 1e-22 < cost < 1e-20  # ~2.9e-21 J

    def test_round_trip(self):
        h = 5.0  # nats
        s = BoltzmannBridge.shannon_to_boltzmann(h)
        h_back = BoltzmannBridge.boltzmann_to_shannon(s)
        assert abs(h - h_back) < 1e-10


class TestInformationBottleneck:

    def test_compression_bound(self):
        np.random.seed(42)
        x = np.random.randn(200, 10)
        y = x[:, 0] * 3 + np.random.randn(200) * 0.1
        ib = InformationBottleneck(beta=1.0)
        tx, ty = ib.compute_compression_bound(x, y, n_components=5)
        assert tx > 0
        assert ty > 0

    def test_relevance_score(self):
        np.random.seed(42)
        feat = np.random.randn(500)
        target = 2 * feat + np.random.randn(500) * 0.1
        ib = InformationBottleneck()
        rel = ib.relevance_score(feat, target)
        assert 0 < rel <= 1.0


class TestMaxEnt:

    def test_gaussian_constraints(self):
        """均值和方差约束 → 最大熵 ≈ 正态"""
        data = np.random.randn(500)
        cons, vals = MaxEnt.gaussian_moment_constraints(data)
        assert len(cons) == 2
        p = MaxEnt.maxent_distribution(cons, vals, n_points=100,
                                       support=(-5, 5), n_iterations=300)
        assert len(p) == 100
        assert abs(p.sum() * (10 / 100) - 1.0) < 0.1

    def test_boltzmann_distribution(self):
        p = MaxEnt.physical_boltzmann(
            energy_func=lambda x: x * x,
            beta=1.0, n_points=50
        )
        assert len(p) == 50
        assert abs(p.sum() * (10 / 50) - 1.0) < 0.1

    def test_entropy_of_distribution(self):
        p = np.array([0.5, 0.5])
        h = MaxEnt.entropy_of_distribution(p, dx=1.0)
        assert abs(h - np.log(2)) < 0.01
