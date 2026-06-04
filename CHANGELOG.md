# PhysCausal Agent — 变更日志

> 记录所有版本变化

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
