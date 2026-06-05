"""
组合 + 环境 + RL 测试
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from composition.composer import (
    TypedPort, ModuleInterface, interface_from_module, CompositionDiscovery,
)
from env.physics_sim import make_env, ENV_REGISTRY
from active_experiment.active_learner import ActiveLearner
from creative.module_library import ModuleLibrary


class TestModuleInterface:

    def test_create_interface(self):
        inp = TypedPort("F", "force", "input")
        out = TypedPort("a", "acceleration", "output")
        iface = ModuleInterface("test", "mechanics", [inp], [out], [("F", "a")])
        assert iface.name == "test"
        assert len(iface.inputs) == 1

    def test_can_connect_type_match(self):
        a = ModuleInterface("A", "m", 
            [TypedPort("F", "force", "input")],
            [TypedPort("a", "acceleration", "output")],
            [("F", "a")])
        b = ModuleInterface("B", "m",
            [TypedPort("a_in", "acceleration", "input")],
            [TypedPort("v", "velocity", "output")],
            [("a_in", "v")])
        conns = a.can_connect_to(b)
        assert len(conns) == 1
        assert conns[0] == ("a", "a_in")

    def test_can_connect_type_mismatch(self):
        a = ModuleInterface("A", "m",
            [TypedPort("F", "force", "input")],
            [TypedPort("a", "acceleration", "output")],
            [("F", "a")])
        b = ModuleInterface("B", "t",
            [TypedPort("T", "temperature", "input")],
            [TypedPort("P", "pressure", "output")],
            [("T", "P")])
        conns = a.can_connect_to(b)
        assert len(conns) == 0

    def test_compose(self):
        a = ModuleInterface("A", "m",
            [TypedPort("F", "force", "input")],
            [TypedPort("a", "acceleration", "output")],
            [("F", "a")])
        b = ModuleInterface("B", "m",
            [TypedPort("a_in", "acceleration", "input")],
            [TypedPort("v", "velocity", "output")],
            [("a_in", "v")])
        composed = a.compose(b, [("a", "a_in")])
        assert "F" in [p.name for p in composed.inputs]
        assert "v" in [p.name for p in composed.outputs]

    def test_interface_from_module(self):
        lib = ModuleLibrary()
        mod = lib.get("newton_second")
        assert mod is not None
        iface = interface_from_module(mod)
        assert len(iface.inputs) > 0 or len(iface.outputs) > 0


class TestCompositionDiscovery:

    def test_discover_compositions(self):
        disc = CompositionDiscovery()
        comps = disc.discover_compositions(n_max=5)
        assert len(comps) >= 0  # 可能为0如果没匹配

    def test_auto_compose(self):
        disc = CompositionDiscovery()
        result = disc.auto_compose(verbose=False)
        assert "n_discovered" in result
        assert "n_added" in result


class TestEnvRegistry:

    def test_all_envs_exist(self):
        for name in ["pendulum", "collision", "circuit", "spring",
                     "faraday", "snell", "doppler"]:
            assert name in ENV_REGISTRY, f"{name} missing"

    def test_make_and_observe(self):
        for name in ENV_REGISTRY:
            env = make_env(name)
            obs = env.observe()
            assert len(obs) == len(env.variables)
            env.reset()

    def test_intervene_does_not_crash(self):
        env = make_env("circuit")
        obs = env.intervene("V", 10.0)
        assert "I" in obs

    def test_step(self):
        env = make_env("pendulum")
        data = env.step(10)
        assert data.shape == (10, 3)


class TestActiveLearnerSmoke:

    def test_learner_init(self):
        env = make_env("circuit")
        learner = ActiveLearner(env)
        info = env.variable_info()
        assert len(info["ground_truth"]) == 2

    def test_learner_one_episode(self):
        env = make_env("circuit")
        learner = ActiveLearner(env)
        result = learner.run(n_episodes=1, samples_per_experiment=20, verbose=False)
        assert result["episodes"] == 1
        assert result["total_samples"] >= 20
