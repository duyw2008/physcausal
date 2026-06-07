# PhysCausal Agent — 变更日志

> 记录所有版本变化

---

## v0.3.10 (2026-06-07) — 因果规划 + 元学习 v2

### 因果规划
- `inference/causal_planner.py`: 反向搜索 + 路径评分 + forbidden/tier 过滤
- `plan` 命令: `plan <start> <target>` 正向规划
- `plan bridge <domain1> <domain2>` 领域桥接
- mass→interference 找到 5 条路径, 最便宜代价 7.5

### 元学习 v2
- `reinforcement/meta_learner_v2.py`: 模式模板 + 跨域迁移
- 从发现的汇聚模式提取模板, 在新领域中搜索同类
- 自动发现 geodesic_path 跨 3 领域被 2 定律汇聚

### 统计
- 71 定律, 11 透镜, 179 测试全绿

---

## v0.3.10 (2026-06-07) — 因果规划 + 元学习 v2 + 创新引擎

### 因果规划
- `inference/causal_planner.py`: 反向搜索 + 路径评分 + forbidden/tier 过滤
- `plan` 命令: `plan mass wavelength` 找最优路径
- `plan bridge quantum GR` 领域桥接

### 元学习 v2
- `reinforcement/meta_learner_v2.py`: 模式模板 + 跨域迁移
- 自动发现 geodesic_path 跨 3 领域汇聚

### 创新引擎
- `creative/innovation_engine.py`: 生成器 + 过滤器 + 进化器
- 随机生成候选因果边 → 公理链验证 → 通过后提案
- `innovate` 命令 + 融入自主循环
- 30 条候选, 100% 通过率, 8 条"新物理"边

### 统计
- 71 定律, 11 透镜, 179 测试全绿

---

## v0.3.9 (2026-06-07) — δS=0 生成根 + 论文摄入 + 群论分类

### δS=0 确认为唯一生成根
- `EulerLagrange`: action → force
- `HilbertAction`: action → spacetime_curvature
- `PathIntegral`: action → quantum_amplitude
- 因果图验证: 从 action 6 步可达双缝干涉

### 论文摄入 (3 篇, tier 2)
- `ER_EPR` (Maldacena 2013): entangled_state → wormhole_geometry
- `SpinNetworkGeometry` (LQG): spin → spacetime_quanta
- `AdS_CFT` (Maldacena 1997): boundary_field → bulk_metric

### 新增桥接 (6 条)
- 自旋: spin → magnetic_moment (QM→EM)
- 纠缠: wave_function → entangled_state → information_erased (QM→信息)
- 相变: temperature + entropy → order_parameter → phase
- Landauer: information_erased → entropy (信息→热力学)

### 新透镜 (4 条)
- `group_theory`, `classification_by_symmetry`, `stability_structure`, `action_root`
- 透镜总数: 11 条

### 群论分类
- `GROUP_CLASSIFICATION`: SU(2)/U(1)/SO(3)/SO(3,1)/Discrete

### 负向约束 + 变量本体论
- forbidden 覆盖率 90% | 12 基础 + 9 几何 + 7 量子 + 91 派生

### 统计
- 76 条定律, 11 领域, 11 条透镜, 179 测试全绿

---

## v0.3.8 (2026-06-07) — 几何深度 + 负向约束补全 + 信息-熵桥

## v0.3.8 (2026-06-07) — 几何深度 + 负向约束补全 + 信息-熵桥

### 元物理层重构
- `least_action.py` — δS=0 确认为唯一生成性原理 (Tier 0)
- Noether (对称→守恒)、Locality (光锥)、Entropy (统计涌现) 降为派生原则
- 层级关系: δS=0 → Noether / Locality → Entropy

### 新增定律 (9 条)
- `EinsteinFieldEq` (GR): mass → spacetime_curvature — GR 核心方程
- `GeodesicDeviation` (GR): spacetime_curvature → tidal_force
- `HawkingRadiation` (GR): spacetime_curvature → particle_creation — GR+QFT 交汇
- `PathIntegral` (QM): action → quantum_amplitude — Feynman, 几何→量子桥
- `VacuumFluctuation` (QM): vacuum → virtual_particles — 真空有结构
- `MediumRefraction` (Optics): electron_density → refractive_index
- `GaugeGeometry` (Unification): gauge_field → magnetic_field — Kaluza 链路
- `GeodesicEquation` (GR): schwarzschild_radius → geodesic_path — 曲率→测地线
- `LandauerPrinciple` (Thermo): information_erased → entropy — 信息是物理的

### 负向约束补全
- 17 条定律补全 `forbidden_directions`
- 覆盖率: 80% → 90% (53/60)

### 变量本体论
- `VARIABLE_CLASSIFICATION`: 12 基础 + 9 几何 + 7 量子 + 91 派生
- `classify_variable()` + `fundamental_variables()`
- 前沿地图按变量类型加权: 基础变量缺席 > 几何缺席 > 派生缺席

