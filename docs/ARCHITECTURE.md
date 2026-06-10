# PhysCausal Agent — 架构设计文档

> 版本: v0.3.11 | 日期: 2026-06-10
> 定位: 物理为骨 · 因果为肌 · 矛盾驱动 · 自主生长
> 身份: Noether (诺特) — δS=0 的守护者

---

## 一、系统全景

PhysCausal 的核心架构**不是纵向堆栈**，而是**三个独立输入层汇入因果推理引擎**，再分流入**三个输出层**。各层正交，通过 integration 接线。

```
                     ┌─────────────────────┐
                     │    感知层 (入口)      │  像素/时序/表格 → 语义变量
                     │    4 后端            │
                     └──────────┬──────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │  spectral/ (降维排序)│  PCA/SVD → k个主成分
                     │                     │  有效秩 → 自动选维度
                     └──────────┬──────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │ information/ (质检)  │  I(T;X) vs I(T;Y)
                     │                     │  信息损失监控
                     └──────────┬──────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │   因果推理引擎       │  DAG + SCM + do-calculus
                     │                     │
                     └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
     ┌────────────┐   ┌──────────────┐   ┌──────────────┐
     │  物理层     │   │   元物理层     │   │  创造性层     │
     │ 39条定律   │   │   三条裁判     │   │  模块库+骨架  │
     │ +局域因果  │   │   原则过滤     │   │  进化+组合    │
     │            │   │              │   │              │
     │ 作用对象:  │   │ 作用对象:     │   │ 作用对象:     │
     │ 因果图的边  │   │ 因果图的边    │   │ 因果模块      │
     └────────────┘   └──────────────┘   └──────────────┘
              │                │                │
              └────────────────┼────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          ▼                    ▼                    ▼
 ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
 │  贝叶斯层     │    │   推理引擎     │    │  LLM 层       │
 │  P(G|D)      │    │  反事实+归因   │    │  自然语言接口  │
 │  主动实验     │    │               │    │               │
 └──────────────┘    └──────────────┘    └──────────────┘
          │                    │                    │
          └────────────────────┼────────────────────┘
                               │
                    ┌──────────┴──────────┐
                    │  仿真 + 主动学习     │
                    │  10 环境, VOI→干预  │
                    └─────────────────────┘
```

### 核心原则

```
1. 感知 → spectral → information → 因果 — 严格顺序的数据流
2. spectral 回答「哪些维度重要」(特征值排序)
3. information 回答「压缩是否保留了因果信息」(I(T;Y) 监控)
4. 物理 + 元物理 — 约束因果引擎 (裁判, 不是数据源)
5. 创造性 + Bayes + 推理 — 因果引擎的输出后处理
```

---

## 二、输入层

### 2.1 感知层 (Perception)

```
输入: 原始数据 (像素/时序/表格)
输出: 结构化的语义变量 (Scene → variable_dict)

后端:
  simple         — 结构化数据 (np.array / dict / csv)
  image          — 图像特征 (颜色/边缘/纹理)  22维 → Scene
  timeseries     — 时间序列 (趋势/周期/差分)  每变量~18维
  object_detect  — 对象分解 (连通分量 + 特征)

感知引擎: PerceptionEngine 自动路由到正确后端

数据流:
  raw_input → PerceptionEngine.encode() → Scene
  Scene → variable_dict() → 因果层
```

### 2.2 谱层 (Spectral) — 横切基础设施

```
核心: 特征分解 = 信息空间骨架 + 重要性度量

工具:
  PCA             — 协方差矩阵特征分解 → 主成分方向 + 有效秩
  SVD             — 任意矩阵奇异值分解 → 降维/压缩
  谱图论          — 图拉普拉斯特征分解 → 代数连通度 + 最优聚类
  Koopman 分解    — 非线性动力学的线性化谱分析
  Observable      — 量子测量类比 → 可观测量的本征值 = 测量结果

独立于所有层 — 纯数学工具
```

### 2.3 信息层 (Information) — 横切数学语言

```
核心: Shannon 信息论 + 信息瓶颈 + 最大熵原理

工具:
  ShannonEntropy   — H(X), 互信息 I(X;Y), KL散度, JS距离, 传递熵
  InformationBottleneck — min I(T;X) s.t. I(T;Y) ≥ c (压缩=理解)
  MaxEnt           — Jaynes 最大熵: 给定约束, 熵最大的分布是最不偏颇的

独立于所有层 — 纯数学工具
```

---

## 三、推理引擎

### 3.1 因果层 (Causal)

```
核心模块 (11个):

  graph.py           — CausalDAG: 有向图 + d-separation + 拓扑排序
  scm.py             — Structural Causal Model: 结构方程 + do() + 反事实
  identification.py  — do-calculus: back-door / front-door / IV / 穷举
  discovery.py       — 因果发现: PC / FCI / GES + bootstrap 置信度
  estimation.py      — 5个ATE估计器: 线性/分层/匹配/双重稳健/IPW
  modern.py          — DML + CATE (S/T/X-learner) + do-why 接口
  mediation.py       — 中介分析: NDE / NIE / CDE + 路径特异性效应
  sensitivity.py     — 敏感性分析: Rosenbaum界限 + E-value + 报告
  ts_discovery.py    — 时间序列因果发现
  visualization.py   — 图形输出: ASCII / DOT / Mermaid / PNG
  llm_client.py      — DeepSeek API 客户端
```

