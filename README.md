# PhysCausal Agent

**物理为骨 · 因果为肌 · 感知为眼**

四层架构的物理因果智能体 — 从元物理原理到反事实推理的完整链路。

## 架构

```
元物理层 (Meta-Physics)  ← 对称性 · 熵增 · 测量坍缩
        ↓ 约束
物理层 (Physics)         ← 11条物理定律 + 约束传播
        ↓ 约束
因果层 (Causal)          ← DAG + SCM + do-calculus
        ↓
感知层 (Perception)      ← 传感器→语义变量 (stub)
```

## 快速开始

```bash
cd physcausal
python agent.py
```

```
> status          # 查看各层状态
> symmetry mass,velocity,height  # 对称性检测
> worlds x=1,v=2 x=0.5;v=2 v   # 多世界反事实
```

## 模块

| 层 | 模块 | 功能 |
|----|------|------|
| 元物理 | `meta_physics/symmetry.py` | 对称性检测 + Noether 定理 + 守恒律验证 |
| 元物理 | `meta_physics/entropy.py` | 熵箭头 + 因果方向判定 + 不可逆过程识别 |
| 元物理 | `meta_physics/measurement.py` | 测量坍缩 = do() 干预 + 多世界反事实 |
| 物理 | `physics/laws.py` | PhysicsLaw + PhysicsLibrary (11条定律) |
| 物理 | `physics/constraints.py` | 物理约束因果图 |
| 感知 | `perception/encoder.py` | PerceptualEncoder 接口 + SimpleFeatureExtractor |

## 测试

```bash
python -m pytest tests/ -v
```

## 与 causal_agent 的关系

PhysCausal 是 causal_agent 的进化版。causal_agent 提供了完整的因果推断引擎（PC/FCI/GES + SCM + do-calculus），PhysCausal 在此基础上增加了：
- 元物理层（对称性、熵增、测量坍缩）
- 物理层增强
- 感知层架构

## 路线图

| 阶段 | 内容 | 状态 |
|------|------|:--:|
| Phase 0 | 架构设计 + 项目骨架 | ✅ |
| Phase 1 | 元物理层 (symmetry + entropy + measurement) | ✅ |
| Phase 2 | 物理层迁移 + 增强 | 待开始 |
| Phase 3 | 因果层适配 (对接 causal_agent) | 待开始 |
| Phase 4 | 层间桥接 (四层联通) | 待开始 |
| Phase 5 | 推理引擎 (反事实+归因+规划) | 待开始 |
| Phase 6 | 感知层 MVP | 待开始 |

## 许可证

MIT
