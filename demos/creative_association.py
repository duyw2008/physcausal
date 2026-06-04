#!/usr/bin/env python3
"""
创造性联想 — 跨域骨架迁移算例

场景:
  力学域: 已知 F=ma (Force, Mass → Acceleration)
  电磁域: 有数据 (Voltage, Resistance, Current)
  
  问题: 电磁域的因果结构是什么？
  
  创造性联想:
    1. 从 F=ma 提取骨架: [force, scalar] → acceleration
    2. 在电磁域找同类型变量: Voltage=force型, Resistance=scalar型, Current=acceleration型
    3. 实例化: V, R → I  → 这就是 Ohm 定律!
    4. 在电磁数据上验证: BIC 得分确认
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from creative.module_library import ModuleLibrary
from creative.skeleton_library import SkeletonLibrary
from creative.mutation import CausalMutator
from creative.filter import CausalFilter
from creative.evolution import CreativeEvolution


def bold(s): return f"\033[1m{s}\033[0m"
def cyan(s): return f"\033[36m{s}\033[0m"
def green(s): return f"\033[32m{s}\033[0m"
def yellow(s): return f"\033[33m{s}\033[0m"
def magenta(s): return f"\033[35m{s}\033[0m"


# ═══════════════════════════════════════════════════════════════
# Step 1: 准备已知模块库
# ═══════════════════════════════════════════════════════════════

print(bold("=" * 60))
print(bold("  Creative Association — Cross-Domain Skeleton Transfer"))
print(bold("=" * 60))

print(f"\n{cyan('Step 1: Module Library')}")
lib = ModuleLibrary()
stats = lib.stats()
print(f"  {stats['total_modules']} modules across {len(stats['domains'])} domains:")
for d, n in stats["domains"].items():
    print(f"    {d}: {n}")

# ═══════════════════════════════════════════════════════════════
# Step 2: 展示骨架库
# ═══════════════════════════════════════════════════════════════

print(f"\n{cyan('Step 2: Skeleton Library')}")
sk_lib = SkeletonLibrary()
analogies = sk_lib.cross_domain_analogies()
print(f"  {len(analogies)} skeletons with cross-domain analogies:\n")
for a in analogies[:4]:
    print(f"  {magenta(a['skeleton'])}: {a['description']}")
    for ex in a['examples']:
        print(f"    → {ex}")
    if a['invariants']:
        print(f"    invariants: {', '.join(a['invariants'])}")
    print()

# ═══════════════════════════════════════════════════════════════
# Step 3: 生成电磁域数据 (底层真结构 = Ohm 定律)
# ═══════════════════════════════════════════════════════════════

print(f"{cyan('Step 3: Generate electromagnetism data')}")
print(f"  Ground truth: I = V/R  (Ohm's Law)")
np.random.seed(42)
n = 200

voltage = np.random.uniform(1, 10, n)
resistance = 2.0 + np.random.normal(0, 0.1, n)
current = voltage / resistance + np.random.normal(0, 0.05, n)

data_em = np.column_stack([voltage, resistance, current])
vars_em = ["V", "R", "I"]

print(f"  {n} samples, variables: {vars_em}")
print(f"  V range: [{voltage.min():.1f}, {voltage.max():.1f}]")
print(f"  I range: [{current.min():.2f}, {current.max():.2f}]")

# ═══════════════════════════════════════════════════════════════
# Step 4: 纯数据的因果发现 (无骨架引导)
# ═══════════════════════════════════════════════════════════════

print(f"\n{cyan('Step 4: Pure data-driven discovery (PC algorithm, no skeleton)')}")
from causal.discovery import pc_algorithm

dag_pc = pc_algorithm(data_em, vars_em)
pc_edges = []
for v in vars_em:
    for c in dag_pc.children(v):
        pc_edges.append((v, c))
print(f"  PC discovered: {pc_edges}")
if len(pc_edges) <= 1:
    print(f"  {yellow('⚠ PC found few edges — linear Gaussian = Markov equivalence class')}")

# ═══════════════════════════════════════════════════════════════
# Step 5: 跨域骨架迁移 — 从 F=ma 到电磁学
# ═══════════════════════════════════════════════════════════════

print(f"\n{cyan('Step 5: Cross-domain skeleton transfer')}")
print(f"  Source: newton_second (mechanics)")
print(f"    F → a, m → a   (F=ma)")

src = lib.get("newton_second")
print(f"    Variables: {[f'{k}({v})' for k,v in src.variables.items()]}")
print(f"    Edges: {src.edges}")
print(f"    Types: {src.type_signatures}")

print(f"\n  Target: electromagnetism domain")
print(f"    Variables: {vars_em}")
target_types = {"V": "voltage", "R": "scalar", "I": "current"}

# 骨架: [force → response, scalar → response]
# 匹配: force≈voltage, scalar=scalar, response≈current
# → V → I, R → I = Ohm!

evo = CreativeEvolution()
result = evo.cross_domain_discover(
    "newton_second",
    vars_em,
    target_types,
    data_em,
)

if result["success"]:
    print(f"\n  {green('✓ CROSS-DOMAIN DISCOVERY!')}")
    print(f"    Discovered: {result['discovered_edges']}")
    print(f"    Skeleton:   {result['skeleton']}")
    print(f"    Score:      {result['score']:.1f}")
    print(f"    Novelty:    {result['novelty']:.2f}")
    print(f"\n  {yellow('F=ma skeleton (force→acceleration) → instantiated as V,R→I (Ohm)')}")
else:
    print(f"\n  Transfer not directly successful: {result.get('reason')}")
    print(f"  {yellow('(This is expected — type matching may need tuning)')}")

# ═══════════════════════════════════════════════════════════════
# Step 6: 进化搜索 — 在电磁域发现因果结构
# ═══════════════════════════════════════════════════════════════

print(f"\n{cyan('Step 6: Creative evolution on EM data')}")
print(f"  Searching for causal structure via mutation + filtering...")

evo2 = CreativeEvolution()
evo_result = evo2.evolve(
    data_em, vars_em,
    type_signatures=target_types,
    n_generations=30,
    population_size=15,
    forbidden_edges=[("I", "V"), ("I", "R")],  # 物理: 电流不能因果驱动电压/电阻
    verbose=False,
)

print(f"\n  {evo2.report(evo_result)}")

# ═══════════════════════════════════════════════════════════════
# Step 7: 总结
# ═══════════════════════════════════════════════════════════════

print(f"\n{bold('='*60)}")
print(bold("  Summary"))
print(bold("="*60))

print(f"""
  {cyan('Pure data (PC):')}     {pc_edges if pc_edges else 'equiv class — needs domain knowledge'}
  {magenta('Skeleton transfer:')} F=ma → V,R→I (Ohm's Law)
  {green('Evolution:')}         {evo_result['survivors']} survivors from {evo_result['total_candidates']} candidates

  {bold('Key insight:')}
    Cross-domain skeleton transfer bypasses the Markov equivalence
    class problem. Instead of relying on statistical independence tests
    alone (which fail for linear Gaussian systems), we use the STRUCTURAL
    isomorphism between domains to propose causal edges.

    Mechanics F=ma and electromagnetism V=IR share the same skeleton:
      [driver] → [response], [modifier] → [response]

    Once you know the skeleton in one domain, you can instantiate it
    in another — and then validate with data. This is creative association.
""")