### 3.2 约束层

```
物理层 (Physics):
  laws.py           — 66 条物理定律, 13 领域 + 自学习扩展
  constraints.py    — PhysicsConstrainedDAG

元物理层 (Meta-Physics) — 1 条生成原理 + 3 条派生原则:

  Tier 0 — 生成性原理:
    least_action.py   — δS = 0, 最小作用量
                        所有动力学方程的源头。
                        经典力学 (Euler-Lagrange) →
                        广义相对论 (Einstein-Hilbert) →
                        量子力学 (路径积分 e^{iS/ħ})

  Tier 1 — 派生原则:
    symmetry.py       — Noether 定理: L 的对称性 → 守恒量
                        是 δS=0 的直接推论, 非独立原理
    locality.py       — 局域因果: 光锥约束, 类空间隔无因果
                        不来自 δS=0 但局域场论天然满足
    entropy.py        — 熵增 ΔS ≥ 0: 统计涌现, 非动力学
                        底层微观动力学时间反演对称

  层级关系:
    δS=0 (生成性)
      ├─→ Noether (推论: 对称→守恒)
      └─→ Locality (约束: 光锥)
             └─→ Entropy (涌现: ΔS≥0)
```

物理层变量本体论:

| 类别 | 数量 | 示例 |
|------|------|------|
| 基础变量 | 12 | mass, energy, time, momentum, charge |
| 几何变量 | 9 | geodesic_path, spacetime_curvature, gauge_field |
| 量子变量 | 7 | wave_function, quantum_amplitude, collapse_probability |
| 派生变量 | 107 | kinetic_energy, pressure, flow_rate |

负向约束覆盖率: 80% (53/66 定律有 forbidden_directions)

### 3.3 创造性层 (Creative)

```
module_library.py   — 14个预置因果模块 + 自动入库
skeleton_library.py — 9个跨领域因果骨架
mutation.py         — 5种加权变异算子
filter.py           — 三层过滤 (物理→BIC→新颖性)
evolution.py        — 进化主循环 (模拟退火 + 精英保留)

skeleton/           — 骨架匹配 fallback:
  __init__.py       — SkeletonMatcher (无物理先验时自动匹配骨架)

composition/        — 组合泛化:
  composer.py       — ModuleInterface + TypedPort + 自动对接
```

### 3.4 认知层 (Meta-Cognition) — 自主智能体的核心

```
meta_cognition/     — 内在驱动力系统:
  autonomous.py     — AutonomousAgent: 五大驱动竞争 (frontier/dissonance/structure/associate/reflect)
                      think() 随机激活 → _learn_from() → update() 品味进化
                      状态持久化到 ~/.hermes/physcausal_autonomous_state.json
  dissonance.py     — 认知失调检测: detect_domain_boundaries() + detect_scale_boundaries()
                      扫描定律库找跨域张力 + 尺度边界
  frontier.py       — FrontierMap: 前沿地图 — 标注未知边界而非已知矛盾
                      稀疏区 (变量缺席哪些领域) + 断头路 (chain 在哪停止) + 尺度裂缝 (跨尺度缺失桥接)
  __init__.py       — ValueSystem (显著性排序), salience 评分

inference/          — 反事实推理:
  counterfactual_chain.py — propagate(): 沿 causal_direction 正向传播假设变化
                             build_dependency_graph() + BFS + forbidden 检查
                             format_chain() 人类可读输出

session/            — 知识生长:
  auto_learn.py     — 三条学习路径:
                      ├─ auto_learn()            — LLM 文本缺口检测 → LLM 补全 (1 API call)
                      ├─ learn_external_mentions() — LLM 回答中提取外部定律 (1 API call)
                      └─ learn_from_chain()      — 因果图结构分析 (0 token)
                         └─ 汇聚路径检测 + 跨域桥接 + 去重 + forbidden 验证
  knowledge_extractor.py — 从 LLM 回答中提取因果断言

自主闭环:
  dissonance → chain → learn_from_chain (0 token, 纯图推理)
     ↓ 无产出
  auto_learn (1 API call, LLM 回退)

Cron 定时:
  physcausal-autonomous: 每 30 分钟跑 15 轮, 0 token, 有发现推送报告
```

| 模块 | 驱动模式 | 输入 | 输出 | token |
|------|---------|------|------|-------|
| `_think_frontier` | 前瞻式 | 前沿地图 | 稀疏区/裂缝/断头路方向 | 0 |
| `_think_dissonance` | 反应式 | 定律库 | 跨域张力/尺度边界 | 0 |
| `_think_structure` | 联想式 | 模块库 | 同构组 | 0 |
| `_think_associate` | 联想式 | 随机模块对 | 跨域同构 | 0 |
| `_think_reflect` | 回顾式 | salience | 重点定律 | 0 |

