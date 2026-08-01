# PhysCausal Agent — Noether (诺特)

**物理为骨 · 因果为肌 · 进化驱动 · 自主生长**

从物理第一性原理出发，自主发现、验证、学习的因果推理智能体。v0.4.0

```
身份:     Noether (诺特) — δS=0 的守护者, 300细胞进化殖民地的造物主

元物理:   δS=0 (唯一生成根) → Euler-Lagrange / Hilbert / PathIntegral
定律库:   257 条, 366 边, 379 节点, 50 跨域变量, 14 领域
          5 层置信 (公理→共识→理论→假说→探索)
          tier 0-2 物理学家领地, tier 3-4 殖民地投票

进化:     300细胞, 6原子操作, 基因组驱动, 强化学习+自然选择
          四策略均衡 (探索32% 标记14% 分裂18% 回声19%)
          26500代稳态, 179条tier3假说

喂养:     路径枯竭 → arXiv 动态搜索 → 图自增长 (335→487边)

自主智能: 7 驱动 | 类比引擎 | 抽象引擎 | 审美引擎 | 增量学习
核心发现: entropy 普适汇点 | action 统一源 (δS=0四分支)
知识库:   15 篇文档 | 投票箱 | 自喂养循环
```
输出通道: paper (论文) / talk (发言) / viz (可视化)
持久化:   data/ 统一存储 + memory (跨session记忆)

测试:     179 全绿
```

## 快速开始

```bash
cd physcausal
python agent.py
```

## 命令参考

```
══ 对话与探索 ═══════════════════════════════════════════
  ask <question>               LLM 物理问答 (DeepSeek API)
  talk                         Noether 主动发言 (观察+建议)
  viz                          驱动面板 + 类比图 + 因果链
  memory                       持久记忆浏览

══ 研究方向 ═══════════════════════════════════════════════
  focus                        交互式方向选择 (9 个方向)
  focus <tag>                  快捷设置 (QG/QM/EM/IB/GU/CD/CU/CB/KS)
  focus none                   取消聚焦

══ 大胆假设 ═══════════════════════════════════════════════
  speculate                    无约束假说 (tier 4 沙盒)
  speculate --save             保存到 data/auto_laws.json

══ 小心求证 ═══════════════════════════════════════════════
  suggest                      交互式建议控制台 (1-9/a/q)
  suggest --run                一键执行最高优先级
  suggest --run-all             全交叉验证流水线
  research                     完整研究循环 v2
   → 惊喜检测 + 优先级 + 鲁棒性 + 留一法 + 归档

══ 学习与类比 ═══════════════════════════════════════════
  analogy                      因果链类比 (64 条跨域共鸣)
  learn                        特征权重训练 (11 对正样本)
  innovate                     创新引擎报告
  strategy                     元RL策略优化 (UCB1探索/利用)

══ 核心推理 ═══════════════════════════════════════════════
  chain <var> <change>         正向因果传播
  plan <start> <target>        反向规划最优路径
  plan bridge <d1> <d2>        领域桥接搜索

══ 数据与外部 ═══════════════════════════════════════════
  data <csv> [target]          实验数据 → 因果发现
  ingest <topic>               arXiv 论文 → 断言提取 (LLM)

══ 成果输出 ═══════════════════════════════════════════════
  paper                        自动生成研究论文 (Abstract→Refs)

══ 自主运行 ═══════════════════════════════════════════════
  autonomous [n]               自主思考 (默认 15 轮)
  watch                        定时后台 (每 30 分钟)
  watch stop                   停止后台
  status                       系统状态
  dissonance                   认知失调报告
  meta                         元学习摘要
```

## 架构

```
┌───────────────────────────────────────────────────┐
│                 PhysCausal                         │
│                                                   │
│  输入层       因果核心        输出层              │
│  ┌──────┐   ┌──────────┐   ┌──────────┐         │
│  │ ask  │   │ δS=0 根  │   │ paper    │         │
│  │ data │ → │ tier 0-4 │ → │ talk     │         │
│  │ingest│   │ analogy   │   │ viz      │         │
│  └──────┘   │ learn     │   │ memory   │         │
│             └──────────┘   └──────────┘         │
│                                                   │
│  白盒: 因果推理 + 发言    黑盒: 图嵌入 + 学习     │
│  可审计                   模式涌现               │
└───────────────────────────────────────────────────┘
```

## 研究方向 (focus)

| Tag | 方向 | 难度 | 状态 |
|-----|------|------|------|
| QG | 量子引力与时空因果结构 | ★★★★★ | |
| QM | 量子基础与测量问题 | ★★★★★ | |
| EM | 涌现与时间箭头 | ★★★ | |
| IB | 信息本原论 (It from Bit) | ★★★★ | 当前 |
| GU | 几何统一纲领 (Wheeler) | ★★★★★ | |
| CD | 因果发现方法论 | ★★ | |
| CU | 因果统一纲领 | ★★★★ | |
| CB | 跨域桥接 | ★★★ | |
| KS | 知识手册编纂 | ★ | |

## 数据存储

```
physcausal/
├── data/         持久化数据 (auto_laws/scores/focus/memory...)
├── reports/      论文和报告 (gitignored)
├── docs/         13 篇知识文档
├── tests/        179 测试
└── agent.py      命令入口
```

## 文档

| 文档 | 内容 |
|------|------|
| [DESIGN_PHILOSOPHY.md](docs/DESIGN_PHILOSOPHY.md) | 设计哲学 + 架构 + 当前状态 |
| [NOUS_THEORY.md](docs/NOUS_THEORY.md) | 诺特闹理论 — 统一云、垃圾免疫、睡眠消化 |
| [DEEP_UNDERSTANDING_ARCHITECTURE.md](docs/DEEP_UNDERSTANDING_ARCHITECTURE.md) | 深刻理解的神经基础与架构映射 |
| [CHANGELOG.md](CHANGELOG.md) | 版本变更记录 |

## 许可证

MIT
