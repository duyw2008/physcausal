# PhysCausal Agent

**物理为骨 · 因果为肌 · 感知为眼 · LLM 为口 · RL 为手**

四层架构 + 三层行动 + 三横切的物理因果智能体。v0.3.0

```
元物理层 (3/3)    ← 最小作用量 / 对称性 / 熵增 (完备性已证)
  │ 约束
物理层 (39定律)   ← Newton / Hooke / Pendulum / Simple Harmonic /
  │                  Ohm / Faraday / Lorentz / Ideal Gas / Doppler / ...
  │ 约束
因果层 (12模块)   ← DAG / SCM / do-calculus / PC / FCI / GES
  │ 包裹
贝叶斯层          ← P(G|D) 结构后验 / P(θ|G,D) 参数后验 / VOI 主动实验
  │
感知层 (4后端)    ← simple / image / timeseries / object_detect

创造性联想层      ← 14模块库 + 9骨架库 + 进化式假说生成
LLM 层            ← DeepSeek 自然语言 → 因果图 → 物理验证 → 中文解释

行动层 (三层协作):
  active_experiment/ ← 模型驱动 VOI, 零样本快速干预
  reinforcement/     ← 数据驱动 Q-Learning, 多步策略学习
  self_organization/ ← 自由能驱动, 自适应探索/利用节奏

骨架匹配 (fallback):
  skeleton/          ← 无物理先验时自动匹配已知骨架迁移因果结构

仿真 + 主动学习    ← 10个物理环境, 全 physics_prior 100% 覆盖

横切基础设施:
  spectral/       ← PCA / SVD / 谱图论 / Koopman
  information/    ← Shannon / 互信息 / KL / 信息瓶颈 / 最大熵
  integration/    ← 5桥接 + information_gate (质检)
```

## 快速开始

```bash
cd physcausal
python agent.py
```

```
> ask 力和质量如何影响加速度      # LLM 因果分析 (+物理纠正)
> learn circuit 3 20              # 主动因果发现 (自动入库)
> learn all                       # 全部10个环境
> pipeline data.csv T Y           # 端到端四层流水线
> modules                         # 模块库 (手工 + 自动发现)
```

## 文档

| 文档 | 内容 |
|------|------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | 完整架构设计 — 架构图 + 模块全景 |
| [META_PHYSICS.md](docs/META_PHYSICS.md) | 元物理三条第一性原理详解 |
| [PHYSICS_MODELS.md](docs/PHYSICS_MODELS.md) | 39条物理定律 — LaTeX + 因果方向 |
| [MATHEMATICAL_FOUNDATIONS.md](docs/MATHEMATICAL_FOUNDATIONS.md) | 数学基础 — SCM/do-演算/反事实/谱/信息论 |
| [COMPRESSION_TAXONOMY.md](docs/COMPRESSION_TAXONOMY.md) | 七条压缩路径分类学 |
| [GAP_ANALYSIS.md](docs/GAP_ANALYSIS.md) | 缺口分析 + 路线图 |
| [AI_ASSOCIATION.md](docs/AI_ASSOCIATION.md) | AI 联想能力分析 |

## 测试

179/179 passing | system_validation: 36 tests | cross_layer_verify: 9 tests | pressure: PC F1=0.94 (3 vars)

## 路线图

| 阶段 | 内容 | 状态 |
|------|------|:--:|
| v0.1 | 元物理三原则 + 因果层 + 感知层 + 桥接 | ✅ |
| v0.2 | 贝叶斯层 + 创造性联想 + LLM + 仿真 + 主动学习 | ✅ |
| v0.3 | 物理定律扩展 (31条) + 骨架迁移 + RL-自组织协同 | ✅ |
| v0.5 | 层次化抽象 / 涌现 (Renormalization × Causal) | P0 |
| v1.0 | 可演示的通用物理因果智能体 | |

## 许可证

MIT
