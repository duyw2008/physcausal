# PhysCausal Agent — 变更日志

> 记录所有版本变化

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
