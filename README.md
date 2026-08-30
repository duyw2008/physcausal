# 费曼脑 (Feynman Brain) — 自主物理发现系统

**自组织细胞殖民地 · 知识图谱 · 神经突触层 · 因果推理引擎**

约 12300 个进化细胞在近万个物理概念的图谱上自主行走、投票、合成、推导，从 δS=0 出发涌现跨域物理连接。

```
当前状态 (gen 38840, 2026-08-30):
  细胞: ~12,300        图节点 (vs.cache): ~10,800    因果边: ~9,400
  突触: ~51,700        emergent 边: ~3,900          t3 假说层: ~8,000
  定律库: ~600 定律 / 1200+ 因果方向
  知识域: 力学/电磁/热力/量子/GR/QFT/光学/流体/声学/现代
```

## 架构

```
┌──────────────────────────────────────────────────────┐
│                    费曼脑 (Feynman Brain)              │
│                                                      │
│  进化殖民地              知识图谱 (KG)                │
│  ┌─────────────┐       ┌──────────────────┐         │
│  │ EvolvableCell│ walk  │ 概念节点 (vs.cache)│        │
│  │ · 基因组驱动  │ ────→ │ · math_verified    │        │
│  │ · 9 操作类型  │ ←───  │ · emergent        │        │
│  │ · 树突/轴突   │ 投票  │ · Compose→Concept │        │
│  │ · 髓鞘高速公路 │       │ · 跨域桥接        │        │
│  └─────────────┘       └──────────────────┘         │
│         ↓                      ↓                    │
│  神经突触层 (SynapticLayer)    认知调度器              │
│  ┌─────────────┐       ┌──────────────────┐         │
│  │ · s/n/tier   │       │ · derive (sympy)  │        │
│  │ · STDP 强化  │       │ · intervene       │        │
│  │ · 密度竞争    │       │ · WHY/ALT 矛盾    │        │
│  │ · 睡眠巩固    │       │ · 预测反馈        │        │
│  └─────────────┘       │ · INTERVENE       │        │
│                         └──────────────────┘         │
│  方程库 (~600 定律)                                    │
│  ┌──────────────────────────────────────────┐       │
│  │ 力学/电磁/热力/量子/QFT/GR/光学/流体/声学  │       │
│  │ δS=0 生成根 → Euler-Lagrange/Hilbert/     │       │
│  │ PathIntegral → 力/时空曲率/量子振幅       │       │
│  └──────────────────────────────────────────┘       │
└──────────────────────────────────────────────────────┘
```

## 核心机制

### 细胞行走
每个细胞是独立智能体，携带基因组决定行为倾向（step_forward/backward/mark/echo/split/intervene/derive/probe/rest）。细胞在图上行走，通过以下机制选边：

- **ε-greedy 探索** (15%): 随机选已有边
- **随机突触新生** (1%): 跳到图中任意节点创建全新连接
- **加权选择** (84%): 综合 EIG×髓鞘×人气×树突的加权路由

### 知识图谱 vs 神经层 (KG/Neural Separation)
人脑同构——知识图谱存「教科书」（客观关系），神经突触层存「学生的笔记」（细胞投票共识）。突触从零积累，不直接写入 KG 边。图=干净，脑=噪声中学习。

### Compose→Concept
细胞反复走的路径 A→B→C 在睡眠中合成为 `comp:A__C` 概念节点。5600+ 个合成概念构成了脑的「词汇量」，是类比和跨域桥接的基础。

### 认知调度器
自由能驱动的竞争调度——各模块输出预测误差，误差大的优先执行。derive (sympy 公式推导)、intervene (物理定律验证)、WHY/ALT (矛盾检测) 按需触发。

### 睡眠三阶段
- **密度竞争**: 高连接度节点削弱弱边
- **幽灵修剪**: 移除无突触支持的图边
- **结构巩固**: s>1 的强边睡眠重放强化
- **噪声审计**: t0-t3 的 hyp/arXiv碎片降级

### 预测反馈
细胞行走时比较预测 s 与实际 s 的偏差，偏差大的反向边触发 sympy derive 建立反馈回路——人脑预测编码的轻量实现。

