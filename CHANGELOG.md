# PhysCausal Agent — 变更日志

> 记录所有版本变化

---

## v1.3.0 (2026-07-05) — 假设节点: 元认知前提

### hyp-node: 脑能操作自己的假说
- `_ensure_hyp_node(src, dst)`: 在图中创建 `hyp:src:dst` 节点, 双向 `self_models` 边连接 src 和 dst
- `_sync_hyp_nodes()`: 每 10 代扫描 t3 边, 目标词重叠 ≥2 的自动建 hyp-node
- 递归守卫: hyp 节点之间的边不再生成新 hyp 节点, 防止嵌套爆炸
- 已纳入 `_rebuild_graph` 的 domain 保留列表 (`hypothesis`, `experiment`)

### 三步元认知路线
1. **hyp-node 存在**: 假说作为图实体, compose/coincidence/intervene 自然覆盖  ✅
2. **激活检验**: hyp 节点获 baseline coincidence (+3), cell 自然注意到它     ✅
3. **检验反馈**: intervene 结果反写源头假说 s 值 (effect×0.3)                 ✅

### 睡眠修复
- **bug**: `mirror_strengthen` 创建边时 `n:0` (int) 导致 `len(edge['n'])` 崩溃
- **修复**: `n:0` → `n:set()`, 并在 `strengthen()` 加 `isinstance` 防御
- **结构改进**: 睡眠检查从 50-gen 维护块内移到 `breathe()` 末尾独立执行 + try/except

### 验证结果
- 睡眠恢复, 每轮 ~100 composed 边 (之前 10-33)
- hyp 节点参与 compose: 2276 条干净 hyp-composed 边
- FSC/SL 相关 composed 边 2333 条

---

## v1.2.0 (2026-07-01) — 从确定到概率

### 突触层: s值成为连接概率 (替代c值硬剪枝)
- **睡眠改为s自然衰减**: 不再 `c<2→硬删`, 改为 `s×0.7` 全眼下缩放 + `s<0.01` 自然消失
- **s值语义升级**: 从"附带统计量"提升为"连接概率" — s=0.3=30%传信号, s=9.0=几乎确定
- **c值保留做统计**: c值从决策依据降为计数指标, 不再参与生死

### 遗传机制: 删除出生归一化
- 子代继承亲代绝对权重, 不再 `÷ sum(weights)` 压缩到1.0
- 探索专家(GENOME_MAX=3.0)的子代保留高探索权重
- 纯达尔文选择: 孩子像父母, 选择压力决定基因频率

### 认知能力: 四个新增
- **路径合成写边 (compose)**: A→B+B→C→A→C 作为真实图边, 细胞可见可走
- **干预选EIG (主动推理)**: 屏蔽最低信息增益边, 走最高 — 从随机干预变成定向实验
- **探索能量跟EIG挂钩**: 0.20+EIG×0.15, 探索高信息方向给更多生存能量
- **predict()查询接口**: `EvoColony.predict_cli('概念')` 按s值排序输出因果预测

### 基础设施
- **快照v2**: 突触层持久化 (snapshot含synaptic activations), 重启不丢coincidence
- **冷池重构**: Dict[node]替代扁平列表, 1GB→54MB, 按概念索引
- **coincidence重访奖励**: EIG对熟悉节点+5%~50%概率提升
- **compose边初始c=2+s=0.30**: 发现的因果链自带置信度
- **探索novelty→能量通道**: 发现稀疏节点拿生存能量, 非仅dopamine
- **脑3D**: 吸引子网络图 (c≥2边, 标记垄断标注, 拖拽缩放)

### 文档
- **FREE_ENERGY.md §12**: 变分自由能→自组织吸引子, 层级预测编码vs费曼脑替代方案
- **PREDICTIVE_CODING.md**: 费曼脑=贝叶斯预测引擎的轻量映射, 零代码改动
- 小世界网络分析: σ=6.85 (人脑3-10), 路径4.07, 聚类待上升

