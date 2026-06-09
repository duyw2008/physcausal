# 耗散系统的因果结构

> PhysCausal 知识库 — 2026-06-09

## 核心问题

δS=0 要求能量守恒。为什么存在耗散？大气层内飞行的无动力飞行器——它的能量去哪了？

## 物理本质: 耗散 = 子系统边界效应

δS=0 对**整个封闭系统**成立。但当我们只观察子系统时：

```
完整系统 (守恒):
  flight + atmosphere
  δS_total = 0  ✓

子系统视角 (耗散):
  flight alone
  能量流出 → atmosphere → 看起来"不可逆"

耗散不是基本物理，是视角问题。
```

## Rayleigh 耗散函数

经典 Lagrange 的处理——在运动方程右边加耗散项：

```
d  ⎛ ∂L ⎞   ∂L     ∂R
── ⎜────⎟ - ── + ──── = 0
dt ⎝ ∂q̇ ⎠   ∂q     ∂q̇

R = ½ Σ cᵢ q̇ᵢ²
```

Rayleigh 函数是对耗散的**现象学描述**——它描述了"发生了耗散"但没有解释"为什么"。在因果图上，它对应 `velocity → drag_force` 这条边。

## 无动力飞行器的完整因果链

```
velocity
  │
  ├──→ dynamic_pressure   (½ρv²)
  │       │
  │       ├──→ lift_force  (升力, 垂直运动方向)
  │       │
  │       └──→ drag_force  (阻力, 平行运动方向)
  │              │
  │              ├──→ kinetic_energy_loss
  │              │       │
  │              │       └──→ atmospheric_heating
  │              │              │
  │              │              └──→ entropy_increase
  │              │
  │              └──→ trajectory_deflection
  │
  └──→ boundary_layer_interaction
          │
          └──→ turbulent_energy_cascade
```

## 与退相干的深层联系

耗散和退相干是同一个物理原理在不同尺度的表现：

| | 经典耗散 | 量子退相干 |
|------|---------|----------|
| **系统** | 飞行器 | 量子比特 |
| **环境** | 大气 | 热浴 |
| **转移** | 动能 → 热能 | 相干性 → 混合态 |
| **边界** | 表面摩擦 | 环境耦合 |
| **不可逆** | 熵增 | 信息丢失 |
| **ΔS** | 摩擦热 | von Neumann 熵 |

两者都是"子系统边界上的信息/能量逃逸"。因果结构完全相同：

```
subsystem ──boundary──→ environment
   │                        │
   │              ┌─────────┘
   ▼              ▼
energy_loss    entropy_increase
coherence_loss  mixed_state
```

## 因果边 (入库)

| 因果边 | 层级 | 物理机制 |
|--------|------|---------|
| `velocity → dynamic_pressure` | tier 1 | Bernoulli, ½ρv² |
| `dynamic_pressure → drag_force` | tier 1 | 阻力公式, F_D = ½ρv² C_D A |
| `drag_force → kinetic_energy_loss` | tier 1 | 功 = 力 × 位移 |
| `kinetic_energy_loss → entropy_increase` | tier 2 | 摩擦生热 → 熵增 |
| `velocity → boundary_layer_interaction` | tier 1 | 流体边界层 |
| `subsystem_boundary → energy_transfer` | tier 2 | 子系统能量泄漏的一般机制 |

## δS=0 视角的最终答案

为什么耗散存在？因为**你选了错误的系统边界做变分**。

- 用飞行器+大气做变分: δS=0 ✓ 能量守恒
- 用飞行器单独做变分: δS≠0 ✗ 出现非保守力

耗散函数 R 是对"没包含在 L 里的自由度"的统计补偿。Rayleigh 的伟大在于他不用建模整个大气，只用一个二次型就抓住了耗散的本质特征。但在因果图上，这条捷径暴露了它的局限——它是一条现象学边，不是基本物理边。
