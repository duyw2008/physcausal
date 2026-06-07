# 物理模型

> PhysCausal 中的物理定律库 — 完整数学形式 + 因果方向
> 版本: v0.3.2 | 41+ 条定律, 10 领域 + 自学习

---

## 定律索引

| # | 名称 | 领域 | 公式 | 因果方向 | 禁止方向 |
|----|------|------|------|---------|---------|
| 1 | Newton II | 力学 | F = ma | m,F→a | a→m |
| 2 | Hooke | 力学 | F = -kx | x→F | F→x |
| 3 | Gravity | 力学 | F=GMm/r² | m1,m2,r→F | — |
| 4 | Pendulum | 力学 | T = 2π√(L/g) | L,g→T | T→L |
| 5 | Momentum Cons. | 力学 | m₁v₁+m₂v₂=m₁v₁'+m₂v₂' | m1,v1,m2,v2→v1',v2' | v1',v2'→m1,v1 |
| 6 | Kinetic Energy | 力学 | E = ½mv² | m,v→E | — |
| 7 | Simple Harmonic | 力学 | ω = √(k/m) | k,m→ω | ω→k,m |
| 8 | Ohm | 电磁 | V = IR | I,R→V | V→I,R |
| 9 | Coulomb | 电磁 | F = kq₁q₂/r² | q1,q2,r→F | — |
| 10 | Faraday | 电磁 | ε = -N dΦ/dt | dΦ,N→ε | ε→dΦ,N |
| 11 | Ampère | 电磁 | ∮B·dl = μ₀I | I→B | — |
| 12 | Lenz | 电磁 | 感应电流阻碍磁通变化 | dΦ→I_ind | I_ind→dΦ |
| 13 | Joule Heat | 电磁 | P = I²R | I,R→P | P→I |
| 14 | Lorentz | 电磁 | F = q(E+v×B) | q,v,B→F | F→q,B |
| 15 | Kinetic Theory | 热力学 | T = (2/3k_B)⟨½mv²⟩ | KE→T | T→KE |
| 16 | Ideal Gas | 热力学 | PV = nRT | T→P,V | P,V→T |
| 17 | Stefan-Boltzmann | 热力学 | P = σAT⁴ | T,A→P | P→T |
| 18 | Newton Cooling | 热力学 | dT/dt = -k(T-T_env) | ΔT→rate | rate→ΔT |
| 19 | Bernoulli | 流体 | P+½ρv²+ρgh=const | ρ,v,h→P | — |
| 20 | Continuity | 流体 | A₁v₁ = A₂v₂ | A→v | v→A |
| 21 | Poiseuille | 流体 | Q = πr⁴ΔP/8ηL | r,ΔP→Q | — |
| 22 | Archimedes | 流体 | F_b = ρgV | ρ,V→F_b | F_b→ρ,V |
| 23 | Snell | 光学 | n₁sinθ₁ = n₂sinθ₂ | n₁,n₂,θ₁→θ₂ | θ₂→θ₁ |
| 24 | Lens | 光学 | 1/f = 1/u + 1/v | u,f→v | — |
| 25 | Reflection | 光学 | θ_i = θ_r | θ_i→θ_r | θ_r→θ_i |
| 26 | Wave Speed | 声学 | v = λf | λ,f→v | — |
| 27 | Doppler | 声学 | f'=f(v±v_o)/(v∓v_s) | f_s,v_s,v_o→f' | f'→v_s,f_s |
| 28 | Mass-Energy | 现代 | E = mc² | m→E | E→m |
| 29 | Photoelectric | 现代 | E = hf - φ | f→E | E→f |
| 30 | de Broglie | 量子 | λ = h/p | p→λ | λ→p |
| 31 | Heisenberg Unc. | 量子 | ΔxΔp ≥ ℏ/2 | — | — |
| 32 | Born Rule | 量子 | P = \|ψ\|² | ψ→P | P→ψ |
| 33 | No-Communication | 量子 | entanglement ⇏ signaling | — | — |
| 34 | Pauli Exclusion | 量子 | no two fermions share all q.n. | state→limit | — |
| 35 | Energy Quantization | 量子 | E_n = (n+½)ℏω | n→E | E→n |
| 36 | Schwarzschild | 广义相对论 | r_s = 2GM/c² | M→r_s | r_s→M |
| 37 | Time Dilation | 广义相对论 | t' = t√(1-v²/c²) | v→t' | t'→v |
| 38 | Grav. Redshift | 广义相对论 | Δf/f = gΔh/c² | g,h→Δf | Δf→g |
| 39 | Equivalence Princ. | 广义相对论 | gravity ≡ acceleration | — | — |
| 40 | Angular Momentum | 力学 | L = Iω = const | I→ω | ω→I |
| 41 | Kepler III | 力学 | T² ∝ a³ | a→T | T→a |

---

## 一、力学 (7 条)

### 1. Newton 第二定律

$$F = ma$$

**因果结构**: 质量和力是因，加速度是果。

```
  mass ──→ acceleration
  force ──→ acceleration
```

参数:
- $m$: 质量 (标量)
- $F$: 合外力 (矢量)
- $a$: 加速度 (矢量)

