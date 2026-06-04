# PhysCausal Agent — 架构设计文档

> 版本: v0.2.1 | 日期: 2026-05-18
> 定位: 物理为骨 · 因果为肌 · 感知为眼 · LLM 为口

---

## 一、系统全景

PhysCausal 的核心架构**不是纵向堆栈**，而是**三个独立输入层汇入因果推理引擎**，再分流入**三个输出层**。各层正交，通过 integration 接线。

```
                     ┌─────────────────────┐
                     │    感知层 (入口)      │  像素/时序/表格 → 语义变量
                     │    4 后端            │
                     └──────────┬──────────┘
                                │
    ┌───────────────────────────┼───────────────────────────┐
    │                           │                           │
    ▼                           ▼                           ▼
┌────────┐             ┌────────────────┐          ┌──────────────┐
│spectral│             │   因果推理引擎   │          │   information │
│ 降维   │◄───────────►│   DAG + SCM +   │◄────────►│   信息度量     │
│ 排序   │             │   do-calculus   │          │               │
└────────┘             └───────┬─────────┘          └──────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
     ┌────────────┐   ┌──────────────┐   ┌──────────────┐
     │  物理层     │   │   元物理层     │   │  创造性+进化   │
     │ 22条定律   │   │   五条裁判     │   │  模块库+骨架  │
     │ 约束+验证  │   │   原则过滤     │   │  组合发现     │
     └────────────┘   └──────────────┘   └──────────────┘
              │                │                │
              └────────────────┼────────────────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
                    ▼                     ▼
           ┌──────────────┐      ┌──────────────┐
           │  贝叶斯层     │      │   推理引擎     │
           │  置信度量化   │      │  反事实+归因   │
           └──────────────┘      └──────────────┘

    LLM 层: 自然语言 ↔ 因果管道 (包装上述所有层)
```

### 核心原则

```
1. 元物理不是基础 — 它是裁判。不产生数据, 只判断对错。
2. 感知是入口 — 数据从这里进入系统。
3. spectral + information 是横切工具 — 所有层都能调用, 不依赖任何层。
4. 物理 + 元物理 是过滤器 — 平行约束因果引擎, 不产生侧效应。
5. 创造性 + Bayes + 推理 是输出 — 因果引擎的结果经过不同后处理。
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
  laws.py           — 22条物理定律, 6领域
  constraints.py    — PhysicsConstrainedDAG

元物理层 (Meta-Physics) — 五条第一性原理:
  least_action.py   — ① 最小作用量 δS = 0 (生成性原理)
  symmetry.py       — ② 对称性 → 守恒 (Noether 定理)
  entropy.py        — ③ 熵增 ΔS ≥ 0 (因果箭头)
  locality.py       — ④ 局域因果 (光锥约束)
  measurement.py    — ⑤ 信息边界 (获取信息 = 投影)
```

### 3.3 创造性层 (Creative)

```
module_library.py   — 14个预置因果模块 + 自动入库
skeleton_library.py — 9个跨领域因果骨架
mutation.py         — 5种加权变异算子
filter.py           — 三层过滤 (物理→BIC→新颖性)
evolution.py        — 进化主循环 (模拟退火 + 精英保留)

composition/        — 组合泛化:
  composer.py       — ModuleInterface + TypedPort + 自动对接
```

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
env/physics_sim.py  — 7个物理仿真环境
rl/active_learner.py — VOI → 干预 → 数据 → 更新 → 入库
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
模块: 44  |  代码行: ~14,000  |  测试: 179 unit + 9 integration
物理定律: 22 条, 6 领域  |  仿真环境: 7 个
预置模块: 14 + 自动发现  |  预置骨架: 9 个
元物理原则: 5/5  |  P0 缺口: 2/4 完成
```