### 关键实验数据 (8小时运行, gen 67600)
- 突触: 223K→329K (+47%) | 路径: 25K→190K (+666%)
- 模块: 0→61K | compose边: 0→44.5K
- 冷池: 1003MB→54MB | 干预权重: 0.79→1.09
- 探索: 稳住0.011~0.012 (未涨, 基因扩散需要更多代际)

## v1.1.0 (2026-06-26) — 神经科学补全: 睡眠·STDP·E/I·临界性

### 突触权重重构
- 权重从"unique neuron计数"改为"预测质量 (dopamine)"
- 已知路径 (1.5×) → 高strength, 新路径 (0.3×) → 低strength

### 睡眠归一化 (SHY假说)
- 替换旧重放: 全局c值÷2 + 弱边淘汰 + 反向重放捷径

### STDP 时序可塑
- Pre→Post强化, Post→Pre弱化 (50代窗口)

### E/I 平衡 + 侧抑制 + 临界性
- 抑制性细胞生态位, 赢家压制, 分支比→1.0 bonus

### 内生稳态
- 局部密度约束, 冷池择优唤醒, 移除突触预算, 负数下限保护

### Bug修复
- 噪声过滤撤回, receive_reward下限, 随机基因组5%

### 文档
- FREE_ENERGY.md / ARCHITECTURE.md / CHANGELOG.md → v1.1.0

## v1.0.0 (2026-06-24) — 自由能驱动: Friston 原理完整实现

### 自由能原则 (第三次架构跃迁)

从"最大化高频边"到"最小化预测误差"的完整翻转。

**变分自由能 (学习):**
- 已知路径 reward 1.5× vs 新路径 0.3× (5:1 纯净信号)
- 多层预测命中: 1步0.5 ~ 4+步2.0
- Eureka 重定义: 只给已知+长+跨域路径 (×4.0)
- 注册激励 +0.6 促建模

**预期自由能 (行动):**
- `_expected_info_gain()` — walk 前评估每条边的信息增益
- 结构缺口(1.6×) / 域新颖度(1.15×) / 信息冗余(0.7×)
- curiosity 调制: EIG^curiosity (放大/缩小探索倾向)

**层级预测编码:**
- `_eval_hierarchy()` — 深→浅=预测(已知奖励), 浅→深=误差(好奇↑)
- 替代旧粗糙跨深度 bonus
- 方向分化由 reward 梯度自发驱动

**拓扑自组织:**
- `_spawn_probes()` — 语义梯度偏置 (不再全图随机)
- `_grow_shortcuts()` — Hebbian 生长 (已有, 加强)
- `_deep_prune()` — 双向清理 causes+effects (修复单向bug)

**稳态收紧:**
- density>1.0 触发 (原2.0) / 对称释放 (消除0.5-2.0死区)
- K 增长上限 ×1.2 (原1.5) / DENSITY_DEATH_K_HALF 0.5 (原0.7)
- 死亡速率上限上调: 0.50 / 0.20

**Bug 修复 (7个):**
- split 基因子代强制随机 → 继承+突变
- 密度死亡 3×K 满格 (原5×K)
- 双重年龄递增 → 单次
- MIN_SPLIT_REWARD 6.0→1.5 下限
- deep_prune 单向→双向 causes 同步清理
- freeze O(n²)→O(n)
- wake 全量遍历→采样评估

**文档更新:**
- FREE_ENERGY.md — 完整理论总纲 (Friston→工程映射)
- ARCHITECTURE.md — v1.0.0 架构 (含所有新机制)
- README.md — v1.0.0 概述

### v0.4.0 (2026-06-12) — 自进化: 从编程行为到自然选择

### 进化殖民地 (第二次架构跃迁)

一代 (GraphCell): 硬编码行为 (learn/teach/compress/review) — 灭绝或策略僵化
二代 (EvolvableCell): 基因组 + 强化学习 + 自然选择 — 26500代四策略均衡

