"""
贝叶斯层测试 — structural + parameter + active_learning
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from bayesian.structural import StructuralPosterior
from bayesian.parameter import ParameterInference
from bayesian.active_learning import ActiveExperimentDesign


class TestStructuralPosterior:

    def setup_method(self):
        self.sp = StructuralPosterior(method="bootstrap")

    def test_bootstrap_posterior(self):
        np.random.seed(42)
        n = 200
        x = np.random.normal(0, 1, n)
        y = 2.0 * x + np.random.normal(0, 0.3, n)
        z = 0.5 * y + np.random.normal(0, 0.2, n)
        data = np.column_stack([x, y, z])
        names = ["X", "Y", "Z"]

        posterior = self.sp.infer(data, names, n_samples=30)
        assert posterior.n_samples > 0
        assert len(posterior.edge_posteriors) > 0

    def test_prior_forbidden_edges(self):
        np.random.seed(42)
        n = 200
        x = np.random.normal(0, 1, n)
        y = 2 * x + np.random.normal(0, 0.3, n)
        data = np.column_stack([x, y])
        names = ["X", "Y"]

        posterior = self.sp.infer(
            data, names,
            prior_edges=[("X", "Y")],
            forbidden_edges=[("Y", "X")],
            n_samples=20,
        )
        for ep in posterior.edge_posteriors:
            if ep.source == "Y" and ep.target == "X":
                assert ep.probability == 0.0

    def test_edge_confidence_report(self):
        np.random.seed(42)
        n = 200
        x = np.random.normal(0, 1, n)
        y = 2 * x + np.random.normal(0, 0.3, n)
        data = np.column_stack([x, y])

        posterior = self.sp.infer(data, ["X", "Y"], n_samples=30)
        report = self.sp.edge_confidence_report(posterior)
        assert "X" in report and "Y" in report

    def test_mcmc_posterior(self):
        sp = StructuralPosterior(method="mcmc")
        np.random.seed(42)
        n = 100
        x = np.random.normal(0, 1, n)
        y = 2 * x + np.random.normal(0, 0.3, n)
        data = np.column_stack([x, y])

        posterior = sp.infer(data, ["X", "Y"], n_samples=50, temperature=0.5)
        assert posterior.n_samples > 0


class TestParameterInference:

    def setup_method(self):
        self.pi = ParameterInference(method="conjugate")

    def test_basic_parameter_inference(self):
        np.random.seed(42)
        n = 200
        x = np.random.normal(0, 1, n)
        y = 2.0 * x + np.random.normal(0, 0.3, n)
        data = np.column_stack([x, y])

        result = self.pi.infer(data, ["X", "Y"], [("X", "Y")])
        assert "Y" in result
        assert "X" in result["Y"].coefficients
        beta = result["Y"].coefficients["X"]
        assert abs(beta.mean - 2.0) < 0.2, f"Expected β≈2.0, got {beta.mean:.3f}"

    def test_ate_posterior(self):
        np.random.seed(42)
        n = 200
        x = np.random.normal(0, 1, n)
        y = 1.5 * x + np.random.normal(0, 0.3, n)
        data = np.column_stack([x, y])

        result = self.pi.infer(data, ["X", "Y"], [("X", "Y")])
        ate = self.pi.ate_posterior(result, "X", "Y")
        assert abs(ate.mean - 1.5) < 0.2

    def test_physical_prior_injection(self):
        np.random.seed(42)
        n = 100
        x = np.random.normal(0, 1, n)
        y = 0.5 * x + np.random.normal(0, 0.3, n)
        data = np.column_stack([x, y])

        # 物理先验: β ≈ 1/m = 1.0 (strong prior)
        result = self.pi.infer(
            data, ["force", "acceleration"],
            [("force", "acceleration")],
            prior_equations={"acceleration": {"force": (1.0, 0.01)}},
        )
        assert "acceleration" in result
        assert "force" in result["acceleration"].coefficients
        beta = result["acceleration"].coefficients["force"]
        # 强先验 (1.0, 0.01) 应把后验拉向 1.0
        assert abs(beta.mean - 1.0) < 0.3

    def test_report(self):
        np.random.seed(42)
        n = 100
        x = np.random.normal(0, 1, n)
        y = 1.5 * x + np.random.normal(0, 0.3, n)
        data = np.column_stack([x, y])
        result = self.pi.infer(data, ["X", "Y"], [("X", "Y")])
        report = self.pi.report(result)
        assert "Y" in report


class TestActiveExperimentDesign:

    def setup_method(self):
        self.aed = ActiveExperimentDesign()

    def test_propose_experiments(self):
        sp = StructuralPosterior(method="bootstrap")
        np.random.seed(42)
        n = 200
        x1 = np.random.normal(0, 1, n)
        x2 = np.random.normal(0, 1, n)
        y = 1.0 * x1 + 0.3 * x2 + np.random.normal(0, 0.5, n)
        data = np.column_stack([x1, x2, y])
        names = ["X1", "X2", "Y"]

        posterior = sp.infer(data, names, n_samples=20)
        plan = self.aed.propose_experiments(posterior, names)

        assert plan.current_entropy >= -0.01  # near-zero is OK
        # With fast mode, may converge quickly → no experiment needed
        assert isinstance(plan.recommended.variable, str)

    def test_simulate_intervention(self):
        sp = StructuralPosterior(method="bootstrap")
        np.random.seed(42)
        n = 200
        x = np.random.normal(0, 1, n)
        y = 1.5 * x + np.random.normal(0, 0.3, n)
        data = np.column_stack([x, y])
        names = ["X", "Y"]

        posterior = sp.infer(data, names, n_samples=20)
        after = self.aed.simulate_intervention(posterior, "X")
        assert after.entropy <= posterior.entropy + 0.1
