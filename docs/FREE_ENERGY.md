# 自由能与熵: 同一变分原理的两个面孔

> PhysCausal 知识库 — 2026-06-11

## 核心关系

最大熵和最小自由能是同一个变分原理（δS=0）在不同约束条件下的等价表述:

```
            δS = 0 (唯一生成根)
                │
        ┌───────┴───────┐
        │               │
   孤立系统          接触热浴
   (E 固定)         (T 固定)
        │               │
        ▼               ▼
   最大化 S         最小化 F = E - TS
   平衡态             平衡态
        │               │
        └───────┬───────┘
                │
        等价: 同一平衡态
```

## Legendre 变换

S 和 F 不是两个独立量——F 是 S 的 Legendre 变换:

```
S(E, V, N)         自然变量: E, V, N
                     │
                     │ Legendre 变换: E → T
                     ▼
F(T, V, N) = E - TS  自然变量: T, V, N

极值条件等价:
  ∂S/∂E = 1/T   ⇔   ∂F/∂T = -S
```

## 因果边

| 因果边 | 层级 | 物理含义 |
|--------|------|---------|
| `temperature × entropy → free_energy` | tier 1 | 定义式 F = E - TS |
| `free_energy → equilibrium_state` | tier 1 | 自由能极小值决定平衡态 |
| `entropy → free_energy` | tier 1 | 熵是自由能的一部分 |
| `temperature → free_energy` | tier 1 | 温度决定熵的权重 |

## 与 δS=0 的关系

- **孤立系统**: δS = 0 直接给出平衡条件
- **接触热浴**: δS_total = δS_system + δS_bath = 0 → δF = 0
  - 因为 δS_bath = -δE/T (热浴吸热)
  - 所以 δ(S - E/T) = 0 → δ(-F/T) = 0 → δF = 0

自由能极小不是新的原理——它就是 δS=0 在用温度替代能量做独立变量后的重新表述。

## 因果图中的位置

```
temperature ──┐
              ├──→ free_energy ──→ equilibrium_state
entropy    ───┘        │
                       │
              (通过 Legendre 变换
               与 δS=0 等价)
```

## 与耗散的连接

耗散统一骨架中的 entropy 现在有了上游（free_energy）:
- system → entropy → free_energy → equilibrium → ...
- 意味着: 耗散（熵增）驱动系统走向自由能极小的平衡态

这补充了之前的耗散统一图——entropy 不只是耗散的终点，也是驱动平衡的起点。