### 因果方向：δS=0 变分是唯一判定
因果方向的唯一来源是 δS=0 变分（`action→force` 欧拉-拉格朗日、`action→spacetime_curvature` 希尔伯特、`action→quantum_amplitude` 路径积分）。三类伪因果被逐层堵死：

- **词共现伪因果**（arXiv 文本两词高频同现）→ signal 闸门（`causal`/`associative` 区分）
- **代数伪因果**（F=ma 解成 m=F/a 当因果）→ `causal_status` 三态判定（causal/forbidden/unverified）
- **双向伪因果**（force↔mass）→ 方向一致性检查 + 一次性清理 296 条假因果 tier2

### 定律库注入：给路径不给结论
定律库 ~600 条 `causal_direction` 通过 `inject_laws.py` 注入 KG（`physics` 域），只给细胞可走的因果路径、不标 tier。脑自动撒细胞到 physics hub → 行走 → Hebbian 强化 → δS=0 闸门验证 → 晋升——结构从学习中涌现，不是注入的结论。入口两层把控：**概念归一化**（公式占位符 m1→mass / q1→charge 映射到物理概念，无法映射的碎片不建节点不建边）+ **生态位**（被走过 ≥10 次且零学习产出的概念失去被选择权，可逆，不删概念）。

### 结构浸润 > 语言浸润
物理理解的载体是**数学结构**，不是文本。脑的语义来自「同一概念在多个独立方程中的角色」（多元约束收敛）——多方程 + 推导 + 预测验证 = 语义浸润；LLM 相关文本爬不动因果（词共现≠因果），故 0LLM 纯符号运行。

### 分布式特征：VSA 域分化
概念意义 = 高维向量（分布式），边按域分存储。`_rebuild_cache` 因果域（axomatic/physics/derive）优先排序，细胞读图时因果邻居排前面——causal 域里的用法才是真意义，emergent（词共现）沦为背景。

## 快速开始

```bash
# 查看状态
cat ~/Agent/physcausal/data/evo_colony.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'gen={d[\"generation\"]} cells={d[\"cells\"]}')"

# 启动 (systemd 独立 cgroup, 不会被 gateway 重启误杀)
systemd-run --user --unit=feynman-brain --same-dir --collect \
  bash -c 'cd ~/Agent/physcausal && exec /usr/bin/python3 -B -u run_evo.py >> data/evo_output.log 2>&1'

# 停止 (优雅退出, 自动存档)
systemctl --user stop feynman-brain

# 健康体检
python3 ~/Agent/physcausal/scripts/health_report.py

# 学习成果评估 (三层: 知识获取/能力涌现/理解, 窗口默认24h)
python3 ~/Agent/physcausal/scripts/feynman_learning_report.py [小时窗口]
```

## 学习成果评估

学习成果 ≠ 知识量。评估分三层，判据是「检索对 ≠ 会推导 ≠ 理解」——库外新发现才算理解：

| 层 | 回答 | 指标 | 实测 (2026-08-30) |
|----|------|------|------|
| L1 知识获取 | 学了什么 | 进图率 (vs.cache ∩ 定律概念) / 入脑率 (突触 ∩ 定律) | 92% / 67% |
| L2 能力涌现 | 会了什么 | 结构增长 / 探索多样性 / 变形产出 (DERIVE) / SETTLE 频率 | 路径+756 / 突触20258 / 变形0 / t3+435 |
| L3 理解 | 懂了吗 | 库外发现 (autonomous/why_gap/alt_view/变分/诺特/预言落空) | 全历史 329 条, 窗口内 4 条 (noether_brain) |

**变形/发现比** 是检索期→理解期的判据：DERIVE 代数变形（sympy 解方程）零新信息，其占比随时间下降、库外发现占比上升 = 理解在萌芽。代数变形产物走 `math_verified` 域，永远进不了因果层（tier2 需 δS=0 变分因果通道）。

```bash
python3 scripts/feynman_learning_report.py        # 默认 24h 窗口
python3 scripts/feynman_learning_report.py 168    # 一周窗口
```

## 关键发现