---

## 四、输出层

### 4.1 贝叶斯层 (Bayesian)

```
structural.py       — P(G|D) 结构后验 (Bootstrap/MCMC)
parameter.py        — P(θ|G,D) 参数后验 (共轭先验 + 物理先验注入)
active_learning.py  — VOI 主动实验设计
```

### 4.2 推理引擎 (Inference)

```
engine.py           — CounterfactualEngine (Pearl 三步 + 物理验证)
                    — AttributionEngine (中介归因)
```

### 4.3 行动层三层协作

主动实验、强化学习、自组织 —— 不是冗余，是分工明确的协作。

```
active_experiment/  — 模型驱动, VOI 公式, 零样本即可用
                      一步算出最优干预, 不学, 快但不一定最优

reinforcement/      — 数据驱动, Q-Learning, 多步策略
                      从经验中学习, 能发现 VOI 算不到的策略

self_organization/  — 自由能驱动, 自适应调节 β
                      告诉系统何时探索, 何时利用
```

**三层协作模式:**

```
self_organization  →  自由能判断:   该探索还是利用?
                          │
            ┌─────────────┴─────────────┐
            ▼                           ▼
       探索模式                       利用模式
       active_experiment             reinforcement
       VOI 提供初始猜测              Q-table 直接选最优
       「优先干预这个变量」          「已知的最好行动是...」
            │                           │
            └─────────────┬─────────────┘
                          ▼
                   reinforcement 更新 Q
                   VOI 先验 → Q 初始值 (不是从零学)
                   经验微调 → 超越先验
```

**核心关系:**

```
active_experiment → reinforcement 的先验
  Q(s,a) 初始值 = f(VOI(a))

reinforcement → 精调, 在经验中修正 VOI 的盲区

self_organization → 驱动, 控制探索/利用的节奏

三者保留, 各司其职, 互补而非冗余。
```

---

## 五、外围

### 5.1 LLM 层

```
bridge.py           — 五步管道:
  1. LLM 提取因果图 (自然语言 → 结构)
  2. 数据生成 (DAG → SCM → 采样)
  3. 物理验证 (元物理过滤 — Step 1.5)
  4. 效应估计 (do-calculus → ATE)
  5. LLM 自然语言解读 (数字 → 中文)
```

### 5.2 仿真 + 主动学习

```
env/physics_sim.py  — 15个物理仿真环境 (经典 + 量子 + 广义相对论)
active_experiment/active_learner.py — VOI → 干预 → 数据 → 更新 → 入库
```

### 5.3 桥接 (Integration)

```
perception_bridge.py    — 感知 → 因果变量
physics_bridge.py       — 物理约束 → 因果图
meta_physics_bridge.py  — 元物理 → 因果约束
pipeline.py             — 端到端四层流水线
```

---

## 六、依赖关系

```
不依赖任何下层的独立模块:
  perception/    meta_physics/    physics/    spectral/    information/

上层组合 (调用独立模块):
  causal/  ← 纯粹因果推理
  bayesian/ ← causal + 统计
  creative/ ← causal + 模块库 + 进化
  integration/ ← 把独立模块接在一起
  llm/ ← LLM + integration

无循环依赖 — 44/44 模块导入正常
```

---

## 七、统计

```
模块: ~70  |  测试: 179
物理定律: 71 条 (11 领域 + 自学习 + paper_ingest)
元物理: 1 生成原理 (δS=0) + 3 派生原则 (Noether, Locality, Entropy)
变量本体论: 12 基础 + 9 几何 + 7 量子 + 91 派生
负向约束: 全覆盖
置信层级: 79 定律, 54 auto-laws (含 arXiv 摄入)
哲学透镜: 11 条 (3 层: 解释/引导/标注)
自主循环: 6 驱动 (新增 analogy), cron 30min, 0 token
元RL策略: UCB1 探索/利用优化 (strategy 命令)
arXiv 摄入: search + read + LLM提取 + 信任分层 (ingest/trust 命令)
论文信任: tier2(确立)/tier3(假说)/tier4(冲突) 自动分层
因果规划: 反向搜索 + 路径评分 (plan 命令)
创新引擎: 生成器 + 过滤器 (innovate 命令)
类比引擎: 图嵌入 64 条跨域共鸣 (analogy 命令)
学习优化: 11 对正样本训练特征权重 (learn 命令)
可视化: ASCII 驱动面板 + 类比图 + 因果链 (viz 命令)
持久记忆: 发现归档 + 跨session检索 (memory 命令)
耗散统一: 动能/相位/信息 → entropy 同一因果骨架
数据管道: CSV → 相关性 → 因果发现 → 定律比对 (data 命令)
输入通道: ask (LLM/DeepSeek) / data (CSV) / ingest (arXiv)
输出通道: paper / talk / viz / memory
知识库: 12 篇文档
测试: 179 全绿
```
