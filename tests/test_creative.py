"""
创造性联想层测试 — module/skeleton/mutation/filter/evolution
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from creative.module_library import ModuleLibrary, CausalModule
from creative.skeleton_library import SkeletonLibrary
from creative.mutation import CausalMutator
from creative.filter import CausalFilter
from creative.evolution import CreativeEvolution


class TestModuleLibrary:

    def setup_method(self):
        self.lib = ModuleLibrary()

    def test_total_modules(self):
        assert len(self.lib.list_all()) >= 10

    def test_domain_filter(self):
        mech = self.lib.list_by_domain("mechanics")
        assert len(mech) >= 4

    def test_compatible_pairs(self):
        pairs = self.lib.compatible_pairs()
        assert len(pairs) > 0

    def test_module_registration(self):
        m = CausalModule("test", "test_domain",
                         {"X": "x"}, [("X", "Y")],
                         {"X": "scalar", "Y": "scalar"})
        self.lib.register(m)
        assert self.lib.get("test") is not None


class TestSkeletonLibrary:

    def setup_method(self):
        self.lib = SkeletonLibrary()

    def test_all_skeletons(self):
        assert len(self.lib.list_all()) >= 5

    def test_find_by_topology(self):
        chains = self.lib.find_by_topology(3, 2)
        assert any(s.name == "chain" for s in chains)

    def test_instantiate(self):
        result = self.lib.instantiate("chain", ["V", "I", "P"])
        assert result["edges"] == [("V", "I"), ("I", "P")]

    def test_cross_domain_analogies(self):
        analogies = self.lib.cross_domain_analogies()
        assert len(analogies) > 0

    def test_suggest_skeleton(self):
        sk = self.lib.suggest_skeleton([("X", "Y"), ("Y", "Z")], 3)
        assert sk == "chain"


class TestCausalMutator:

    def setup_method(self):
        self.mutator = CausalMutator()

    def test_basic_mutation(self):
        edges = [("X", "Y"), ("Y", "Z")]
        vars_ = ["X", "Y", "Z"]
        mutated = self.mutator.mutate(edges, vars_, n_mutations=2)
        assert isinstance(mutated, list)

    def test_cross_domain_mutate(self):
        lib = ModuleLibrary()
        ohm = lib.get("ohm_law")
        assert ohm is not None

        # 尝试跨域: Ohm → 力学
        target_vars = ["F", "m", "a"]
        target_types = {"F": "force", "m": "scalar", "a": "acceleration"}
        # 这个映射可能不完美 (Ohm 用 voltage/current, 力学用 force/acceleration)
        # 但 mutation 应该优雅处理类型不匹配
        result = self.mutator.cross_domain_mutate(ohm, target_vars, target_types)
        # 可能返回空或结果 — 两者都应该不崩溃
        assert isinstance(result, list)


class TestCausalFilter:

    def setup_method(self):
        self.filter = CausalFilter()

    def test_tier0_valid_dag(self):
        ok, reason = self.filter.tier0_physics(
            [("X", "Y"), ("Y", "Z")], ["X", "Y", "Z"]
        )
        assert ok, reason

    def test_tier0_invalid_dag(self):
        # 创建环
        ok, reason = self.filter.tier0_physics(
            [("X", "Y"), ("Y", "Z"), ("Z", "X")], ["X", "Y", "Z"]
        )
        assert not ok

    def test_tier0_forbidden_edge(self):
        ok, reason = self.filter.tier0_physics(
            [("X", "Y")], ["X", "Y"],
            forbidden_edges=[("X", "Y")]
        )
        assert not ok

    def test_tier1_bic(self):
        np.random.seed(42)
        n = 100
        x = np.random.normal(0, 1, n)
        y = 2 * x + np.random.normal(0, 0.3, n)
        data = np.column_stack([x, y])
        bic = self.filter.tier1_bic([("X", "Y")], ["X", "Y"], data)
        assert isinstance(bic, float)  # just check it runs

    def test_full_filter(self):
        np.random.seed(42)
        n = 100
        x = np.random.normal(0, 1, n)
        y = 2 * x + np.random.normal(0, 0.3, n)
        data = np.column_stack([x, y])
        result = self.filter.full_filter(
            [("X", "Y")], ["X", "Y"], data,
        )
        assert result["passed"]


class TestCreativeEvolution:

    def setup_method(self):
        self.evo = CreativeEvolution()

    def test_evolution_smoke(self):
        np.random.seed(42)
        n = 100
        x = np.random.normal(0, 1, n)
        y = 2 * x + np.random.normal(0, 0.3, n)
        z = 0.5 * y + np.random.normal(0, 0.2, n)
        data = np.column_stack([x, y, z])
        names = ["X", "Y", "Z"]

        result = self.evo.evolve(
            data, names,
            n_generations=10, population_size=10,
            verbose=False,
        )
        assert result["total_candidates"] > 0
        assert result["generations"] > 0

    def test_cross_domain_discover(self):
        np.random.seed(42)
        n = 100
        # 生成符合 Ohm 定律的数据: I ~ V/R
        v = np.random.uniform(1, 10, n)
        r = 2.0
        i = v / r + np.random.normal(0, 0.1, n)
        data = np.column_stack([v, i])

        result = self.evo.cross_domain_discover(
            "ohm_law",
            ["V", "I"],
            {"V": "voltage", "I": "current"},
            data,
        )
        # 可能成功也可能失败 (取决于类型匹配)
        assert "success" in result

    def test_report(self):
        result = {"generations": 5, "total_candidates": 50,
                  "survivors": 10, "survival_rate": 0.2,
                  "discoveries": [], "best_graph": ([("X","Y")], -10.0)}
        report = self.evo.report(result)
        assert "Creative Evolution" in report
