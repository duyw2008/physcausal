# 对称破缺的因果结构

> PhysCausal 知识库 — 2026-06-09

## 核心问题

δS=0 保证了稳定解的存在，但为什么自然界要"破缺"对称性？

## 关系: 对称性与稳定性

```
               作用量 S
                  │
       ┌──────────┴──────────┐
       │                     │
  变分约束                不变性约束
  δS = 0                 S[φ] = S[φ + δφ]
       │                     │
       ▼                     ▼
   稳定性                 对称性
 "路径选哪条"           "规则不变的那些方向"
       │                     │
       └──────────┬──────────┘
                  │
             Noether 定理
      (同源关系, 不是因果关系)
```

不是"谁先谁后"的问题。稳定性更根本（没有 δS=0 连对称的载体都没有），但两者来自同一个 S，是同一个原理的两个面孔。

## 为什么需要破缺

δS=0 只规定"选哪个极小值"，不规定选"谁"。

S 本身关于某变换对称（作用层面），但使 δS=0 的具体解可以不对称（解层面）。这是自发破缺的本质——不是 S 出了 bug，是解在多个等价的极小值中必须选一个。

如果不选 → 所有方向等价 → 没有粒子质量 → 没有化学元素 → 没有结构。

对称破缺不是对称性的失败，是稳定性产生复杂性的必然代价。

## 因果分类: 什么可靠, 什么不可靠

### 可靠边 (可入库)

| 因果边 | 层级 | 物理机制 |
|--------|------|---------|
| `temperature < T_c → broken_symmetry` | tier 2 | 热力学相变，降温到临界点以下 |
| `external_perturbation → broken_symmetry` | tier 2 | 加外场打破对称 (Zeeman, Stark) |
| `quantum_fluctuation + degenerate_vacuum → broken_symmetry` | tier 3 | 量子涨落触发选择 |

### 不可靠"变量" (禁止入库)

"自发选择" (`spontaneous_choice`) 不是一个因果变量。它是我们对未知触发机制的占位符。

这和 `collapse_probability` 是同一类问题:
- 测不准不是因为"不知道"
- 坍缩不是因为"有人看"
- 对称破缺不是因为"系统选了"

这些都是因果机制缺失时的命名。PhysCausal 不应该把它们当因果变量使用。

## 因果图现状

已有边:
- `temperature → order_parameter` (PhaseTransition, tier 1)
- `order_parameter → phase` (SymmetryBreaking, tier 1)

新增边 (本次):
- `temperature → broken_symmetry` (tier 2)
- `external_perturbation → broken_symmetry` (tier 2)
- `quantum_fluctuation → broken_symmetry` (tier 3, 带 degenerate_vacuum 条件)

## 哲学涵义

Landauer 视角: 对称破缺 = 信息被写入系统。破缺前，"选哪个方向"的信息不在系统里；破缺后，信息注入。对称性代表了系统的"无知"，破缺代表了"知道了"。

这和 Wheeler 的几何同一性形成呼应: 几何是物理的"稳定骨架"，对称性是骨架的"规则性"，破缺是骨架在具体动力学态中的"姿态选择"。