禁止方向: 加速度不能反向驱动力和质量。

---

### 2. Hooke 定律

$$F = -kx$$

**因果结构**: 位移是因，回复力是果。

```
  x ──→ F  (位移越大, 回复力越大)
  k: 弹性系数 (常数)
```

---

### 3. 万有引力

$$F = G \frac{m_1 m_2}{r^2}$$

**因果结构**: 质量和距离是因，引力是果。

```
  m1, m2, r ──→ F
```

---

### 4. 单摆周期

$$T = 2\pi\sqrt{\frac{L}{g}}$$

**因果结构**: 摆长和重力加速度是因，周期是果。

```
  L ──→ T
  g ──→ T (g越大, T越小)
```

---

### 5. 动量守恒

$$m_1 v_1 + m_2 v_2 = m_1 v_1' + m_2 v_2'$$

**因果结构**: 两体碰撞前参数是因，碰撞后速度是果。

```
  m1, v1, m2, v2 ──→ v1', v2'
```

**禁止方向**: 碰撞后速度不能反向改变碰撞前参数。

---

### 6. 动能

$$E_k = \frac{1}{2}mv^2$$

**因果结构**: 质量和速度是因，动能是果。

---

### 7. 简谐振动

$$\omega = \sqrt{\frac{k}{m}}$$

**因果结构**: 弹性系数和质量是因，角频率是果。

```
  k ──→ ω  (k越大, ω越大)
  m ──→ ω  (m越大, ω越小)
```

**禁止方向**: 角频率不能反向决定弹性系数或质量。

---

## 二、电磁学 (7 条)

### 8. Ohm 定律

$$V = IR$$

**因果结构**: 电流和电阻是因，电压是果。

注意: 这在电路理论中有争议——有些语境下电压是原因。在我们的 SCM 中，我们采用物理学的标准: $I$ 和 $R$ 决定 $V$ 的取值。

---

### 9. Coulomb 定律

$$F = k\frac{q_1 q_2}{r^2}$$

**因果结构**: 电荷和距离是因，电场力是果。

---

### 10. Faraday 电磁感应

$$\mathcal{E} = -N \frac{d\Phi_B}{dt}$$

**因果结构**: 磁通量变化和线圈匝数是因，感应电动势是果。

**禁止方向**: 感应电动势不能反向驱动磁通量变化。

---

### 11. Ampère 定律

$$\oint \mathbf{B} \cdot d\mathbf{l} = \mu_0 I$$

**因果结构**: 电流是因，磁场是果。

---

### 12. Lenz 定律

> 感应电流的方向总是阻碍引起它的磁通量变化。

**因果结构**: 磁通量变化是因，感应电流是果 (反向)。

禁止方向: 感应电流不能反向驱动磁通量变化。

---

### 13. Joule 热效应

$$P = I^2R$$

**因果结构**: 电流和电阻是因，热功率是果。

**禁止方向**: 热量不能反向驱动电流 (熵增方向)。

---

### 14. Lorentz 力

$$F = q(E + v \times B)$$

**因果结构**: 电荷、速度和磁场是因，洛伦兹力是果。

**禁止方向**: 洛伦兹力不能反向改变电荷或磁场。

---

## 三、热力学 (4 条)

### 15. 气体分子运动论

$$T = \frac{2}{3k_B} \langle \frac{1}{2}mv^2 \rangle$$

**因果结构**: 分子平均动能是因，温度是果。

**关键**: 温度是分子动能的**统计量**——不是温度导致分子运动，是分子运动定义了温度。这和「班级平均分不会导致学生考高分」是同一个逻辑。

**禁止方向**: 温度不能反向驱动分子动能。

---

### 16. 理想气体状态方程

$$PV = nRT$$

**因果结构**: 温度是因，压力和体积是果 (nR 固定时)。

**禁止方向**: 压力和体积不能反向改变温度。

---

### 17. Stefan-Boltzmann 定律

$$P = \sigma A T^4$$

**因果结构**: 温度和面积是因，辐射功率是果。

**禁止方向**: 辐射功率不能反向改变温度。

---

### 18. Newton 冷却定律

$$\frac{dT}{dt} = -k(T - T_{env})$$

**因果结构**: 温差是因，冷却速率是果。

**禁止方向**: 冷却速率不能反向扩大温差。

---

## 四、流体力学 (4 条)

### 19. Bernoulli 方程

$$P + \frac{1}{2}\rho v^2 + \rho gh = \text{const}$$

守恒律——无单一因果方向。

---

### 20. 连续性方程

$$A_1 v_1 = A_2 v_2$$

**因果结构**: 截面积变化是因，流速变化是果。

**禁止方向**: 流速不能反向改变截面积。

---

### 21. Poiseuille 定律

$$Q = \frac{\pi r^4}{8\eta}\frac{\Delta P}{L}$$

**因果结构**: 半径和压差是因，流量是果。

---

### 22. Archimedes 浮力原理

$$F_b = \rho g V$$

**因果结构**: 流体密度和排开体积是因，浮力是果。

**禁止方向**: 浮力不能反向改变流体密度或体积。