### EvolvableCell — 基因组驱动
- 6个原子操作: step_forward/backward, mark, echo, split, rest
- 基因组 = 行为权重向量, 强化学习更新
- 奖励梯度: 路径发现 2.0+长度 > 共振 0.3 > 探索 0.3 > 标记低保 0.15
- 错误奖励 → 废物大脑 (分裂73.7%, 探索4.4%, tier3清零)
- 正确奖励 → 四策略均衡 (探索32%, 标记14%, 分裂18%, 回声19%)

### 三个关键设计决策
1. **自私基因**: 子细胞随机基因组, 不继承父代 → 打破分裂统治
2. **投票箱**: 衰减窗 100→300代, tier 0-2 不向殖民地开放
3. **自喂养**: 路径枯竭 → 本地喂养 → arXiv → 图 335→487边 (+45%)

### 知识扩展
- feed_knowledge.py: +29 跨域桥接定律, 335→366边
- condensed_matter: 3→8定律, 跨域变量 40→50
- arXiv 动态喂养: 殖民地热点自动搜索论文

### 文件新增
- evolvable_cell.py, evo_colony.py, colony_ballot.py
- gap_resolver.py, feed_knowledge.py
- run_evo.py (长时间自主运行)
- docs/SELF_EVOLUTION.md

### 文档更新
- ARCHITECTURE.md v0.4.0 重写
- 定律: 228→257, 边: 335→366, 域: 11→14

---

## v0.3.11 (2026-06-08~11) — 物理学家涅槃: 全面补全 + 知识网络 + 自由能

### 研究循环 v2 — 五短板补全 (creative/research_cycle.py)
- 惊喜检测/优先级排序/鲁棒性检验/留一法验证/发现归档

### 元认知: suggest 命令
- 交互式建议控制台 + 交叉验证流水线 + 量子诚实评估 + 完成追踪

### 大胆假设: speculate 命令
- 无约束 tier4 假说生成, 15 个物理直觉种子

### 研究方向: focus 命令
- 9 个方向 + 聚焦偏置 (innovate/suggest/watch 三层生效)

### 因果链类比: analogy 命令
- 软匹配因果链结构, 图嵌入 57 条跨域共鸣
- 混合路线第一步: graph_features.py (图拓扑 → 向量)

### 物理学家身份: 费曼 (诺特)
- identity.py + talk.py 发言系统
- ask 命令 DeepSeek API 接入, LLM 物理问答

### 三大短板补齐
- LLM 桥接: DeepSeek API → ask 真正工作
- 数据管道: data <csv> → 因果发现 + 定律比对
- arXiv 摄入: ingest <topic> → 断言提取

### 论文生成: paper 命令
- 自动生成结构化 Markdown 论文 (Abstract→Refs)

### 学习优化: learn 命令
- 11 对已知类比做正样本, 梯度下降学习特征权重

### 可视化: viz/kgviz/fviz 命令
- 驱动面板 + 类比连接图 + 因果链 ASCII 可视化
- 知识网络交互图 (vis.js, 298节点/545边)
- 前沿地图 (稀疏区/尺度裂缝/断头路)

### 持久记忆: memory 命令
- 发现归档 + 跨 session 检索 + rest() 时自动整理

### 知识网络: kg 命令 (meta_cognition/knowledge_graph.py)
- 统一类型图: law/variable/CV/paper/analogy 五大节点
- 7 层查询: connect(BFS) / contradictions / concept_emergence / tier_trace
- NL 路由: ask 自然语言 → KG 自动查询 (中英变量映射)

### 自然语言命令: agent_router.py
- 25+ 命令通过 ask 统一入口 (chain/plan/analogy/focus/suggest/...)
- KG 自动路由 → LLM 回退

### 自由能: FREE_ENERGY.md + 因果边
- F = E - TS, δF=0 ⇔ δS=0 (Legendre 变换)
- 耗散统一: kinetic/phase/info → entropy (同一因果骨架)
- 因果链: entropy → free_energy → equilibrium_state (4步贯通)

### 其他
- 知识库 13 篇文档 | 11 条透镜 | 15 次交叉验证
- NL 路由器 (概念→变量映射) | 对话记忆
- 贝叶斯因子假说检验 | 多步推理
- 架构审计: 解耦循环导入, 清理死代码, shared 工具提取