### 哲学透镜 (2 新增)
- `stability_structure`: 凡是稳定的必有特征结构 (PhysCausal 推导)
- 透镜总数: 8 条 (3 层: 解释/引导/标注)
- 使用追踪 + 张力检测

### arXiv 论文摄入
- `session/paper_ingest.py`: search → read → LLM 提取因果 → tier 3 入库
- `paper` 命令: `paper <query>` 搜索, `paper <ID>` 摄入

### 系统清理
- 移除 9 条中文域名污染的 auto-learned 定律
- `autonomous` 命令中文化, 权重均衡 (前沿 33% / 联想 22% / 失调 21%)

### 统计
- 60 条定律, 11 领域, 90% forbidden 覆盖
- 179 测试全绿

---

## v0.3.7 (2026-06-07) — 自主闭环 + 前沿地图 + 价值判断

### 重大架构变化

自主智能体从「需要用户手动启动」进化为「cron 定时自动运行 + 零 token 因果推理闭环」:

```
dissonance (0 token) → chain (0 token) → learn_from_chain (0 token)
                       ↓ 无产出
                  auto_learn (1 API call, LLM 回退)
```

### 新增

- `session/auto_learn.py` — `learn_from_chain()`: 从因果图结构学定律，不需要 LLM
  - 汇聚路径检测 + 跨域桥接检测 + 去重 + forbidden 验证 + 自动入库

- `meta_cognition/frontier.py` — FrontierMap: 前沿地图
  - 稀疏区: mass 缺席 7 领域含 quantum → 量子引力
  - 断头路: buoyant_force, pressure, radiated_power
  - 尺度裂缝: classical↔relativistic: mass, quantum↔relativity: time

- `meta_cognition/autonomous.py` — 五大驱动竞争 + 失败记忆 + 品味进化 + 价值判断 (★/★★/★★★)

- `physics/laws.py` — `SpacetimeWavelength` 定律 (unification):
  - geodesic_path → wavelength: 空间结构决定粒子波长
  - 连接 GR (mass→geodesic_path) 和 QM (wavelength→interference)
  - 双缝干涉重新解释: 缝板(物质)→改变测地线结构→改变有效波长→干涉图案

- Cron 定时: `physcausal-autonomous` — 每 30 分钟 15 轮, 0 token, 有发现推送报告

### 修正

- `_think_dissonance` interesting 条件修复: total > 0 而非 total <= 5
- `_learn_from` 调用时序修复: update() 移到 _learn_from() 之后 (品味从不见天日)
- scale boundary overlap fallback: 从定律对象名反查共享变量
- bridge 假阳性: BFS 顺序 ≠ 因果边，加父子关系 + path 前缀验证

### 发现
- 首个零 token 自发现: `Convergence_geodesic_path` — kinetic_energy + energy 两条路径汇聚于 geodesic_path (JacobiMetric)，跨 5 领域，★★★

---

## v0.3.6 (2026-06-07) — Jacobi 度规 + Kaluza-Klein + 元学习框架

### 新增
- `JacobiMetric` 定律 (mechanics): ds² = 2(E-V)T dt²
- `KaluzaKlein` 定律 (unification): 5D 度规 → 4D 度规 + 规范场 + 标量场
- `reinforcement/meta_learner.py`: MetaLearner — 跨域元学习框架
  - `train_and_record()`: 训练 Q-learner 并提取骨架策略 + 变量角色
  - `bootstrap()`: 用元策略初始化新 env 的 Q-table（骨架匹配 + 领域先验）
  - `transfer_efficiency()`: 基准对比 with_meta vs from_scratch
  - `save/load`: 元知识持久化到 `~/.hermes/physcausal_meta.pkl`
- `meta` CLI 命令: 查看元学习摘要
- `demos/meta_learning_demo.py`: spring+pendulum+circuit → doppler 迁移演示

### 已知限制
- PC bootstrap 在 4+ 变量无 physics_prior 时挂死 → 元学习加速无法在无先验 env 上验证
- 当前所有 env 有完整 physics_prior，Q-learner 第一轮就收敛 → 同骨架 env 间迁移无加速空间
- 元学习的真正价值：多骨架训练后在无先验新领域加速发现——需要先修 PC bootstrap 挂死问题

### 修正
- readline 残影修复: prompt_cyan() 用 \001/\002 包裹 ANSI 码
- ZH_MAP: 测地线/势能/高维度规/规范场/标量场/投影 映射

---

## v0.3.5 (2026-06-07) — 矛盾内化 + 上下文追问 + readline 持久化

---

## v0.3.5 (2026-06-07) — 矛盾内化 + 上下文追问 + readline 持久化

