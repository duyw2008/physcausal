# 无动力飞行器在大气层内的耗散动力学

> 用 Lagrange-Rayleigh 形式主义分析飞行器轨迹
> PhysCausal 专题报告 — 2026-06-09

## 1. 问题设定

无动力飞行器在大气层内滑翔。没有发动机推力，只有：

- **重力** mg (保守力, 有势)
- **升力** L (垂直于速度方向, 非耗散)
- **阻力** D (平行于速度方向, 耗散)

**为什么不用标准 Lagrangian？**

标准 Euler-Lagrange 方程假设所有力都能写成势能的梯度。阻力不能——它依赖速度，且在闭环路径上做功不为零 (∮D·dx ≠ 0)。需要扩展形式主义。

## 2. Lagrange-Rayleigh 公式

在 Euler-Lagrange 方程右边加上 Rayleigh 耗散函数 R:

```
d  ⎛ ∂L ⎞   ∂L   ∂R   ∂Q
── ⎜────⎟ - ── + ── = ──
dt ⎝ ∂q̇ᵢ ⎠   ∂qᵢ  ∂q̇ᵢ  ∂qᵢ

其中:
  L = T - V          (标准 Lagrangian)
  R = ½ Σ cᵢ q̇ᵢ²   (Rayleigh 耗散函数)
  Q = 非保守广义力  (升力在这里)
```

Rayleigh 的洞见：如果耗散力与速度成正比，总可以写成一个关于速度的二次型。对飞行器：

```
R = ½ D(v) v = ½ (½ ρ v² C_D S) v = ¼ ρ C_D S v³
```

## 3. 广义坐标与 Lagrangian

```python
# 广义坐标: (x, y) 水平+垂直位移
# 速度: (v_x, v_y)

# 动能
T = ½ m (v_x² + v_y²)

# 势能 (重力)
V = m g y

# Lagrangian
L = ½ m (v_x² + v_y²) - m g y
```

## 4. Rayleigh 耗散函数

```python
# 合速度
v = sqrt(v_x² + v_y²)

# 攻角 α (飞行器纵轴与速度方向的夹角)
α = θ - arctan(v_y / v_x)   # θ = 俯仰角

# 阻力系数 (与攻角相关)
C_D(α) = C_D0 + k C_L²(α)   # 诱导阻力 + 零升阻力

# Rayleigh 函数
R(v_x, v_y) = ∫₀ᵛ D(v') dv'
            = ⅓ · ½ ρ S C_D(α) v³
```

注意 R 中的 C_D 和 C_L 都依赖攻角 α，而 α 又依赖速度方向。所以 R 不仅是速度大小的函数，还隐含速度方向的耦合——这使它比简单的 R=½cv² 更复杂。

## 5. 运动方程

```python
# x 方向
m dv_x/dt = -∂R/∂v_x           # 阻力分量
           + L sin(γ)          # 升力的水平分量 (γ = 航迹角)

# y 方向  
m dv_y/dt = -mg                # 重力
           - ∂R/∂v_y           # 阻力分量
           + L cos(γ)          # 升力的垂直分量

# 其中
γ = arctan(v_y / v_x)          # 航迹角
D = ½ ρ v² C_D(α) S            # 阻力
L = ½ ρ v² C_L(α) S            # 升力
```

展开 ∂R/∂v_x:

```
∂R/∂v_x = D · v_x / v          # 阻力在 x 方向的分量
```

## 6. 为什么不直接用 Hamiltonian？

经典 Hamiltonian H = p·q̇ - L 对耗散系统失效：

```
问题 1: p = ∂L/∂q̇ 仍可定义，但 ṗ ≠ -∂H/∂q
         因为非保守力不在 H 的梯度里

问题 2: H 不代表总能量
         dH/dt = -∂R/∂q̇ · q̇ < 0
         能量不断减少，H 不是守恒量

问题 3: Liouville 定理失效
         相空间体积收缩 dΓ/dt < 0
         轨迹向吸引子收敛
```

如果要用 Hamiltonian 形式主义，需要扩展到**接触 Hamiltonian** 或** metriplectic 系统**，但这超出了标准分析力学的范围。

## 7. 因果图视角

在 PhysCausal 因果图中，这条链已经入库：

```
velocity → dynamic_pressure → drag_force → kinetic_energy_loss → entropy
                │
                └──→ lift_force (非耗散)
```

关键洞察：**耗散不是基本物理，是子系统视角**。

- 对"飞行器+大气"做变分：δS_total = 0 ✓ 能量守恒
- 对"飞行器"单独做变分：δS≠0 ✗ 出现非保守力

Rayleigh 函数是对"未包含在 L 里的自由度"的统计补偿。δS=0 没有被违反——被选错了系统边界。

## 8. 与退相干的同构

| | 飞行器耗散 | 量子退相干 |
|------|---------|----------|
| 子系统 | 飞行器 | 量子比特 |
| 环境 | 大气 | 热浴 |
| 转移量 | 动能 → 热能 | 相干性 → 混合态 |
| 不可逆性 | 摩擦熵增 | von Neumann 熵 |
| 边界机制 | 边界层摩擦 | 环境耦合 |
| 形式化 | Rayleigh R(v) | Lindblad 方程 L[ρ] |
| δS=0 | 全系统守恒 | 幺正演化守恒 |

两者因果同构——PhysCausal 因果图已验证。
