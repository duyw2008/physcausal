# 费曼脑 (Feynman Brain) — 自主物理发现系统

**自组织细胞殖民地 · 知识图谱 · 神经突触层 · 因果推理引擎**

25000 个进化细胞在 6000 个物理概念的图谱上自主行走、投票、合成、推导，从 δS=0 出发涌现跨域物理连接。

```
当前状态 (gen ~20300):
  细胞: ~25,000        图节点: 5,982       comp:合成概念: 2,641
  突触边: 5,687         定律库: 422          t3 假说: 3,049
  t1/t2 验证: 480       多神经元共识: 60.1%   跨域桥: 11
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
│  方程库 (422 定律)                                    │
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
细胞反复走的路径 A→B→C 在睡眠中合成为 `comp:A__C` 概念节点。2641 个合成概念构成了脑的「词汇量」，是类比和跨域桥接的基础。

### 认知调度器
自由能驱动的竞争调度——各模块输出预测误差，误差大的优先执行。derive (sympy 公式推导)、intervene (物理定律验证)、WHY/ALT (矛盾检测) 按需触发。

### 睡眠三阶段
- **密度竞争**: 高连接度节点削弱弱边
- **幽灵修剪**: 移除无突触支持的图边
- **结构巩固**: s>1 的强边睡眠重放强化
- **噪声审计**: t0-t3 的 hyp/arXiv碎片降级

### 预测反馈
细胞行走时比较预测 s 与实际 s 的偏差，偏差大的反向边触发 sympy derive 建立反馈回路——人脑预测编码的轻量实现。

## 快速开始

```bash
# 查看状态
cat ~/physcausal/data/evo_colony.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'gen={d[\"generation\"]} cells={d[\"cells\"]}')"

# 启动 (systemd 独立 cgroup, 不会被 gateway 重启误杀)
systemd-run --user --unit=feynman-brain --same-dir --collect \
  bash -c 'cd ~/physcausal && exec /usr/bin/python3 -B -u run_evo.py >> data/evo_output.log 2>&1'

# 停止 (优雅退出, 自动存档)
systemctl --user stop feynman-brain

# 健康体检
python3 ~/physcausal/scripts/health_report.py
```

## 关键发现

| 发现 | 类型 | 机制 |
|------|------|------|
| broken_symmetry → gauge_coupling → mass | Higgs 链 | 方程库桥 + 细胞共识 |
| gauge_coupling → mass (s=6.5, n=125) | 独立重发现 | emergent 行走 |
| heat_power ↔ mass (电磁↔引力) | 跨域桥 | t0-2 跨域 |
| universal_mass_ratio → decoherence_dynamics | 量子-经典桥 ⚡ | t3 speculative |
| curvature → new_physics_parameters | 几何→新物理 ⚡ | t3 speculative |

⚡ = speculative (细胞发现, 未经 sympy 或教材确认)

## 设计哲学

**只给容量，不给方法。** 不硬编码「应发现什么」，给机制让发现自然涌现。
- 强制加层级模块 = 给方法。吸引子通过 coincidence 聚团 + 生态位分化自发涌现 = 给容量。
- 硬编码因果边 = 教材。细胞行走 + 投票共识 → emergent 边 = 发现。

**结构决定结果，噪声创造路径。** 脑的结构一致性逼出规律，随机探索发现新路。

**少重启，多收敛。** 脑需要连续运行数天积累共识。改代码→批量修→一次重启→至少跑一天不动。

## 项目结构

```
physcausal/
├── run_evo.py              主运行入口
├── meta_cognition/
│   ├── evo_colony.py        殖民地核心 (认知调度/睡眠/derive/intervene)
│   ├── evolvable_cell.py    进化细胞 (行走/基因组/树突/髓鞘)
│   ├── synaptic_layer.py    突触层 (s/n/tier/STDP)
│   └── feed_queue.py        知识注入队列
├── physics/
│   ├── laws.py              定律库 (422 条)
│   ├── laws_expansion.py    定律扩展 (EM/光学/声学/QFT/Higgs)
│   └── astronomy_laws.py    天文定律
├── scripts/
│   ├── health_report.py     10 维能力体检
│   ├── cron_health_check.py Cron 健康检查
│   └── start_brain.sh       启动脚本
├── data/                    运行时数据 (快照/日志/殖民地状态)
├── docs/                    设计文档
└── references/              ~100 篇诊断/修复/分析参考
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
