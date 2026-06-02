"""
最小作用量原理测试 — Lagrangian + ActionPrinciple + NoetherBridge
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from meta_physics.least_action import (
    Lagrangian, ActionResult, ActionPrinciple, NoetherBridge,
    CausalPathValidator,
    simple_pendulum, harmonic_oscillator, free_particle, kepler_system,
)


class TestLagrangian:
    """拉格朗日量测试"""

    def test_pendulum_creation(self):
        L = simple_pendulum(length=1.0, g=9.81)
        assert L.name == "Simple Pendulum"
        assert "length" in L.parameters

    def test_harmonic_oscillator_creation(self):
        L = harmonic_oscillator(omega=2.0)
        assert L.name == "Harmonic Oscillator"
        assert L.parameters["k"] == 4.0  # k = omega^2

    def test_free_particle_zero_potential(self):
        L = free_particle()
        assert L.potential(1.0) == 0.0

    def test_lagrangian_call(self):
        L = free_particle()
        val = L(q=1.0, q_dot=2.0)
        assert val > 0  # T-V = ½mv² > 0


class TestActionPrinciple:
    """作用量原理引擎测试"""

    def setup_method(self):
        self.L = harmonic_oscillator(omega=1.0)
        self.ap = ActionPrinciple(self.L, tolerance=0.05)

    def test_compute_action_constant(self):
        """静止路径的作用量应为 0 (T=0, V=0 at q=0)"""
        path = np.zeros(50)
        S = self.ap.compute_action(path, dt=0.01)
        assert abs(S) < 1e-6

    def test_validate_straight_line(self):
        """直线路径对谐振子不满足 δS=0"""
        path = np.linspace(0.0, 1.0, 100)
        result = self.ap.validate_path(path, dt=0.01)
        assert result.action != 0
        # 直线不是稳态路径
        assert not result.is_stationary or result.max_gradient > 0

    def test_find_stationary_path(self):
        """变分优化应找到接近 δS=0 的路径"""
        result = self.ap.find_stationary_path(
            q_start=0.5, q_end=-0.3, n_steps=50, dt=0.01,
            n_iterations=300, learning_rate=0.01
        )
        assert result.action != 0
        # 路径应比直线更接近稳态
        straight = np.linspace(0.5, -0.3, 50)
        S_straight = self.ap.compute_action(straight, dt=0.01)
        assert result.action < S_straight, \
            f"Optimized action {result.action:.4f} should < straight {S_straight:.4f}"

    def test_pendulum_action(self):
        """单摆: 物理路径作用量应小于线性路径"""
        L = simple_pendulum(length=1.0, g=9.81)
        ap = ActionPrinciple(L, tolerance=0.05)

        n = 100; dt = 0.01
        straight = np.linspace(0.5, -0.3, n)
        S_lin = ap.compute_action(straight, dt)

        result = ap.find_stationary_path(0.5, -0.3, n_steps=n, dt=dt,
                                         n_iterations=300, learning_rate=0.005)
        assert result.action < S_lin, \
            f"Physical action {result.action:.6f} should be < linear {S_lin:.6f}"


class TestNoetherBridge:
    """Noether 桥接测试"""

    def setup_method(self):
        self.L = harmonic_oscillator(omega=1.0)
        self.bridge = NoetherBridge(self.L)

    def test_energy_computation(self):
        """谐振子能量计算"""
        E = self.bridge.energy(q=1.0, q_dot=0.0)
        # E = T + V = 0 + ½kq² = 0.5
        assert abs(E - 0.5) < 0.1

    def test_energy_conservation(self):
        """小振幅振荡应近似能量守恒"""
        dt = 0.01; n = 500
        t = np.arange(n) * dt
        path = 0.1 * np.cos(t)  # 谐振子解
        conserved = self.bridge.is_energy_conserved(path, dt)
        assert conserved

    def test_conserved_quantities(self):
        conserved = self.bridge.conserved_quantities()
        assert len(conserved) > 0


class TestCausalPathValidator:
    """因果路径验证器测试"""

    def setup_method(self):
        L = harmonic_oscillator(omega=1.0)
        ap = ActionPrinciple(L, tolerance=0.05)
        self.validator = CausalPathValidator(ap)

    def test_possible_causal_path(self):
        """合理范围内的因果路径应标记为可能"""
        possible, note = self.validator.is_physically_possible(
            cause_state=0.0, effect_state=0.5, n_steps=50
        )
        assert possible, f"Should be possible: {note}"

    def test_rank_paths(self):
        """候选路径按作用量排序"""
        candidates = self.validator.rank_causal_paths(
            start=0.0, end=0.5, n_candidates=3
        )
        assert len(candidates) == 3
        # 应升序排列
        for i in range(len(candidates) - 1):
            assert candidates[i].action <= candidates[i + 1].action
