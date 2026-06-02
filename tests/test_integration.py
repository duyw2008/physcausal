"""
桥接层测试 — perception_bridge + physics_bridge + pipeline
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from integration.perception_bridge import PerceptionToCausal, VariableSelector
from integration.physics_bridge import PhysicsToCausal
from integration.pipeline import PhysCausalPipeline


class TestPerceptionToCausal:

    def setup_method(self):
        self.bridge = PerceptionToCausal(variance_threshold=0.95)

    def test_basic_processing(self):
        np.random.seed(42)
        data = np.random.randn(200, 10)
        # 前三列方差大
        data[:, :3] *= 10

        result = self.bridge.process(data)
        assert result["n_original"] == 10
        assert result["n_selected"] <= 10
        assert result["n_selected"] >= 1
        assert result["data"].shape[1] == result["n_selected"]
        assert "importance" in result
        assert 0 < result["explained_variance"] <= 1.0

    def test_variable_importance_ranking(self):
        np.random.seed(42)
        data = np.random.randn(200, 5)
        data[:, 0] *= 20   # v0 方差最大
        data[:, 4] *= 0.1  # v4 方差最小

        result = self.bridge.process(data)
        imp = result["importance"]
        assert imp["V0"] > imp["V4"], \
            f"V0 importance {imp['V0']:.4f} should > V4 {imp['V4']:.4f}"

    def test_max_variables(self):
        bridge = PerceptionToCausal(max_variables=3)
        np.random.seed(42)
        data = np.random.randn(100, 10)
        result = bridge.process(data)
        assert result["n_selected"] <= 3


class TestVariableSelector:

    def setup_method(self):
        self.selector = VariableSelector(method="spectral", max_variables=5)

    def test_spectral_select(self):
        np.random.seed(42)
        data = np.random.randn(200, 8)
        data[:, :2] *= 20  # 前两列高方差

        names = [f"x{i}" for i in range(8)]
        selected_names, selected_data = self.selector.select(data, names)
        assert len(selected_names) <= 5
        assert selected_data.shape[1] == len(selected_names)

    def test_variance_select(self):
        selector = VariableSelector(method="variance", variance_threshold=0.5)
        np.random.seed(42)
        data = np.random.randn(100, 5)
        names = [f"x{i}" for i in range(5)]
        selected_names, _ = selector.select(data, names)
        assert len(selected_names) >= 1


class TestPhysicsToCausal:

    def setup_method(self):
        self.bridge = PhysicsToCausal()

    def test_constrain_graph_mechanics(self):
        """力学变量应受到物理约束"""
        edges = [("force", "acceleration"), ("acceleration", "velocity")]
        vars_ = ["force", "mass", "acceleration", "velocity"]

        result = self.bridge.constrain_graph(edges, vars_)
        assert "force" in str(result["constrained_edges"]) or \
               "acceleration" in str(result["constrained_edges"])
        assert len(result["physics_laws_applied"]) > 0

    def test_suggest_causal_variables(self):
        """物理定律应建议因果边"""
        vars_ = ["force", "mass", "acceleration", "velocity", "x", "k"]
        result = self.bridge.suggest_causal_variables(vars_)
        assert len(result["suggested_edges"]) > 0
        assert len(result["relevant_laws"]) > 0

    def test_validate_causal_path(self):
        """因果路径验证"""
        path = ["force", "acceleration", "velocity"]
        result = self.bridge.validate_causal_path(
            path, ["force", "mass", "acceleration", "velocity"]
        )
        assert result["is_physically_valid"]


class TestPipeline:

    def setup_method(self):
        self.pipeline = PhysCausalPipeline()

    def test_end_to_end_smoke(self):
        """端到端冒烟测试"""
        np.random.seed(42)
        n = 200

        # 生成有因果结构的数据
        x1 = np.random.normal(0, 1, n)
        x2 = np.random.normal(0, 1, n)
        treatment = 2.0 * x1 + 0.5 * x2 + np.random.normal(0, 0.3, n)
        outcome = 1.5 * treatment + 0.8 * x1 + np.random.normal(0, 0.2, n)

        data = np.column_stack([x1, x2, treatment, outcome])
        names = ["confounder1", "confounder2", "treatment", "outcome"]

        result = self.pipeline.run(
            data, names,
            treatment="treatment", outcome="outcome",
            verbose=False,
        )

        assert result["stage"] == "complete"
        assert "perception" in result
        assert "causal" in result

    def test_quick_analyze(self):
        np.random.seed(42)
        n = 100
        x1 = np.random.normal(0, 1, n)
        treatment = 2.0 * x1 + np.random.normal(0, 0.2, n)
        outcome = 1.5 * treatment + 0.5 * x1 + np.random.normal(0, 0.2, n)
        data = np.column_stack([x1, treatment, outcome])
        names = ["X", "T", "Y"]

        summary = self.pipeline.quick_analyze(data, names, "T", "Y")
        assert "PhysCausal" in summary
        assert "Perception" in summary or "perception" in summary.lower()
