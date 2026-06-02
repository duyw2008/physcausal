# PhysCausal Agent

**物理为骨 · 因果为肌 · 感知为眼**

四层架构的物理因果智能体 — 从元物理第一性原理到反事实推理的完整链路。

```
元物理层 (5/5 原则)    ← 最小作用量 / 对称性 / 熵增 / 局域因果 / 信息边界
  │ 约束
物理层 (11条定律)      ← Newton / Hooke / Maxwell / ...
  │ 约束
因果层 (12模块)        ← DAG / SCM / do-calculus / PC / FCI / GES
  │
感知层 (4后端)         ← simple / image / timeseries / object_detect

横切基础设施:
  spectral/            ← PCA / SVD / 谱图论 / Koopman (本征值=重要性)
  information/         ← Shannon / 互信息 / KL / 信息瓶颈 / Jaynes 最大熵
```

## 快速开始

```bash
cd physcausal
python agent.py
```

```
> status                          # 各层状态
> symmetry mass,velocity,height   # 对称性检测
> pipeline data.csv T Y           # 端到端管线
```

## 文档

| 文档 | 内容 |
|------|------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | 完整架构设计 + 元物理五原则 + 压缩即理解 |
| [COMPRESSION_TAXONOMY.md](docs/COMPRESSION_TAXONOMY.md) | 七条压缩路径分类学 |
| [GAP_ANALYSIS.md](docs/GAP_ANALYSIS.md) | 缺口分析与路线图 (P0/P1/P2) |

## 架构

```
physcausal/
├── meta_physics/      元物理层 — 五条第一性原理 (5/5)
│   ├── least_action.py   ① 最小作用量 δS=0
│   ├── symmetry.py       ② 对称性 → 守恒 (Noether)
│   ├── entropy.py        ③ 熵增 → 因果箭头
│   ├── locality.py       ④ 局域因果 — 光锥验证
│   └── measurement.py    ⑤ 信息边界 — 获取信息=投影
│
├── spectral/          横切层 — 特征分解
│   └── spectral.py       PCA / SVD / 谱图论 / Koopman
│
├── information/       横切层 — 信息度量
│   ├── shannon.py        Shannon / 互信息 / KL / JS / 传递熵
│   ├── bottleneck.py     信息瓶颈 (感知压缩理论基础)
│   └── jaynes.py         最大熵原理 (连接概率与物理)
│
├── physics/           物理层 — 11条定律 + 约束
├── causal/            因果层 — 12模块 (DAG/SCM/discovery/estimation/...)
├── perception/        感知层 — 4后端
├── integration/       桥接层 — perception/physics/pipeline
│
└── tests/             143 tests
```

## 测试

```bash
cd physcausal
python -c "
import sys, os, importlib
sys.path.insert(0,'.'); os.chdir('/home/duyw/physcausal')
# ... run all test modules
"
# 143/143 passing
```

## 路线图

| 阶段 | 内容 | 状态 |
|------|------|:--:|
| v0.1 | 元物理五原则 + 因果层 + 感知层 + 桥接 | ✅ |
| v0.4 | 主动实验设计 (Causal Bandit) | P0 |
| v0.5 | 层次化抽象 / 涌现 | P0 |
| v0.6 | 组合泛化 (Modular SCM) | P0 |
| v0.7 | 自由能原理 (Active Inference) | P0 |
| v0.8 | Bayesian SCM + 不确定性量化 | P1 |
| v0.9 | 因果规划 + 元学习 | P1 |
| v1.0 | 可演示的通用物理因果智能体 | |

详见 [GAP_ANALYSIS.md](docs/GAP_ANALYSIS.md)

## 许可证

MIT