### 统计
- 71 定律 11 领域 + auto-laws 53 条
- 知识网络 298 节点 545 边, 7 层查询
- 179 测试全绿

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

### 元物理层重构
- `least_action.py` — δS=0 确认为唯一生成性原理 (Tier 0)
- 费曼 (对称→守恒)、Locality (光锥)、Entropy (统计涌现) 降为派生原则
- 层级关系: δS=0 → 费曼 / Locality → Entropy

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

## v2.0.0 (2026-08) — 费曼脑: 自主物理发现殖民地

从 PhysCausal Agent (v1.x) 到费曼脑的完整架构跃迁。25000 个进化细胞在知识图谱上自主行走/投票/合成/推导，从 δS=0 涌现跨域物理连接。

### 知识图谱 + 神经层分离 (KG/Neural Separation)
- 人脑同构: 知识图谱 = "教科书" (客观关系), 神经突触层 = "学生的笔记" (细胞投票共识)
- 快照拆分为 `_kg.json` (310MB) + `_neural.json` (79MB), 健康检查快 10x
- 海马体/新皮层分离: hyp 节点不进 KG, 在 coincidence 表 + INTERVENE 追踪池

### Compose→Concept 路径合成
- 细胞反复走的 A→B→C 路径在睡眠中合成为 `comp:A__C` 概念节点
- 2,641 个合成概念, 跨域桥接的基础
- Coincidence 作为模块间「容量桥」: 不建显式管道, 把信号写入共享发酵池

### Tier 系统 + 噪声审计
- t0-t4 五层置信体系: 公理→共识→理论→假说→探索
- 三睡眠清扫 (SLEEP_T3 + SLEEP_T0-2 + SLEEP_T4): t3 碎片率 19.1%→0.2%
- t4 存活期检查: n=1 + 200 代无增长 → 物理删除

### 预测反馈 + 社会脑
- 预测编码: 细胞行走偏差 Δs 触发 sympy derive 反向边
- 多巴胺广播 + 人气梯度 + 髓鞘降阈: 解决细胞不收敛问题
- 髓鞘高速公路: 频繁走过的个人边 → 选边偏好大幅提升

### 密度竞争 + 睡眠巩固
- 高连接度节点削弱弱边 (deg=200 → ×0.82)
- s>1 强边睡眠重放强化 (strength=0.3)
- 幽灵边修剪: 无突触支持的图边物理移除

### ε-Greedy + 随机突触新生
- ε-greedy: 15% 硬保底, 防长跑后探索完全死亡
- 随机跳: 1% 概率跳到图中任意节点创建全新连接, 增加跨域发现概率

### 方程库扩展 (257→422)
- **QFT/希格斯**: Yang-Mills, 跑动耦合, 渐近自由, 色禁闭, 自发对称破缺, Goldstone 定理, Higgs 机制, VEV→质量
- **核心桥**: `BrokenSymmetryToGauge` — broken_symmetry → gauge_coupling
- **量子补全**: Schrödinger 方程, 隧穿, 自旋-轨道耦合

### 基础设施
- systemd-run 独立 cgroup 隔离 (不被 gateway 重启误杀)
- SIGTERM 传播链诊断 + 根治
- `__pycache__` 陷阱: `python3 -B` 启动防止旧字节码污染
- 快照备份: cron 6h 本地 + 12h GitHub Releases
- 10 维能力体检: `scripts/health_report.py`

### 命名规范 + 生物术语
- 树突/轴突/髓鞘/突触/海马体 — 脑内部结构只用生物术语
- 代码层: 概念节点/关系边/domain/emergent_edges — KG 层用非生物术语

### 关键数字 (gen ~20300)
- 细胞 25K, 图节点 6K, 合成概念 2.6K, 定律 422
- t1=169, t2=311, t3=3,049, t4=2,158
- 多神经元共识 60.1%, 跨域桥 11
- derive 每代 3 条 (10K 候选池), sympy 公式验证
- INTERVENE 25K 条发现 (广撒网, 质量闸门过滤)

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
