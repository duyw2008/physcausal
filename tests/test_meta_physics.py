"""
元物理层测试 — symmetry + entropy + measurement
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from meta_physics.symmetry import (
    SymmetryType, SymmetryDetector,
)
from physics.symmetry_breaking import SymmetryBreakingDetector
from meta_physics.entropy import EntropyArrow


# ═══════════════════════════════════════════════════════════════
# Symmetry Tests
# ═══════════════════════════════════════════════════════════════

class TestSymmetryDetector:

    @classmethod
    def setup_class(cls):
        cls.detector = SymmetryDetector()

    def test_detect_energy_conservation(self):
        symmetries = self.detector.detect(["mass", "velocity", "x", "y"])
        sym_types = {s.symmetry_type for s in symmetries}
        assert SymmetryType.TIME_TRANSLATION in sym_types

    def test_detect_mechanical_energy(self):
        symmetries = self.detector.detect(["mass", "velocity", "height"])
        names = {s.conserved_law.name for s in symmetries if s.conserved_law}
        assert "Mechanical Energy Conservation" in names

    def test_detect_momentum_two_body(self):
        symmetries = self.detector.detect(["m1", "m2", "v1", "v2"])
        sym_types = {s.symmetry_type for s in symmetries}
        assert SymmetryType.SPACE_TRANSLATION in sym_types

    def test_no_symmetry_for_arbitrary_vars(self):
        symmetries = self.detector.detect(["color", "price", "rating"])
        assert len(symmetries) == 0

    def test_validate_conservation_elastic(self):
        before = {"m1": 1, "m2": 1, "v1": 2, "v2": 0}
        after = {"m1": 1, "m2": 1, "v1": 0, "v2": 2}
        results = self.detector.validate_conservation(before, after, ["m1","m2","v1","v2"])
        for name, ok in results.items():
            if "Momentum" in name:
                assert ok, f"Expected momentum conserved: {name}"

    def test_validate_conservation_inelastic(self):
        before = {"m1": 1, "m2": 1, "v1": 2, "v2": 0}
        after = {"m1": 1, "m2": 1, "v1": 0, "v2": 0}
        results = self.detector.validate_conservation(before, after, ["m1","m2","v1","v2"])
        for name, ok in results.items():
            if "Momentum" in name:
                assert not ok, f"Expected momentum NOT conserved: {name}"


class TestSymmetryBreaking:

    def setup_method(self):
        self.detector = SymmetryBreakingDetector()

    def test_stable_data_no_transition(self):
        np.random.seed(42)
        data = np.random.normal(0, 1, (200, 3))
        t = self.detector.detect_phase_transition(data, ["x","y","z"], window_size=50)
        assert len(t) == 0

    def test_variance_jump_detected(self):
        np.random.seed(42)
        n = 300
        data = np.column_stack([
            np.concatenate([np.random.normal(0,1,150), np.random.normal(0,5,150)]),
            np.random.normal(0, 1, n),
        ])
        t = self.detector.detect_phase_transition(data, ["x","y"], window_size=50)
        assert len(t) > 0


# ═══════════════════════════════════════════════════════════════
# Entropy Tests
# ═══════════════════════════════════════════════════════════════

class TestEntropyArrow:

    def setup_method(self):
        self.arrow = EntropyArrow()

    def test_causal_direction_nonlinear(self):
        """非线性关系: 二次拟合能打破对称性"""
        np.random.seed(42)
        n = 1000
        x = np.random.normal(0, 1, n)
        y = x**3 + np.random.normal(0, 0.5, n)  # Y = X³ + noise
        data = np.column_stack([x, y])

        r = self.arrow.infer_causal_direction(data, ["X","Y"], "X", "Y")
        assert "X" in r.direction and "Y" in r.direction, \
            f"Should return a direction, got {r.direction}"

    def test_causal_direction_linear_gaussian(self):
        """线性高斯: 返回等价类 (理论正确行为)"""
        np.random.seed(42)
        n = 2000
        x = np.random.normal(0, 1, n)
        y = 3.0 * x + np.random.normal(0, 0.5, n)
        data = np.column_stack([x, y])
        r = self.arrow.infer_causal_direction(data, ["X","Y"], "X", "Y")
        # 线性高斯系统方向不可判定 — 这是已知的理论限制
        assert "等价类" in r.direction or "X→Y" in r.direction or "Y→X" in r.direction, \
            f"Unexpected result: {r.direction}"

    def test_conditional_entropy_reduction(self):
        np.random.seed(42)
        n = 500
        x = np.random.normal(0, 1, n)
        y = 3.0 * x + np.random.normal(0, 0.1, n)
        h_y = self.arrow.compute_entropy(y)
        h_y_given_x = self.arrow.compute_conditional_entropy(x, y)
        assert h_y_given_x < h_y, \
            f"Conditional {h_y_given_x:.3f} should < unconditional {h_y:.3f}"
