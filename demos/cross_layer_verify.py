#!/usr/bin/env python3
"""
跨层协作验证 — 端到端全栈测试

验证:
  1. 感知 → 谱分解 → 因果发现 → 物理约束 → 效应估计
  2. 反事实 + 守恒律验证
  3. 元物理桥接 → 因果图约束
  4. LLM 管道 (physics validation)
  5. 主动学习 → 模块入库 → 组合发现
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
np.random.seed(42)


def bold(s): return f"\033[1m{s}\033[0m"
def green(s): return f"\033[32m{s}\033[0m"
def red(s): return f"\033[31m{s}\033[0m"
def cyan(s): return f"\033[36m{s}\033[0m"
def yellow(s): return f"\033[33m{s}\033[0m"

results = []
def check(name, passed, detail=""):
    marker = green("✓") if passed else red("✗")
    results.append((name, passed, detail))
    print(f"  {marker} {name}")
    if detail: print(f"    {detail}")


print(bold("=" * 60))
print(bold("  Cross-Layer Integration Verification"))
print(bold("=" * 60))

# ═══════════════════════════════════════════════════════════════
# Test 1: 感知 → 谱分解 → 因果发现
# ═══════════════════════════════════════════════════════════════

print(f"\n{cyan('Test 1: Perception → Spectral → Causal Discovery')}")

from perception.engine import PerceptionEngine
from integration.perception_bridge import PerceptionToCausal

n = 200
x1 = np.random.normal(0, 1, n)
x2 = np.random.normal(0, 1, n)
y = 2 * x1 + 0.5 * x2 + np.random.normal(0, 0.3, n)
data = np.column_stack([x1, x2, y])

bridge = PerceptionToCausal()
result = bridge.process(data, ["X1", "X2", "Y"])
check("Perception→Causal pipeline", 
      result["n_selected"] >= 2 and result["n_selected"] <= 3,
      f"Selected {result['n_selected']}/{result['n_original']} vars")

# ═══════════════════════════════════════════════════════════════
# Test 2: 物理约束 → 因果图
# ═══════════════════════════════════════════════════════════════

print(f"\n{cyan('Test 2: Physics Constraints → Causal Graph')}")

from integration.physics_bridge import PhysicsToCausal
from integration.meta_physics_bridge import MetaPhysicsBridge

phys = PhysicsToCausal()
vars_phys = ["force", "mass", "acceleration"]
edges_test = [("acceleration", "mass")]  # 错误方向!
result = phys.constrain_graph(edges_test, vars_phys)
check("Physics corrects wrong direction",
      ("acceleration", "mass") not in result["constrained_edges"] or
      len(result["forced_added"]) > 0)

meta = MetaPhysicsBridge()
forbidden = meta.get_forbidden_edges(vars_phys)
check("Meta-physics bridge reports forbidden edges",
      len(forbidden) > 0,
      f"Forbidden: {forbidden[:2]}")

# ═══════════════════════════════════════════════════════════════
# Test 3: 端到端流水线
# ═══════════════════════════════════════════════════════════════

print(f"\n{cyan('Test 3: End-to-End Pipeline')}")

from integration.pipeline import PhysCausalPipeline

pipe = PhysCausalPipeline()
result = pipe.run(data, ["X1", "X2", "Y"], treatment="X1", outcome="Y", verbose=False)
check("Pipeline completes", result["stage"] == "complete")
inference = result.get("inference", {})
check("ATE is estimated", inference.get("ate") is not None,
      f"ATE={inference.get('ate', 'N/A'):.3f}" if inference.get('ate') else "")

# ═══════════════════════════════════════════════════════════════
# Test 4: 反事实 + 守恒律验证
# ═══════════════════════════════════════════════════════════════

print(f"\n{cyan('Test 4: Counterfactual + Conservation Validation')}")

from inference.engine import CounterfactualEngine

cf_engine = CounterfactualEngine()

# 碰撞数据
n = 100
m1 = np.random.uniform(0.5, 2, n); m2 = np.random.uniform(0.5, 2, n)
v1 = np.random.uniform(1, 5, n); v2 = np.random.uniform(-3, 1, n)
d = m1 + m2
v1p = (m1-m2)*v1/d + 2*m2*v2/d + np.random.normal(0, 0.05, n)
v2p = 2*m1*v1/d + (m2-m1)*v2/d + np.random.normal(0, 0.05, n)
coll_data = np.column_stack([m1,m2,v1,v2,v1p,v2p])
coll_vars = ["m1","m2","v1","v2","v1p","v2p"]
coll_edges = [("m1","v1p"),("m2","v1p"),("v1","v1p"),("v2","v1p"),
              ("m1","v2p"),("m2","v2p"),("v1","v2p"),("v2","v2p")]

cf_result = cf_engine.infer(
    coll_data, coll_vars, coll_edges,
    observed={"v1": 2.0, "v1p": 0.5},
    intervention={"v1": 1.0},
    target="v1p",
)
# Counterfactual may return None if SCM coefficients are unreliable
check("Counterfactual engine runs",
      cf_result is not None,
      f"Result: {cf_result}")

# ═══════════════════════════════════════════════════════════════
# Test 5: LLM 管道 (phys validation)
# ═══════════════════════════════════════════════════════════════

print(f"\n{cyan('Test 5: LLM Bridge Physics Validation')}")

from llm.bridge import LLMBridge

bridge_llm = LLMBridge()
# 测试 LLM 不可用时的回退
bridge_llm.client = None  # force fallback
result = bridge_llm.ask("温度升高和分子运动加剧谁是因谁是果", verbose=False)
check("LLM fallback works without API",
      result["graph"] is not None and result["analysis"] is not None)

# ═══════════════════════════════════════════════════════════════
# Test 6: 主动学习 → 模块入库 → 组合发现
# ═══════════════════════════════════════════════════════════════

print(f"\n{cyan('Test 6: Learn → Module Library → Composition')}")

from env.physics_sim import make_env
from rl.active_learner import ActiveLearner
from creative.module_library import ModuleLibrary
from composition.composer import CompositionDiscovery

env = make_env("circuit")
learner = ActiveLearner(env)
result = learner.run(n_episodes=2, samples_per_experiment=20, verbose=False)
check("Active learner converges", result["accuracy"] > 0.5,
      f"Accuracy: {result['accuracy']:.0%}, {result['total_samples']} samples")

lib = ModuleLibrary()
before = lib.stats()["total_modules"]

disc = CompositionDiscovery()
comp_result = disc.auto_compose(verbose=False)
after = lib.stats()["total_modules"]
check("Composition discovers new modules",
      comp_result["n_discovered"] > 0,
      f"Module count: {before}→{after}")

# ═══════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════

print(f"\n{bold('=' * 60)}")
print(bold("  Summary"))
print(bold("=" * 60))

passed = sum(1 for _, p, _ in results if p)
total = len(results)
for name, p, detail in results:
    marker = green("✓") if p else red("✗")
    print(f"  {marker} {name}")
print(f"\n  {passed}/{total} tests passed")