| 发现 | 类型 | 机制 |
|------|------|------|
| broken_symmetry → gauge_coupling → mass | Higgs 链 | 方程库桥 + 细胞共识 |
| gauge_coupling → mass (s=6.5, n=125) | 独立重发现 | emergent 行走 |
| heat_power ↔ mass (电磁↔引力) | 跨域桥 | t0-2 跨域 |
| universal_mass_ratio → decoherence_dynamics | 量子-经典桥 ⚡ | t3 speculative |
| curvature → new_physics_parameters | 几何→新物理 ⚡ | t3 speculative |
| fast_mode_short_wavelength_characteristics → radial_velocity_anomaly: v=f·λ (conf=0.90) | 波-星系旋转异常链 | DERIVE |
| radial_velocity_anomaly → galaxy_luminosity: T_orb=2π·r^(3/2)·√v/(√G·√p) (conf=0.65) | 星系动力学链 | DERIVE |

⚡ = speculative (细胞发现, 未经 sympy 或教材确认)

## 设计哲学

**只给容量，不给方法。** 不硬编码「应发现什么」，给机制让发现自然涌现。
- 强制加层级模块 = 给方法。吸引子通过 coincidence 聚团 + 生态位分化自发涌现 = 给容量。
- 硬编码因果边 = 教材。细胞行走 + 投票共识 → emergent 边 = 发现。
- 给路径（KG 边，细胞可走）≠ 给结论（标 tier）。定律库 causal_direction 注入是给路径——结构仍是脑走出来的，不是注入的结论。

**结构决定结果，噪声创造路径。** 脑的结构一致性逼出规律，随机探索发现新路。

**少重启，多收敛。** 脑需要连续运行数天积累共识。改代码→批量修→一次重启→至少跑一天不动。

## 项目结构

```
physcausal/
├── run_evo.py              主运行入口
├── inject_laws.py          定律库因果方向 → KG 注入 (给路径不给 tier)
├── inject_sm.py            标准模型结构化知识注入
├── inject_greens.py        格林函数知识注入
├── inject_homotopy.py      同伦代数知识注入
├── meta_cognition/
│   ├── evo_colony.py        殖民地核心 (认知调度/睡眠/derive/intervene)
│   ├── evolvable_cell.py    进化细胞 (行走/基因组/树突/髓鞘)
│   ├── synaptic_layer.py    突触层 (s/n/tier/STDP/causal_status)
│   └── feed_queue.py        知识注入队列
├── physics/
│   ├── laws.py              定律库 (~154 基础定律, 含 causal_direction)
│   ├── laws_expansion.py    定律扩展 (EM/光学/声学/QFT/Higgs)
│   ├── astronomy_laws.py    天文定律
│   └── qft_book_laws.py     QFT 书白名单加料 (24 定律/75 因果方向/48 概念)
├── scripts/
│   ├── health_report.py     10 维能力体检
│   ├── feynman_learning_report.py  三层学习成果评估 (L1获取/L2能力/L3理解)
│   ├── restart_brain.sh     重启 (清 pycache + 停旧 + systemd-run 启新)
│   ├── topo_*.py            拓扑体检族 (metrics/health/check/probe/trend)
│   └── cron_*.py            Cron 任务 (健康检查/边结构/快照序列)
├── data/                    运行时数据 (快照/日志/殖民地状态, git 不跟踪)
├── docs/                    设计文档
└── reports/                 发现报告 (论文/可视化 HTML)
```

## 文档

| 文档 | 内容 |
|------|------|
| [DESIGN_PHILOSOPHY.md](docs/DESIGN_PHILOSOPHY.md) | 设计哲学 + KG/神经分离 |
| [NOUS_THEORY.md](docs/NOUS_THEORY.md) | Nous 理论 — 统一云、垃圾免疫、睡眠消化 |
| [DEEP_UNDERSTANDING_ARCHITECTURE.md](docs/DEEP_UNDERSTANDING_ARCHITECTURE.md) | 深刻理解的神经基础 |
| [CHANGELOG.md](CHANGELOG.md) | 版本变更记录 |

## 许可证

MIT
