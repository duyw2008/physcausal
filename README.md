# PhysCausal Agent

**物理为骨 · 因果为肌 · 矛盾驱动 · 自主生长**

从物理第一性原理出发，自主发现、验证、学习的因果推理智能体。v0.3.11

```
元物理:   δS=0 (唯一生成根) → Noether / Locality / Entropy (派生)
定律库:   71 条, 11 领域, 5 层置信 (公理→共识→理论→假说→探索)
          负向约束 90% 覆盖, 变量本体论 12+9+7+91
桥梁:     QM↔GR (Hawking + ER=EPR + LQG + AdS/CFT + PathIntegral)
          QM↔信息 (Landauer + 纠缠熵)
          热力学↔结构 (PhaseTransition + SymmetryBreaking)

自主智能: 5 驱动竞争 (前沿/失调/联想/结构/反思)
          品味进化 + 失败记忆 + 升级机制
          语义聚类 + 粗粒化 + 创新引擎 + 研究循环 v2
          元认知建议 (suggest) + 聚焦偏置 (focus)

哲学层:   11 条透镜 (Wheeler, Feynman, Boltzmann, Galois...)
          群论分类 SU(2)/U(1)/SO(3)/SO(3,1)/Discrete

大胆假设: speculate — 无约束假说生成 (tier 4 沙盒)
小心求证: suggest --run — 交互式交叉验证, 诚实标注缺失桥梁
研究论文: paper — 自动生成结构化 Markdown 论文
研究方向: focus — 9 个热门方向, 聚焦偏置全程生效

测试:     179 全绿
```

## 快速开始

```bash
cd physcausal
python agent.py
```

## 命令参考

```
══ 核心推理 ═══════════════════════════════════════════
  chain mass 减半              正向因果传播
  plan mass wavelength         反向规划最优路径
  plan bridge quantum GR       领域桥接搜索

══ 研究方向 ═══════════════════════════════════════════
  focus                        交互式方向选择 (9 个方向)
  focus CB                     快捷设置方向 (按 tag)
  focus none                   取消聚焦

══ 大胆假设 ═══════════════════════════════════════════
  speculate                    无约束假说 (tier 4 沙盒)
  speculate --save             保存到 auto_laws

══ 小心求证 ═══════════════════════════════════════════
  suggest                      交互式建议控制台
   → 1-9 执行指定建议
   → a   全部交叉验证
   → q   退出
  suggest --run                一键执行 #1
  suggest --run-all             全部交叉验证流水线
  research                     完整研究循环 v2
   → 惊喜检测 + 优先级 + 鲁棒性 + 留一法 + 归档

══ 成果输出 ═══════════════════════════════════════════
  paper                        自动生成研究论文
   → Abstract / Methods / Discoveries / CV / Discussion / Refs

══ 自主运行 ═══════════════════════════════════════════
  autonomous [n]               自主思考 (默认 15 轮)
  watch                        定时后台 (每 30 分钟)
  watch stop                   停止后台
  innovate                     创新引擎报告
  meta                         元学习摘要
  dissonance                   认知失调报告
  status                       系统状态
```

## 研究循环 v2

```
research → 完整物理学家闭环
  ⚠ 惊喜检测  — 验证分数骤降 30% 触发警报
  🔝 优先级排序 — 基础变量缺席 > 几何 > 派生
  🔄 鲁棒性检验 — 同假说 3 轮验证 std<0.3 才算稳定
  ✂ 留一法验证 — 每条定律的因果贡献
  📄 发现归档  — confirmed → reports/
```

## 研究方向 (focus)

| Tag | 方向 | 难度 |
|-----|------|------|
| QG | 量子引力与时空因果结构 | ★★★★★ |
| QM | 量子基础与测量问题 | ★★★★★ |
| EM | 涌现与时间箭头 | ★★★ |
| IB | 信息本原论 (It from Bit) | ★★★★ |
| GU | 几何统一纲领 (Wheeler) | ★★★★★ |
| CD | 因果发现方法论 | ★★ |
| CU | 因果统一纲领 (PhysCausal) | ★★★★ |
| CB | 跨域桥接 (PhysCausal) | ★★★ |
| KS | 知识手册编纂 (PhysCausal) | ★ |

聚焦后 innovate/suggest/watch 均偏向该方向。

## 数据存储

所有持久化数据统一放在 `data/` 目录下，不再散落 `~/.hermes/`:

```
physcausal/
├── data/
│   ├── auto_laws.json             自动发现的定律
│   ├── cv_summary.json            交叉验证汇总
│   ├── focus.json                 当前研究方向
│   ├── completed_suggestions.json 已完成的建议
│   ├── scores.json                验证分数历史
│   ├── salience.json              价值系统记忆
│   └── autonomous_state.json      自主智能体状态
├── reports/                       论文和发现报告 (gitignored)
├── docs/                          架构文档
└── tests/                         179 测试
```

## 文档

| 文档 | 内容 |
|------|------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | 完整架构设计 |
| [META_PHYSICS.md](docs/META_PHYSICS.md) | δS=0 唯一生成原理 |
| [PHYSICS_MODELS.md](docs/PHYSICS_MODELS.md) | 71 定律, 11 领域 |
| [GAP_ANALYSIS.md](docs/GAP_ANALYSIS.md) | 缺口分析 + 路线图 |
| [CHANGELOG.md](CHANGELOG.md) | 版本变更记录 |
| [SYMMETRY_BREAKING.md](docs/SYMMETRY_BREAKING.md) | 对称破缺的因果结构 |
| [DISSIPATIVE_SYSTEMS.md](docs/DISSIPATIVE_SYSTEMS.md) | 耗散系统: Rayleigh, 子系统边界 |

## 许可证

MIT