---

## 五、光学 (3 条)

### 23. Snell 折射定律

$$n_1 \sin\theta_1 = n_2 \sin\theta_2$$

**因果结构**: 入射角 + 折射率是因，折射角是果。

**禁止方向**: 折射角不能反向决定入射角。

---

### 24. 薄透镜方程

$$\frac{1}{f} = \frac{1}{u} + \frac{1}{v}$$

**因果结构**: 物距和焦距是因，像距是果。

---

### 25. 反射定律

$$\theta_i = \theta_r$$

**因果结构**: 入射角是因，反射角是果。

---

## 六、声学 (2 条)

### 26. 波速公式

$$v = \lambda f$$

**因果结构**: 波长和频率是因，波速是果。

---

### 27. Doppler 效应

$$f' = f\frac{v \pm v_o}{v \mp v_s}$$

**因果结构**: 声源频率 + 声源速度 + 观测者速度是因，观测频率是果。

**禁止方向**: 观测频率不能反向驱动声源速度或声源频率。

---

## 七、现代物理 (2 条)

### 28. 质能方程

$$E = mc^2$$

**因果结构**: 质量是因，能量是果。

**禁止方向**: 能量不能反向决定质量 (在狭义相对论框架内)。

---

### 29. 光电效应

$$E = hf - \phi$$

**因果结构**: 入射光频率是因，逸出电子能量是果。

**禁止方向**: 电子能量不能反向改变光频率。

---

## 八、量子力学 (6 条)

### 30. de Broglie 波粒二象性

$$\lambda = h / p$$

**因果结构**: 动量是因，物质波波长是果。

**禁止方向**: 波长不能反向决定动量。

---

### 31. Heisenberg 不确定性原理

$$\Delta x \Delta p \geq \hbar/2$$

**本质**: 位置和动量不能同时精确确定——不是测量技术的限制，是自然界的本性。这是一个不等式约束，无单一因果方向。

---

### 32. Born 规则

$$P = |\psi|^2$$

**因果结构**: 波函数是因，观测概率是果。这是量子力学中"测量坍缩"的数学表达——概率幅的模方给出测量结果的概率。

**禁止方向**: 概率不能反向决定波函数。

---

### 33. No-Communication 定理

$$\text{entanglement} \nRightarrow \text{signaling}$$

**本质**: 量子纠缠产生非定域关联，但不能用于超光速传递信息。任何测量结果都是随机的，无法编码信号。

---

### 34. Pauli 不相容原理

$$\text{no two fermions share all quantum numbers}$$

**因果结构**: 量子态是因，占据限制是果。每个量子态最多容纳一个费米子。

---

### 35. 能量量子化

$$E_n = (n + 1/2)\hbar\omega$$

**因果结构**: 量子数 n 是因，能级是果。能量取离散值。

**禁止方向**: 能级不能反向决定量子数。

---

## 九、广义相对论 (4 条)

### 36. Schwarzschild 半径

$$r_s = 2GM/c^2$$

**因果结构**: 质量是因，事件视界半径是果。质量越大，黑洞越大。

**禁止方向**: 事件视界不能反向决定质量。

---

### 37. 时间膨胀

$$t' = t\sqrt{1 - v^2/c^2}$$

**因果结构**: 速度是因，膨胀后的时间是果。速度越接近光速，时间越慢。

**禁止方向**: 时间膨胀不能反向改变速度。

---

### 38. 引力红移

$$\Delta f / f = g\Delta h / c^2$$

**因果结构**: 引力场强度和高度差是因，频率偏移是果。

**禁止方向**: 频率偏移不能反向改变引力场。

---

### 39. 等效原理

$$\text{gravity} \equiv \text{acceleration}$$

惯性质量 = 引力质量。在一个封闭的加速参考系中，无法区分是引力还是加速。这是广义相对论的基础公理。

---

## 仿真环境覆盖

PhysCausal 的 10 个仿真环境与物理定律的对应关系:

| 环境 | 定律 | 变量 | 边数 |
|------|------|------|------|
| pendulum | Pendulum | L, g → T | 2 |
| spring | Simple Harmonic | k, m → ω | 2 |
| collision | Momentum Conservation | m1,v1,m2,v2 → v1p,v2p | 8 |
| circuit | Ohm | I, R → V | 2 |
| faraday | Faraday | dΦ, N → ε | 2 |
| lorentz | Lorentz | q, v, B → F | 3 |
| snell | Snell | n1,θ1,n2 → θ2 | 3 |
| doppler | Doppler | f_s,v_s,v_o → f' | 3 |
| gas_law | Ideal Gas | T → P, V | 2 |
| buoyancy | Archimedes | ρ, V → F_b | 2 |
| debroglie | de Broglie | p → λ | 1 |
| energy_levels | Energy Quantization | n → E | 1 |
| schwarzschild | Schwarzschild | M → r_s | 1 |
| time_dilation | Time Dilation | v → t' | 1 |
| redshift | Grav. Redshift | g, h → Δf | 2 |

全 15 环境 physics_prior 100% 覆盖，主动学习精度 100%。自学习定律可继续扩展。
