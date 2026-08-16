"""
突触层 v2 — 费曼脑的长期记忆 (compact storage)

神经元重复走过同一条边 → 突触强化 (LTP)
长期不走 → 突触衰减 (LTD) → 消除

关键改动 v1→v2:
  - 不再存储单个 SynapticActivation 对象 (v1 的 O(N) 内存泄漏)
  - 每边只存聚合: {神经元集合, 最后代, 总强度, 次数}
  - _check_ltp() 从 O(N) set comprehension 变成 O(1) len(set)
  - 保存格式压缩 (不再逐条写激活记录)

tier 0-2: 物理学家领地 — 不可修改
tier 3:   严肃物理假说 — 突触强化可达
tier 4:   探索编码 — 初始状态
"""

from __future__ import annotations
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import time, json, os


MEMORY_PATH = None


def _memory_path() -> str:
    global MEMORY_PATH
    if MEMORY_PATH is None:
        MEMORY_PATH = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "synaptic_memory.json"
        )
    return MEMORY_PATH


class SynapticLayer:
    """突触层 v3 — 双向信号 (前向LTP + 后向retrograde)

    前向 (anterograde): 神经元走过 src→dst → strengthen         (谷氨酸)
    后向 (retrograde):   dst 被 mark 激活 → 回传信号给所有 src  (内源性大麻素/NO)
    """

    LTP_THRESHOLD: int = 10
    CONSOLIDATION_THRESHOLD: int = 50
    LTD_WINDOW: int = 400  # 边衰减窗口 (微增容错)
    ELIMINATION_THRESHOLD: int = 3
    STDP_WINDOW: int = 50       # 时序窗口: 反向走在此窗口内触发STDP
    MAX_NEURONS_PER_EDGE: int = 2000  # 快照序列化安全上限 (live 系统无上限)
    TIER4_WINDOW: int = 500     # tier 4 晋升窗口期: 超时未晋升→消除 (放宽, 给新边更多时间积累神经元共识)

    # 系统级神经元 ID: 无细胞上下文的系统操作使用这些唯一ID
    # 不同操作类型贡献不同"神经元"→ 多操作验证的边更容易晋升 t4→t3
    SYS_HIPPOCAMPUS: int = 50002   # 海马体组合推理
    SYS_SHELF: int = 50003         # 磁盘种子库回放
    SYS_CLOSURE: int = 50004       # 因果闭包
    SYS_FEEDBACK: int = 50005      # 预测反馈
    SYS_TEACHER: int = 50006       # 教师轨迹镜像

    # tier 代谢成本倍率 (A): 越高越贵
    TIER_COST = {0: 0.3, 1: 0.5, 2: 0.7, 3: 2.5, 4: 3.0}  # t1补充(空洞), t3严出

    # 后向信号阈值
    RETROGRADE_POTENTIATION = 5     # 后向信号≥此数 → 前向LTP加速 (+1 bonus)
    RETROGRADE_DEPRESSION = -3      # 后向信号≤此数 → 前向LTD加速 (连接有毒)
    RETROGRADE_DECAY = 0.05         # 每50代后向信号衰减比例

    # LLM 残留词 / 非物理概念黑名单: _physics_check 直接拒绝 (防 arXiv 碎片溜进"通过验证")
    _LLM_JUNK_WORDS = (
        'analyzing', 'analyze', 'robot_foot', '未在给定', 'todo', 'none',
        'null', 'undefined', 'example', 'placeholder', 'xxx', 'nan',
    )

    def __init__(self):
        # v3: 前向 + 后向
        self.activations: Dict[Tuple[str, str], dict] = {}   # 前向 {(src,dst): {n,g,s,c}}
        self.tiers: Dict[Tuple[str, str], int] = {}
        self.external_validated: Dict[Tuple[str, str], bool] = {}
        self._last_fired: Dict[Tuple[str, str], int] = {}
        self._walk_timing: Dict[Tuple[str, str], int] = {}  # STDP: 记录每方向最后走的时间
        self._physics_results: Dict[Tuple[str, str], dict] = {}
        # 后向: {(dst,src): score}  — 从后突触回传的信号
        self.retrograde: Dict[Tuple[str, str], float] = {}
        # 上下文引用 (由 EvoColony 更新)
        self._cell_count: int = 0
        self._graph_ref: object = None

    def update_context(self, cell_count: int, graph: object):
        """每代更新: 用于动态阈值 + 节点存在性检查"""
        self._cell_count = cell_count
        self._graph_ref = graph

    def to_dict(self) -> dict:
        """快照用: 序列化核心状态"""
        return {
            'activations': {f"{k[0]}|||{k[1]}": {
                'n': len(v['n']), 'g': v['g'], 's': round(v['s'], 2), 'c': v['c'],
                'neurons': list(v['n'])[:self.MAX_NEURONS_PER_EDGE],
                't4_birth': v.get('t4_birth', 0)
            } for k, v in self.activations.items() if v.get('c', 0) >= 1},
            'tiers': {f"{k[0]}|||{k[1]}": v for k, v in self.tiers.items()},
            'retrograde': {f"{k[0]}|||{k[1]}": round(v, 2) for k, v in self.retrograde.items()},
            'physics': {f"{k[0]}|||{k[1]}": v for k, v in self._physics_results.items()},
        }

    def from_dict(self, data: dict):
        """从快照恢复"""
        if not data:
            return
        for k, v in data.get('activations', {}).items():
            parts = k.split('|||')
            if len(parts) == 2:
                self.activations[(parts[0], parts[1])] = {
                    'n': set(v.get('neurons', [])),
                    'g': v.get('g', 0),
                    's': v.get('s', 0.1),
                    'c': v.get('c', 1),
                    't4_birth': v.get('t4_birth', 0),
                }
        for k, v in data.get('tiers', {}).items():
            parts = k.split('|||')
            if len(parts) == 2:
                self.tiers[(parts[0], parts[1])] = v
        for k, v in data.get('retrograde', {}).items():
            parts = k.split('|||')
            if len(parts) == 2:
                self.retrograde[(parts[0], parts[1])] = v
        for k, v in data.get('physics', {}).items():
            parts = k.split('|||')
            if len(parts) == 2:
                self._physics_results[(parts[0], parts[1])] = v
        self._load()

    # ── 前向操作 (不变) ──

    def strengthen(self, neuron_id: int, src: str, dst: str,
                   strength: float, generation: int):
        """神经元走过一条边 → 突触强化"""
        key = (src, dst)
        edge = self.activations.get(key)

        if edge is None:
            edge = {'n': set(), 'g': generation, 's': 0.0, 'c': 0, 't4_birth': generation}
            self.activations[key] = edge

        # 防御: 如果 n 不是 set (旧数据或 bug), 修复为 set
        if not isinstance(edge.get('n'), set):
            edge['n'] = set()
        edge['n'].add(neuron_id)
        edge['g'] = generation
        # 🏋️ BCM 突触竞争: 低 s → Hebbian 增强, 高 s → 自限抑制
        # s=0→×1.0, s=3→×1.3(峰值), s=5→×0.81, s=10→×0.42
        s_val = edge['s']
        if s_val <= 3.0:
            bcm_factor = 1.0 + s_val * 0.1
        else:
            bcm_factor = 1.3 / (1.0 + (s_val - 3.0) * 0.3)
        bonus = strength * bcm_factor
        edge['s'] = min(edge['s'] + bonus, 100.0)
        edge['c'] += 1
        
        # 🧠 STDP: 时序依赖可塑
        # Pre→Post (A先走B后走): 强化 A→B
        # Post→Pre (B先走A后走): 弱化 A→B (因果反向)
        rev_key = (dst, src)
        rev_time = self._walk_timing.get(rev_key, 0)
        fwd_time = self._walk_timing.get(key, 0)
        if rev_time > 0 and generation - rev_time < self.STDP_WINDOW:
            if rev_time > fwd_time:
                # 反向先走 → Post→Pre → LTD: 削弱本次强化
                edge['s'] -= strength * 0.3  # 减30%
                edge['c'] = max(1, edge['c'] - 1)
        self._walk_timing[key] = generation
        self._last_fired[key] = generation

        if key not in self.tiers:
            self.tiers[key] = 4

        self._check_ltp(key, generation)

    def _check_ltp(self, key: Tuple[str, str], generation: int):
        """O(1) LTP 检查 + 三道质量闸门"""
        current = self.tiers.get(key, 4)
        edge = self.activations[key]
        unique = len(edge['n'])  # O(1)!

        # ── t4 → t3 晋升 (三道闸门 + 生存期) ──
        if current == 4:
            # 闸门1: 严进 — 需要足够独立神经元共识 (可达但不廉价)
            # 动态阈值: 随规模缩放但保持可达, 当前脑的神经元重叠率低
            threshold = max(2, min(
                self._cell_count // 2000 if self._cell_count > 0 else 2,
                6  # 硬上限, 等重叠率上来再调高
            ))
            if unique < threshold:
                edge.pop('eligible_since', None)  # 掉落 → 重置生存期
                return

            src, dst = key

            # 闸门2: 节点存在性 — 两端必须在因果图中
            if self._graph_ref is not None:
                if src not in self._graph_ref or dst not in self._graph_ref:
                    return  # 假节点, 不晋升

            # 闸门3: 物理检查 — forbidden edge 不晋升
            self._physics_check(key)
            phys = self._physics_results.get(key, {})
            if not phys.get("passed", True):
                return  # 物理约束失败, 留在 t4

            # 🕐 生存期: 需持续满足闸门 SURVIVAL_WINDOW 代才晋升 (过滤随机碰撞假阳性)
            SURVIVAL_WINDOW = 50
            eligible_since = edge.get('eligible_since')
            if eligible_since is None:
                edge['eligible_since'] = generation
                return
            if generation - eligible_since < SURVIVAL_WINDOW:
                return

            self.tiers[key] = 3
            edge.pop('t4_birth', None)  # 晋升成功 → 撤销死刑计时器
            edge.pop('eligible_since', None)

        # ── t3 → t2 巩固 ──
        if current == 3 and unique >= self.CONSOLIDATION_THRESHOLD:
            if self.external_validated.get(key, False):
                self.tiers[key] = 2

    def _physics_check(self, key: Tuple[str, str]):
        src, dst = key
        try:
            from physics.constraints import PhysicsConstrainedDAG
            from physics.laws import library

            all_vars = set()
            for law in library._laws:
                for s, d in law.causal_direction:
                    all_vars.add(s); all_vars.add(d)

            constraint = PhysicsConstrainedDAG(list(all_vars))
            issues = []

            # 节点有效性: LLM 残留词 / 非物理概念直接拒绝 (防 arXiv 碎片溜进"通过验证")
            for node in (src, dst):
                nl = node.lower()
                if any(w in nl for w in self._LLM_JUNK_WORDS):
                    issues.append(f"llm_junk: {node}")

            for f_src, f_dst in constraint.forbidden_edges:
                if f_src == src and f_dst == dst:
                    issues.append(f"forbidden: {f_src} → {f_dst}")
                    break

            if src == dst:
                issues.append("self-loop")

            if not issues:
                if self._has_verified_path(src, dst):
                    issues.append("path_exists")

            self._physics_results[key] = {
                "passed": len([i for i in issues if i != "path_exists"]) == 0,
                "issues": issues,
            }
        except Exception as e:
            self._physics_results[key] = {"passed": False, "issues": [str(e)]}

    def _has_verified_path(self, src: str, dst: str, max_depth: int = 10) -> bool:
        try:
            from physics.laws import library
            graph = {}
            for law in library._laws:
                for s, d in law.causal_direction:
                    graph.setdefault(s, []).append(d)
            if src not in graph or dst not in graph:
                return False
            visited, frontier = {src}, [src]
            for _ in range(max_depth):
                if not frontier:
                    break
                node = frontier.pop(0)
                for nb in graph.get(node, []):
                    if nb == dst:
                        return True
                    if nb not in visited:
                        visited.add(nb)
                        frontier.append(nb)
        except Exception:
            pass
        return False

    def validate_externally(self, src: str, dst: str):
        key = (src, dst)
        self.external_validated[key] = True
        if self.tiers.get(key, 4) == 3:
            self._check_ltp(key, 0)

    # ── LTD 衰减 & 消除 ──

    def decay(self, generation: int) -> List[Tuple[str, str]]:
        """LTD 衰减 + 四机制垃圾免疫系统:
        (A) tier 代谢成本 — tier4 3倍速衰减
        (B) 相干场 — 孤立于验证知识的边加速衰减
        (C) 用进废退 — tier4 失活窗口缩短为 1/3
        (D) 晋升窗口期 — tier4 超 200 代未晋升 → 消除 (遍历所有activation)
        """
        eliminated = []

        # (D) 晋升窗口期: 扫描所有 tier 4 边, 超时直接消除 (独立于 _last_fired)
        for key, edge in list(self.activations.items()):
            if self.tiers.get(key, 4) != 4:
                continue
            t4_birth = edge.get('t4_birth')
            if t4_birth and (generation - t4_birth) > self.TIER4_WINDOW:
                eliminated.append(key)

        # (B) 预计算相干节点: 出现在 tier ≤ 2 边上的节点
        coherent_nodes = set()
        for (s, d), t in self.tiers.items():
            if t <= 2:
                coherent_nodes.add(s)
                coherent_nodes.add(d)

        # (A,B,C) 衰减: 处理有 _last_fired 记录的老边
        for key, last_gen in list(self._last_fired.items()):
            age = generation - last_gen
            tier = self.tiers.get(key, 4)
            effective_window = self.LTD_WINDOW
            if tier == 4:
                effective_window = self.LTD_WINDOW // 3

            if age <= effective_window:
                continue

            edge = self.activations.get(key)
            if edge is None:
                continue

            base_decay = 0.5 ** (age / effective_window)
            tier_mult = self.TIER_COST.get(tier, 1.0)
            effective_decay = base_decay ** tier_mult

            src, dst = key
            if tier >= 3 and src not in coherent_nodes and dst not in coherent_nodes:
                effective_decay = effective_decay ** 1.5
            if tier == 4 and age > self.LTD_WINDOW // 2:
                effective_decay = effective_decay ** 1.5

            edge['c'] = max(1, int(edge['c'] * effective_decay))
            edge['s'] *= effective_decay
            # 🏋️ BCM LTD竞争: 高s边衰减加速, 给低s边成长空间
            s_val = edge['s']
            if s_val > 3.0:
                bcm_ltd = 1.0 + (s_val - 3.0) * 0.15  # s=5→×1.3, s=10→×2.05
                edge['s'] *= bcm_ltd

            if len(edge['n']) > 10:
                keep_n = max(1, int(len(edge['n']) * effective_decay))
                edge['n'] = set(list(edge['n'])[:keep_n])

            unique = len(edge['n'])
            dyn_threshold = max(2, min(
                self._cell_count // 2000 if self._cell_count > 0 else 2,
                6  # 硬上限
            ))
            if tier == 3 and unique < dyn_threshold:
                self.tiers[key] = 4
                edge['t4_birth'] = generation

            if edge['s'] < 0.001 or (tier == 4 and edge['s'] < 0.01 and edge['c'] < 2):
                eliminated.append(key)

        # 🧹 清理未走过的边: 从未点火 → 快速衰减
        fired_keys = set(self._last_fired.keys())
        for key, edge in list(self.activations.items()):
            if key in fired_keys:
                continue
            creation_gen = edge.get('g', generation)
            age = generation - creation_gen
            if age < self.LTD_WINDOW // 2:
                continue
            base_decay = 0.5 ** (age / (self.LTD_WINDOW // 4))
            edge['s'] *= base_decay
            edge['c'] = max(0, int(edge.get('c', 1) * base_decay))
            if edge['s'] < 0.001:
                eliminated.append(key)

        for key in set(eliminated):
            self.activations.pop(key, None)
            self._last_fired.pop(key, None)
            self.tiers.pop(key, None)
            self._physics_results.pop(key, None)
            self.retrograde.pop(key, None)

        return eliminated

    def trim(self):
        """内存修剪: 靠自然衰退调节, 不做硬上限截断"""

    # ── 查询 ──

    def get_strongest(self, n: int = 5) -> List[Dict]:
        scored = []
        for key, edge in self.activations.items():
            tier = self.tiers.get(key, 4)
            phys = self._physics_results.get(key, {})

            scored.append({
                "src": key[0], "dst": key[1],
                "unique_neurons": len(edge['n']),
                "total_strength": round(edge['s'], 1),
                "tier": tier,
                "external_validated": self.external_validated.get(key, False),
                "physics_passed": phys.get("passed"),
                "physics_issues": phys.get("issues", []),
            })

        scored.sort(key=lambda x: -x["unique_neurons"])
        return scored[:n]

    # ── 持久化 (v2 compact format) ──

    def _load(self):
        path = _memory_path()
        if not os.path.exists(path):
            return
        try:
            with open(path) as f:
                state = json.load(f)

            version = state.get('v', 1)

            if version >= 2:
                # v2 compact format (含神经元ID)
                edges = state.get('edges', {})
                for key_str, info in edges.items():
                    src, dst = key_str.split('|||')
                    key = (src, dst)
                    # 恢复神经元集合 (持久化的采样)
                    # 2026-08-13: cell_id 自增在重启后归零, 磁盘旧神经元ID(旧id%10000, 0-9999)
                    # 会与新 cell_id 空间冲突 → 清空重新累积 (旧细胞已不存在, 共识理应重算)
                    neuron_ids = set()
                    self.activations[key] = {
                        'n': neuron_ids,
                        'g': info.get('g', 0),
                        's': info.get('s', 0.0),
                        'c': info.get('c', 0),
                    }
                    self._last_fired[key] = info.get('g', 0)

                max_gen = state.get('max_gen', 0)
                if max_gen > 0:
                    print(f"🧠 突触记忆 v2: {len(edges)}条边, max_gen={max_gen}")

            else:
                # v1 legacy: 逐条激活记录 → 聚合为v2
                for item in state.get("activations", []):
                    key = (item["src"], item["dst"])
                    edge = self.activations.get(key)
                    if edge is None:
                        edge = {'n': set(), 'g': 0, 's': 0.0, 'c': 0}
                        self.activations[key] = edge
                    edge['n'].add(item.get("neuron_id", 0))
                    edge['g'] = max(edge['g'], item.get("generation", 0))
                    edge['s'] += item.get("strength", 0)
                    edge['c'] += 1
                    self._last_fired[key] = max(
                        self._last_fired.get(key, 0), item.get("generation", 0))

                total_saved = state.get("activations", [])
                print(f"🧠 突触记忆 v1→v2 迁移: {len(total_saved)}条记录 → {len(self.activations)}条边")

            # tiers / external_validated (格式兼容v1和v2)
            loaded_tiers = state.get('tiers', {})
            if loaded_tiers:
                # v2格式 key 用 |||, v1 用 →
                sep = '|||' if '|||' in next(iter(loaded_tiers)) else '→'
                self.tiers = {}
                for k, v in loaded_tiers.items():
                    parts = k.split(sep)
                    if len(parts) == 2:
                        self.tiers[(parts[0], parts[1])] = v

            loaded_ext = state.get('external_validated', {})
            if loaded_ext:
                sep = '|||' if '|||' in next(iter(loaded_ext)) else '→'
                self.external_validated = {}
                for k, v in loaded_ext.items():
                    parts = k.split(sep)
                    if len(parts) == 2:
                        self.external_validated[(parts[0], parts[1])] = v

            loaded_phys = state.get('physics_results', {})
            if loaded_phys:
                sep = '|||' if loaded_phys and '|||' in next(iter(loaded_phys)) else '→'
                self._physics_results = {}
                for k, v in loaded_phys.items():
                    parts = k.split(sep)
                    if len(parts) == 2:
                        self._physics_results[(parts[0], parts[1])] = v

        except Exception as e:
            pass  # 静默失败，从头开始

    def save(self):
        path = _memory_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)

        # 保存前修剪内存
        try:
            self.trim()
        except Exception:
            pass

        try:
            edges = {}
            for key, edge in self.activations.items():
                neuron_sample = list(edge['n'])[:self.MAX_NEURONS_PER_EDGE]
                edges[f"{key[0]}|||{key[1]}"] = {
                    'n': len(edge['n']),
                    'neurons': neuron_sample,
                    'g': edge['g'],
                    's': round(edge['s'], 2),
                    'c': edge['c'],
                }

            max_gen = max((e['g'] for e in self.activations.values()), default=0)

            state = {
                'v': 2,
                'max_gen': max_gen,
                'edges': edges,
                'tiers': {f"{k[0]}|||{k[1]}": v for k, v in self.tiers.items()},
                'external_validated': {f"{k[0]}|||{k[1]}": v for k, v in self.external_validated.items()},
                'physics_results': {f"{k[0]}|||{k[1]}": v for k, v in self._physics_results.items()},
            }

            with open(path, "w") as f:
                json.dump(state, f, ensure_ascii=False)
        except Exception as e:
            print(f"  ⚠ 突触保存失败: {e}")
            # 保存失败不致命 — 下次重试

    def status(self) -> str:
        total = len(self.activations)
        retro = len(self.retrograde)
        by_tier = defaultdict(int)
        for key in self.activations:
            by_tier[self.tiers.get(key, 4)] += 1

        lines = [f"🧠 突触层 v3: {total}条前向 + {retro}条后向"]
        for tier in [4, 3, 2, 1, 0]:
            if by_tier[tier]:
                name = {0: "公理", 1: "共识", 2: "主流", 3: "假说(LTP)", 4: "探索"}[tier]
                lines.append(f"   tier {tier} ({name}): {by_tier[tier]}条")

        total_n = sum(len(e['n']) for e in self.activations.values())
        lines.append(f"   总神经元引用: {total_n}")

        return "\n".join(lines)

    # ── 后向信号 (retrograde) ──

    def retrograde_signal(self, dst_node: str, valence: float = 1.0):
        """后向信号: 后突触 dst 被 mark 激活 → 回传信号给所有输入边

        valence > 0: "你的输入有用，强化"  (内源性大麻素)
        valence < 0: "你的输入有害，弱化"  (抑制性反馈)
        """
        # 找所有指向 dst 的边 (在 activations 中)
        # 注意: activations 存的是前向边 (src,dst)，后向键是 (dst,src)
        for (src, dst) in list(self.activations.keys()):
            if dst == dst_node:
                retro_key = (dst, src)
                self.retrograde[retro_key] = self.retrograde.get(retro_key, 0.0) + valence

    def retrograde_inhibit(self, dead_node: str):
        """死路节点 → 后向抑制: 所有连到它的边都收到负信号"""
        self.retrograde_signal(dead_node, valence=-1.0)

    def decay_retrograde(self):
        """衰减后向信号 (每50代)"""
        for key in list(self.retrograde.keys()):
            self.retrograde[key] *= (1.0 - self.RETROGRADE_DECAY)
            if abs(self.retrograde[key]) < 0.01:
                del self.retrograde[key]

    def apply_retrograde(self, generation: int):
        """将后向信号应用到前向LTP检查

        后向信号≥POTENTIATION → 前向 LTP 获得 +1 bonus
        后向信号≤DEPRESSION → 前向 LTD 加速 (从 activations 中移除)
        """
        for (dst, src), score in list(self.retrograde.items()):
            fwd_key = (src, dst)
            if score >= self.RETROGRADE_POTENTIATION and fwd_key in self.activations:
                # 后向确认 → 前向加速
                edge = self.activations[fwd_key]
                edge['s'] += 1.0  # bonus strength
                self._check_ltp(fwd_key, generation)
            elif score <= self.RETROGRADE_DEPRESSION and fwd_key in self.activations:
                # 后向否定 → 前向衰减
                edge = self.activations[fwd_key]
                edge['s'] = max(0, edge['s'] - 1.0)
                if edge['s'] <= 0:
                    del self.activations[fwd_key]
                    if fwd_key in self.tiers:
                        del self.tiers[fwd_key]


def neuron_fire_on_path(neuron, synapse: SynapticLayer, generation: int, strength: float = None):
    """神经元走过路径 → 每步突触激活。strength=预测质量(默认用walk长度)"""
    for step in neuron.current_walk:
        if len(step) >= 3:
            src, law, dst = step[0], step[1], step[2]
            if strength is None:
                strength = min(1.0, len(neuron.current_walk) / 10.0)
            neuron_id = getattr(neuron, 'cell_id', id(neuron) % 10000)
            synapse.strengthen(neuron_id, src, dst, strength, generation)


def mirror_strengthen(synapse: SynapticLayer, src: str, dst: str,
                      generation: int, multiplier: float = 2.0):
    """镜像神经元式突触加强 —— 教师轨迹快车道。
    
    比普通 strengthen 强 multiplier 倍。不修改 timing 语义，
    因为这是"看老师做"的通道而非细胞自己探索的通道。
    用于社会模仿：细胞走的路径与教师轨迹重叠时，
    对重叠段施加额外强化。
    """
    key = (src, dst)
    if key not in synapse.activations:
        synapse.activations[key] = {
            'n': set(), 'g': generation,
            's': 0.0, 'c': 0
        }
    edge = synapse.activations[key]
    edge['g'] = generation
    edge['s'] += 1.0 * multiplier
    edge['c'] += int(multiplier)
    synapse._walk_timing[key] = generation
    synapse._last_fired[key] = generation
    if key not in synapse.tiers:
        synapse.tiers[key] = 4