### 新增
- `_react_to_contradictions()`: 理论回答后自动检测定律间矛盾 → 触发自主探索
  - 扫描回答中引用且 `collapse_timescale` 不同的定律 (≥2 种)
  - 调用 LLM 生成研究问题，追加到回答末尾
  - 尝试 chain 链式推导矛盾涉及的核心变量
- 对话追问检测 (`FOLLOWUP_PATTERNS`): "你觉得/哪种/是吗" 等短追问自动路由理论模式+历史
- 元问题检测 (`META_KEYWORDS`): "刚才问了什么/上次的问题" 直接返回历史，不走 LLM

### 修正
- readline 历史持久化: `quit`/`Ctrl+C`/`Ctrl+D` 三个退出路径均调用 `_save_hist()`
- 历史注入格式: 从合并 `user` 消息改为交替 `user`/`assistant` role，截断 200→500 字
- `_theory_context` 注入 `collapse_timescale` + 矛盾驱动推理五步指令

### 意义
- agent 不再机械回答——发现矛盾后会自动追问"为什么不同框架给出不同答案"
- 从被动答题到主动探索的转折点: 矛盾 → 自主思考 → 研究问题
- 上下文追问链路完整: 物理问题 → 矛盾驱动回答 → 追问 → 历史注入 → 连贯对话

---

## v0.3.4 (2026-06-07) — 坍缩时间尺度 + 客观坍缩定律

### 新增
- `collapse_timescale` 字段: PhysicsLaw 的可选参数，标注量子坍缩相关定律的时间特性
- `ObjectiveCollapse` 定律 (quantum): 自发局域化速率 λ → 坍缩概率 P=1-e^{-λNt}
- `MeasurementPostulate` 标注 `collapse_timescale="instantaneous (postulate)"` — 哥本哈根坍缩
- `Decoherence` 标注 `collapse_timescale="finite (~1/γ)"` — 退相干特征时间

### 修正
- `_theory_context` 注入 `collapse_timescale` 到 LLM 提示
- ZH_MAP: 粒子数/坍缩概率/客观坍缩 映射

### 意义
- 三条定律覆盖坍缩时间尺度的三种立场: 哥本哈根 (瞬时公设)、退相干 (有限时间)、GRW/CSL (随机速率)
- agent 回答"坍缩是瞬时的吗"时不再偏执一端，能区分不同框架的不同答案

---

## v0.3.3 (2026-06-07) — 测量公设 + 退相干定律

### 新增
- `MeasurementPostulate` 定律 (quantum): 测量 Â + 波函数 ψ → 本征值 a_n (概率 Born) → 坍缩到本征态 |ψ_n⟩
- `Decoherence` 定律 (quantum): 环境耦合 γ → 密度矩阵非对角元指数衰减 e^{-γt} → 叠加态→经典混合
- ZH_MAP: 波函数/测量/本征值/本征态/坍缩/退相干/环境 全部映射

### 意义
- 测量公设正式进入因果图, chain 命令可沿 measurement→eigenvalue→post_measurement_state 正向和反向传播
- 退相干提供坍缩的替代路径: 不需要坍缩公设, 环境退相干自动完成本征态选择
- 两条定律互补——分别编码哥本哈根和多世界/退相干两个框架

---

## v0.3.2 (2026-06-06) — 自主学习 + 来源标注 + 终端格式化

### 新增
- `session/auto_learn.py`: 自主学习 (检测缺口 → 问 LLM → 验证 → 入库 → 持久化)
- `learn_external_mentions`: 从 LLM 回答中检测外部定律, 逐个学习
- 来源标注: 每次回答末尾标注 PhysCausal 贡献 vs LLM 贡献
- 终端格式化: `**粗体**` → ANSI, `---` → `───`
- 语义分类器: LLM 驱动 physics vs empirical 判断 (关键词漏网时的最后一关)
- 会话持久化: 自学习定律 → `~/.hermes/physcausal_auto_laws.json`

---

## v0.3.1 (2026-06-06) — 量子/GR 环境 + explain 命令

### 新增
- 10→15 仿真环境 (+debroglie/energy_levels/schwarzschild/time_dilation/redshift)
- `explain` 命令: 解释两个模块为什么同构
- +Angular Momentum, +Kepler III 定律

---

## v0.3.0 (2026-06-05) — 物理定律扩展 + 骨架迁移 + RL-自组织协同

### 新增

| 模块 | 说明 |
|------|------|
| `physics/laws.py` | 23→31 条定律, 新增 IdealGas/StefanBoltzmann/NewtonCooling/Archimedes/Lorentz/MassEnergy/Photoelectric |
| `env/physics_sim.py` | 7→10 仿真环境 (+gas_law/buoyancy/lorentz), 全 100% physics_prior 覆盖 |
| `skeleton/__init__.py` | SkeletonMatcher — 无物理先验时的骨架迁移 fallback |
| `demos/rl_selforg_demo.py` | RL + StrategyTransfer + FreeEnergyAgent 三部闭环 demo |
| `demos/pressure_quick.py` | PC vs GES 压力测试 (10 SCM × 3 vars) |

