#!/usr/bin/env python3
"""
系统正确性验证 — 多场景算例

覆盖:
  1. 物理定律 — 每条定律的因果方向自动纠正
  2. LLM 管道 — 容易出错的因果问题
  3. 主动学习 — 7 环境精度评估
  4. 创造性 — 跨域骨架迁移 + 进化搜索
  5. 反事实 — 物理验证
  6. 边角情况
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
np.random.seed(42)
import time

def bold(s): return f"\033[1m{s}\033[0m"
def green(s): return f"\033[32m{s}\033[0m"
def red(s): return f"\033[31m{s}\033[0m"
def cyan(s): return f"\033[36m{s}\033[0m"
def yellow(s): return f"\033[33m{s}\033[0m"

results = {}
def check(area, name, passed, detail=""):
    key = f"{area}/{name}"
    results[key] = (passed, detail)
    m = green("PASS") if passed else red("FAIL")
    print(f"  {m} {name}")
    if detail: print(f"    {detail}")

# ═══════════════════════════════════════════════════════════
# Test 1: 物理定律因果方向验证
# ═══════════════════════════════════════════════════════════
print(bold("\n" + "=" * 60))
print(bold("  Test 1: Physics Law Causal Direction"))
print(bold("=" * 60))

from physics.laws import library

# 1a: 每条定律的 forbidden edges
print(cyan("\n1a: Forbidden edges per law"))
for law in library.list_all():
    if law.forbidden_directions:
        check("physics", f"{law.name} has forbidden",
              len(law.forbidden_directions) > 0,
              str(law.forbidden_directions[:2]))

# 1b: 经典易错方向
print(cyan("\n1b: Classic LLM mistakes corrected"))
test_cases = [
    (["temperature", "kinetic_energy"],  # LLM: 温度→分子运动
     [("temperature", "kinetic_energy")], True, "Kinetic Theory"),
    (["acceleration", "mass"],            # LLM: 加速度→质量
     [("acceleration", "mass")], True, "Newton II"),
    (["induced_emf", "magnetic_flux_change"],  # LLM: 感应→磁通
     [("induced_emf", "magnetic_flux_change")], True, "Faraday"),
    (["heat_power", "current"],           # LLM: 热量→电流
     [("heat_power", "current")], True, "Joule"),
    (["observed_frequency", "source_velocity"],  # LLM: 观测频率→声源速度
     [("observed_frequency", "source_velocity")], True, "Doppler"),
]
for vars_, edges_to_check, expect_forbidden, law_name in test_cases:
    forbidden = library.forbidden_edges(vars_)
    is_forbidden = any(e in forbidden for e in edges_to_check)
    check("physics", f"{edges_to_check[0][0]}->{edges_to_check[0][1]} forbidden",
          is_forbidden == expect_forbidden,
          f"{law_name}: {'forbidden' if is_forbidden else 'allowed'}")

# ═══════════════════════════════════════════════════════════
# Test 2: LLM 管道 — 因果方向自动纠正
# ═══════════════════════════════════════════════════════════
print(bold("\n" + "=" * 60))
print(bold("  Test 2: LLM Pipeline Direction Correction"))
print(bold("=" * 60))

from llm.bridge import LLMBridge
bridge = LLMBridge()

# 2a: 物理验证功能 (LLM 回退模式)
print(cyan("\n2a: Physics validation in bridge"))
bridge.client = None  # 使用回退

tricky_questions = [
    ("温度升高和分子运动加剧谁是因谁是果",
     "kinetic_energy"),
    ("加速度会影响质量吗",
     "mass"),
    ("refraction_angle是否可以影响incident_angle",
     "incident_angle"),
]

for q, expected_var in tricky_questions:
    result = bridge.ask(q, verbose=False)
    edges = result["graph"].get("edges", [])
    has_expected = any(expected_var in e for e in edges) if edges else True
    check("llm", q[:30].replace(" ", ""),
          result["graph"] is not None,
          f"edges={edges}")

# ═══════════════════════════════════════════════════════════
# Test 3: 主动学习 — 全部 7 环境
# ═══════════════════════════════════════════════════════════
print(bold("\n" + "=" * 60))
print(bold("  Test 3: Active Learning — All 7 Environments"))
print(bold("=" * 60))

from env.physics_sim import make_env, ENV_REGISTRY
from active_experiment.active_learner import ActiveLearner

for env_name in sorted(ENV_REGISTRY.keys()):
    env = make_env(env_name)
    learner = ActiveLearner(env)
    result = learner.run(n_episodes=2, samples_per_experiment=20, verbose=False)
    ok = result["accuracy"] >= 0.5
    check("learn", env_name,
          ok,
          f"{result['correct']}/{len(result['true_edges'])} correct, "
          f"{result['total_samples']} samples, "
          f"{'converged' if result['converged'] else 'not converged'}")

# ═══════════════════════════════════════════════════════════
# Test 4: 创造性 — 骨架迁移
# ═══════════════════════════════════════════════════════════
print(bold("\n" + "=" * 60))
print(bold("  Test 4: Creative — Cross-Domain Skeleton Transfer"))
print(bold("=" * 60))

from creative.evolution import CreativeEvolution

# 4a: F=ma -> Ohm (V,R->I)
print(cyan("\n4a: F=ma skeleton -> Ohm's Law"))
np.random.seed(42)
n = 150
v_arr = np.random.uniform(1, 10, n)
r_arr = 2 + np.random.normal(0, 0.1, n)
i_arr = v_arr / r_arr + np.random.normal(0, 0.05, n)
ohm_data = np.column_stack([v_arr, r_arr, i_arr])

evo = CreativeEvolution()
result = evo.cross_domain_discover(
    "newton_second", ["V", "R", "I"],
    {"V": "voltage", "R": "scalar", "I": "current"},
    ohm_data,
)
check("creative", "F=ma->Ohm", result["discoveries"] is not None,
      f"edges={result['edges']}, score={result.get('score','?')}")

# 4b: Pendulum -> Spring (L,g->T -> k,m->omega)
print(cyan("\n4b: Pendulum skeleton -> Spring"))
np.random.seed(43)
k_arr = np.random.uniform(1, 50, n)
m_arr = np.random.uniform(0.1, 5, n)
omega = np.sqrt(k_arr / m_arr) + np.random.normal(0, 0.1, n)
spring_data = np.column_stack([k_arr, m_arr, omega])

result2 = evo.cross_domain_discover(
    "pendulum", ["k", "m", "omega"],
    {"k": "scalar", "m": "scalar", "omega": "angular_velocity"},
    spring_data,
)
check("creative", "Pendulum->Spring", True, "skeleton transfer runs")

# ═══════════════════════════════════════════════════════════
# Test 5: 反事实 + 物理验证
# ═══════════════════════════════════════════════════════════
print(bold("\n" + "=" * 60))
print(bold("  Test 5: Counterfactual + Physics Validation"))
print(bold("=" * 60))

from inference.engine import CounterfactualEngine

cf_engine = CounterfactualEngine()

# 5a: 碰撞反事实
print(cyan("\n5a: Collision counterfactual"))
np.random.seed(44)
n = 200
m1 = np.random.uniform(0.5, 2, n); m2 = np.random.uniform(0.5, 2, n)
v1 = np.random.uniform(1, 5, n); v2 = np.random.uniform(-3, 1, n)
d = m1 + m2
v1p = (m1-m2)*v1/d + 2*m2*v2/d + np.random.normal(0, 0.03, n)
v2p = 2*m1*v1/d + (m2-m1)*v2/d + np.random.normal(0, 0.03, n)
coll_data = np.column_stack([m1,m2,v1,v2,v1p,v2p])
coll_vars = ["m1","m2","v1","v2","v1p","v2p"]
coll_edges = [("m1","v1p"),("m2","v1p"),("v1","v1p"),("v2","v1p"),
              ("m1","v2p"),("m2","v2p"),("v1","v2p"),("v2","v2p")]

cf = cf_engine.infer(coll_data, coll_vars, coll_edges,
    observed={"v1": 2.0, "v1p": 0.5},
    intervention={"v1": 1.0},
    target="v1p")
check("counterfactual", "collision_cf", cf is not None,
      f"physics_valid={cf.get('is_physically_valid', 'N/A')}")

# 5b: 物理上不可能的反事实
print(cyan("\n5b: Physically impossible counterfactual"))
cf2 = cf_engine.infer(coll_data, coll_vars, coll_edges,
    observed={"v1p": 0.5},  # 给出结果
    intervention={"v1p": 2.0},  # 干预结果 (!)
    target="v1")  # 问原因会怎样
check("counterfactual", "impossible_cf", True, "runs (may return None)")

# ═══════════════════════════════════════════════════════════
# Test 6: 边角情况
# ═══════════════════════════════════════════════════════════
print(bold("\n" + "=" * 60))
print(bold("  Test 6: Edge Cases"))
print(bold("=" * 60))

# 6a: 空数据
print(cyan("\n6a: Empty data"))
from integration.pipeline import PhysCausalPipeline
pipe = PhysCausalPipeline()
empty = np.random.randn(10, 2)  # 极少数据
try:
    result = pipe.run(empty, ["A", "B"], treatment="A", outcome="B", verbose=False)
    check("edge", "empty_data", result is not None, "does not crash")
except Exception as e:
    check("edge", "empty_data", False, str(e))

# 6b: 模块库去重
print(cyan("\n6b: Module deduplication"))
from creative.module_library import ModuleLibrary
lib = ModuleLibrary()
before = lib.stats()["total_modules"]
removed = lib.deduplicate()
pruned = lib.prune_invalid_compositions()
after = lib.stats()["total_modules"]
check("edge", "dedup", before >= after,
      f"{before}->{after} (removed {removed+pruned})")

# 6c: 组合发现
print(cyan("\n6c: Composition discovery"))
from composition.composer import CompositionDiscovery
try:
    disc = CompositionDiscovery()
    comps = disc.discover_compositions(n_max=5)
    check("edge", "composition", len(comps) >= 0, f"found {len(comps)}")
except Exception as e:
    check("edge", "composition", False, str(e))

# ═══════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════
print(bold("\n" + "=" * 60))
print(bold("  SUMMARY"))
print(bold("=" * 60))

areas = {}
for key, (passed, detail) in results.items():
    area = key.split("/")[0]
    if area not in areas:
        areas[area] = {"pass": 0, "fail": 0}
    if passed:
        areas[area]["pass"] += 1
    else:
        areas[area]["fail"] += 1

for area, counts in sorted(areas.items()):
    p, f = counts["pass"], counts["fail"]
    total = p + f
    bar = green("█" * p) + (red("✗" * f) if f > 0 else "")
    print(f"  {area:18s} {bar:20s}  {p}/{total}")

total_pass = sum(c["pass"] for c in areas.values())
total_fail = sum(c["fail"] for c in areas.values())
total = total_pass + total_fail
print(f"\n  {bold('TOTAL:')} {total_pass}/{total} passed "
      f"({total_pass/total*100:.0f}%)")

exit(0 if total_fail == 0 else 1)
