# PhysCausal — 缺口分析与后续方向

> 版本: 2026-05-18 | 定位: 从当前架构到通用智能体的路线图
> 当前状态: 143 tests | 5/5 元物理原则 | 4 后端感知 | 端到端管线

---

## 一、已完成 (地基)

```
元物理层   5/5 原则 ✅     least_action / symmetry / entropy / locality / measurement
横切层     2/2 ✅          spectral (特征谱) / information (信息度量)
物理层     基础 ✅          11 条定律 + constraint DAG
因果层     完整 ✅          12 模块 (DAG/SCM/discovery/estimation/mediation/...)
感知层     4 后端 ✅        simple / image / timeseries / object_detect
桥接层     3 模块 ✅        perception_bridge / physics_bridge / pipeline
```

---

## 二、致命缺口 — 必须有

没有这些，谈不上通用。每个都需要从零构建，不能用已有模块拼凑。

### 2.1 主动因果实验设计 (Active Causal Discovery)

```
当前: 只能分析已有观测数据
缺口: 不知道「下一步该干预哪个变量来消除不确定性」

核心能力:
  - 给定部分因果图，计算每条边的信息价值 (VOI)
  - 「做实验 X 能最大程度缩小剩余 DAG 的不确定性」
  - 实验设计预算约束下的最优干预序列

理论基础:
  - Causal Bandit (每一步选择一个干预)
  - Bayesian Optimal Experimental Design
  - Mutual Information Maximization: argmax_a I(G; D ∪ {do(a)})

优先级: P0 (致命) — 没有这个，永远是被动的分析工具
```

### 2.2 层次化抽象与涌现 (Hierarchical Abstraction)

```
当前: 因果变量必须预定义，不能自动从数据中涌现
缺口: 不会跨尺度压缩 — 从分子运动自动发现「温度」

核心能力:
  - 从微观变量自动构建宏观序参量
  - 不同尺度使用不同精细度的因果模型
  - 尺度间的因果关系映射 (downward causation)

理论基础:
  - Renormalization Group (Wilson)
  - Information Bottleneck across scales
  - Causal Emergence (Hoel et al.)
  - Coarse-graining 的信息保真度度量

优先级: P0 (致命) — 没有层次化抽象，复杂度天花板很低
```

### 2.3 组合泛化 (Compositional Generalization)

```
当前: SCM 是平铺的。学会了「摆锤」和「推车」，不会「推车上的摆锤」
缺口: 因果模块不能自动组合

核心能力:
  - 因果子图作为可复用模块
  - 模块接口: 输入端口 / 输出端口 / 内部 SCM
  - 「球A撞球B」+「球B撞球C」→ 自动组合为三体碰撞
  - 在相遇点对接模块接口

理论基础:
  - Category Theory for causal modules
  - Causal abstraction mapping
  - Modular SCM (Forney-style factor graphs)

优先级: P0 (致命) — 没有组合，泛化边界就是训练边界
```

### 2.4 目标/价值系统 (Free Energy / Intrinsic Motivation)

```
当前: 智能体没有内在驱动力
缺口: 不知道「什么值得关心」— 永远在等指令

核心能力:
  - Free Energy Principle: 维持稳态 = 存活
  - 惊奇最小化 (surprise minimization)
  - 信息增益驱动的好奇心
  - 「维持对世界的可预测性」作为内在目标

理论基础:
  - Friston 的自由能原理 (Active Inference)
  - Empowerment maximization
  - Causal entropy regularized planning

优先级: P0 (致命) — 没有驱动力，永远不会主动行动
```

---

## 三、严重缺口 — 应该有

### 3.1 元学习 (Meta-Learning)

```
当前: 每次遇到新领域从零运行因果发现
缺口: 不能越学越快。碰到第 10 个力学场景时仍和第 1 个一样慢

核心能力:
  - 从因果结构库中快速匹配相似结构
  - 「这个新场景和之前见过的 pendulum 很像」→ 迁移先验
  - 共享物理模板的跨域迁移 (type5 domain transfer 的扩展版)

优先级: P1 (严重)
```

### 3.2 不确定性量化 (Bayesian SCM)

```
当前: 效应估计只给点估计 (ATE ± CI)
缺口: 不能量化「我对这个因果图的置信度是多少」

核心能力:
  - Bayesian Causal Discovery: P(G|D) 而非单点 G
  - 结构不确定性传播到效应估计
  - 「60% 概率 X→Y, 40% 概率 X←Y」的真概率

优先级: P1 (严重)
```

### 3.3 多步因果规划 (Causal + RL 规划)

```
当前: 能反事实 (一步)，不能多步规划
缺口: 知道「如果做A会怎样」，不知道「怎么做才能达到目标Z」

核心能力:
  - do-calculus + 搜索: 到达目标的最小干预序列
  - 在物理约束下找到可行路径
  - 因果归因驱动调试: 「为什么没达到目标？哪一步出了问题？」

优先级: P1 (严重)
```

---

## 四、规模缺口 — 需要堆

### 4.1 物理领域扩展

```
当前: 11 条定律，3 个领域 (力学/电磁/热力学/流体)
需要: 50+ 领域全覆盖

  - 声学 (波动方程、共振)
  - 光学 (折射/反射/干涉/偏振)
  - 弹性力学 (应力-应变)
  - 化学反应动力学
  - 生物学基础 (种群增长、酶动力学)
  - 气候/海洋 (流体+热力学耦合)
```

### 4.2 组合知识库

```
当前: 0 (没有组合机制)
需要: >10⁴ 可组合的因果模块
需要: 自动发现新模块 (从感知数据中提取)
需要: 模块版本化 + 冲突解决
```

### 4.3 工程规模

```
当前:     ~8000 行 Python, 143 tests
需要:     测试框架 (property-based, fuzzing)
需要:     CI/CD + benchmark suite
需要:     分布式因果发现 (大数据集)
```

---

## 五、优先级排序

```
P0 (致命 — 无此不通用):
  ├── 主动实验设计             ← 下一个要做的
  ├── 层次化抽象 / 涌现
  ├── 组合泛化
  └── 目标/价值系统

P1 (严重 — 当前能工作但有天花板):
  ├── 元学习
  ├── Bayesian SCM
  └── 多步因果规划

P2 (工程 — 规模化和体验):
  ├── 物理领域扩展
  ├── 组合知识库
  └── 工程基础设施

P3 (研究 — 长期探索):
  ├── 因果表示学习
  └── 全息原理 / 重整化群 的因果版本
```

---

## 六、阶段性里程碑

```
v0.2  — 元物理完备 + 因果层迁移                    ✅
v0.3  — 感知层升级 + information 横切层            ✅
v0.4  — 主动实验设计 (Causal Bandit)               P0
v0.5  — 层次化抽象 (Renormalization × Causal)      P0
v0.6  — 组合泛化 (Modular SCM)                     P0
v0.7  — 自由能原理 (Active Inference engine)       P0
v0.8  — Bayesian SCM + 不确定性量化                P1
v0.9  — 因果规划 + 元学习                           P1
v1.0  — 可演示的通用物理因果智能体
```

---

## 七、一句话

> 地基是对的。差距不在核心原理 (五条原则已经完备)，而在生长机制 (如何从这些原则中生长出组合抽象和主动探索)。下一阶段的核心问题不是「还缺什么原则」，而是「如何让已确立的原则互相咬合，产生涌现行为」。