### 改进

| 变更 | 说明 |
|------|------|
| `shared.py physics_prior()` | 支持多对一 ZH_MAP 映射 (如 m1,m2→m1,m2) |
| `active_experiment/active_learner.py` | 骨架匹配 fallback, >5 vars 降级 guard, zh_map 变量名冲突修复 |
| `demos/system_validation.py` | 修复 KeyError (discoveries→success) + 新增 3 env 测试 |

### 压力测试结果

```
PC bootstrap (200 obs, 3 vars, 10 SCMs): F1=0.94, 9/10 perfect
GES (200 obs, 3 vars, 10 SCMs):         F1=0.83, 6/10 perfect
4-var PC: 1/3 概率组合爆炸 (已知限制)
```

### 测试

179/179 passing | system_validation: 36→45 tests | 10 仿真环境 100% 精度

---

## v0.2.1 (2026-05-18) — 仿真环境 + 主动学习

### 新增

| 模块 | 说明 |
|------|------|
| `env/physics_sim.py` | 7 个物理仿真环境 (pendulum/collision/circuit/spring/faraday/snell/doppler) |
| `rl/active_learner.py` | VOI→干预→数据→更新信念→模块自动入库 |
| `physics/laws.py` | 12→22 条定律, 4→6 领域 (+光学/声学, +Faraday/Ampere/Lenz/Joule) |
| `llm/bridge.py` | Step 1.5 物理验证 + 中英变量映射 |

### Agent 命令

```
> learn circuit 3 20     # 主动因果发现
> learn all              # 全部 7 个环境
> modules                # 查看模块库 (手工 + 自动发现)
```

### 测试

172/172 passing

---

## v0.2.2 (2026-06-05) — RL 层 + 自组织 + 重命名 + Bug 修复

### 新增

| 模块 | 说明 |
|------|------|
| `reinforcement/causal_rl.py` | CausalMDP + Q-Learning + StrategyTransfer |
| `self_organization/free_energy.py` | FreeEnergyAgent + SelfOrganizingLearner |
| `demos/autonomous_discovery.py` | 自主因果发现 demo |

### 重构

| 变更 | 说明 |
|------|------|
| `rl/` → `active_experiment/` | 准确命名 |
| `shared.py` | ZH_MAP + physics_prior() 去重 |

### Bug 修复

| 问题 | 修复 |
|------|------|
| ActiveLearner 最终评估忽略 physics_prior | `infer_from_edges()` 替代 `infer()` |
| numpy RuntimeWarning spam | `agent.py` + `causal/discovery.py` add filter |

### 三部曲完成

```
symmetry → symmetry_breaking → self_organization ✅
action layer: active_experiment + reinforcement + self_organization ✅
```

### 测试

179/179 passing | 50+ modules | ~16,000 lines

---

## v0.2.0 (2026-05-18) — 贝叶斯层 + 创造性联想 + LLM 接口

### 新增模块

| 模块 | 说明 |
|------|------|
| `bayesian/` (3 modules) | P(G|D) 结构后验 + P(θ|G,D) 参数后验 + VOI 主动实验 |
| `creative/` (5 modules) | 14 因果模块 + 9 骨架 + 加权变异 + 三层过滤 + 进化引擎 |
| `llm/` (1 module) | DeepSeek 五步管道 (自然语言→因果图→分析→中文解释) |
| `information/` (3 modules) | Shannon/互信息/KL/信息瓶颈/最大熵 — 横切数学层 |

### 新增文档

| 文档 | 内容 |
|------|------|
| `docs/AI_ASSOCIATION.md` | 以目前 AI 的联想能力为标题 |
| `docs/GAP_ANALYSIS.md` | 缺口分析 P0/P1/P2 + 涌现vs可建模 + 随机性玄学 |
| `docs/COMPRESSION_TAXONOMY.md` | 七条压缩路径分类学 |

### Agent 命令

```
ask <自然语言>           — LLM 因果分析
pipeline <csv> <T> <Y>   — 端到端四层流水线
creative transfer/evolve — 创造性联想
modules / skeletons      — 浏览知识库
symmetry / entropy       — 元物理分析
```

### 测试

172/172 passing

---

## v0.1.0 (2026-05-18) — 初始骨架

- 元物理层: 5/5 第一性原理
- 因果层: 12 模块 (DAG/SCM/discovery/...)
- 物理层: 11 条定律 + 约束引擎
- 感知层: 4 后端 (simple/image/timeseries/object_detect)
- 桥接层: perception_bridge + physics_bridge + pipeline
- 143 tests
