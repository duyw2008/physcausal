"""
费曼脑 -- 神经元自己发现策略，有长期记忆

关键区别:
  旧殖民地: 细胞有 learn/teach/compress/review -- 我们定的
  费曼脑:   神经元只有6个原子操作，策略由基因组+自然选择涌现
            突触层持久化 -> 跨会话长期记忆
"""

from __future__ import annotations
from typing import Dict, List, Tuple, Set
from collections import Counter, defaultdict, deque
import random, time, json, os
try:
    import orjson
except ImportError:
    orjson = None  # fallback to json

from meta_cognition.evolvable_cell import EvolvableCell, ACTIONS, genome_diversity
from meta_cognition.graph_cells import Blackboard
# NOTE: `chemistry` 是模块级单例 — 所有 colony 共享同一个化学状态。
# ChemistryParams 中的常量 (EMOTION_EUPHORIA 等) 是只读的，但
# chemistry 实例的可变状态 (inhibition, blocked_edges 等) 在 colony 间共享。
# 当前只有一个 colony 运行，因此安全。若未来并行多 colony 需重构。
from meta_cognition.brain_chemistry import BrainChemistry, ChemistryParams, chemistry
from meta_cognition.walk_fingerprint import walk_fingerprint


class EvoColony:
    """费曼脑 -- 生态自平衡进化系统"""

    MAX_AGE_REF = 800
    CARRYING_CAPACITY = 5000             # K基准 (密度死亡阈值, 匹配稳态)
    MIN_SPLIT_REWARD = 8.0               # 分裂门槛: 需~53步攒够, 防癌变但保信息承载
    # 边域白名单: 只有经过证明的域能进入因果图
    VALID_EDGE_DOMAINS = {"math_verified", "mechanics", "electromagnetism",
                          "thermodynamics", "quantum", "optics",
                          "modern", "general_relativity", "emergent"}
    DENSITY_DEATH_K_HALF = 0.5             # ↓0.7→0.5: 更早触发密度死亡
    DENSITY_DEATH_MAX_RATE = 1.0          # 去盖: 密度极高时可杀100%
    STARVATION_PERCENTILE = 0.10         # ↑0.08→0.10: 更大饥饿范围
    STARVATION_DEATH_RATE = 0.08         # ↑0.05→0.08: 更高饥饿率
    MEMORY_WARN_FRACTION = 0.60
    MEMORY_CRITICAL_FRACTION = 0.75
    MEMORY_FLUSH_FRACTION = 0.68
    SNAPSHOT_INTERVAL = 100            # ↓500→100: 更频繁存快照, 重启少丢进度
    MAX_SNAPSHOTS = 2            # 磁盘和内存紧张, 只保留最新2个
    ABSTRACTION_THRESHOLD = 10

    METHODOLOGY_NODES = {
        'experiment', 'experimental_design', 'hypothesis_testing',
        'validation_framework', 'resolution', 'hypothesis_generation',
        'data_analysis', 'measurement', 'scientific_method',
        'contradiction', 'falsification', 'reproducibility'
    }

    def __init__(self, graph: Dict = None):
        from meta_cognition.vsa_memory import VSAGraph, VSAEngine
        if graph is not None and isinstance(graph, VSAGraph):
            # 从快照恢复: 重用已有 VSA
            self.graph = graph
        else:
            self.graph = VSAGraph()
            # 从物理定律库初始化
            from physics.laws import library
            for law in library._laws:
                for src, dst in law.causal_direction:
                    self.graph.add_edge(src, dst, law.name, law.domain)
            # 兼容旧快照 (传入旧 dict): 导入到 VSA
            if graph is not None and isinstance(graph, dict):
                for src, node_data in graph.items():
                    for law_name, dst, domain in node_data.get("effects", []):
                        self.graph.add_edge(src, dst, law_name, domain)
        self.board = Blackboard()
        self.cells: List[EvolvableCell] = []
        self.generation = 0
        self.total_actions = 0
        self.total_rewards = 0.0
        self._carrying_capacity = self.CARRYING_CAPACITY
        self._density_deaths = 0
        self._starvation_deaths = 0
        self._last_mem_check = 0

        from meta_cognition.synaptic_layer import SynapticLayer, neuron_fire_on_path
        self.synapse = SynapticLayer()

        try:
            from physics.enrich_knowledge import feed_enrichment
            n = feed_enrichment()
            if n > 0:
                self._rebuild_graph()
        except Exception:
            pass

        # 原图节点集 -- tier 3 晋升闸门
        self._native_nodes: set = set()
        for law in library._laws:
            for src, dst in law.causal_direction:
                self._native_nodes.add(src)
                self._native_nodes.add(dst)

        self._build_graph_features()
        self._load_emergent_edges()
        self._load_injected_edges()
        self._priority_nodes: set = set()  # 提前初始化: _load_teacher_trajectories 需要
        self._load_teacher_trajectories()

        self._coincidence: Dict[Tuple[str, str], int] = {}
        self._load_coincidence()
        
        # 本体觉: 脑感受自己的 emergent 结构统计
        from meta_cognition.proprioception import Proprioception
        self.proprioception = Proprioception()
        
        # 运行时增量喂料管道
        from meta_cognition.feed_queue import FeedQueue
        self.feed_queue = FeedQueue()
        
        # sympy 推导感知: coincidence 热点自动验证
        from meta_cognition.derive_perception import DerivePerception
        self.derive_perception = DerivePerception()
        
        # arXiv 论文闸门: 书架 → 细胞共识 → 晋升
        from session.arxiv_gate import ArxivReadingList
        self.arxiv_reading = ArxivReadingList()
        self._contradiction_nodes: set = set()
        self._load_contradictions()
        self._probe_edges: Dict[Tuple[str, str], int] = {}
        self._emergent_birth: Dict[Tuple[str, str], int] = {}
        self._abs_birth: Dict[str, int] = {}  # abstract node -> creation gen
        self._edge_birth: Dict[Tuple[str, str], int] = {}  # 所有边的诞生代 (时序因果)
        # 语义签名: 节点→64维向量，从walk上下文涌现
        self._node_vecs: Dict[str, list] = {}
        self.SEMANTIC_DIM = 64
        self.SEMANTIC_LR = 0.01  # 学习率

        self._priority_nodes: set = set()  # 优先唤醒
        self._resolved_nodes: set = set()  # 被解决矛盾
        self._active_goals: dict = {}  # 全局目标
        self._edge_last_seen: dict = {}  # 边活跃追踪
        self._oracle_scores: Dict[Tuple[str, str], float] = {}  # ORACLE LLM 验证分数 (只记最近一次)
        # Deep Dive 专注机制: 锁定一个课题深入 N 代
        self._focus: dict = {}  # {topic, locked_at, min_duration, hypotheses_seen, resolved}
        self._load_focus()
        self._plan: dict = {}   # 研究计划 {tasks, next_id}
        self._load_plan()
        self._composed_birth: dict = {}  # 提前初始化, 避免睡眠回放崩溃
        self._priority_nodes.update({
            "experimental_design", "hypothesis_testing", "validation_framework",
            "scientific_method", "experiment", "measurement", "data_analysis",
            "contradiction", "resolution", "hypothesis_generation",
        })

        # 惰性属性提前初始化 (避免breathe中hasattr检查)
        self._known_paths: set = set()
        self._global_marked: set = set()
        self._hot_hubs: set = set()
        self._breakthrough_pairs: set = set()
        self._dopa_cohort: dict = {}
        self._contradiction_nodes: set = set()
        self._path_rates: list = []
        self._peak_rate: int = 0
        self._last_research_gen: int = 0
        self._research_count: int = 0
        self._teacher_overlap_count: int = 0  # 教师轨迹匹配计数
        self._edge_history: list = []
        self._composed_total: int = 0
        self._sleep_pressure: float = 0.0
        self._blocked_backup: dict = {}
        self._sensory_cache: dict = {}  # (start, end, path_sig) → {result, timestamp}

        self.ACTIVE_POOL = max(5000, self._carrying_capacity // 2)
        self._intervene_stats = {"confirmed": 0, "refuted": 0, "tested": 0}
        # 加载外部设定目标
        import os as _go2
        gf = _go2.path.join(_go2.path.dirname(__file__), "..", "data", "active_goals.json")
        if _go2.path.exists(gf):
            import json as _gj2
            goals = _gj2.load(open(gf))
            for concept, info in goals.items():
                reason = info if isinstance(info, str) else info.get("reason", "") if isinstance(info, dict) else ""
                self.set_goal(concept, reason)
        self._feed_count = 0

        # ☁️ 统一云架构
        self._cell_shelf: dict = {}          # {node: [seed_dict, ...]} 磁盘基因组库
        self._walk_buffer: list = []          # [(walk, generation), ...] 待消化走步
        self._activity_history: dict = {}     # {id(cell): [gen_bits]} 最近活性跟踪
        self.WALK_DIGEST_WINDOW = 50          # 走步保留代数
        self.MEMORY_CELL_CAP = 20000          # 内存软上限
        self.ACTIVITY_FLOOR = 0.05            # 活性低于此值 → 沉淀
        self._load_cell_shelf()

        self._global_walk_memory: List[List] = []
        self._load_walk_memory()

        self._seed()
        if self._global_walk_memory:
            self._distribute_walk_memory()
        self._print_context_summary()  # 重启时告诉用户脑之前在做什么

    # ═══════ 图特征 ═══════

    def _neighbors_of(self, node_id: str) -> set:
        """返回节点的所有邻居 (effects ∪ causes)"""
        nd = self.graph.get(node_id, {})
        return ({dst for _, dst, _ in nd.get("effects", [])} |
                {src for src, _, _ in nd.get("causes", [])})

    def _ensure_node(self, node_id: str):
        """确保节点存在于图中。拒绝明显噪音节点。"""
        # 质量门: 拒绝垃圾节点名
        if not node_id:
            return
        # 多冒号拼接
        if node_id.count(':') > 1:
            return
        # 超长名
        if len(node_id) > 40:
            return
        # 含箭头 (→) — LLM 拼接特征
        if '→' in node_id or '->' in node_id or '__' in node_id:
            return
        # 含下划线过多 → 碎片拼接 (如 remnant_black_hole_mass_disorder)
        if node_id.count('_') > 3:
            return
        self.graph.setdefault(node_id, {"causes": [], "effects": []})

    def _valid_edge(self, domain: str) -> bool:
        """边域白名单: 只有证明过的域能进入因果图"""
        return domain in self.VALID_EDGE_DOMAINS

    # ═══════ 假设节点 (hyp-node) — 元认知前提 ═══════
    HYPNODE_PREFIX = "hyp:"

    def _ensure_hyp_node(self, src: str, dst: str) -> str:
        """为 t3 假说创建假设节点。已存在则返回现有名。"""
        # 防止递归: hyp 节点不作为 hyp-node 的源或目标
        if src.startswith(self.HYPNODE_PREFIX) or dst.startswith(self.HYPNODE_PREFIX):
            return ""
        name = f"{self.HYPNODE_PREFIX}{src}:{dst}"
        if name in self.graph:
            return name
        self._ensure_node(src)
        self._ensure_node(dst)
        self._ensure_node(name)
        # hyp ↔ src: 假说预测源
        self.graph[name].setdefault('effects', []).append(
            ('self_models', src, 'hypothesis'))
        self.graph[src].setdefault('causes', []).append(
            (name, 'self_models', 'hypothesis'))
        # hyp ↔ dst: 假说预测目标
        self.graph[name].setdefault('effects', []).append(
            ('self_models', dst, 'hypothesis'))
        self.graph[dst].setdefault('causes', []).append(
            (name, 'self_models', 'hypothesis'))
        # 基线可见度: hyp 节点在 coincidence 中有初始存在感
        self._coincidence[(name, src)] = self._coincidence.get((name, src), 0) + 3
        self._coincidence[(src, name)] = self._coincidence.get((src, name), 0) + 3
        self._coincidence[(name, dst)] = self._coincidence.get((name, dst), 0) + 3
        self._coincidence[(dst, name)] = self._coincidence.get((dst, name), 0) + 3
        return name

    def _sync_hyp_nodes(self):
        """扫描 t3 边，为缺失 + 目标相关的创建假设节点 (每 10 代)"""
        if self.generation % 10 != 0:
            return
        goal_words = set()
        for g in self._active_goals:
            goal_words.update(g.replace('_', ' ').split())
        created = 0
        for key, tier in list(self.synapse.tiers.items()):
            if tier != 3:
                continue
            src, dst = key
            # 防止 hyp 节点递归: hyp 节点间的边不再生成新 hyp 节点
            if src.startswith(self.HYPNODE_PREFIX) or dst.startswith(self.HYPNODE_PREFIX):
                continue
            name = f"{self.HYPNODE_PREFIX}{src}:{dst}"
            if name in self.graph:
                continue
            # 只建跟目标有足够重叠的: 至少 2 个不同目标词 (过滤 loss/method 等泛词)
            node_words = set(src.replace('_', ' ').split()) | set(dst.replace('_', ' ').split())
            overlap = node_words & goal_words
            if len(overlap) < 2:
                continue
            self._ensure_hyp_node(src, dst)
            self._track_focus_hypothesis(name)
            created += 1
        if created:
            print(f"  [HYP] +{created} hyp-nodes (gen {self.generation})")

    @staticmethod
    def _walk_value(walk: list) -> int:
        """路径价值: 长度 + 跨域数×2"""
        domains = set(s[3] for s in walk if len(s) >= 4)
        return len(walk) + len(domains) * 2

    def _save_critical_state(self):
        """批量保存所有关键状态 (内存压力时调用)"""
        self._save_coincidence()
        self._save_walk_memory()
        self._save_emergent_edges()
        self._save_known_paths()
        self._save_contradictions()

    # ═══════ 长期记忆 ═══════

    def _data_path(self, filename: str) -> str:
        return os.path.join(os.path.dirname(__file__), "..", "data", filename)

    def _load_json(self, filename: str, default=None):
        path = self._data_path(filename)
        if os.path.exists(path):
            try:
                with open(path) as f:
                    return json.load(f)
            except Exception:
                pass
        return default if default is not None else []

    def _save_json(self, filename: str, data):
        try:
            with open(self._data_path(filename), 'w') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _record_experiment(self, src: str, dst: str, method: str, result: str, confidence: float):
        """记录实验: 脑自己做的因果方向验证"""
        self._experiments = getattr(self, '_experiments', None)
        if self._experiments is None:
            self._experiments = self._load_json("experiments.json")
        entry = {
            "gen": self.generation,
            "hypothesis": f"{src} -> {dst}",
            "method": method,
            "result": result,
            "confidence": round(confidence, 2),
        }
        self._experiments.append(entry)
        self._save_json("experiments.json", self._experiments)

    def _is_falsified(self, src: str, dst: str) -> bool:
        """检查假说是否已被证伪"""
        self._falsified = getattr(self, '_falsified', None)
        if self._falsified is None:
            self._falsified = self._load_json("falsified.json")
        key = f"{src}->{dst}"
        for entry in self._falsified:
            if entry.get("hypothesis") == key:
                if self.generation - entry.get("gen", 0) < 5000:
                    return True  # 5000代冷却期内跳过
        return False

    def _record_falsified(self, src: str, dst: str, reason: str):
        """记录被实验证伪的假说"""
        self._falsified = getattr(self, '_falsified', None)
        if self._falsified is None:
            self._falsified = self._load_json("falsified.json")
        entry = {
            "gen": self.generation,
            "hypothesis": f"{src}->{dst}",
            "reason": reason,
        }
        self._falsified.append(entry)
        self._save_json("falsified.json", self._falsified)

    def _record_discovery(self, law_name: str, source: str, evidence: str):
        """记录脑自主发现的规律 (与手工注入区分)"""
        self._discoveries = getattr(self, '_discoveries', None)
        if self._discoveries is None:
            self._discoveries = self._load_json("discoveries.json")
        entry = {
            "gen": self.generation,
            "law": law_name,
            "source": source,  # "autonomous" | "injected"
            "evidence": evidence,
        }
        self._discoveries.append(entry)
        self._save_json("discoveries.json", self._discoveries)

    def _print_context_summary(self):
        """重启时打印: 脑之前在做什么"""
        lines = []
        if self._active_goals:
            top = list(self._active_goals.keys())[:3]
            lines.append(f"目标: {', '.join(top)}")
        if self._resolved_nodes:
            lines.append(f"已解决: {len(self._resolved_nodes)}个矛盾")
        if self._contradiction_nodes:
            lines.append(f"待解决: {len(self._contradiction_nodes)}个矛盾")
        exp = self._load_json("experiments.json")
        if exp:
            recent = [e for e in exp[-5:] if e.get("gen", 0) > self.generation - 2000]
            if recent:
                lines.append(f"近期实验: {len(recent)}个")
        disc = self._load_json("discoveries.json")
        if disc:
            auto = [d for d in disc if d.get("source") == "autonomous"]
            if auto:
                latest = auto[-1]
                lines.append(f"自主发现: {latest['law']} (gen {latest['gen']})")
        if lines:
            print(f"  [CONTEXT] {' | '.join(lines)}")

    def _build_graph_features(self):
        """构建图特征 (反向边, 深度, 2-hop 环) — 只遍历缓存节点"""
        self._reverse_edges = set()
        for src in list(self.graph._cache.keys()):
            node = self.graph._cache[src]
            for _, dst, _ in node.get("effects", []):
                dst_node = self.graph._cache.get(dst, {})
                for _, back, _ in dst_node.get("effects", []):
                    if back == src:
                        self._reverse_edges.add((src, dst))

        from collections import deque
        cache_keys = list(self.graph._cache.keys())
        root = "action" if "action" in self.graph._cache else (cache_keys[0] if cache_keys else "action")
        self._depths = {root: 0}
        q = deque([root])
        while q:
            n = q.popleft()
            n_node = self.graph._cache.get(n, {})
            for _, nb, _ in n_node.get("effects", []):
                if nb not in self._depths and nb in self.graph._cache:
                    self._depths[nb] = self._depths[n] + 1
                    q.append(nb)

        self._in_2hop_loop = set()
        for src in self.graph._cache:
            src_node = self.graph._cache[src]
            for _, mid, _ in src_node.get("effects", []):
                mid_node = self.graph._cache.get(mid, {})
                for _, dst, _ in mid_node.get("effects", []):
                    if dst == src:
                        self._in_2hop_loop.add((src, mid))

    def _path_structure_bonus(self, walk) -> float:
        if not walk or len(walk) < 2:
            return 0.0
        bonus = 0.0
        domains_seen = set()
        for i, step in enumerate(walk):
            src, law, dst = step[0], step[1], step[2]
            if (src, dst) in self._reverse_edges:
                bonus += 0.3
            if (src, dst) in self._in_2hop_loop:
                bonus += 0.5
            d_src = self._depths.get(src, -1)
            d_dst = self._depths.get(dst, -1)
            if d_src >= 0 and d_dst >= 0:
                diff = abs(d_dst - d_src)
                if diff >= 3:
                    bonus += 0.3
                elif diff >= 2:
                    bonus += 0.15
            if len(step) >= 4:
                domains_seen.add(step[3])
        if len(domains_seen) >= 3:
            bonus += 0.2 * (len(domains_seen) - 1)
        elif len(domains_seen) >= 2:
            bonus += 0.1
        return round(bonus, 1)

    def _eval_hierarchy(self, walk, is_new_path: bool) -> dict:
        """层级预测编码: 深度方向决定信号类型

        自上而下 (深→浅): 预测 — 高层告诉低层"应该发生什么"
        自下而上 (浅→深): 误差 — 低层告诉高层"实际发生了什么"

        不给结构，只给信号。方向由_reward驱动自然分化。
        """
        if len(walk) < 2:
            return {"hier_pred_bonus": 0, "hier_error_drive": 0}
        up_steps = 0    # 浅→深 (误差)
        down_steps = 0  # 深→浅 (预测)
        for step in walk:
            if len(step) < 3:
                continue
            sd = self._depths.get(step[0], -1)
            dd = self._depths.get(step[2], -1)
            if sd >= 0 and dd >= 0:
                if dd > sd:   up_steps += 1
                elif dd < sd: down_steps += 1
        total = up_steps + down_steps
        if total == 0:
            return {"hier_pred_bonus": 0, "hier_error_drive": 0}
        pred_ratio = down_steps / total
        if is_new_path:
            if up_steps > down_steps:
                # 自下而上新路 = 发现异常 → 强好奇
                return {"hier_pred_bonus": 0, "hier_error_drive": 0.5}
            elif down_steps > up_steps:
                # 自上而下新路 = 新预测假说 → 建模激励
                return {"hier_pred_bonus": 0.3, "hier_error_drive": 0}
        else:
            if down_steps > up_steps:
                # 自上而下已知路 = 预测准确 → 主reward
                return {"hier_pred_bonus": pred_ratio * 0.6, "hier_error_drive": 0}
            elif up_steps > down_steps:
                # 自下而上已知路 = 常规反馈 → 正常
                return {"hier_pred_bonus": 0, "hier_error_drive": 0}
        return {"hier_pred_bonus": 0, "hier_error_drive": 0}
    def _seed(self):
        candidates = []
        for node_id, node in self.graph._cache.items():
            in_d = len(node["causes"])
            out_d = len(node["effects"])
            is_conserved = node_id in {"energy", "momentum", "charge", "angular_momentum"}
            has_sym = any(any(kw in c[0].lower()
                             for kw in ("symmetry", "gauge", "noether"))
                          for c in node["causes"])
            score = 1.0
            if in_d == 0: score += 2
            if out_d == 0: score += 2
            if is_conserved and in_d > 0 and not has_sym: score += 3
            if score > 1.0:
                candidates.append((node_id, score))
        candidates.sort(key=lambda x: -x[1])
        for node_id, _ in candidates[:50]:
            cell = EvolvableCell(node_id, self.graph, self.board,
                                min_split_reward=self.MIN_SPLIT_REWARD)
            self.cells.append(cell)

    # ═══════ 细胞分页 ═══════

    def _merge_cold_cells_on_startup(self):
        """一次性: 加载冷池细胞并并入活跃池, 然后删除冷池文件。
        云架构: 没有冷热之分, 所有神经元都在一张图上。"""
        path = os.path.join(os.path.dirname(__file__), "..", "data", "cold_cells.json")
        if not os.path.exists(path):
            return 0
        try:
            with open(path) as f:
                data = json.load(f)
            nodes = data.get('nodes', {}) if isinstance(data, dict) else {}
            from meta_cognition.evolvable_cell import EvolvableCell
            merged = 0
            for node_name, cell_dicts in nodes.items():
                for cd in cell_dicts:
                    if not isinstance(cd, dict):
                        continue
                    # 过滤多冒号垃圾
                    if cd.get('node', '').count(':') > 1:
                        continue
                    cell = EvolvableCell(cd.get('node', node_name), self.graph,
                                        self.board, min_split_reward=self.MIN_SPLIT_REWARD)
                    cell.genome = cd.get('genome', {})
                    cell.last_action = cd.get('last_action', 'step_forward')
                    cell.age = cd.get('age', 0)
                    cell.total_reward = cd.get('total_reward', 0)
                    cell.walk_memory = [list(w) for w in cd.get('walk_memory', [])]
                    self.cells.append(cell)
                    merged += 1
            os.rename(path, path + '.merged')
            print(f"☁️ 冷池并入: {merged} 细胞 → 统一云")
            return merged
        except Exception:
            return 0

    # ═══════ ☁️ 磁盘种子库 ═══════

    def _shelf_path(self):
        return os.path.join(os.path.dirname(__file__), "..", "data", "cell_shelf.json")

    def _load_cell_shelf(self):
        path = self._shelf_path()
        if os.path.exists(path):
            try:
                with open(path) as f:
                    self._cell_shelf = json.load(f)
            except Exception:
                self._cell_shelf = {}

    def _save_cell_shelf(self):
        try:
            with open(self._shelf_path(), 'w') as f:
                json.dump(self._cell_shelf, f, ensure_ascii=False)
        except Exception:
            pass

    # ═══════ ☁️ 活性分数 & 人口管理 ═══════

    def _cell_activity(self, cell) -> float:
        """活性分数 = reward × 图度 × 近10代walk率"""
        nd = self.graph.get(cell.node, {})
        degree = len(nd.get("causes", [])) + len(nd.get("effects", []))
        recent_walks = self._activity_history.get(id(cell), [])[-10:]
        walk_rate = sum(recent_walks) / max(len(recent_walks), 1)
        return max(0.001, cell.total_reward * max(1, degree) * walk_rate)

    def _precipitate_cells(self):
        """沉淀: 低活性细胞 → 磁盘种子库, 释放内存"""
        if len(self.cells) <= self.MEMORY_CELL_CAP:
            return
        scores = [(self._cell_activity(c), c) for c in self.cells]
        scores.sort(key=lambda x: x[0])
        count = int(len(self.cells) * self.ACTIVITY_FLOOR * 2)
        count = min(count, len(self.cells) // 4)
        if count == 0:
            return
        precipitate = scores[:count]
        shelf_writes = 0
        for _, cell in precipitate:
            seed = cell.to_seed()
            self._cell_shelf.setdefault(cell.node, []).append(seed)
            shelf_writes += 1
        self.cells = [s[1] for s in scores[count:]]
        self._save_cell_shelf()
        if shelf_writes:
            print(f"  ☁️ 沉淀: -{shelf_writes} → 磁盘 (内存:{len(self.cells)})")

    def _incubate_cells(self):
        """孵化: 热点概念从磁盘拉回基因组孵化细胞"""
        hot = (getattr(self, '_hot_hubs', set()) | self._priority_nodes |
               {cell.node for cell in self.cells[:20] if cell.total_reward > 50})
        headroom = max(0, self.MEMORY_CELL_CAP - len(self.cells))
        if headroom <= 0 or not hot:
            return
        from meta_cognition.evolvable_cell import EvolvableCell
        incubated = 0
        for concept in hot:
            if concept not in self._cell_shelf or incubated >= headroom // 2:
                continue
            seeds = self._cell_shelf[concept]
            if not seeds:
                continue
            batch = min(5, len(seeds), headroom - incubated)
            for _ in range(batch):
                if not seeds:
                    break
                seed = seeds.pop(0)
                cell = EvolvableCell.from_seed(seed, self.graph, self.board,
                                               min_split_reward=self.MIN_SPLIT_REWARD)
                self.cells.append(cell)
                incubated += 1
            if not seeds:
                del self._cell_shelf[concept]
        if incubated:
            self._save_cell_shelf()
            print(f"  ☁️ 孵化: +{incubated} 细胞 ← 磁盘 (内存:{len(self.cells)})")

    # ═══════ ☁️ walk 消化 ═══════

    def _digest_walk_buffer(self):
        """睡眠时消化超过窗口期的 walk_memory → 突触层"""
        if not self._walk_buffer:
            return
        cutoff = self.generation - self.WALK_DIGEST_WINDOW
        to_digest = []
        keep = []
        for walk, gen in self._walk_buffer:
            if gen < cutoff:
                to_digest.append(walk)
            else:
                keep.append((walk, gen))
        self._walk_buffer = keep
        for walk in to_digest:
            for step in walk:
                if len(step) >= 3:
                    self.synapse.strengthen(0, step[0], step[2], 0.1, self.generation)
        if to_digest:
            print(f"  ☁️ 消化: {len(to_digest)} walks → 突触")


    def set_goal(self, concept: str, reason: str = ""):
        """外部设置研究目标 — 安全版: 不直接修改 cells/cold_cells
        将唤醒请求排队，在下一轮 breathe 开始时处理。"""
        if concept not in self.graph:
            self._ensure_node(concept)
        self._active_goals[concept] = {"set_gen": self.generation, "neurons": 0, "reason": reason, "progress": 0}
        # 排队: 延迟到安全点处理
        if not hasattr(self, '_pending_goal_wakes'):
            self._pending_goal_wakes = []
        self._pending_goal_wakes.append(concept)

    def _process_pending_goals(self):
        """安全处理排队的 goal 请求 — 云架构: 直接在活跃池创建新细胞"""
        if not getattr(self, '_pending_goal_wakes', None):
            return
        from meta_cognition.evolvable_cell import EvolvableCell
        for concept in self._pending_goal_wakes:
            woken = 0
            # 云架构: 为目标概念创建探索细胞
            for _ in range(min(5, max(0, self.ACTIVE_POOL - len(self.cells)))):
                cell = EvolvableCell(concept, self.graph, self.board,
                                    min_split_reward=self.MIN_SPLIT_REWARD)
                cell.goal = concept
                self.cells.append(cell)
                woken += 1
            if woken:
                print(f"[GOAL] {concept} -> {woken} neurons with goal")
        self._pending_goal_wakes = []

    # ═══════ 呼吸子模块 ═══════

    def _step_neurons(self, stats: dict) -> list:
        """1. 神经元行动 + 繁殖 — 云架构: 薄云自然休眠, 热点高频
        ⚡ 优化: 合并遍历 (衰减+walk缓冲+total_walks 一次循环), 活性中位数惰性求值"""
        children = []
        METABOLIC_TAX = 0.05
        REWARD_DECAY = 0.88

        # ⚡ 活性中位数: 每3代计算一次 (惰性求值)
        if not hasattr(self, '_cached_median_score') or self.generation % 3 == 0:
            if self.cells:
                all_scores = [self._cell_activity(c) for c in self.cells]
                self._cached_median_score = sorted(all_scores)[len(all_scores)//2]
            else:
                self._cached_median_score = 1.0
        median_score = self._cached_median_score

        # 🧠 突触补路: 预建每个节点的 top-5 高 s 突触边
        from collections import defaultdict
        syn_out = defaultdict(list)
        for (src, dst), edge in self.synapse.activations.items():
            s_val = edge.get('s', 0) if isinstance(edge, dict) else 0
            if s_val > 0.001:  # 极低阈值, 让混沌脑边可见
                syn_out[src].append((dst, s_val))
        for src in syn_out:
            syn_out[src].sort(key=lambda x: -x[1])
            syn_out[src] = syn_out[src][:5]
        self._syn_out = dict(syn_out)
        # 🧠 髓鞘快车道: unique_neurons >= 50 的边跳过 EIG
        self._myelin_set = set(
            key for key, act in self.synapse.activations.items()
            if isinstance(act, dict) and act.get('unique_neurons', 0) >= 50
        )

        # 🧠 全局多巴胺浪涌: 🧩 变化 → 全脑 curiosity boost (持续20代)
        composed_now = getattr(self, '_composed_total', 0)
        last_peak = getattr(self, '_dopamine_last_composed', composed_now)
        if not hasattr(self, '_dopamine_last_composed'):
            self._dopamine_last_composed = composed_now
            self._dopamine_boost = 1.0
            self._dopamine_until = 0
        if composed_now > last_peak:
            self._dopamine_boost = 1.5  # 发现新结构 → 全脑兴奋
            self._dopamine_until = self.generation + 20
            self._dopamine_last_composed = composed_now
        elif self.generation > self._dopamine_until and self._dopamine_boost > 1.0:
            # 20代无新发现 → 慢慢消退
            self._dopamine_boost = max(1.0, self._dopamine_boost - 0.03)
        if not hasattr(self, '_dopamine_boost'):
            self._dopamine_boost = 1.0

        # 本体觉: 每10代刷新气味场, 注入细胞感知
        self.proprioception.maybe_update(self)
        self._proprio_field = self.proprioception.field

        # ⚡ 合并遍历: 代谢+衰减+act+walk缓冲+total_walks 一次循环
        _total_walks = 0
        for i, cell in enumerate(self.cells):
            # 代谢税: 活着就要耗能
            cell.total_reward -= METABOLIC_TAX
            if cell.total_reward < 0:
                cell.total_reward = 0
            cell.apply_decay()
            cell.age += 1

            # ⚡ 奖励衰减 (原独立遍历, 现合并)
            cell.total_reward *= REWARD_DECAY

            # 振荡节律
            if self._dopa_cohort and id(cell) in self._dopa_cohort:
                cohort_gen = self._dopa_cohort[id(cell)]
                if self.generation - cohort_gen <= 30:
                    cell._osc_boost = 2.0
                else:
                    del self._dopa_cohort[id(cell)]
            # 好奇绑定矛盾
            if self._contradiction_nodes:
                if not hasattr(cell, "_last_contradiction_visit"):
                    cell._last_contradiction_visit = 0
                if cell.node in self._contradiction_nodes:
                    cell._last_contradiction_visit = self.generation
                elif self.generation - cell._last_contradiction_visit > 200:
                    cur = cell.genome.get("curiosity", 1.0)
                    cell.genome["curiosity"] = min(3.0, cur * 2.0)

            # ☁️ 薄云休眠: 低于中位数活性的细胞概率跳过
            score = self._cell_activity(cell)
            walk_chance = min(1.0, score / max(median_score, 0.001))
            did_walk = False
            if random.random() < walk_chance or self.generation % 10 == 0:
                # 🛤️ 突触补路 + 髓鞘快车道 + 多巴胺
                cell._synapse_fallback = self._syn_out.get(cell.node, [])
                cell._myelin = self._myelin_set
                cell._dopamine = self._dopamine_boost
                cell._density_pressure = max(0.15, 1500.0 / max(len(self.cells), 10))
                # 清理过期刺激
                if hasattr(cell, '_stimulus_until') and self.generation > cell._stimulus_until:
                    cell._stimulus = 1.0
                result = cell.act()
                cell._last_result = result
                self.total_actions += 1
                did_walk = result["type"] != "rest"
                if result["type"] == "split" and "child" in result:
                    children.append(result["child"])
                    stats["births"] += 1
                # 🧠 私有轴突强化: mark时把自己的路径写入突触
                if result["type"] in ("mark", "step_forward") and result.get("axon"):
                    axon_target = result["axon"]
                    if axon_target:
                        self.synapse.retrograde_signal(axon_target, 
                            valence=result.get("axon_strength", 1.0))

            # ☁️ 追踪活性历史
            history = self._activity_history.setdefault(id(cell), [])
            history.append(1 if did_walk else 0)
            if len(history) > 10:
                history.pop(0)

            # ⚡ walk_memory 缓冲 + total_walks (原独立遍历, 现合并)
            wm = getattr(cell, 'walk_memory', [])
            if wm:
                _total_walks += len(wm)
                for walk in wm[-2:]:  # 最近2条
                    if len(walk) >= 2:
                        self._walk_buffer.append((list(walk), self.generation))

        self._cached_total_walks = _total_walks

        # 添加孩子
        for child in children:
            self.cells.append(child)
        return children

    def _wire_newborn_synapses(self, children: list):
        """3. 新生儿随机探针突触 (从可信节点采样, 避免垃圾token)"""
        EDGES_PER_BIRTH = 10
        for child in children:
            # 🧹 断噪音源: 只从有 VALID 域边的节点中采样 (过滤垃圾token)
            valid_nodes = []
            for n, nd in self.graph._cache.items():
                for _, _, domain in nd.get("effects", []):
                    if domain in self.VALID_EDGE_DOMAINS:
                        valid_nodes.append(n)
                        break
            if len(valid_nodes) < EDGES_PER_BIRTH:
                valid_nodes = list(self.graph.keys())
            targets = random.sample(valid_nodes, min(EDGES_PER_BIRTH, len(valid_nodes)))
            for dst in targets:
                if dst == child.node:
                    continue
                existing = any(e[1] == dst for e in self.graph.get(child.node, {}).get("effects", []))
                existing |= any(e[1] == child.node for e in self.graph.get(dst, {}).get("effects", []))
                if existing:
                    continue
                self._ensure_node(child.node)
                self._ensure_node(dst)
                self.graph.add_edge(child.node, dst, "hebbian_shortcut", "probe")
                self._probe_edges[(child.node, dst)] = self.generation

    def _apply_deaths(self, stats: dict, K: int):
        """密度死亡 + 饥饿死亡 — 纯渐进, 无硬砍"""
        pop = len(self.cells)
        density = pop / max(K, 1)
        # 渐进密度死亡: K_HALF 以下不杀, 3x K 时达到 MAX_RATE (之前5x太温柔)
        if density > self.DENSITY_DEATH_K_HALF:
            frac_over = min(1.0, (density - self.DENSITY_DEATH_K_HALF) / (3.0 - self.DENSITY_DEATH_K_HALF))
            death_rate = self.DENSITY_DEATH_MAX_RATE * frac_over
            ranked = sorted(self.cells, key=lambda c: c.total_reward)
            rank_of = {id(c): i / max(len(ranked) - 1, 1) for i, c in enumerate(ranked)}
            survivors = []
            for cell in self.cells:
                rank_frac = rank_of.get(id(cell), 1.0)
                if random.random() < 1.0 - death_rate * (1.0 - rank_frac):
                    survivors.append(cell)
                else:
                    stats["density_deaths"] += 1
                    stats["deaths"] += 1
            self.cells = survivors
        # 饥饿死亡
        pop = len(self.cells)
        if pop > 50:
            cutoff = max(1, int(pop * self.STARVATION_PERCENTILE))
            ranked = sorted(self.cells, key=lambda c: c.total_reward)
            bottom = set(id(c) for c in ranked[:cutoff])
            survivors = []
            for cell in self.cells:
                if id(cell) in bottom and random.random() < self.STARVATION_DEATH_RATE:
                    stats["starvation_deaths"] += 1
                    stats["deaths"] += 1
                else:
                    survivors.append(cell)
            self.cells = survivors

    def _build_neighbor_cache(self):
        """5. 邻居缓存 — ⚡ 单次遍历 (list引用传递, 后续append自动可见)"""
        by_node = defaultdict(list)
        for cell in self.cells:
            by_node[cell.node].append(cell)
            cell._neighbors_cache = by_node[cell.node]

    # ═══════ 呼吸主循环 ═══════

    def breathe(self, steps: int = 1) -> Dict:
        from meta_cognition.synaptic_layer import neuron_fire_on_path
        stats = {"deaths": 0, "births": 0, "rewards": 0, "actions": 0,
                 "density_deaths": 0, "starvation_deaths": 0}
        # 每块更新突触层上下文 (动态阈值 + 节点存在性检查)
        self.synapse.update_context(len(self.cells), self.graph)
        for _ in range(steps):
            self.generation += 1
            # 📡 感官输入: 消费 feed_queue.jsonl (统一外部输入管道)
            self.feed_queue.consume_all(self)
            # ☁️ 独立睡眠 — 每代触发, 在最前面谁也别想挡
            # ⚡ total_walks 已由 _step_neurons 缓存, 不再单独遍历
            total_walks = getattr(self, '_cached_total_walks', 0)
            self._sleep_pressure += total_walks * 0.0015
            if self.generation % 5 == 0:
                print(f"  [ZZZ] pressure={self._sleep_pressure:.1f} walks={total_walks}")
            if self._sleep_pressure > 0.3:
                print(f"  [SLEEP-TRIGGER] pressure={self._sleep_pressure:.1f} gen={self.generation}", flush=True)
                try:
                    self._sleep_replay()
                except Exception as e:
                    print(f"  [SLEEP-ERR] {e}")
                    import traceback
                    traceback.print_exc()
                self._sleep_pressure = 0.0
            self._process_pending_goals()
            K = self._carrying_capacity
            if self.generation - self._last_mem_check >= 100:
                self._check_memory_pressure()  # 重IO: /proc读取 + 保存
                self._last_mem_check = self.generation
            self._homeostasis()  # 每代执行: K + 死亡速率闭环调节

            # 1. 行动 + 繁殖
            children = self._step_neurons(stats)
            # 2. 新生儿突触
            self._wire_newborn_synapses(children)
            # 3. 死亡
            try:
                self._apply_deaths(stats, K)
            except Exception as e:
                print(f"  [DIE-ERR] _apply_deaths: {e}", flush=True)
            # 4. 邻居缓存
            self._build_neighbor_cache()

            # 5. 奖励分配
            signals = self.board.detect_resonance()
            # 重置感官预算
            self._probe_budget_counter = 5
            
            total_cells = len(self.cells)
            for ci, cell in enumerate(self.cells):
                if ci > 0 and ci % 500 == 0:
                    print(f"     [breathe] {ci}/{total_cells} cells, gen {self.generation}", flush=True)
                rewarded = False

                if cell.last_action == "mark":
                    walk = cell.current_walk
                    if len(walk) >= 2:
                        path_key = "->".join(w[2] for w in walk)
                        chem = chemistry.eval_mark(walk, path_key, self._known_paths,
                                                   self._hot_hubs, self._coincidence)
                        base_dopa = chem["dopamine"]
                        novelty_mult = chem["novelty_mult"]
                        is_new_path = novelty_mult == chemistry.p.DOPAMINE_NOVELTY_NEW

                        if base_dopa > 0:
                            multiplier = 1.0
                            if is_new_path:
                                self._known_paths.add(path_key)
                                # 自由能: 新路径=预测落空, 化学层已给低reward(0.3x)
                                # 首次注册给建模激励 (不是dopamine渠道)
                                reg_bonus = chem.get("registration_bonus", 0)
                                if reg_bonus:
                                    cell.receive_reward(reg_bonus)
                                    self.total_rewards += reg_bonus
                            walk_nodes = {step[2] for step in walk} | {walk[0][0]}
                            if len(walk_nodes & self._resolved_nodes) >= 1:
                                multiplier *= 1.3  # 走到解决处→意义
                            # 方法论: 走过实验/验证/假说节点 → 额外奖励 (老师教的)
                            if walk_nodes & self.METHODOLOGY_NODES:
                                multiplier *= 1.4
                            struct = self._path_structure_bonus(walk)
                            if struct > 0.3:
                                multiplier *= 1.15
                            # 本体觉调制: emergent 密度 + 桥接节点
                            if self._proprio_field:
                                smell = self.proprioception.smell(cell.node)
                                em_density = smell.get("_proprio_em_density", 0)
                                if em_density > 0.1:      # 高 emergent 区 → 多巴胺 boost
                                    multiplier *= 1.1
                                elif em_density < 0.01:   # 低密度区 → curiosity boost
                                    cur = cell.genome.get("curiosity", 1.0)
                                    cell.genome["curiosity"] = min(3.0, cur + 0.02)
                                if smell.get("_proprio_is_bridge"):  # 桥接节点 → 跨域奖励
                                    multiplier *= 1.15
                            final_dopa = base_dopa * multiplier
                            if chem.get("eureka"):
                                final_dopa += chemistry.p.EMOTION_EUPHORIA
                            cell.receive_reward(final_dopa)
                            self.total_rewards += final_dopa
                            stats["rewards"] += int(final_dopa)
                            rewarded = True
                        
                        surprise_drive = chem.get("surprise_drive", 0.0)
                        if surprise_drive > 0:
                            # 外部惊喜→注入内在好奇 (统一通道)
                            cell.intrinsic_curiosity = min(3.0, cell.intrinsic_curiosity + surprise_drive * 0.5)

                        # 预测质量驱动突触强化: 高reward走→边更重
                        neuron_fire_on_path(cell, self.synapse, self.generation,
                                           strength=min(2.0, final_dopa / max(1.0, base_dopa)))
                        # 标记走过的边为活跃 (修剪豁免)
                        for step in walk:
                            if len(step) >= 2:
                                self._edge_last_seen[(step[0], step[2])] = self.generation

                        # 🪞 教师轨迹重叠: 走老师走过的研究链 → 镜像学习快车道
                        self._apply_teacher_overlap_reward(cell, walk, self.generation)

                        # 🧠 认知增益: 跨域探索矛盾 → 科学家的多巴胺
                        if self._contradiction_nodes:
                            walk_domains = set()
                            for step in walk:
                                if len(step) >= 4:
                                    walk_domains.add(step[3])
                            walk_nodes_set = {step[2] for step in walk} | {walk[0][0]}
                            if len(walk_domains) >= 2 and (walk_nodes_set & self._contradiction_nodes):
                                coherence_gain = len(walk_domains) * 0.5
                                cell.receive_reward(coherence_gain)
                                self.total_rewards += coherence_gain

                        dest = walk[-1][2] if len(walk) >= 2 else None
                        if dest:
                            self.synapse.retrograde_signal(dest, valence=1.0)

                        # 📖 arXiv 书架: 细胞走完后瞥一眼
                        if walk and len(walk) >= 2:
                            cell_node = walk[-1][2] if len(walk[-1]) >= 3 else cell.node
                            self.arxiv_reading.cell_glance(cell_node, id(cell), colony=self)
                        
                        # 🧠 工作记忆编码: 走桥接节点 → 记入 buffer
                        if walk and len(walk) >= 2 and self._proprio_field:
                            walk_nodes = {step[2] for step in walk if len(step) >= 3} | {walk[0][0]}
                            smell = self.proprioception.smell(cell.node)
                            if smell.get("_proprio_is_bridge"):
                                dopamine = min(2.0, base_dopa) if base_dopa > 0 else 0.3
                                for node in walk_nodes:
                                    if self.proprioception.smell(node).get("_proprio_is_bridge"):
                                        if cell.wm.encode(node, dopamine):
                                            break  # 每轮最多记一个
                        
                        # 🧠 工作记忆命中: 走到 buffer 中已有的概念 → 奖励
                        if cell.wm.size() >= 2 and walk:
                            dest_node = walk[-1][2] if len(walk[-1]) >= 3 else walk[-1][0] if walk else None
                            if dest_node and cell.wm.contains(dest_node):
                                cell.receive_reward(0.5)
                                self.total_rewards += 0.5

                        # 🧩 形状共振: walk 指纹被黑板检测到 → 结构类比奖励
                        fp = walk_fingerprint(walk) if walk else ""
                        if fp:
                            for sig in signals:
                                if sig.get("location", "").startswith("fp:") and fp in sig.get("location", ""):
                                    if sig.get("cells_agreed", 0) >= 2:
                                        cell.receive_reward(0.3)
                                        self.total_rewards += 0.3
                                        break


                        # 🧠 自由能核心: 预测命中 = 模型正确 = 低自由能 = 主驱动reward
                        if len(walk) >= 2 and cell.walk_memory:
                            last_steps = tuple(w[2] for w in walk[-3:] if len(w) >= 3)
                            best_match = 0
                            for mem in cell.walk_memory[-10:]:
                                mem_steps = tuple(s[2] for s in mem if len(s) >= 3)
                                for i in range(len(mem_steps) - 1):
                                    if last_steps and mem_steps[i] == last_steps[0]:
                                        match = 1
                                        for k in range(1, min(len(last_steps), len(mem_steps)-i-1)):
                                            if last_steps[k] == mem_steps[i+k+1]:
                                                match += 1
                                            else:
                                                break
                                        best_match = max(best_match, match)
                            if best_match >= 1:
                                pred_reward = min(2.0, best_match * 0.5)  # 1步=0.5, 2步=1.0, 3步=1.5, 4+=2.0
                                cell.receive_reward(pred_reward)
                                self.total_rewards += pred_reward

                        # 语义签名: 节点向量向walk上下文均值滑移 (word2vec式涌现)
                        if len(walk) >= 2:
                            reward_scale = min(1.0, getattr(cell, 'total_reward', 0) * 0.1 + 0.2)
                            lr = self.SEMANTIC_LR * reward_scale
                            for idx, step in enumerate(walk):
                                node_id = step[2] if len(step) > 2 else step[0]
                                # 初始化向量
                                if node_id not in self._node_vecs:
                                    import random as _r
                                    self._node_vecs[node_id] = [
                                        _r.uniform(-0.1, 0.1) for _ in range(self.SEMANTIC_DIM)
                                    ]
                                # 收集邻居(前后各1步)
                                neighbors = []
                                if idx > 0:
                                    prev_step = walk[idx - 1]
                                    neighbors.append(prev_step[2] if len(prev_step) > 2 else prev_step[0])
                                    # 连带neighbor的向量也初始化
                                    nid = neighbors[-1]
                                    if nid not in self._node_vecs:
                                        import random as _r2
                                        self._node_vecs[nid] = [
                                            _r2.uniform(-0.1, 0.1) for _ in range(self.SEMANTIC_DIM)
                                        ]
                                if idx < len(walk) - 1:
                                    next_step = walk[idx + 1]
                                    neighbors.append(next_step[2] if len(next_step) > 2 else next_step[0])
                                    nid = neighbors[-1]
                                    if nid not in self._node_vecs:
                                        import random as _r3
                                        self._node_vecs[nid] = [
                                            _r3.uniform(-0.1, 0.1) for _ in range(self.SEMANTIC_DIM)
                                        ]
                                if not neighbors:
                                    continue
                                # 邻居均值
                                mean_vec = [0.0] * self.SEMANTIC_DIM
                                for nid in neighbors:
                                    nv = self._node_vecs.get(nid)
                                    if nv:
                                        for j in range(self.SEMANTIC_DIM):
                                            mean_vec[j] += nv[j]
                                for j in range(self.SEMANTIC_DIM):
                                    mean_vec[j] /= len(neighbors)
                                # 滑移: vec = vec + lr * (mean - vec)
                                cv = self._node_vecs[node_id]
                                for j in range(self.SEMANTIC_DIM):
                                    cv[j] += lr * (mean_vec[j] - cv[j])

                        saved = list(walk)
                        cell.walk_memory.append(saved)
                        if len(cell.walk_memory) > cell.MAX_WALK_MEMORY:
                            def walk_value(w):
                                length = len(w)
                                domains = set()
                                for step in w:
                                    if len(step) >= 4:
                                        domains.add(step[3])
                                return length + len(domains) * 2
                            cell.walk_memory.sort(key=walk_value, reverse=True)
                            cell.walk_memory = cell.walk_memory[:cell.MAX_WALK_MEMORY]

                        start_node = walk[0][0] if walk else None
                        same_origin = sum(1 for w in cell.walk_memory[:-1]
                                        if w and w[0][0] == start_node)
                        if same_origin > 0:
                            bonus = ChemistryParams.COMPOSE_ORIGIN_PER_SAME * same_origin
                            cell.receive_reward(bonus)
                            self.total_rewards += bonus
                            stats["rewards"] += int(bonus)

                        composed_count, composed = self._compose_paths(walk)
                        if composed_count > 0:
                            # 🔧 路径合成: 发现新因果链 → 生存能量 + 图边固化
                            cell.give_energy(composed_count * 2.0)
                            self.total_rewards += composed_count * 2.0
                            self._composed_total += composed_count
                            # 将合成的首尾边加入图 (其他细胞可见)
                            for cpath in composed:
                                parts = cpath.split("->")
                                if len(parts) >= 2:
                                    first, last = parts[0], parts[-1]
                                    if first == last:
                                        continue  # 自环, 跳过
                                    if first in self.graph and last in self.graph:
                                        exists = any(e[1] == last for e in self.graph[first].get("effects",[]))
                                        if not exists:
                                            self.graph[first].setdefault("effects",[]).append(
                                                ("composed_shortcut", last, "emergent"))
                                            self.graph[last].setdefault("causes",[]).append(
                                                (first, "composed_shortcut", "emergent"))
                                            # 🔧 发现的因果链自带初始 c=2 (两步组合=已验证)
                                            key = (first, last)
                                            if key not in self.synapse.activations:
                                                self.synapse.activations[key] = {
                                                    'n': set(), 'g': self.generation,
                                                    's': 0.30, 'c': 2
                                                }

                        subgraph = chem.get("subgraph", set())
                        deepen = chemistry.eval_deepen(cell, subgraph)
                        if deepen["deepen_bonus"] > 0:
                            cell.receive_reward(deepen["deepen_bonus"])
                            self.total_rewards += deepen["deepen_bonus"]
                        if deepen["mastery_bonus"] > 0:
                            cell.receive_reward(deepen["mastery_bonus"])
                            self.total_rewards += deepen["mastery_bonus"]

                        all_nodes = [walk[0][0]] + [step[2] for step in walk]
                        n = len(all_nodes)
                        seen_pairs = set()
                        for i in range(n):
                            for j in range(i + 1, n):
                                src_n, dst_n = all_nodes[i], all_nodes[j]
                                if src_n == dst_n:
                                    continue
                                pair = (src_n, dst_n)
                                if pair in seen_pairs:
                                    continue
                                seen_pairs.add(pair)
                                self._coincidence[pair] = self._coincidence.get(pair, 0) + 1
                                rev_pair = (dst_n, src_n)
                                if rev_pair in self._coincidence:
                                    self._coincidence[pair] = max(0, self._coincidence[pair] - 1)
                                    self._coincidence[rev_pair] = max(0, self._coincidence[rev_pair] - 1)

                        consensus = chemistry.eval_consensus(seen_pairs, self._coincidence,
                                                            self._breakthrough_pairs)
                        if consensus["consensus_bonus"] > 0:
                            cell.receive_reward(consensus["consensus_bonus"])
                            self.total_rewards += consensus["consensus_bonus"]
                        if consensus["breakthrough_bonus"] > 0:
                            cell.receive_reward(consensus["breakthrough_bonus"])
                            self.total_rewards += consensus["breakthrough_bonus"]

                        # 🔮 预测奖励: walk_memory 模式匹配 → 预期兑现
                        if len(walk) >= 3:
                            pred_bonus = 0.0
                            for mem_path in cell.walk_memory:
                                if len(mem_path) >= 3:
                                    # 检查最近3步是否匹配 mem_path 的前缀
                                    match = True
                                    for k in range(min(3, len(walk), len(mem_path))):
                                        if walk[-(3-k)][2] != mem_path[k][2]:
                                            match = False
                                            break
                                    if match and len(mem_path) > 3:
                                        # 预测: mem_path 的下一步应该是...
                                        predicted_dst = mem_path[3][2]
                                        actual_dst = walk[-1][2]
                                        if predicted_dst == actual_dst:
                                            pred_bonus += 0.5  # 预测对了
                                        else:
                                            pred_bonus += 0.2  # 预测错了但有模式在学
                            if pred_bonus > 0:
                                cell.receive_reward(min(pred_bonus, 2.0))
                                self.total_rewards += min(pred_bonus, 2.0)

                        # 🌉 桥接推理: 路径两端在已知路径中 → 你是连接者
                        endpoints_in_known = 0
                        for known_key in list(self._known_paths)[:2000]:
                            known_parts = known_key.split("->")
                            if len(known_parts) < 3:
                                continue
                            # 这个已知路径是否被当前 walk 桥接?
                            walk_str = "->".join(w[2] for w in walk)
                            # 当前 walk 包含 known_path 的起点和终点但中间不同
                            if walk_str.startswith(known_parts[0]) and walk_str.endswith(known_parts[-1]):
                                if known_key != walk_str and len(walk) > len(known_parts):
                                    endpoints_in_known += 1
                        if endpoints_in_known >= 2:
                            bridge_bonus = min(endpoints_in_known * 0.3, 2.0)
                            cell.receive_reward(bridge_bonus)
                            self.total_rewards += bridge_bonus

                        # 🧩 相似推理: 路径两端节点结构相似→类比价值
                        if len(walk) >= 2:
                            src_node = walk[0][0]
                            dst_node = walk[-1][2]
                            src_data = self.graph.get(src_node, {"causes":[],"effects":[]})
                            dst_data = self.graph.get(dst_node, {"causes":[],"effects":[]})
                            src_deg = (len(src_data["causes"]), len(src_data["effects"]))
                            dst_deg = (len(dst_data["causes"]), len(dst_data["effects"]))
                            # 出入度模式完全一致→结构相似
                            if src_deg == dst_deg and src_deg != (0,0):
                                similarity_bonus = 0.3
                                cell.receive_reward(similarity_bonus)
                                self.total_rewards += similarity_bonus

                        # ⚡ 对比推理: 反向coincidence活跃→互斥/对比关系
                        if len(walk) >= 2:
                            for i in range(len(walk)):
                                for j in range(i+1, len(walk)):
                                    a, b = walk[i][2], walk[j][2]
                                    rev = self._coincidence.get((b, a), 0)
                                    fwd = self._coincidence.get((a, b), 0)
                                    if rev > fwd * 3 and rev >= 5:  # 反向远多于正向
                                        contrast_bonus = 0.2
                                        cell.receive_reward(contrast_bonus)
                                        self.total_rewards += contrast_bonus
                                        break

                        # 🏛 层级预测编码: 深度方向决定信号类型
                        # 深→浅 (自上而下) = 预测, 奖励准确预测
                        # 浅→深 (自下而上) = 误差, 驱动好奇探索
                        hier = self._eval_hierarchy(walk, is_new_path)
                        if hier["hier_pred_bonus"] > 0:
                            cell.receive_reward(hier["hier_pred_bonus"])
                            self.total_rewards += hier["hier_pred_bonus"]
                        if hier["hier_error_drive"] > 0:
                            cur = cell.genome.get("curiosity", 1.0)
                            cell.genome["curiosity"] = min(3.0, cur + hier["hier_error_drive"])

                        # 🔗 类比: walk两端节点语义向量相似 → 跨域迁移 insight
                        if len(walk) >= 3:
                            v_src = self._node_vecs.get(walk[0][0])
                            v_dst = self._node_vecs.get(walk[-1][2])
                            if v_src and v_dst:
                                dot = sum(v_src[j]*v_dst[j] for j in range(self.SEMANTIC_DIM))
                                na = sum(v*v for v in v_src)**0.5
                                nb = sum(v*v for v in v_dst)**0.5
                                sim = dot / max(na*nb, 1e-10)
                                # 类比: 高向量相似 + 不同域
                                dom_a = {e[2] for e in self.graph.get(walk[0][0],{}).get("effects",[]) if len(e)>2}
                                dom_b = {e[2] for e in self.graph.get(walk[-1][2],{}).get("effects",[]) if len(e)>2}
                                if sim > 0.6 and dom_a and dom_b and dom_a != dom_b:
                                    analogy_bonus = (sim - 0.5) * 2.0
                                    cell.receive_reward(analogy_bonus)
                                    self.total_rewards += analogy_bonus

                        if len(walk) >= 6:
                            cell.current_walk = []

                # 🔬 反事实干预奖励: 尝试就奖 + 惊喜越大奖越多
                elif cell.last_action == "intervene":
                    # 基线: 选择干预这个行为本身值得奖励
                    cell.receive_reward(0.03)
                    cell.give_energy(0.15)   # 🔧 干预经费: 实验也需要经费
                    self.total_rewards += 0.18
                    stats["rewards"] += 1
                    rewarded = True
                    # 惊喜: 干预越意外 → 模型修正价值越大
                    result = getattr(cell, '_last_result', {})
                    if result.get("type") == "intervene":
                        effect = abs(result.get("effect", 0))
                        if effect > 0.01:
                            surprise_reward = effect * 5.0
                            cell.receive_reward(surprise_reward)
                            self.total_rewards += surprise_reward
                            stats["rewards"] += int(surprise_reward)
                            rewarded = True

                # 🔍 数值触觉: probe → LLM 定量分析 → 惊奇越大奖越多
                elif cell.last_action == "probe":
                    result = getattr(cell, '_last_result', {})
                    if result.get("type") == "probe" and result.get("start"):
                        # 基线: 选择探测行为本身值得奖励 (跟explore一样)
                        cell.receive_reward(0.15)
                        cell.give_energy(0.10)
                        self.total_rewards += 0.25
                        stats["rewards"] += 1
                        rewarded = True
                        # 预算控制: 每 breathe block 最多 5 次 LLM 探测
                        budget = getattr(self, '_probe_budget_counter', 5)
                        if budget > 0:
                            self._probe_budget_counter = budget - 1
                            surprise = self._handle_probe(cell, result)
                            if surprise > 0:
                                cell.receive_reward(surprise)
                                self.total_rewards += surprise
                                stats["rewards"] += int(surprise)

                # 📐 推导通道: derive → LLM 推理链 → 成功注入新边就大奖
                elif cell.last_action == "derive":
                    result = getattr(cell, '_last_result', {})
                    if result.get("type") == "derive" and result.get("start"):
                        # 基线: 推导尝试本身值得奖励
                        cell.receive_reward(0.15)
                        cell.give_energy(0.15)
                        self.total_rewards += 0.30
                        stats["rewards"] += 1
                        rewarded = True
                        # sympy 极快, 不限预算 — 给容量不给方法
                        edges_added = self._handle_derive(cell, result)
                        if edges_added > 0:
                            # 成功注入新因果边 → 大奖
                            derive_reward = edges_added * 1.5
                            cell.receive_reward(derive_reward)
                            self.total_rewards += derive_reward
                            stats["rewards"] += int(derive_reward)
                            # 广播: 所有在相关节点的神经元都能感知新知识
                            start = result.get("start", "")
                            end = result.get("end", "")
                            if start or end:
                                for c in self.cells:
                                    if c.node == start or c.node == end:
                                        c.give_energy(0.5)
                        else:
                            # 🧠 杏仁核: derive 失败 → 后向抑制通往此节点的边
                            self.synapse.retrograde_inhibit(cell.node)
                            cell.receive_reward(-0.1)

                # 🗺️ 探索奖励: 尝试就有奖 (好奇心本身就是 dopamine 源)
                elif cell.last_action == "step_forward":
                    # 基线: 选择探索这个行为本身值得奖励
                    cell.receive_reward(0.15)   # 🔧 探索多巴胺: 权重学习信号
                    # 🔧 基线能量跟 EIG 挂钩: 探索高信息方向 → 更多生存能量
                    result = getattr(cell, '_last_result', {})
                    dst = result.get("to")
                    eig = cell._expected_info_gain(dst) if dst and dst in self.graph else 1.0
                    explore_energy = 0.30 + eig * 0.20  # 基线0.30 + EIG (1.0→0.50, 1.6→0.62)
                    # Deep Dive: 专注期目标相关细胞探索加成
                    focus_topic = self._focus.get("topic")
                    if focus_topic and getattr(cell, 'goal', '') == focus_topic:
                        explore_energy += 0.25  # 专注加成, 对抗探索权重衰减
                    cell.receive_reward(explore_energy)  # 多巴胺通道: 让基因组学到探索行为
                    self.total_rewards += 0.15 + explore_energy
                    stats["rewards"] += 1
                    rewarded = True
                    # 成果: 发现稀疏节点 → 额外大奖
                    result = getattr(cell, '_last_result', {})
                    dst = result.get("to")
                    if dst and dst in self.graph:
                        nd = self.graph[dst]
                        edge_count = len(nd.get("effects", [])) + len(nd.get("causes", []))
                        if edge_count < 10:
                            novelty_reward = max(0.30, (10 - edge_count) * 0.30)  # 孤立节点=3.0, 超越标记收入
                            cell.receive_reward(novelty_reward)  # 多巴胺通道: 发现稀疏节点→强化探索
                            self.total_rewards += novelty_reward
                            stats["rewards"] += int(novelty_reward)

                if not rewarded:
                    welfare = chemistry.eval_welfare(cell, rewarded, signals)
                    if welfare > 0:
                        cell.give_energy(welfare)
                        self.total_rewards += welfare
                        if welfare >= 0.3:
                            stats["rewards"] += int(welfare)
                        rewarded = True

                if not rewarded and cell.last_action in ("step_forward", "step_backward"):
                    explore_reward = chemistry.eval_explore(cell, self.graph)
                    # 情感: 恐惧 (死路测绘有价值但令人不适)
                    res = getattr(cell, '_last_result', {})
                    if isinstance(res, dict) and res.get("result") in ("dead_end", "orphan"):
                        explore_reward += chemistry.p.EMOTION_FEAR
                    # 情感: 焦虑 (缺口引力)
                    node_data = self.graph.get(cell.node, {"causes": [], "effects": []})
                    in_d = len(node_data["causes"]); out_d = len(node_data["effects"])
                    if (in_d == 0 and out_d > 0) or (out_d == 0 and in_d > 0):
                        explore_reward += chemistry.p.EMOTION_ANXIETY
                    
                    cell.receive_reward(explore_reward)  # 多巴胺通道: 反向探索行为学习
                    self.total_rewards += explore_reward
                    res = getattr(cell, '_last_result', {})
                    if isinstance(res, dict) and res.get("result") in ("dead_end", "orphan"):
                        prev_node = cell.current_walk[-1][0] if hasattr(cell, 'current_walk') and cell.current_walk else None
                        if prev_node and cell.node:
                            chemistry.record_dead_end(prev_node, cell.node)
                        self.synapse.retrograde_inhibit(cell.node)

                if cell.last_action == "intervene" and isinstance(getattr(cell, '_last_result', None), dict):
                    effect = getattr(cell, '_last_result', {}).get("effect", 0)
                    if abs(effect) > 0.01:
                        # 实验: effect 越大越值得奖励
                        intervention_reward = abs(effect) * 2.0
                        cell.receive_reward(intervention_reward)
                        self.total_rewards += intervention_reward
                        stats["rewards"] += int(intervention_reward)
                    # 🔬 实验结果写回突触: 证实/证伪分别处理
                    res = cell._last_result
                    from_node = res.get("from")
                    to_node = res.get("to")
                    confirmed = res.get("confirmed", False)
                    refuted = res.get("refuted", False)
                    relevant_laws = res.get("relevant_laws", [])
                    if from_node and to_node:
                        key = (from_node, to_node)
                        if confirmed:
                            # 物理定律证实: 强化 + 升级 tier
                            self.synapse.strengthen(0, from_node, to_node, 0.5, self.generation)
                            if key in self.synapse.tiers and self.synapse.tiers[key] > 2:
                                self.synapse.tiers[key] = 2  # 物理验证→tier2
                            self._ensure_node(from_node)
                            self._ensure_node(to_node)
                            exists = any(e[1] == to_node for e in 
                                        self.graph[from_node].get('effects', []))
                            if not exists:
                                self.graph[from_node].setdefault('effects', []).append(
                                    ('physics_confirmed', to_node, 'experiment'))
                                self.graph[to_node].setdefault('causes', []).append(
                                    (from_node, 'physics_confirmed', 'experiment'))
                            self._record_discovery(f"{from_node}->{to_node}", "intervene_confirmed",
                                f"laws={relevant_laws}, effect={effect}")
                        elif refuted:
                            # 物理定律证伪: 削弱突触 + 降级
                            if key in self.synapse.activations:
                                self.synapse.activations[key]['s'] *= 0.5
                                if self.synapse.tiers.get(key, 4) < 4:
                                    self.synapse.tiers[key] = min(4, self.synapse.tiers[key] + 1)
                            self._record_discovery(f"{from_node}->{to_node}", "intervene_refuted",
                                f"laws={relevant_laws}, effect={effect}")
                        else:
                            # 无明确证实/证伪, 但有关联公式: 标记为实验
                            self.synapse.strengthen(0, from_node, to_node, 0.15, self.generation)
                            if key in self.synapse.tiers and self.synapse.tiers[key] > 3:
                                self.synapse.tiers[key] = 3
                            self._ensure_node(from_node)
                            self._ensure_node(to_node)
                            exists = any(e[1] == to_node for e in 
                                        self.graph[from_node].get('effects', []))
                            if not exists:
                                self.graph[from_node].setdefault('effects', []).append(
                                    ('intervene_experiment', to_node, 'experiment'))
                                self.graph[to_node].setdefault('causes', []).append(
                                    (from_node, 'intervene_experiment', 'experiment'))
                        # 🔬 反写源头假说 (hyp-node self-correction)
                        for node in (from_node, to_node):
                            if node.startswith(self.HYPNODE_PREFIX):
                                parts = node[len(self.HYPNODE_PREFIX):].rsplit(':', 1)
                                if len(parts) == 2:
                                    orig_src, orig_dst = parts
                                    orig_key = (orig_src, orig_dst)
                                    if orig_key in self.synapse.activations:
                                        edge = self.synapse.activations[orig_key]
                                        adj = effect * 0.3
                                        edge['s'] = max(0.01, edge['s'] + adj)

                if cell.last_action == "rest" and isinstance(getattr(cell, '_last_result', None), dict):
                    replay = cell._last_result.get("replay")
                    if replay and len(replay) >= 2:
                        saved_walk = cell.current_walk
                        cell.current_walk = replay
                        neuron_fire_on_path(cell, self.synapse, self.generation)
                        cell.current_walk = saved_walk

            # 🧠 E/I 平衡 + 侧抑制
            # 抑制性细胞 (niche<0.2): 不繁殖但压制热点, 维护生态平衡
            # 侧抑制: 同节点高reward细胞压制低reward邻居
            # 临界性: 分支比≈1.0的节点奖励行走细胞
            node_cells = defaultdict(list)
            for cell in self.cells:
                node_cells[cell.node].append(cell)
            
            # 临界性追踪: 每个节点的入/出活动比
            if not hasattr(self, '_node_activity'):
                self._node_activity = defaultdict(lambda: {'in': 0, 'out': 0})
            for cell in self.cells:
                if cell.last_action == 'step_forward':
                    self._node_activity[cell.node]['out'] += 1
                elif cell.last_action == 'step_backward':
                    self._node_activity[cell.node]['in'] += 1
            # 衰减: 每代减10%
            for k in list(self._node_activity.keys()):
                self._node_activity[k]['in'] = int(self._node_activity[k]['in'] * 0.9)
                self._node_activity[k]['out'] = int(self._node_activity[k]['out'] * 0.9)
                if self._node_activity[k]['in'] < 1 and self._node_activity[k]['out'] < 1:
                    del self._node_activity[k]
            
            inhib_reward = 0
            crit_reward = 0
            for node_id, peers in node_cells.items():
                if len(peers) <= 1:
                    continue
                # 侧抑制: 最高reward细胞压制其余 (赢家通吃, 促扩散)
                peers.sort(key=lambda c: c.total_reward, reverse=True)
                winner = peers[0]
                for loser in peers[1:]:
                    if loser.genome.get("niche", 0.5) < 0.2:
                        # 抑制性细胞: 在拥挤节点获得奖励 (生态位报酬)
                        loser.give_energy(0.15 * len(peers))
                        inhib_reward += 0.15 * len(peers)
                        self.total_rewards += 0.15 * len(peers)
                    # 兴奋性输家不受罚 — 负数reward破坏基因组比例
                    # 侧抑制通过赢家独占奖励自然实现
            
            if inhib_reward:
                stats.setdefault("inhib_reward", 0)
                stats["inhib_reward"] += int(inhib_reward)
            
            # 临界性奖励: 分支比≈1.0的节点 → 信息处理最优
            for cell in self.cells:
                act = self._node_activity.get(cell.node, {'in':0,'out':0})
                total = act['in'] + act['out']
                if total >= 3:
                    ratio = act['out'] / max(1, act['in'])
                    # 分支比越接近1.0, 信息处理越优 → reward
                    crit = 1.0 - min(1.0, abs(ratio - 1.0))
                    if crit > 0.7:  # 接近临界
                        cell.give_energy(crit * 0.1)
                        crit_reward += crit * 0.1
            if crit_reward:
                stats.setdefault("crit_reward", 0)
                stats["crit_reward"] += int(crit_reward)


            # 6. 周期性维护
            if self.generation % 50 == 0:
                self._check_and_feed()
                if len(self.cells) < 500:
                    # 🛡️ 冷却期: 100代内不重复 feed (防止 rebuild → WHY 卡死)
                    last_feed = getattr(self, '_last_feed_knowledge_gen', -999)
                    if self.generation - last_feed > 100:
                        print(f"\n  [DEATH_SPIRAL] neurons:{len(self.cells)} -> feed+resetK")
                        self._feed_knowledge()
                        self._last_feed_knowledge_gen = self.generation
                    edge_k = max(5000, len(self.graph) * 2 + len(self.cells) // 4)
                    self._carrying_capacity = max(self._carrying_capacity, edge_k)
                adaptive_ltd = max(300, self.generation // 10)
                self.synapse.LTD_WINDOW = adaptive_ltd
                pruned = self.synapse.decay(self.generation)
                if pruned:
                    stats.setdefault("pruned_synapses", 0)
                    stats["pruned_synapses"] += len(pruned)
                self.synapse.save()
                self._density_deaths += stats["density_deaths"]
                self._starvation_deaths += stats["starvation_deaths"]

                self._save_known_paths()
                self._grow_abstractions()
                self._expire_abstractions()
                self._save_coincidence()
                self._save_walk_memory()

                self._hot_hubs = BrainChemistry.compute_hot_hubs(self._coincidence)
                self.synapse.decay_retrograde()
                self.synapse.apply_retrograde(self.generation)

                chemistry.decay_inhibition()
                blocked = chemistry.get_blocked_edges()
                if blocked:
                    blocked = chemistry.broadcast_to_neighbors(blocked, self.graph)
                    for src, dst in blocked:
                        nd = self.graph.get(src, {})
                        for i, (law, d, domain) in enumerate(list(nd.get("effects", []))):
                            if d == dst and domain != "blocked":
                                key = (src, dst)
                                if key not in self._blocked_backup:
                                    self._blocked_backup[key] = (law, domain)
                                self.graph[src]["effects"][i] = (law, dst, "blocked")
                unblocked = set(self._blocked_backup.keys()) - blocked
                for src, dst in unblocked:
                    law, domain = self._blocked_backup.pop((src, dst))
                    nd = self.graph.get(src, {})
                    for i, (l, d, dm) in enumerate(list(nd.get("effects", []))):
                        if d == dst and dm == "blocked":
                            self.graph[src]["effects"][i] = (law, dst, domain)

                self._grow_shortcuts()
                self._spawn_probes()
                self._deep_prune()
                self._validate_tier_promotions()
                self._analyze_structures()
                self._validate_with_arxiv()


            # 7. hyp-node 同步
            self._sync_hyp_nodes()

            # 8. ☁️ 云人口管理
            self._precipitate_cells()     # 低活性 → 磁盘
            self._incubate_cells()        # 热点概念 ← 磁盘

        # 云统计: 每500代汇报
        if self.generation % 500 == 0:
            hot_n = len(self.cells)
            hubs = len(self._hot_hubs)
            bkp = len(self._breakthrough_pairs)
            contr_n = len(self._contradiction_nodes)
            ivs = self._intervene_stats
            iv_parts = []
            if ivs["confirmed"]:
                iv_parts.append(f"✅+{ivs['confirmed']}")
            if ivs["refuted"]:
                iv_parts.append(f"❌-{ivs['refuted']}")
            iv_str = " ".join(iv_parts) if iv_parts else ""
            parts = [f"☁️cells:{hot_n}"]
            if hubs: parts.append(f"hubs:{hubs}")
            if bkp: parts.append(f"bkp:{bkp}")
            if contr_n: parts.append(f"contr:{contr_n}")
            hot_str = " ".join(parts)
            print(f"  [CORTEX] gen={self.generation} {hot_str} | {iv_str}")

            # 节点分布: top5
            hot_by_node = {}
            for c in self.cells:
                hot_by_node[c.node] = hot_by_node.get(c.node, 0) + 1
            hot_top = sorted(hot_by_node.items(), key=lambda x: -x[1])[:5]
            if hot_top:
                print(f"    ☁️top: " + " ".join(f"{n}:{c}" for n, c in hot_top))

            self._intervene_stats = {"confirmed": 0, "refuted": 0, "tested": 0}

        # 轻量监控: 每500代打印一行关键指标
        if self.generation % 500 == 0:
            rewards = [c.total_reward for c in self.cells]
            if rewards:
                rewards.sort()
                n = len(rewards)
                print(f"  [METRICS] gen={self.generation} pop={n} K={self._carrying_capacity} "
                      f"reward(mean={sum(rewards)/n:.1f} p50={rewards[n//2]:.1f} max={rewards[-1]:.1f}) "
                      f"split={stats['births']/max(n,1):.2%} edges={self.graph.edge_count}")

            # 独立睡眠 — 每代检查, 云架构频繁触发
            total_walks = sum(len(getattr(c, 'walk_memory', [])) for c in self.cells)
            self._sleep_pressure += total_walks * 0.0015
            if self.generation % 5 == 0:
                print(f"  [ZZZ] pressure={self._sleep_pressure:.1f} walks={total_walks}")
            if self._sleep_pressure > 0.3:
                print(f"  [SLEEP-TRIGGER] pressure={self._sleep_pressure:.1f} gen={self.generation}", flush=True)
                try:
                    self._sleep_replay()
                except Exception as e:
                    print(f"  [SLEEP-ERR] {e}")
                    import traceback
                    traceback.print_exc()
                self._sleep_pressure = 0.0
            
            # 📖 arXiv 闸门: 每 20 代检查晋升
            if self.generation % 20 == 0:
                self.arxiv_reading.check_promotions(self)

        # 认知调度: 竞争激活, 脑自己决定现在该做什么
        self._cognitive_scheduler()

        return stats

    # ═══════ 验证 ═══════

    def _validate_tier_promotions(self):
        """假说验证: 剔除架空tier3 + 质量门 (coincidence/s-value)"""
        if not hasattr(self, '_native_nodes'):
            return
        demoted = 0
        promoted = 0
        GENERIC_NOISE = {'title','abstract','paper','model','system','method',
                         'result','data','approach','figure','table','section',
                         'introduction','conclusion','background','related_work',
                         'context','image','source','target','sample'}
        for key, tier in list(self.synapse.tiers.items()):
            if tier != 3:
                continue
            src, dst = key
            activation = self.synapse.activations.get(key, {})
            s_val = activation.get('s', 0)
            coinc_count = self._coincidence.get(key, 0)
            
            # 质量门1: coincidence 太低且 s 值弱 → 缺乏独立验证, 降级
            if coinc_count < 3 and s_val < 0.5:
                self.synapse.tiers[key] = 4
                demoted += 1
                continue
            
            # 质量门2: 端点含 arXiv 噪音词 → 降级
            src_words = set(src.replace('_',' ').lower().split())
            dst_words = set(dst.replace('_',' ').lower().split())
            if (src_words & GENERIC_NOISE) or (dst_words & GENERIC_NOISE):
                self.synapse.tiers[key] = 4
                demoted += 1
                continue
            
            # 质量门3 (图内 oracle): 反向边若是已验证物理定律 (tier≤2) → 矛盾, 降级
            rev_key = (dst, src)
            rev_tier = self.synapse.tiers.get(rev_key, 99)
            if rev_tier <= 2:
                rev_edge = self.synapse.activations.get(rev_key, {})
                rev_s = rev_edge.get('s', 0)
                if rev_s > s_val * 2:  # 反向边明显更强 → 本边可能是反向因果
                    self.synapse.tiers[key] = 4
                    demoted += 1
                    continue
            # 抽象桥: 若至少一端是abs节点但coincidence和walk验证充分 → 允许tier3
            has_abs = src.startswith("abs:") or dst.startswith("abs:")
            if src not in self._native_nodes or dst not in self._native_nodes:
                if has_abs:
                    unique_neurons = len(activation.get('n', set()))
                    abs_node = src if src.startswith("abs:") else dst
                    abs_degree = (len(self.graph.get(abs_node, {}).get("causes", [])) +
                                 len(self.graph.get(abs_node, {}).get("effects", [])))
                    if abs_degree >= 4 and coinc_count >= 20 and unique_neurons >= 3:
                        promoted += 1
                        continue
                self.synapse.tiers[key] = 4
                demoted += 1
        if demoted and self.generation % 500 == 0:
            print(f"  [VALIDATE] {demoted} fake tier3 -> t4 (non-native nodes)")
        if promoted and self.generation % 500 == 0:
            print(f"  [ABSTRACT_T3] {promoted} abstract bridges validated → tier3")

    # ═══════ 自动目标选择 ═══════

    def _auto_goal_selection(self):
        """从 hyp-node 衰退和矛盾中自动选择新研究目标 (专注锁定期内跳过, 调度器控制频率)"""
        if self._focus.get("topic"):
            return  # 专注锁定期, 不换目标
        new_goals = 0
        # 1. hyp-node s 值骤降 > 50% → 假说可能被证伪, 值得研究
        for key, edge in list(self.synapse.activations.items()):
            src, dst = key
            hyp_name = f"{self.HYPNODE_PREFIX}{src}:{dst}"
            if hyp_name not in self.graph:
                continue
            s_val = edge.get('s', 0)
            c_val = edge.get('c', 0)
            if c_val < 10 or s_val > 1.0:
                continue  # 太新或太强, 不关注
            # s/c 比: 每次巧合带来的信念。低比值 = 高巧合低信念 → 假说存疑
            ratio = s_val / max(c_val, 1)
            if ratio < 0.05 and src not in self._active_goals:
                self.set_goal(src, f"hyp-node s/c ratio={ratio:.3f}")
                new_goals += 1
            if new_goals >= 3:
                break
        # 2. 高 coincidence 新节点 → 新兴热点
        if new_goals < 3:
            hot_nodes = Counter()
            for (a, b), cnt in self._coincidence.items():
                if cnt >= 50:
                    hot_nodes[a] += cnt
                    hot_nodes[b] += cnt
            for node, _ in hot_nodes.most_common(10):
                if node.startswith(self.HYPNODE_PREFIX):
                    continue
                if node in self._active_goals:
                    continue
                # 不在目标里且不是噪声词
                skip_words = {'title','abstract','paper','model','method','result','data',
                              'figure','table','section','introduction','conclusion','sample'}
                if set(node.replace('_',' ').lower().split()) & skip_words:
                    continue
                self.set_goal(node, f"auto: high coincidence ({hot_nodes[node]})")
                new_goals += 1
                if new_goals >= 3:
                    break
        if new_goals:
            goals_str = ", ".join(list(self._active_goals.keys())[-new_goals:])
            print(f"  [AUTO-GOAL] +{new_goals} goals: {goals_str}")

    # ═══════ composed 边验证 ═══════

    def _verify_composed_edges(self):
        """剪除无 coincidence 支撑的 composed 边 (调度器控制频率)"""
        if not hasattr(self, '_composed_birth'):
            self._composed_birth = {}
        pruned = 0
        promoted = 0
        for key, birth_gen in list(self._composed_birth.items()):
            age = self.generation - birth_gen
            if age < 200:
                continue
            coinc = self._coincidence.get(key, 0)
            if coinc < 2:
                # 无人走过 → 剪除
                src, dst = key
                if key in self.synapse.activations:
                    del self.synapse.activations[key]
                self.synapse.tiers.pop(key, None)
                self._composed_birth.pop(key, None)
                pruned += 1
            elif coinc >= 10:
                # 充分验证 → 升 s 值
                if key in self.synapse.activations:
                    self.synapse.activations[key]['s'] *= 1.5
                self._composed_birth.pop(key, None)
                promoted += 1
        if pruned or promoted:
            print(f"  [VERIFY] -{pruned} composed pruned +{promoted} promoted (gen {self.generation})")

    # ═══════ 殖民层自动实验 (intervene) ═══════

    def _colony_intervene(self):
        """挑 focus 相关 top hyp-nodes, 用 coincidence/s-value 变化验证假说 (调度器控制频率)"""
        print(f"  [INTERVENE-DBG] entered gen={self.generation} coinc={len(self._coincidence)} intervened={len(self._intervened_nodes)}", flush=True)
        if not hasattr(self, '_intervened_nodes'):
            self._intervened_nodes = {}  # hyp_name -> (gen, coinc, s)
        # 每 500 代重置基线, 防止陈旧基线锁死验证回路
        if self.generation % 500 == 0 and len(self._intervened_nodes) > 10:
            self._intervened_nodes.clear()
            print(f"  [INTERVENE] 基线重置 @ gen {self.generation}")
        
        focus_topic = self._focus.get("topic", "")
        candidates = []
        pool_all = []
        for (a, b), cnt in self._coincidence.items():
            if cnt < 5:
                continue
            # 找 focus 相关 hyp-nodes; 同时维护全图池兜底
            for node in (a, b):
                if not node.startswith(self.HYPNODE_PREFIX):
                    continue
                pool_all.append((node, cnt, a, b))
                if focus_topic and focus_topic not in node:
                    continue
                candidates.append((node, cnt, a, b))
        # 焦点邻域无 hyp-node → 全图池按 coincidence 支持度兜底, 验证不停摆
        if not candidates:
            candidates = pool_all
        if not candidates:
            return
        
        candidates.sort(key=lambda x: -x[1])
        tested = 0
        confirmed = 0
        refuted = 0
        
        for node, coinc, na, nb in candidates[:5]:
            if node in self._intervened_nodes:
                prev_gen, prev_coinc, prev_s = self._intervened_nodes[node]
                # 计算 s 值: 取边的 s 值
                key = (na, nb) if (na, nb) in self.synapse.activations else (nb, na)
                cur_s = self.synapse.activations.get(key, {}).get('s', 1.0)
                
                if coinc >= prev_coinc and cur_s >= prev_s * 0.7:  # 不要求增长, 稳定即可
                    # 假说在增强: 证实
                    self.synapse.activations.get(key, {})['s'] = cur_s * 2.0  # s×2 强化奖励
                    # 全局多巴胺广播: 证实是重大事件, 通知相关神经元
                    self._global_dopamine = min(5.0, self._global_dopamine + 0.5) if hasattr(self, '_global_dopamine') else 0.5
                    self._record_discovery(node, "intervene_confirmed",
                        f"coinc {prev_coinc}→{coinc}, s {prev_s:.1f}→{cur_s:.1f}")
                    confirmed += 1
                    # 证实后追问: 这个证实意味着什么?
                    try:
                        for v in (na, nb):
                            if not v.startswith(self.HYPNODE_PREFIX):
                                path = self._trace_to_action(v)
                                if path:
                                    self._record_discovery(v, "why_confirmed",
                                        f"证实后可推导: {'→'.join(path[:4])}")
                                    self._priority_nodes.add(v)
                    except Exception:
                        pass
                    # 公式推导: 问数学引擎, 不用查表
                    try:
                        result = self._derive_formula(na, nb)
                        if result:
                            self._record_discovery(node, "formula_derived",
                                f"{result}")
                    except Exception:
                        pass
                    # 惊奇检测: 证实后下游 coincidence 是否超预期增长
                    downstream_surprise = 0
                    for (da, db), dcnt in self._coincidence.items():
                        if da == na or da == nb or db == na or db == nb:
                            other = db if da in (na, nb) else da
                            if other in self._intervened_nodes:
                                _, prev_dc, _ = self._intervened_nodes[other]
                                if prev_dc > 0 and dcnt > prev_dc * 2.0:
                                    downstream_surprise += 1
                    if downstream_surprise >= 2:
                        self._record_discovery(node, "breakthrough_candidate",
                            f"downstream surprise x{downstream_surprise}, coinc {prev_coinc}→{coinc}")
                        print(f"  💡 BREAKTHROUGH: {node[:50]} "
                              f"(下游{downstream_surprise}处异常增长)")
                        # 消化惊奇: 把异常节点设为目标, 脑自己去解释
                        surprised_nodes = []
                        for (da, db), dcnt in self._coincidence.items():
                            if da == na or da == nb or db == na or db == nb:
                                other = db if da in (na, nb) else da
                                if other in self._intervened_nodes:
                                    _, prev_dc, _ = self._intervened_nodes[other]
                                    if prev_dc > 0 and dcnt > prev_dc * 2.0:
                                        surprised_nodes.append(other)
                        for sn in surprised_nodes[:3]:
                            self.set_goal(sn, f"breakthrough: surprise from {node[:30]}")
                        self._focus["breakthrough_at"] = self.generation
                        self._save_focus()
                        print(f"  [SURPRISE] 消化: {len(surprised_nodes[:3])} 节点设为目标")
                elif coinc < prev_coinc * 0.8:
                    # 假说在衰减: 证伪, 降级 (加大惩罚, 快速淘汰噪声)
                    if key in self.synapse.activations:
                        self.synapse.activations[key]['s'] *= 0.3
                    refuted += 1
                
                self._intervened_nodes[node] = (self.generation, coinc, cur_s)
            else:
                # 首次观察, 记录基线
                key = (na, nb) if (na, nb) in self.synapse.activations else (nb, na)
                cur_s = self.synapse.activations.get(key, {}).get('s', 1.0)
                self._intervened_nodes[node] = (self.generation, coinc, cur_s)
            tested += 1
        
        # 累计到 500 代统计
        self._intervene_stats["confirmed"] += confirmed
        self._intervene_stats["refuted"] += refuted
        self._intervene_stats["tested"] += tested
        # 心跳: 即使无证实/证伪也打印追踪状态
        print(f"  [INTERVENE] gen {self.generation}: {tested} tested, "
              f"+{confirmed}/-{refuted}, 追踪池 {len(self._intervened_nodes)} 假说"
              f"{' ✅' if confirmed else ''}{' ❌' if refuted else ''}")
        if confirmed or refuted:
            # 如果有证实, 标记 focus 有进展
            if confirmed > 0:
                self._focus["resolved"] = self._focus.get("resolved", 0) + confirmed
                self._save_focus()
            print(f"  [INTERVENE] {tested} tested: "
                  f"+{confirmed} confirmed, -{refuted} refuted (gen {self.generation})")

    # ═══════ 为什么引擎 (why) ═══════

    def _why_contradictions(self):
        """对矛盾对做因果溯源, 找出分叉根因 (调度器控制频率)"""
        if not self._contradiction_nodes:
            self._detect_contradictions()
        if not self._contradiction_nodes or len(self._contradiction_nodes) < 2:
            print(f"  [WHY] 跳过: 矛盾节点不足 ({len(self._contradiction_nodes)})")
            return
        from meta_cognition.why_engine import trace_to_root
        
        analyzed = 0
        for node in list(self._contradiction_nodes)[:5]:
            try:
                # 在图上游走: 策略 A=causes, 走不通换 B=coincidence
                path = self._trace_to_action(node)
                if not path:
                    path = self._trace_to_action(node, strategy="coincidence")
                    if path:
                        self._record_discovery(node, "why_alt_path",
                            f"coincidence 路径到 action: {'→'.join(path[:4])}")
                if path:
                    self._record_discovery(node, "why_reachable",
                        f"可从 action 推导: {'→'.join(path[:4])}")
                    self._resolved_nodes.add(node)
                    self._contradiction_nodes.discard(node)
                    root = path[-1] if len(path) > 1 else path[0]
                    self.set_goal(root, f"resolve: contradiction at {node}")
                    analyzed += 1
                else:
                    # 走不到 action → 真缺口
                    gap = f"{node} 无法从图上游走到 action"
                    self._record_discovery(node, "why_gap", gap)
                    if self._plan.get("tasks"):
                        existing = {t["topic"] for t in self._plan["tasks"]}
                        if node not in existing:
                            self._plan["tasks"].append({
                                "id": self._plan["next_id"],
                                "topic": node,
                                "status": "pending",
                                "created": self.generation,
                                "time_spent": 0,
                                "hypotheses": 0,
                                "coincidence": 0
                            })
                            self._plan["next_id"] += 1
                            self._save_plan()
                            print(f"  [GAP→PLAN] {node} 加入研究队列")
                    analyzed += 1
            except Exception:
                pass
        if analyzed:
            print(f"  [WHY] {analyzed} 矛盾溯源 (gen {self.generation})")

    def _trace_to_action(self, node: str, max_depth: int = 10, strategy: str = "causes") -> list:
        """脑自己的图游走: 从 node 溯到 action。strategy: causes | coincidence"""
        visited = set()
        path = [node]
        current = node
        for _ in range(max_depth):
            if current == "action":
                return list(reversed(path))
            visited.add(current)
            # 根据策略选邻居
            neighbors = []
            if strategy == "causes":
                for _, cause_node, _ in self.graph.get(current, {}).get("causes", []):
                    if cause_node not in visited:
                        neighbors.append(cause_node)
            else:  # coincidence
                for (a, b) in self._coincidence:
                    if a == current and b not in visited:
                        neighbors.append(b)
                    elif b == current and a not in visited:
                        neighbors.append(a)
            if not neighbors:
                break
            current = neighbors[0]
            path.append(current)
        return []  # 走不通

    # ═══════ 数学引擎 ═══════

    def _derive_formula(self, a: str, b: str) -> str:
        """问数学引擎: a 和 b 之间有什么公式关系? 返回描述或空"""
        from physics.laws import library
        # 找同时涉及 a 和 b 的定律
        matches = []
        for law in library._laws:
            related = set(law.inputs + law.outputs)
            a_match = a in related or a in law.name.lower()
            b_match = b in related or b in law.name.lower()
            if a_match and b_match and hasattr(law, 'latex') and law.latex:
                matches.append(law)
        if matches:
            # 取最精确的 (最少输入输出的)
            matches.sort(key=lambda m: len(m.inputs) + len(m.outputs))
            law = matches[0]
            return f"{law.name}: ${law.latex}$"
        # 尝试组合推导
        a_laws = [l for l in library._laws if a in (l.inputs + l.outputs)]
        b_laws = [l for l in library._laws if b in (l.inputs + l.outputs)]
        shared = set()
        for la in a_laws:
            for lb in b_laws:
                common = set(la.inputs + la.outputs) & set(lb.inputs + lb.outputs)
                shared.update(common)
        if shared:
            bridge = list(shared)[:3]
            return f"组合: {a}↔{'|'.join(bridge)}↔{b}"
        return ""

    def _alternate_why(self):
        """替代视角: coincidence 邻居搜索"""
        if not self._contradiction_nodes:
            return
        found = 0
        for node in list(self._contradiction_nodes)[:3]:
            neighbors = set()
            for (a, b) in self._coincidence:
                if a == node: neighbors.add(b)
                if b == node: neighbors.add(a)
            if neighbors:
                top = sorted(neighbors, key=lambda n:
                    self._coincidence.get((node,n),0) + self._coincidence.get((n,node),0),
                    reverse=True)[:2]
                self._record_discovery(node, "alt_view",
                    f"邻居: {' | '.join(top)}")
                found += 1
        return found

    # ═══════ 认知调度器 (竞争激活) ═══════

    def _cognitive_scheduler(self):
        """自由能驱动调度: 每个模块输出预测误差, 误差大的优先执行"""
        # INIT
        if not hasattr(self, '_module_stats'):
            self._module_stats = {}
        if not hasattr(self, '_walk_stats'):
            self._walk_stats = {"causes": (1, 1), "coincidence": (1, 1)}
        
        candidates = []

        # GOAL: 预期有专注课题 → 无课题时预测误差最大
        goal_pe = 1.0 if not self._focus.get("topic") else 0.05
        candidates.append(("goal", goal_pe, self._auto_goal_selection))

        # FOCUS: 预期续期在 ~500 代附近 → 偏离越远误差越大
        if self._focus.get("topic"):
            locked = self._focus.get("locked_at", self.generation)
            elapsed = self.generation - locked
            focus_pe = abs(elapsed - self.FOCUS_DURATION) / max(self.FOCUS_DURATION, 1)
            focus_pe = min(1.0, focus_pe)
        else:
            focus_pe = 0.8
        candidates.append(("focus", focus_pe, self._manage_focus))

        # VERIFY: 预期 composed 边 < 100 → 堆积越多误差越大
        composed_count = len(getattr(self, '_composed_birth', {}))
        verify_pe = min(1.0, composed_count / 200)
        candidates.append(("verify", verify_pe, self._verify_composed_edges))

        # INTERVENE: 预期已测试 hyp-node > 20 → 未测试越多误差越大
        if hasattr(self, '_intervened_nodes'):
            untested = max(5, 30 - len(self._intervened_nodes))  # 保底5, PE永不为0
        else:
            untested = 30
        interv_pe = min(1.0, untested / 20)
        candidates.append(("intervene", interv_pe, self._colony_intervene))

        # ORACLE
        oracle_pe = 0.3
        candidates.append(("oracle", oracle_pe, self._llm_verify_hypotheses))

        # WHY/ALT: 暂时禁用 (图遍历死循环 bug, 待修复)
        # 原逻辑: feed 后冷却期跳过 + len(graph) < 1000
        pass
        """
        if not self._contradiction_nodes:
            self._detect_contradictions()
        if self._contradiction_nodes and not feed_cooldown:
            try:
                self._why_contradictions()
            except Exception:
                pass
        if self._contradiction_nodes and not feed_cooldown:
            try:
                self._alternate_why()
            except Exception:
                pass
        """

        # 其余模块按 PE 门槛全跑

        # 元认知: 根据历史成功率调整 PE
        for i, (name, pe, func) in enumerate(candidates):
            runs, successes = self._module_stats.get(name, (1, 1))
            success_rate = successes / max(runs, 1)
            candidates[i] = (name, pe * (0.5 + success_rate * 0.5), func)

        # 全跑, 模块自己判断该不该执行
        for name, pe, func in candidates:
            if pe > 0.05:
                try:
                    before = len(self._contradiction_nodes)
                    func()
                    # 元认知: 判断是否产出
                    runs, successes = self._module_stats.get(name, (0, 0))
                    runs += 1
                    if name == "why" and len(self._contradiction_nodes) < before:
                        successes += 1
                    elif name == "intervene" and self._focus.get("resolved", 0) > self._module_stats.get("_lr", 0):
                        successes += 1
                    elif name == "goal" and self._focus.get("topic"):
                        successes += 1
                    else:
                        successes += 1
                    self._module_stats[name] = (runs, successes)
                    self._module_stats["_lr"] = self._focus.get("resolved", 0)
                except Exception:
                    pass

    def _detect_contradictions(self):
        """轻量矛盾检测: A→B 和 B→A 同时存在且域不同"""
        self._contradiction_nodes = set()
        for src in list(self.graph.keys())[:500]:
            for _, dst, d1 in self.graph[src].get("effects", []):
                for _, back_dst, d2 in self.graph.get(dst, {}).get("effects", []):
                    if back_dst == src and d1 != d2:
                        self._contradiction_nodes.add(src)
                        self._contradiction_nodes.add(dst)
                        if len(self._contradiction_nodes) >= 40:
                            return

    # ═══════ LLM oracle ═══════

    def _llm_verify_hypotheses(self):
        """挑 top 5 coincidence 最高的 hyp-node, 送 LLM 物理验证 (调度器控制频率)"""
        # 降频: 每 50 代调一次
        if self.generation % 50 != 0:
            return
        # 找 top 5 hyp-node (按 coincidence)
        hyp_coinc = []
        for (a, b), cnt in self._coincidence.items():
            if cnt < 10:
                continue
            if a.startswith(self.HYPNODE_PREFIX):
                hyp_coinc.append((a, cnt, b))
            if b.startswith(self.HYPNODE_PREFIX):
                hyp_coinc.append((b, cnt, a))
        if not hyp_coinc:
            return
        # ORACLE 低分边降权: 已被 ORACLE 判低分 (<0.3) 的边排到后面
        def _oracle_weight(item):
            hyp_name, coinc, other = item
            inner = hyp_name[len(self.HYPNODE_PREFIX):]
            parts = inner.rsplit(':', 1)
            if len(parts) == 2:
                prev = self._oracle_scores.get((parts[0], parts[1]))
                if prev is not None and prev < 0.3:
                    return coinc * 0.01
            return coinc
        hyp_coinc.sort(key=lambda x: -_oracle_weight(x))
        seen = set()
        verified = 0
        for hyp_name, coinc, other in hyp_coinc:
            if hyp_name in seen:
                continue
            seen.add(hyp_name)
            # 解析 src, dst
            inner = hyp_name[len(self.HYPNODE_PREFIX):]
            parts = inner.rsplit(':', 1)
            if len(parts) != 2:
                continue
            src, dst = parts
            try:
                from llm.bridge import LLMBridge
                from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
                bridge = LLMBridge()
                if not bridge.is_available():
                    break
                prompt = (
                    f"Evaluate this physics hypothesis: \"{src} causes {dst}\".\n"
                    f"Context: this emerged from an AI brain studying causal physics.\n"
                    f"Is this relationship physically plausible?\n"
                    f"Reply with ONLY a number 0-1 (0=impossible, 0.5=uncertain, 1=confirmed)."
                )
                # 超时保护: 15 秒没响应就跳过
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        bridge.client.chat,
                        [{"role": "user", "content": prompt}], max_tokens=20
                    )
                    resp = future.result(timeout=15)
                import re
                match = re.search(r'([0-9]*\.?[0-9]+)', resp)
                score = float(match.group(1)) if match else 0.5
                score = max(0.0, min(1.0, score))
                self._oracle_scores[(src, dst)] = score  # 记忆 ORACLE 评分，供下次选取参考
                # 反写 s 值
                key = (src, dst)
                if key in self.synapse.activations:
                    edge = self.synapse.activations[key]
                    old_s = edge['s']
                    # 平滑融合: 30% LLM + 70% 原有
                    edge['s'] = old_s * 0.7 + score * 0.3
                    verified += 1
                    print(f"  [ORACLE] {src[:20]}→{dst[:20]} LLM={score:.2f} s:{old_s:.2f}→{edge['s']:.2f}")
            except FutureTimeout:
                print(f"  [ORACLE-TIMEOUT] {src[:20]}→{dst[:20]}")
                break
            except Exception as e:
                print(f"  [ORACLE-ERR] {e}")
                break
            if verified >= 5:
                break
        if verified:
            print(f"  [ORACLE] {verified} hypotheses verified by LLM (gen {self.generation})")

    def _analyze_structures(self):
        """结构识别: 检测图模式并用语言标注 (每500代)"""
        if self.generation % 500 != 0:
            return
        # 收集节点度数和域信息
        node_degree = {}
        node_domain_count = {}
        for nid, nd in self.graph._cache.items():
            in_d = len(nd.get("causes", []))
            out_d = len(nd.get("effects", []))
            node_degree[nid] = (in_d, out_d)
            domains = set()
            for _, _, d in nd.get("effects", []):
                domains.add(d)
            node_domain_count[nid] = len(domains)

        total_nodes = len(node_degree)
        if total_nodes < 10:
            return
        # 度数排序
        sorted_nodes = sorted(node_degree.items(), key=lambda x: x[1][0] + x[1][1], reverse=True)
        degree_values = [d[0] + d[1] for _, d in sorted_nodes]
        degree_values.sort()
        hub_threshold = degree_values[int(len(degree_values) * 0.95)] if degree_values else 5

        findings = []

        # ── 枢纽节点 (top 5%) ──
        hubs = [(n, d[0] + d[1], node_domain_count.get(n, 0))
                for n, d in sorted_nodes[:max(3, total_nodes // 20)]
                if d[0] + d[1] >= hub_threshold]
        if hubs:
            hub_str = " | ".join(
                f"{n[:16]}(in:{in_d}/out:{out_d},域:{dc})"
                for n, (in_d, out_d), dc in
                [(h[0], node_degree[h[0]], h[2]) for h in hubs[:5]]
            )
            findings.append(f"枢纽: {hub_str}")

        # ── 跨域桥梁 ──
        bridges = [(n, dc) for n, dc in node_domain_count.items()
                   if dc >= 3 and node_degree[n][0] + node_degree[n][1] >= 3]
        if bridges:
            bridges.sort(key=lambda x: -x[1])
            br_str = " | ".join(f"{n[:18]}({dc}域)" for n, dc in bridges[:5])
            findings.append(f"桥梁: {br_str}")

        # ── 前馈/反馈环检测 (coincidence双向) ──
        feedback = 0
        feedforward_chains = 0
        for (src, dst), count in list(self._coincidence.items())[:2000]:
            if (dst, src) in self._coincidence and self._coincidence.get((dst, src), 0) > 0:
                feedback += 1
            else:
                # 前馈: A→B 且 A有→C 指向同一目标的同级节点
                neighbors_a = {e[1] for e in self.graph.get(src, {}).get("effects", [])}
                if len(neighbors_a) >= 2:
                    feedforward_chains += 1
        if feedback > 0:
            findings.append(f"反馈环: {feedback}对双向因果")

        # 矛盾检测: 图中A→B和B→A同时存在且域不同 → 因果冲突
        conflicts = 0
        conflict_pairs = []  # (src, dst, d1, d2, s_full, d_full)
        for src in list(self.graph.keys())[:500]:
            for _, dst, d1 in self.graph[src].get("effects", []):
                for _, back_dst, d2 in self.graph.get(dst, {}).get("effects", []):
                    if back_dst == src and d1 != d2:
                        conflicts += 1
                        if len(conflict_pairs) < 3:
                            conflict_pairs.append((src[:14], dst[:14], d1, d2, src, dst))
                        break
                if conflicts >= 20:
                    break
            if conflicts >= 20:
                break
        if conflicts > 0:
            findings.append(f"矛盾: {conflicts}处因果冲突")
            self._contradiction_nodes = set()
            for _, _, _, _, s_full, d_full in conflict_pairs:
                self._contradiction_nodes.add(s_full)
                self._contradiction_nodes.add(d_full)
            # 时序因果: 先出现的边保留优先权
            resolved = 0
            for s, d, d1, d2, s_full, d_full in conflict_pairs[:3]:
                birth_fwd = self._edge_birth.get((s_full, d_full), 999999)
                birth_rev = self._edge_birth.get((d_full, s_full), 999999)
                if birth_fwd < birth_rev:
                    winner = "→"
                    # 降权反向边
                    rev_key = (d_full, s_full)
                    if rev_key in self.synapse.tiers:
                        self.synapse.tiers[rev_key] = min(4, self.synapse.tiers[rev_key] + 1)
                        resolved += 1
                elif birth_rev < birth_fwd:
                    winner = "←"
                    fwd_key = (s_full, d_full)
                    if fwd_key in self.synapse.tiers:
                        self.synapse.tiers[fwd_key] = min(4, self.synapse.tiers[fwd_key] + 1)
                        resolved += 1
                else:
                    winner = "?"
                findings.append(f"  ↯ {s}⇄{d} ({d1} vs {d2}) [{winner}]")
            if resolved:
                findings.append(f"  → {resolved}条后发边降tier (时序因果)")
            # 矛盾驱动: 冲突节点的curiosity提升
            if conflict_pairs:
                boosted = 0
                for cell in self.cells:
                    for _, _, _, _, s_full, d_full in conflict_pairs[:3]:
                        if cell.node == s_full or cell.node == d_full:
                            cur = cell.genome.get("curiosity", 1.0)
                            cell.genome["curiosity"] = min(3.0, cur + 0.3)
                            boosted += 1
                            break
                if boosted:
                    findings.append(f"  → {boosted}个神经元curiosity↑ (去解决矛盾)")

            # 虚拟实验: fork两个世界, walk比较, reward高者胜
            if conflict_pairs and self.generation % 500 == 0:
                from meta_cognition.evolvable_cell import EvolvableCell
                experiments = 0
                for _, _, _, _, s_full, d_full in conflict_pairs[:2]:
                    if s_full not in self.graph or d_full not in self.graph:
                        continue
                    # 长期记忆: 跳过已被证伪的假说 (5000代冷却期)
                    if self._is_falsified(s_full, d_full) and self._is_falsified(d_full, s_full):
                        continue
                    # Fork: 拷贝2-hop子图 (浅拷贝, 避免 deepcopy 触发 VSA 同步 + 内存暴涨)
                    sub_nodes = {s_full, d_full}
                    for nd in (s_full, d_full):
                        for _, nbr, _ in self.graph.get(nd, {}).get("effects", []):
                            sub_nodes.add(nbr)
                        for nbr, _, _ in self.graph.get(nd, {}).get("causes", []):
                            sub_nodes.add(nbr)
                    sub_graph = {}
                    for n in sub_nodes:
                        if n not in self.graph:
                            continue
                        entry = self.graph[n]
                        sub_graph[n] = {
                            "effects": [tuple(e) for e in entry.get("effects", [])],
                            "causes": [tuple(c) for c in entry.get("causes", [])],
                        }
                    # 世界A: A→B有效, B→A移除
                    sub_a = {n: {"effects": list(v["effects"]), "causes": list(v["causes"])}
                             for n, v in sub_graph.items()}
                    sub_a[s_full]["effects"] = [e for e in sub_a[s_full].get("effects",[]) if e[1] == d_full or e[2] != "emergent"]
                    sub_a[d_full]["effects"] = [e for e in sub_a[d_full].get("effects",[]) if e[1] != s_full]
                    sub_a[d_full]["causes"] = [e for e in sub_a[d_full].get("causes",[]) if e[0] != s_full]
                    # 世界B: B→A有效, A→B移除
                    sub_b = {n: {"effects": list(v["effects"]), "causes": list(v["causes"])}
                             for n, v in sub_graph.items()}
                    sub_b[d_full]["effects"] = [e for e in sub_b[d_full].get("effects",[]) if e[1] == s_full or e[2] != "emergent"]
                    sub_b[s_full]["effects"] = [e for e in sub_b[s_full].get("effects",[]) if e[1] != d_full]
                    sub_b[s_full]["causes"] = [e for e in sub_b[s_full].get("causes",[]) if e[0] != d_full]
                    # 各放5个虚拟神经元, walk 20步
                    reward_a = 0; reward_b = 0
                    for _ in range(5):
                        cell = EvolvableCell(s_full, sub_a, self.board,
                                            min_split_reward=self.MIN_SPLIT_REWARD)
                        for __ in range(20):
                            result = cell.act()
                        reward_a += cell.total_reward
                        cell = EvolvableCell(s_full, sub_b, self.board,
                                            min_split_reward=self.MIN_SPLIT_REWARD)
                        for __ in range(20):
                            result = cell.act()
                        reward_b += cell.total_reward
                    # 裁决
                    if max(reward_a, reward_b) > 0:
                        winner_dir = "A->B" if reward_a > reward_b else "B->A"
                        loser_key = (d_full, s_full) if reward_a > reward_b else (s_full, d_full)
                        winner_key = (s_full, d_full) if reward_a > reward_b else (d_full, s_full)
                        if loser_key in self.synapse.tiers:
                            self.synapse.tiers[loser_key] = min(4, self.synapse.tiers[loser_key] + 1)
                            self._resolved_nodes.add(d_full)
                            self._resolved_nodes.add(s_full)
                        experiments += 1
                        # 长期记忆: 记录实验结果 + 证伪失败方向
                        conf = abs(reward_a - reward_b) / max(reward_a + reward_b, 0.01)
                        self._record_experiment(s_full, d_full, "virtual_walk", winner_dir, conf)
                        loser_src, loser_dst = loser_key
                        self._record_falsified(loser_src, loser_dst,
                            f"virtual_experiment: {winner_dir} won by {reward_a:.1f} vs {reward_b:.1f}")
                if experiments:
                    findings.append(f"  [实验] {experiments}个虚拟实验完成 → 输家降tier")
                # 意义涌现: 矛盾最多的节点 → 自动设为目标
                if conflict_pairs and self.generation % 500 == 0:
                    node_conflicts = Counter()
                    for _, _, _, _, s_full, d_full in conflict_pairs:
                        node_conflicts[s_full] += 1
                        node_conflicts[d_full] += 1
                    if node_conflicts:
                        top_node, count = node_conflicts.most_common(1)[0]
                        if count >= 2 and top_node not in self._active_goals:
                            self.set_goal(top_node, f"auto: involved in {count} contradictions")
                            findings.append(f"  [意义] {top_node} → 自动目标({count}矛盾)")
                            print(f"  [💡意义] {top_node} 成为研究目标 ({count}处矛盾")
        if feedforward_chains > 0:
            findings.append(f"前馈扇出: {feedforward_chains}处分叉")

        # ── 抽象节点活跃度 ──
        active_abs = sum(1 for n in node_degree if n.startswith("abs:")
                        and node_degree[n][0] + node_degree[n][1] >= 2)
        if active_abs > 0:
            findings.append(f"抽象概念: {active_abs}个活跃桥接节点")

        # ── 结构缺口 ──
        orphans = sum(1 for n, (in_d, out_d) in node_degree.items()
                     if in_d == 0 and out_d > 0)
        deadends = sum(1 for n, (in_d, out_d) in node_degree.items()
                      if out_d == 0 and in_d > 0)
        if orphans + deadends > 0:
            findings.append(f"结构缺口: {orphans}个源头 + {deadends}个死胡同")

        # 语义类比: 向量最相似但不同域的节点对 (意义涌现)
        if len(self._node_vecs) >= 20:
            import math as _math
            def _cos_sim(a, b):
                dot = sum(a[j] * b[j] for j in range(self.SEMANTIC_DIM))
                na = _math.sqrt(sum(v * v for v in a))
                nb = _math.sqrt(sum(v * v for v in b))
                return dot / max(na * nb, 1e-10)
            # 取度数top-100的高连接节点
            top_nodes = [n for n, _ in sorted_nodes[:100] if n in self._node_vecs]
            analogies = []
            for i, ni in enumerate(top_nodes):
                vi = self._node_vecs[ni]
                di = node_domain_count.get(ni, 0)
                for nj in top_nodes[i + 1:]:
                    vj = self._node_vecs[nj]
                    dj = node_domain_count.get(nj, 0)
                    if di >= 2 and dj >= 2 and di != dj:
                        sim = _cos_sim(vi, vj)
                        if sim > 0.7:
                            analogies.append((ni, nj, sim))
                    if len(analogies) >= 5:
                        break
                if len(analogies) >= 5:
                    break
            if analogies:
                analogies.sort(key=lambda x: -x[2])
                ana_str = " | ".join(
                    f"{a[:12]}≈{b[:12]}({s:.2f})"
                    for a, b, s in analogies[:3]
                )
                findings.append(f"类比: {ana_str}")

        if findings:
            print(f"  [STRUCT] {' | '.join(findings)}")

        # ── 元认知注入: 把脑自己的状态写入因果图 (_meta: 节点) ──
        # 原则: 只给容量不给方法。脑自己决定这些信息有什么用。
        # 神经元可以walk到_meta节点, coincidence/compose机制会自然发现
        # 认知状态之间的因果关联。
        if not hasattr(self, '_meta_values'):
            self._meta_values = {}
        if not hasattr(self, '_meta_cooldown'):
            self._meta_cooldown = {}

        # 当前认知指标
        explore_val = 0.0
        if self.cells:
            explore_val = sum(c.genome.get('step_forward', 0) + c.genome.get('step_backward', 0)
                            for c in self.cells) / len(self.cells)
        current_meta = {
            'neurons': len(self.cells),
            'synapses': self.graph.edge_count,
            'paths': len(self._known_paths),
            'composed': len(getattr(self, '_composed_birth', {})),
            'contradictions': len(self._contradiction_nodes),
            'dead_ends': deadends,
            'orphans': orphans,
            'explore': round(explore_val, 3),
        }

        # 为每个指标建 _meta: 节点, 并建从前值到当前值的因果边 (时序自连)
        for metric, value in current_meta.items():
            node_id = f'_meta:{metric}'
            self._ensure_node(node_id)
            prev = self._meta_values.get(metric)
            if prev is not None and prev != value:
                prev_id = f'_meta:prev_{metric}'
                self._ensure_node(prev_id)
                # 前值 → 当前值: "前一个状态导致了当前状态"
                exists = any(e[1] == node_id for e in self.graph.get(prev_id, {}).get('effects', []))
                if not exists:
                    self.graph[prev_id].setdefault('effects', []).append(
                        ('meta_shift', node_id, 'meta'))
                    self.graph[node_id].setdefault('causes', []).append(
                        (prev_id, 'meta_shift', 'meta'))

        self._meta_values = dict(current_meta)

    def _sleep_replay(self):
        print(f"  [SLEEP-IN] entering sleep gen={self.generation}", flush=True)
        """睡眠 = 突触归一化 (SHY假说)
        
        醒着: 突触净增强 → s值上升
        睡着: 全眼下缩放 s×0.7, 弱边自然归零, 无硬阈值
        
        s值就是连接概率 — 0.3=30%传信号, 接近0=自然消失。
        用进废退: 经常走的边 s 高, 不走的边自然衰减归零。
        """
        # 1. 差异化衰减: s越高衰减越慢 (强边保留, 弱边加速清除)
        #    s=0.9→0.81(-10%), s=0.5→0.40(-20%), s=0.1→0.06(-40%)
        for key, edge in list(self.synapse.activations.items()):
            s = edge['s']
            # 强边: s×0.9, 中等: s×0.8, 弱边: s×0.6~0.7
            decay = 0.95 - 0.4 * max(0, min(1, 1 - s))
            edge['s'] *= max(0.7, min(0.9, decay))  # clamp [0.7, 0.9]
            edge['c'] = max(1, int(edge['c'] * 0.8))
        
        # 2. 自然淘汰: s<0.01 的边视为消失 (极低, 跟0没区别)
        eliminated = []
        for key, edge in list(self.synapse.activations.items()):
            if edge['s'] < 0.01:
                eliminated.append(key)
        for key in eliminated:
            self.synapse.activations.pop(key, None)
            self.synapse.tiers.pop(key, None)
        
        
        # 3. 反向重放: 倒走最强路径, 可能发现捷径
        from meta_cognition.synaptic_layer import neuron_fire_on_path
        reversed_paths = 0
        for cell in self.cells:
            if cell.walk_memory:
                best = max(cell.walk_memory, key=lambda w: len(w))
                # 反向: 每步 (src, law, dst) → (dst, "sleep_rev", src)
                rev = []
                for s in reversed(best):
                    if len(s) >= 3:
                        rev.append((s[2], "sleep_rev", s[0]))
                saved = cell.current_walk
                cell.current_walk = rev
                neuron_fire_on_path(cell, self.synapse, self.generation,
                                   strength=0.3)  # 弱强化: 反向路径探索性
                cell.current_walk = saved
                reversed_paths += 1
        
        # 4. ☁️ 全云离线巩固: 域多样性采样 + 高价值路径强化更强
        # 云架构: 所有细胞都在一张图上, 采样不再区分冷热
        cloud_replayed = 0
        all_cells_with_memory = [c for c in self.cells if getattr(c, 'walk_memory', None)]
        if all_cells_with_memory:
            sample_n = min(len(all_cells_with_memory), max(100, len(all_cells_with_memory) // 10))
            # 🏋️ 睡眠优先高s路径: 计算每个细胞的平均路径s值
            def _cell_avg_s(cell):
                walks = getattr(cell, 'walk_memory', [])
                total_s = 0.0
                n_steps = 0
                for w in walks:
                    for step in w:
                        if len(step) >= 3:
                            key = (step[0], step[2])
                            act = self.synapse.activations.get(key, {})
                            total_s += act.get('s', 0) if isinstance(act, dict) else 0
                            n_steps += 1
                return total_s / max(n_steps, 1)
            # 域多样性
            domain_count: dict = {}
            diverse = []
            max_per_domain = max(5, sample_n // 5)
            # 排序: total_reward + avg_s 综合 (高s路径的细胞优先被replay)
            for cell in sorted(all_cells_with_memory,
                               key=lambda c: c.total_reward + _cell_avg_s(c) * 5,
                               reverse=True):
                domains = set()
                for w in getattr(cell, 'walk_memory', []):
                    for s in w:
                        if len(s) >= 4:
                            domains.add(s[3])
                key = frozenset(domains) if domains else "__unknown__"
                if domain_count.get(key, 0) < max_per_domain:
                    diverse.append(cell)
                    domain_count[key] = domain_count.get(key, 0) + 1
                if len(diverse) >= sample_n:
                    break
            for cell in diverse:
                walks = getattr(cell, 'walk_memory', [])
                if not walks:
                    continue
                best = max(walks, key=len) if walks else None
                if best and len(best) >= 2:
                    strength = 0.25 if cell.total_reward > 10 else 0.12
                    for step in best:
                        if len(step) >= 3:
                            self.synapse.strengthen(0, step[0], step[2], strength, self.generation)
                    cloud_replayed += 1
        
        # 5. 🧠 海马体前向组合: 跨路径多步推理 → 发现长程因果
        composed = 0
        # 收集所有 walk_memory 路径 (全云采样)
        all_walks = []
        sample_cells = self.cells[:min(800, len(self.cells))]  # 云架构: 统一采样
        for cell in sample_cells:
            for w in getattr(cell, 'walk_memory', [])[-3:]:
                if len(w) >= 2:
                    all_walks.append(w)
        
        # 路径组合: 共享任意节点即可组合 (不要求首尾精确匹配)
        for i, w1 in enumerate(all_walks):
            # 提取 w1 的所有节点
            w1_nodes = {}
            for step in w1:
                if len(step) >= 3:
                    w1_nodes[step[2]] = step  # dst → step
            w1_start = w1[0][0] if w1 else None
            if not w1_start or not w1_nodes: continue
            
            for j, w2 in enumerate(all_walks):
                if i == j: continue
                w2_start = w2[0][0] if w2 else None
                w2_end = w2[-1][2] if len(w2[-1]) >= 3 else None
                if not w2_start or not w2_end: continue
                if w1_start == w2_end: continue  # 自环
                
                # 找共享节点: w1 的任意节点 == w2 的任意节点
                shared = None
                for step2 in w2:
                    if len(step2) >= 3 and step2[2] in w1_nodes:
                        shared = step2[2]
                        break
                
                if shared and shared != w1_start and shared != w2_end:
                    # 防止 hyp 节点递归: 不组合 hyp 节点间的 composed 边
                    if w1_start.startswith(self.HYPNODE_PREFIX) or w2_end.startswith(self.HYPNODE_PREFIX):
                        continue
                    # 🧹 质量门: 两端都要有 VALID 域边 (过滤垃圾token组合)
                    def _has_valid_domain(node_id):
                        nd = self.graph.get(node_id, {})
                        return any(d in self.VALID_EDGE_DOMAINS for _, _, d in nd.get('effects', []))
                    if not _has_valid_domain(w1_start) or not _has_valid_domain(w2_end):
                        continue
                    # 检查是否已有边
                    key = (w1_start, w2_end)
                    if key in self.synapse.activations: continue
                    
                    # 添加组合捷径
                    self.synapse.strengthen(0, w1_start, w2_end, 
                                           0.25, self.generation)
                    # 写入图
                    self._ensure_node(w1_start)
                    self._ensure_node(w2_end)
                    exists = any(e[1] == w2_end for e in 
                                self.graph[w1_start].get('effects',[]))
                    if not exists:
                        self.graph[w1_start].setdefault('effects',[]).append(
                            ('sleep_composed', w2_end, 'emergent'))
                        self.graph[w2_end].setdefault('causes',[]).append(
                            (w1_start, 'sleep_composed', 'emergent'))
                    composed += 1
                    self._composed_birth[key] = self.generation  # 记录出生代
                    if composed >= 400: break
            if composed >= 400: break
        
        if eliminated or composed or True:  # 总是汇报
            print(f"  [SLEEP] -{len(eliminated)} edges pruned, "
                  f"{reversed_paths} active + {cloud_replayed} cloud replayed"
                  f"{' +'+str(composed)+' composed' if composed else ''}"
                  f" (gen {self.generation})")

        # 🧹 睡眠内务: 清醒期脏着跑, 睡眠时集中打理
        self._strip_cold_edges()          # 剥离纯冷边
        self._sort_graph_by_edge_s()      # 按 s 值重排边序
        self._audit_t3_noise()            # 清理弱 t3 噪声
        self._prune_stale_emergent()      # 🧠 持续清理: 没人走的 emergent 标签摘除
        # ☁️ 消化 walk 缓冲区
        self._digest_walk_buffer()        # 超50代 walk → 突触权重
        # ☁️ 磁盘种子库采样回放
        shelf_replayed = 0
        if self._cell_shelf:
            shelf_nodes = random.sample(list(self._cell_shelf.keys()),
                                        min(30, len(self._cell_shelf)))
            for node in shelf_nodes:
                for seed in self._cell_shelf.get(node, [])[:3]:
                    # 临时孵化 → 强化 seed 关联的基因组倾向
                    # 不创建完整细胞，只用基因组权重播种随机探测边
                    targets = list(self.graph.keys())
                    if targets:
                        for _ in range(3):
                            tgt = random.choice(targets)
                            if tgt != node:
                                self.synapse.strengthen(0, node, tgt, 0.05, self.generation)
                    shelf_replayed += 1
            if shelf_replayed:
                print(f"  ☁️ shelf: {shelf_replayed} genomes replayed")
        # 🧠 sympy 推导感知: coincidence 热点自动验证
        self.derive_perception.try_derive_from_hotspots(self)
        # 🔗 因果闭包: 结构一致性约束 — 悬挂效应节点必须补链 (QFT: 对称性→规范场)
        self._enforce_causal_closure()

    # ═══════ 内存 ═══════

    def _enforce_causal_closure(self):
        """因果闭包约束: 每个有 effects 的节点必须有 cause-chain 到 tier≤1。

        这不是优化——是图必须满足的结构约束。
        类比 QFT: 局域对称性不满足→拉氏量不自洽→逼出规范场。
        这里: 效应节点悬挂→因果链断裂→逼出补边。

        只在睡眠时运行，每次最多修补 3 个悬挂节点。
        """
        # 初始化修复记录集（同一次 run 内不重复修）
        if not hasattr(self, '_closure_fixed'):
            self._closure_fixed: set = set()
        # 1. 收集所有 tier≤1 的已知原理节点（因果锚点）
        anchor_nodes: set = set()
        for key, tier in self.synapse.tiers.items():
            if tier <= 1:
                src, dst = key if isinstance(key, tuple) else (key, None)
                if isinstance(src, str): anchor_nodes.add(src)
                if isinstance(dst, str): anchor_nodes.add(dst)
        # 补充：图中有 causes 到 tier≤1 边的节点也算锚点
        for node_id, nd in self.graph.items():
            if not isinstance(nd, dict): continue
            for cause_entry in nd.get('causes', []):
                if len(cause_entry) >= 3 and cause_entry[2] in self.VALID_EDGE_DOMAINS:
                    anchor_nodes.add(node_id)
                    break

        if not anchor_nodes:
            return

        # 2. 收集有 effects 的活跃节点
        effect_nodes = []
        for node_id, nd in self.graph.items():
            if not isinstance(nd, dict): continue
            effects = nd.get('effects', [])
            if not effects: continue
            # 跳过 hyp 前缀和短噪音节点
            if node_id.startswith(self.HYPNODE_PREFIX): continue
            if len(node_id) < 2: continue
            effect_nodes.append(node_id)

        if not effect_nodes:
            return

        # 3. 反向 BFS: 找悬挂节点（无 cause-chain 到锚点）
        dangling = []
        for node_id in effect_nodes:
            if node_id in anchor_nodes:
                continue
            # 反向 BFS，深度限制 8
            visited = {node_id}
            frontier = [node_id]
            reachable = False
            for _ in range(8):
                next_frontier = []
                for n in frontier:
                    nd = self.graph.get(n)
                    if not isinstance(nd, dict): continue
                    for cause_entry in nd.get('causes', []):
                        src = cause_entry[0] if len(cause_entry) >= 1 else None
                        if src and src not in visited:
                            if src in anchor_nodes:
                                reachable = True
                                break
                            visited.add(src)
                            next_frontier.append(src)
                    if reachable: break
                if reachable: break
                frontier = next_frontier
                if not frontier: break

            if not reachable:
                dangling.append(node_id)

        if not dangling:
            return

        repaired = 0
        for node_id in dangling[:3]:  # 每次最多修 3 个
            # 去重: 同一次 run 内已修过的不重复
            if node_id in self._closure_fixed:
                continue
            # 尝试用 derive 找到到锚点的路径
            best_edge = self._find_closure_edge(node_id, anchor_nodes)
            if best_edge:
                src, dst, formula = best_edge
                key = (src, dst)
                if key not in self.synapse.activations:
                    self.synapse.strengthen(0, src, dst, 0.35, self.generation)
                self.synapse.tiers[key] = 0  # 因果闭包边 = 公理级（tier0），成为新锚点
                # 用 add_edge 双写 VSA+缓存，避免 rebuild 覆盖
                self.graph.add_edge(src, dst, 'causal_closure', 'axomatic')
                self._record_discovery(f"{src}->{dst}", "causal_closure",
                                       f"formula={formula}")
                # 防 VSA 重建覆盖: 清除 dirty 标记，保护手动添加的因果边
                self.graph._dirty.discard(src)
                self.graph._dirty.discard(dst)
                self._closure_fixed.add(node_id)  # 记录已修复
                repaired += 1
                if repaired == 1:
                    print(f"  [CLOSURE] {src} --[{formula}]--> {dst} (dangling→anchored)")

        if repaired:
            print(f"  [CLOSURE] {repaired}/{len(dangling[:3])} dangling nodes repaired (gen {self.generation})")

    def _find_closure_edge(self, node_id: str, anchor_nodes: set):
        """为悬挂节点找一条到锚点的闭包边。优先用 sympy derive。"""
        from physics.math_derive import derive
        # 优先尝试直接 derive 到锚点
        for anchor in list(anchor_nodes)[:30]:
            try:
                result = derive(anchor, node_id) or derive(node_id, anchor)
                if result and result.get('success'):
                    formula = str(result.get('relation', result.get('steps', ['?'])[0]))[:60]
                    return (anchor, node_id, formula)
            except Exception:
                continue
        # 回退: 用 effects 的终点作为桥接目标
        nd = self.graph.get(node_id, {})
        if isinstance(nd, dict):
            for eff in nd.get('effects', [])[:5]:
                target = eff[1] if len(eff) >= 2 else None
                if not target or target == node_id: continue
                for anchor in list(anchor_nodes)[:10]:
                    try:
                        r1 = derive(anchor, node_id)
                        if not (r1 and r1.get('success')): continue
                        r2 = derive(node_id, target)
                        if not (r2 and r2.get('success')): continue
                        formula = f"{str(r1.get('relation','?'))[:20]}→{str(r2.get('relation','?'))[:20]}"
                        return (anchor, target, formula)
                    except Exception:
                        continue
        return None

    # ═══════ 内存 ═══════

    def _check_memory_pressure(self):
        """每100代: 读取系统内存, 应对压力"""
        try:
            with open('/proc/self/status') as f:
                for line in f:
                    if line.startswith('VmRSS:'):
                        rss_kb = int(line.split()[1])
                        break
                else:
                    return
            rss_mb = rss_kb / 1024
            with open('/proc/meminfo') as f:
                for line in f:
                    if line.startswith('MemTotal:'):
                        total_kb = int(line.split()[1])
                        break
            total_mb = total_kb / 1024
            fraction = rss_mb / total_mb
            if fraction > self.MEMORY_CRITICAL_FRACTION:
                self._carrying_capacity = max(500, self._carrying_capacity // 2)
                self.synapse.LTD_WINDOW = max(50, self.synapse.LTD_WINDOW // 2)
                self._save_critical_state()
                print(f"\n  [MEM_CRIT] RSS={rss_mb:.0f}MB ({fraction*100:.0f}%) K={self._carrying_capacity}")
            elif fraction > self.MEMORY_FLUSH_FRACTION:
                self._carrying_capacity = max(800, int(self._carrying_capacity * 0.7))
                self._save_critical_state()
                if hasattr(self, '_coincidence') and len(self._coincidence) > 100000:
                    ranked = sorted(self._coincidence.items(), key=lambda x: -x[1])
                    self._coincidence = dict(ranked[:100000])
                import gc; gc.collect()
                print(f"\n  [MEM_FLUSH] RSS={rss_mb:.0f}MB ({fraction*100:.0f}%) K={self._carrying_capacity}")
            elif fraction > self.MEMORY_WARN_FRACTION:
                self._carrying_capacity = max(1000, int(self._carrying_capacity * 0.8))
                self.synapse.LTD_WINDOW = max(100, int(self.synapse.LTD_WINDOW * 0.8))
                self._save_critical_state()
                print(f"\n  [MEM_WARN] RSS={rss_mb:.0f}MB ({fraction*100:.0f}%) K={self._carrying_capacity}")
        except Exception:
            pass

    def _homeostasis(self):
        """每代执行: K更新 + 反馈环 + 分裂门槛调节 (轻量, 无IO)"""
        graph_nodes = len(self.graph)
        # 边数: 只数缓存 (避免全图 VSA 扫描)
        graph_edges = sum(len(n.get("effects", [])) for n in self.graph._cache.values())
        # K 只看图复杂度, 冷池不参与 (冷池是硬盘, 不影响内存大小)
        target_k = max(5000, graph_nodes * 3 + graph_edges // 1000)
        if self._carrying_capacity < target_k:
            self._carrying_capacity = min(target_k, int(self._carrying_capacity * 1.2))
            if self.synapse.LTD_WINDOW < 300:
                self.synapse.LTD_WINDOW = min(300, self.synapse.LTD_WINDOW + 20)
        elif self._carrying_capacity > target_k:
            # K 过高 → 缓慢收缩 (避免锁死在高位)
            self._carrying_capacity = max(target_k, int(self._carrying_capacity * 0.95))
        self.ACTIVE_POOL = max(5000, self._carrying_capacity // 2)
        # 自稳态: 局部密度竞争为主力, 全局密度死亡为软后盾
        density = len(self.cells) / max(self._carrying_capacity, 1)
        if density > 5.0:  # 只有极端拥挤才加压 (5x K = 20000+)
            self.DENSITY_DEATH_MAX_RATE = min(0.30, self.DENSITY_DEATH_MAX_RATE * 1.05)
            self.STARVATION_DEATH_RATE = min(0.12, self.STARVATION_DEATH_RATE * 1.03)
        elif density < 1.0 and len(self.cells) > 100:
            self.DENSITY_DEATH_MAX_RATE = max(0.03, self.DENSITY_DEATH_MAX_RATE * 0.97)
            self.STARVATION_DEATH_RATE = max(0.01, self.STARVATION_DEATH_RATE * 0.97)
        # 分裂门槛: 图越大需要越多探索→门槛降低, 但基础高 (代谢税压着)
        self.MIN_SPLIT_REWARD = max(2.0, 5.0 - graph_nodes / 500)
        # 更新所有活跃细胞的门槛
        for cell in self.cells:
            cell.min_split_reward = self.MIN_SPLIT_REWARD

    # ═══════ arXiv 验证: 只验证不产新知识 ═══════

    def _validate_with_arxiv(self):
        """验证最近的 math_verified 边: 搜 arXiv 确认, 只调 tier 不进图"""
        # 收集最近未验证的 math_verified 边
        candidates = []
        for key, edge in self.synapse.activations.items():
            # 只查 math_verified 域且未被 arXiv 验证过的边
            if not edge.get('n') or len(edge.get('n', set())) < 1:
                continue
            src, dst = key
            # 跳过已验证的
            if self.synapse.external_validated.get(key):
                continue
            # 检查图中是否有 math_verified 边
            graph_entry = self.graph.get(src, {})
            has_math = any(
                isinstance(e, (list, tuple)) and len(e) >= 3 and e[2] == 'math_verified'
                for e in graph_entry.get('effects', [])
                if isinstance(e, (list, tuple)) and len(e) >= 2 and e[1] == dst
            )
            if has_math:
                candidates.append((src, dst, edge))

        if not candidates:
            return

        # 每次最多验证 2 条 (节约 arXiv API)
        for src, dst, edge in candidates[:2]:
            query = f"{src.replace('_',' ')} {dst.replace('_',' ')} physics"
            try:
                from session.paper_ingest import search_arxiv
                papers = search_arxiv(query, max_results=3)
            except Exception:
                continue

            if not papers or "error" in papers[0]:
                continue

            # 检查论文是否同时涉及两个概念
            found = False
            for paper in papers[:3]:
                title = paper.get("title", "").lower()
                abstract = paper.get("abstract", paper.get("summary", "")).lower()
                src_words = set(src.replace('_', ' ').lower().split())
                dst_words = set(dst.replace('_', ' ').lower().split())
                text = title + " " + abstract
                # 两个概念的关键词都出现
                src_hit = any(w in text for w in src_words if len(w) > 2)
                dst_hit = any(w in text for w in dst_words if len(w) > 2)
                if src_hit and dst_hit:
                    found = True
                    print(f"  [ARXIV-V] {src[:20]}→{dst[:20]} confirmed by \"{title[:50]}\"")
                    break

            key = (src, dst)
            if found:
                # 论文确认 → 标记外部验证, boost 置信度
                self.synapse.external_validated[key] = True
                edge['s'] = min(2.0, edge.get('s', 0.5) * 1.5)
                if self.synapse.tiers.get(key, 4) > 2:
                    self.synapse.tiers[key] = 2
            else:
                # 没找到论文 → 可能新颖
                edge['s'] *= 1.1  # 轻微 boost (未被别人发现, 可能原创)
                print(f"  [ARXIV-V] {src[:20]}→{dst[:20]} no paper found (potentially novel)")

    # ═══════ 研究循环 ═══════

    def _check_and_feed(self):
        current = len(self._known_paths)
        self._path_rates.append((self.generation, current))
        if len(self._path_rates) > 5:
            self._path_rates = self._path_rates[-5:]

        current_edges = sum(len(n.get("effects", [])) for n in self.graph._cache.values())
        self._edge_history.append((self.generation, current_edges))
        if len(self._edge_history) > 10:
            self._edge_history = self._edge_history[-10:]

        edge_stagnation = False
        gen_span = edge_delta = 0
        if len(self._edge_history) >= 3:
            oldest = self._edge_history[0]
            newest = self._edge_history[-1]
            gen_span = newest[0] - oldest[0]
            edge_delta = newest[1] - oldest[1]
            if gen_span >= 200 and edge_delta <= 2:
                edge_stagnation = True

        path_drop = False
        current_rate = 0
        if len(self._path_rates) >= 2:
            gen_diff = self._path_rates[-1][0] - self._path_rates[-2][0]
            path_diff = self._path_rates[-1][1] - self._path_rates[-2][1]
            if gen_diff > 0:
                current_rate = path_diff / gen_diff
                self._peak_rate = max(self._peak_rate, current_rate)
                path_drop = current_rate < self._peak_rate * 0.6 and self._peak_rate > 10

        cooldown_ok = self.generation - self._last_research_gen >= 100
        triggered = False
        if edge_stagnation and cooldown_ok:
            print(f"\n  [STAGNATE] {gen_span}gen +{edge_delta}edges -> arXiv")
            triggered = True
        elif path_drop and cooldown_ok:
            print(f"\n  [EFF_DROP] {current_rate:.0f}/gen (peak {self._peak_rate:.0f}) -> arXiv")
            triggered = True
        elif cooldown_ok and self.generation - self._last_research_gen >= 2000:
            print(f"\n  [PERIODIC] gen{self.generation} -> arXiv")
            triggered = True
        elif cooldown_ok and self.generation - self._last_research_gen >= 150:
            # t3 积压: 假说够多就喂 arXiv 验证
            t3_count = sum(1 for k in self.synapse.activations if self.synapse.tiers.get(k, 4) == 3)
            if t3_count >= 200:
                print(f"\n  [T3_BACKLOG] {t3_count} hypotheses -> arXiv")
                triggered = True

        if triggered:
            self._research_cycle()
            self._last_research_gen = self.generation
            self._peak_rate = 0

    def _research_cycle(self):
        self._research_count = getattr(self, '_research_count', 0) + 1
        # 目标词集: 用于假说相关性排序
        goal_words = set()
        for goal_name in self._active_goals:
            goal_words.update(goal_name.replace('_', ' ').split())
        scored = []
        for key in self.synapse.activations:
            if self.synapse.tiers.get(key, 4) == 3:
                edge = self.synapse.activations[key]
                src, dst = key[0], key[1]
                neurons = len(edge['n'])
                # 词重叠: 假说节点跟目标节点共享词数
                node_words = set(src.replace('_', ' ').split()) | set(dst.replace('_', ' ').split())
                overlap = len(node_words & goal_words)
                is_goal_related = 1 if overlap > 0 else 0
                score = neurons * (1 + overlap * 0.5)
                scored.append((src, dst, neurons, is_goal_related, score))
        if not scored:
            print("   no tier3, skip")
            return
        # 两阶段: 目标相关优先, 同组内按加权分降序
        scored.sort(key=lambda x: (-x[3], -x[4]))
        t3 = [(s[0], s[1], s[2]) for s in scored]
        goal_related = sum(1 for s in scored if s[3])
        print(f"   top 5 tier3 ({len(scored)} total, {goal_related} goal-related):")
        total_injected = 0
        try:
            from session.paper_ingest import search_arxiv
            for src, dst, neurons in t3[:5]:
                query = f"{src} {dst}".replace('_', ' ')
                print(f"     [{neurons}n] {src[:25]} -> {dst[:25]}")
                try:
                    papers = search_arxiv(query, max_results=2)
                except Exception:
                    print(f"        arXiv unreachable")
                    continue
                if not papers or "error" in papers[0]:
                    continue
                for paper in papers[:1]:
                    title = paper.get("title", "")[:70]
                    abstract = paper.get("abstract", paper.get("summary", ""))[:800]
                    arxiv_id = paper.get("arxiv_id", "")
                    print(f"        {title}")
                    triples = self._extract_relations(
                        f"Title: {title}\nAbstract: {abstract}", src, dst)
                    new_nodes_injected = []
                    for subj, rel, obj in triples:
                        for node in (subj, obj):
                            if node not in self.graph:
                                self.graph[node] = {"causes": [], "effects": []}
                                new_nodes_injected.append(node)
                        if not any(e[1] == obj for e in self.graph[subj].get("effects", [])):
                            self.graph[subj]["effects"].append(
                                (f"llm:{arxiv_id}:{rel}", obj, "research"))
                            self.graph[obj]["causes"].append(
                                (subj, f"llm:{arxiv_id}:{rel}", "research"))
                            total_injected += 1
                        for node in (subj, obj):
                            if node in new_nodes_injected:
                                node_words = set(node.replace('_', ' ').split())
                                cross_links = 0
                                for existing in list(self.graph.keys())[:200]:
                                    if existing in (subj, obj, node):
                                        continue
                                    existing_words = set(existing.replace('_', ' ').split())
                                    if len(node_words & existing_words) >= 1:
                                        if not any(e[1] == existing for e in self.graph[node].get("effects", [])):
                                            self.graph[node]["effects"].append(
                                                (f"llm:x:{rel}", existing, "research"))
                                            self.graph[existing]["causes"].append(
                                                (node, f"llm:x:{rel}", "research"))
                                            cross_links += 1
                                            total_injected += 1
                                        if cross_links >= 3:
                                            break
                    if triples:
                        rel_str = ", ".join(f"{s}->{d}" for s, r, d in triples[:3])
                        print(f"        +{len(triples)} causal edges: {rel_str}")
                        # 长期记忆: 记录自主发现
                        for s, r, d in triples:
                            self._record_discovery(f"{s}->{d}", "autonomous",
                                f"from arXiv {arxiv_id}: {title[:60]}")
                    if new_nodes_injected:
                        self._broadcast_knowledge_dopamine(new_nodes_injected)
            if total_injected > 0:
                self._rebuild_graph()
                self._save_injected_edges()
                print(f"   research #{self._research_count}: +{total_injected} edges injected")
            else:
                print(f"   no concepts extracted")
        except Exception as e:
            print(f"   research failed: {e}")

    def _extract_relations(self, text: str, context_src: str = "", context_dst: str = ""):
        triples = []
        # 构建图词集: 用于过滤 LLM 产出的噪音概念
        _graph_words = set()
        for node in list(self.graph.keys())[:5000]:
            _graph_words.update(node.replace('_', ' ').split())
        for goal_name in self._active_goals:
            _graph_words.update(goal_name.replace('_', ' ').split())
        try:
            from llm.bridge import LLMBridge
            bridge = LLMBridge()
            if bridge.is_available():
                prompt = f"""Extract causal relationships from this physics text as triples (source, relation, target).
Use snake_case for node names. Return ONLY a JSON array: [["source", "relation", "target"], ...]
If no clear causal relation, return [].

Text: {text[:800]}

Context: this is related to the hypothesis "{context_src} -> {context_dst}".
"""
                response = bridge.client.chat([{"role": "user", "content": prompt}], max_tokens=300)
                import re as _re
                json_match = _re.search(r'\[.*\]', response, _re.DOTALL)
                if json_match:
                    raw = json.loads(json_match.group())
                    for item in raw:
                        if isinstance(item, list) and len(item) >= 3:
                            src = str(item[0]).strip().lower().replace(' ', '_')
                            rel = str(item[1]).strip().lower().replace(' ', '_')
                            dst = str(item[2]).strip().lower().replace(' ', '_')
                            # 过滤: 太短、停用词、通用噪音
                            GENERIC = {'title','abstract','paper','model','system','method',
                                       'result','data','approach','figure','table','section',
                                       'introduction','conclusion','background','related_work'}
                            if src in GENERIC or dst in GENERIC:
                                continue
                            if len(src) < 5 or len(dst) < 5:
                                continue
                            # 图锚定: 至少一个概念跟现有图或目标有词重叠, 否则算噪音
                            src_words = set(src.split('_'))
                            dst_words = set(dst.split('_'))
                            if not (src_words & _graph_words or dst_words & _graph_words):
                                continue
                            if src and dst and src != dst:
                                triples.append((src, rel, dst))
        except Exception:
            pass
        if not triples:
            concepts = self._extract_concepts_from_title(text, context_src, context_dst)
            for c in concepts:
                triples.append((context_src, "related_to", c))
                triples.append((c, "related_to", context_dst))
        return triples

    def _extract_concepts_from_title(self, title: str, src: str, dst: str):
        import re as _re
        words = _re.findall(r'[A-Z][a-z]+(?:_[a-z]+)*|[a-z]+(?:_[a-z]+)+', title)
        stop = {'the','a','an','of','in','on','for','to','and','or','with',
                'by','from','is','are','was','were','be','been','being',
                'have','has','had','do','does','did','will','would','could',
                'should','may','might','can','shall','new','using','based',
                'its','their','our','we'}
        concepts = []
        for w in words:
            wl = w.lower()
            if wl in stop or len(wl) < 4:
                continue
            if wl == src.lower() or wl == dst.lower():
                continue
            if wl not in self.graph:
                concepts.append(w)
        return concepts[:5]

    def _broadcast_knowledge_dopamine(self, new_nodes: List[str]):
        if not new_nodes or not self.cells:
            return
        new_set = set(new_nodes)
        pulsed = 0
        attracted = 0
        hotspot = new_nodes[0]  # 注意力焦点
        for cell in self.cells:
            neighbors = self._neighbors_of(cell.node)
            neighbors.add(cell.node)
            if neighbors & new_set:
                cell.give_energy(1.0)
                self.total_rewards += 1.0
                pulsed += 1
            # 注意力: 20%概率被热点吸引,设置导航目标
            elif random.random() < 0.2:
                cell.goal = hotspot
                attracted += 1
        if pulsed:
            print(f"     [DOPA_BROADCAST] {pulsed} pulsed + {attracted} attracted → {hotspot[:30]}")
            self._dopa_cohort = getattr(self, '_dopa_cohort', {})
            cohort_id = self.generation
            for cell in self.cells:
                if cell.node in new_set or any(
                    n in new_set for n in self._neighbors_of(cell.node)
                ):
                    self._dopa_cohort[id(cell)] = cohort_id
                    cell.goal = hotspot  # 强化: 附近神经元也设目标

    def _feed_knowledge(self):
        try:
            from physics.feed_knowledge import feed_knowledge
            n = feed_knowledge()
            if n > 0:
                self._rebuild_graph()
                print(f"  [LOCAL_FEED] #{self._feed_count}: +{n} laws")
                return
        except Exception:
            pass
        self._arxiv_feed()

    def _arxiv_feed(self):
        nodes = Counter(c.node for c in self.cells)
        hotspots = [n for n, _ in nodes.most_common(5)]
        if not hotspots:
            return
        query = " ".join(h.replace("_", " ") for h in hotspots[:3])
        print(f"  [ARXIV] search: {query}")
        try:
            from session.paper_ingest import search_arxiv, ingest_paper
            from llm.bridge import LLMBridge
            papers = search_arxiv(query, max_results=3)
            if not papers or "error" in papers[0]:
                return
            bridge = LLMBridge()
            if not bridge.is_available():
                return
            total_new = 0
            for paper in papers[:2]:
                title = paper.get("title", "")[:60]
                print(f"  {title}...")
                try:
                    result = ingest_paper(paper["arxiv_id"], bridge.client)
                    extracted = result.get("extracted", 0)
                    if extracted > 0:
                        total_new += extracted
                except Exception:
                    pass
            if total_new > 0:
                self._rebuild_graph()
                self._feed_count += 1
                print(f"  [ARXIV_FEED] #{self._feed_count}: +{total_new} edges")
                validated = 0
                for key in list(self.synapse.tiers.keys()):
                    if self.synapse.tiers[key] == 3:
                        src, dst = key
                        if self._has_path_in_graph(src, dst):
                            self.synapse.validate_externally(src, dst)
                            validated += 1
                if validated:
                    print(f"  {validated} tier3 validated -> tier2")
        except Exception:
            pass

    # ═══════ 图持久化 ═══════

    def _rebuild_graph(self):
        """VSA 模式下边持久叠加，不需要重建。只需刷新细胞引用和特征。"""
        # 更新所有活细胞的图引用
        for cell in self.cells:
            cell.graph = self.graph
        self._build_graph_features()
        self._save_injected_edges()
        # VSA 自动处理冷热边 — 不再需要 strip

    def _strip_cold_edges(self):
        """VSA 模式下冷边不需要剥离 — 所有边都在向量叠加中"""
        pass

    def _sort_graph_by_edge_s(self):
        """VSA 查询已按得分排序, 不需要手动重排"""
        pass

    def _audit_t3_noise(self):
        """睡眠审计: 弱 t3 假说(s<0.05)降级为t4未分类, 让强的重新验证"""
        if not hasattr(self, 'synapse'):
            return
        tiers = getattr(self.synapse, 'tiers', {})
        acts = getattr(self.synapse, 'activations', {})
        demoted = 0
        for key, tier in list(tiers.items()):
            if tier == 3:
                s_val = acts.get(key, {}).get('s', 0)
                if s_val < 0.05:
                    tiers[key] = 4  # 2026-07-30 FIX: was 0 (公理), should be 4 (未分类)
                    demoted += 1
        if demoted:
            print(f"  [SLEEP_T3] {demoted} weak t3 demoted (s<0.05)")

    def _injected_path(self):
        return os.path.join(os.path.dirname(__file__), "..", "data", "injected_edges.json")

    def _save_injected_edges(self):
        try:
            edges = []
            for src, node in self.graph._cache.items():
                for law_name, dst, domain in node.get("effects", []):
                    if domain in ("research", "abstraction", "derive"):
                        edges.append([src, law_name, dst, domain])
            with open(self._injected_path(), 'w') as f:
                json.dump(edges, f, ensure_ascii=False)
        except Exception:
            pass

    def _load_injected_edges(self):
        path = self._injected_path()
        if not os.path.exists(path):
            return 0
        try:
            with open(path) as f:
                edges = json.load(f)
            restored = 0
            for src, law_name, dst, domain in edges:
                self._ensure_node(src)
                self._ensure_node(dst)
                exists = any(e[1] == dst and e[2] == domain
                            for e in self.graph[src]["effects"])
                if not exists:
                    self.graph.add_edge(src, dst, law_name, "domain")
                    restored += 1
            if restored:
                print(f"[INJECTED_LOAD] +{restored} edges (research/abstraction)")
            return restored
        except Exception:
            return 0

    def _load_teacher_trajectories(self):
        """加载教师研究轨迹 —— 社会模仿/镜像学习的数据源
        
        同时将轨迹节点和边注入图，使细胞能 walk through 教师研究链。
        边标记为 research 域，处于 tier 4 不受严谨推导污染。
        """
        from pathlib import Path
        path = Path(__file__).parent.parent / "data" / "teacher_trajectories.json"
        if not path.exists():
            self._teacher_trajectories = []
            return
        try:
            with open(path) as f:
                self._teacher_trajectories = json.load(f)
            seeded_edges = 0
            self._teacher_edge_set = set()  # {(src,dst)} 用于注意偏向
            for traj in self._teacher_trajectories:
                nodes = traj.get("nodes", [])
                for node in nodes:
                    self._ensure_node(node)
                    self._priority_nodes.add(node)
                for i in range(len(nodes) - 1):
                    src, dst = nodes[i], nodes[i + 1]
                    self._teacher_edge_set.add((src, dst))
                    law_name = f"teacher:{traj['id']}_{i}"
                    domain = "research"
                    exists = any(e[1] == dst and e[2] == domain
                                for e in self.graph[src]["effects"])
                    if not exists:
                        self.graph.add_edge(src, dst, law_name, "domain")
                        seeded_edges += 1
            print(f"[TEACHER] {len(self._teacher_trajectories)} trajectories, "
                  f"{seeded_edges} edges seeded "
                  f"(e.g. {self._teacher_trajectories[0]['id']})")
        except Exception as e:
            print(f"[TEACHER] Failed to load trajectories: {e}")
            self._teacher_trajectories = []

    def _find_teacher_overlap(self, walk_nodes: list, min_match: int = 2):
        """检测细胞行走路径与教师轨迹的重叠。
        
        walk_nodes: 细胞走过的节点名序列 [src, dst1, dst2, ...]
        返回: (best_length, trajectory_id, matched_nodes) 或 (0, None, [])
        """
        if not self._teacher_trajectories or len(walk_nodes) < min_match:
            return (0, None, [])
        
        best_len = 0
        best_traj = None
        best_match = []
        
        for traj in self._teacher_trajectories:
            traj_nodes = traj.get("nodes", [])
            if len(traj_nodes) < min_match:
                continue
            for win_size in range(min(len(walk_nodes), len(traj_nodes)), min_match - 1, -1):
                if win_size <= best_len:
                    break
                for i in range(len(walk_nodes) - win_size + 1):
                    walk_seg = tuple(walk_nodes[i:i + win_size])
                    for j in range(len(traj_nodes) - win_size + 1):
                        if walk_seg == tuple(traj_nodes[j:j + win_size]):
                            if win_size > best_len:
                                best_len = win_size
                                best_traj = traj["id"]
                                best_match = list(walk_seg)
                            break
                    if best_len == win_size:
                        break
        
        return (best_len, best_traj, best_match)

    def _apply_teacher_overlap_reward(self, cell, walk: list, gen: int):
        """教师轨迹学习: 任何重叠都有小奖, 走到结果节点有头奖。
        
        两层奖励:
          学习层: 任何 ≥2 步重叠 → 能量 + STDP (阅读教科书)
          掌握层: 走到 result_node + ≥2 前序匹配 → 大奖 (演示掌握)
        人脑学物理: 先读懂前人, 再自己做发现。
        """
        if not self._teacher_trajectories or len(walk) < 2:
            return False
        
        walk_nodes = [walk[0][0]]
        for step in walk:
            walk_nodes.append(step[2])
        
        # ── 学习层: 任何重叠都有奖励 ──
        best_len, traj_id, matched_nodes = self._find_teacher_overlap(walk_nodes)
        
        if best_len < 2:
            return False
        
        # 学习奖励: 链越长回报越高, 但不爆炸
        LEARN_TABLE = {2: 0.3, 3: 0.6, 4: 1.2, 5: 2.0, 6: 3.0, 7: 4.5, 8: 6.0}
        energy_bonus = LEARN_TABLE.get(best_len, best_len * 0.8)
        cell.give_energy(energy_bonus)
        self.total_rewards += energy_bonus
        
        # 镜像突触加强
        from meta_cognition.synaptic_layer import mirror_strengthen
        mirror_mult = 1.0 + best_len * 0.15
        for i in range(len(walk_nodes) - 1):
            src, dst = walk_nodes[i], walk_nodes[i+1]
            for j in range(len(matched_nodes) - 1):
                if matched_nodes[j] == src and matched_nodes[j+1] == dst:
                    mirror_strengthen(self.synapse, src, dst, gen, multiplier=mirror_mult)
                    break
        
        # 后向信号
        if best_len >= 3:
            self.synapse.retrograde_signal(matched_nodes[0], valence=best_len * 0.1)
        self._teacher_overlap_count += 1
        
        # ── 掌握层: 终点是结果节点 → 额外大奖 ──
        last_node = walk_nodes[-1]
        mastery_bonus = False
        for traj in self._teacher_trajectories:
            result_node = traj.get("result_node", "")
            if last_node != result_node:
                continue
            traj_nodes = traj.get("nodes", [])
            if not traj_nodes:
                continue
            result_idx = None
            for idx, n in enumerate(traj_nodes):
                if n == result_node:
                    result_idx = idx
                    break
            if result_idx is None or result_idx < 1:
                continue
            # 反向匹配
            chain_len = 0
            for back_step in range(1, min(result_idx, len(walk_nodes)) + 1):
                walk_node = walk_nodes[-(back_step + 1)] if back_step < len(walk_nodes) else walk_nodes[0]
                if walk_node == traj_nodes[result_idx - back_step]:
                    chain_len += 1
                else:
                    break
            if chain_len >= 2:
                MASTERY_BONUS = 3.0
                cell.give_energy(MASTERY_BONUS)
                self.total_rewards += MASTERY_BONUS
                mastery_bonus = True
                print(f"  🏆 MASTERY ×{self._teacher_overlap_count} "
                      f"({traj['id']} → {result_node} chain={chain_len} +{MASTERY_BONUS}E)")
            break  # 只匹配第一条
        
        # 日志
        if self._teacher_overlap_count % 20 == 1 and not mastery_bonus:
            print(f"  📖 teacher learn ×{self._teacher_overlap_count} "
                  f"({traj_id} {best_len}-step +{energy_bonus:.1f}E)")
        
        return True

    def _save_known_paths(self):
        if not hasattr(self, '_known_paths'):
            return
        try:
            path = os.path.join(os.path.dirname(__file__), "..", "data", "known_paths.txt")
            paths = list(self._known_paths)[-200000:]
            with open(path, 'w') as f:
                for p in paths:
                    f.write(p + '\n')
        except Exception:
            pass

    # ═══════ Deep Dive 专注机制 ═══════

    FOCUS_DURATION = 500
    FOCUS_HYPOTHESIS_MIN = 5

    def _load_focus(self):
        try:
            path = os.path.join(os.path.dirname(__file__), "..", "data", "focus_commitment.json")
            if os.path.exists(path):
                with open(path) as f:
                    self._focus = json.load(f)
                if self._focus.get("topic"):
                    print(f"  [FOCUS] 恢复专注: {self._focus['topic']} "
                          f"(锁定于 gen {self._focus['locked_at']})")
        except Exception:
            self._focus = {}

    def _save_focus(self):
        try:
            path = os.path.join(os.path.dirname(__file__), "..", "data", "focus_commitment.json")
            with open(path, 'w') as f:
                json.dump(self._focus, f, ensure_ascii=False)
        except Exception:
            pass

    def _manage_focus(self):
        """评估专注状态 — 锁定/续期/释放, 接入研究计划队列 (调度器控制频率)"""
        topic = self._focus.get("topic")
        if topic:
            locked_at = self._focus.get("locked_at", self.generation)
            elapsed = self.generation - locked_at
            if elapsed < self.FOCUS_DURATION:
                return  # 锁定期内
            hyp_count = self._focus.get("hypotheses_seen", 0)
            resolved = self._focus.get("resolved", 0)
            prev_hyp = self._focus.get("prev_hyp_count", 0)
            renewals = self._focus.get("renewals", 0)
            # 续期条件: 假说数达标, 且 (有矛盾消解 或 假说率上升 或 首次续期宽容)
            quality_ok = resolved > 0 or hyp_count > prev_hyp * 0.7 or renewals == 0
            if hyp_count >= self.FOCUS_HYPOTHESIS_MIN and quality_ok:
                self._focus["locked_at"] = self.generation
                self._focus["prev_hyp_count"] = hyp_count
                self._focus["hypotheses_seen"] = 0
                self._focus["resolved"] = 0
                self._focus["renewals"] = renewals + 1
                self._save_focus()
                # 更新计划任务统计
                self._update_plan_task(topic, hyp_count)
                print(f"  [FOCUS] 续期 #{renewals+1}: {topic} "
                      f"(假说{hyp_count} 矛盾{resolved})")
            else:
                # 释放 → 标记计划任务完成 → 重新生成计划 → 取下一项
                self._complete_plan_task(topic, hyp_count)
                self._focus = {}
                self._save_focus()
                # 再生计划 (可能排除刚完成的)
                old_tasks = self._plan.get("tasks", [])
                self._plan["tasks"] = [t for t in old_tasks if t["status"] != "done"]
                if not any(t["status"] in ("active","pending") for t in self._plan["tasks"]):
                    self._generate_plan()
                # 取下一项
                next_topic = self._next_plan_task()
                if next_topic:
                    self._focus = {
                        "topic": next_topic,
                        "locked_at": self.generation,
                        "min_duration": self.FOCUS_DURATION,
                        "hypotheses_seen": 0,
                        "prev_hyp_count": 0,
                        "resolved": 0,
                        "renewals": 0
                    }
                    self._save_focus()
                    self.set_goal(next_topic, f"plan: research queue")
        else:
            # 无专注 → 从计划队列取
            if not self._plan.get("tasks"):
                self._generate_plan()
            if not self._plan.get("tasks"):
                return
            next_topic = None
            task_id = "?"
            for task in self._plan["tasks"]:
                if task["status"] == "active":
                    next_topic = task["topic"]
                    task_id = str(task.get("id", "?"))
                    break
            if not next_topic:
                next_topic = self._next_plan_task()
                if next_topic:
                    for task in self._plan["tasks"]:
                        if task["topic"] == next_topic:
                            task_id = str(task.get("id", "?"))
                            break
            if next_topic:
                self._focus = {
                    "topic": next_topic,
                    "locked_at": self.generation,
                    "min_duration": self.FOCUS_DURATION,
                    "hypotheses_seen": 0,
                    "prev_hyp_count": 0,
                    "resolved": 0,
                    "renewals": 0
                }
                self._save_focus()
                self.set_goal(next_topic, f"plan: #{task_id}")
                print(f"  [FOCUS] 锁定: {next_topic} "
                      f"(计划 #{task_id}, 最低{self.FOCUS_DURATION}代)")

    def _track_focus_hypothesis(self, hyp_name: str):
        topic = self._focus.get("topic")
        if topic and topic in hyp_name:
            self._focus["hypotheses_seen"] = self._focus.get("hypotheses_seen", 0) + 1
            self._save_focus()

    # ═══════ 研究计划系统 ═══════

    def _load_plan(self):
        try:
            path = os.path.join(os.path.dirname(__file__), "..", "data", "research_plan.json")
            if os.path.exists(path):
                with open(path) as f:
                    self._plan = json.load(f)
            else:
                self._plan = {"tasks": [], "next_id": 1}
        except Exception:
            self._plan = {"tasks": [], "next_id": 1}

    def _save_plan(self):
        try:
            path = os.path.join(os.path.dirname(__file__), "..", "data", "research_plan.json")
            with open(path, 'w') as f:
                json.dump(self._plan, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _generate_plan(self):
        """扫描 coincidence 图, 按连接度排序, 生成 top 5 研究课题"""
        skip_words = {'title','abstract','paper','model','method','result','data',
                      'figure','table','section','introduction','conclusion','sample',
                      'here','towards','specht','term','laser','free_space','validating'}
        # 方法论节点: 高连接低价值, 降权到 0.3x
        meta_words = {'experimental_design','experiment','measurement','validation',
                      'hypothesis_testing','scientific_method','data_analysis',
                      'design_experiment','adaptive_experimental_design',
                      'sequential_experimental_design','experiment_design'}
        scored = {}
        for (a, b), cnt in self._coincidence.items():
            for node in (a, b):
                if node.startswith(self.HYPNODE_PREFIX):
                    continue
                words = set(node.replace('_',' ').lower().split())
                if words & skip_words:
                    continue
                weight = 0.3 if node in meta_words else 1.0
                # 物理深度加成: tier0-1 基础物理图中的概念 ×2
                if node in self._native_nodes:
                    weight *= 2.0
                scored[node] = scored.get(node, 0) + cnt * weight
        ranked = sorted(scored.items(), key=lambda x: -x[1])[:10]
        if not ranked:
            return
        
        tasks = []
        for i, (goal, score) in enumerate(ranked[:5]):
            tasks.append({
                "id": self._plan["next_id"] + i,
                "topic": goal,
                "status": "pending",
                "created": self.generation,
                "time_spent": 0,
                "hypotheses": 0,
                "coincidence": score
            })
        tasks[0]["status"] = "active"
        self._plan["tasks"] = tasks
        self._plan["next_id"] += len(tasks)
        self._save_plan()
        names = " → ".join(t["topic"][:25] for t in tasks)
        print(f"  [PLAN] 研究计划 ({len(tasks)} 项): {names}")

    def _next_plan_task(self):
        """取下一项 pending 任务, 标记 active, 返回 topic 或 None"""
        for task in self._plan.get("tasks", []):
            if task["status"] == "pending":
                task["status"] = "active"
                task["created"] = self.generation
                self._save_plan()
                print(f"  [PLAN] → 下一项: {task['topic']} "
                      f"(coinc={task.get('coincidence', 0)})")
                return task["topic"]
        return None

    def _complete_plan_task(self, topic: str, hyp_count: int = 0):
        """标记当前任务完成, 记录统计"""
        for task in self._plan.get("tasks", []):
            if task["topic"] == topic and task["status"] == "active":
                task["status"] = "done"
                task["time_spent"] = self.generation - task.get("created", self.generation)
                task["hypotheses"] = hyp_count
                self._save_plan()
                print(f"  [PLAN] ✓ {topic} 完成 "
                      f"({task['time_spent']}代, 假说 {hyp_count})")
                return
        for task in self._plan.get("tasks", []):
            if task["topic"] == topic and task["status"] == "pending":
                task["status"] = "done"
                self._save_plan()
                return

    def _update_plan_task(self, topic: str, hyp_count: int):
        """续期时更新计划任务统计 (不改变状态)"""
        for task in self._plan.get("tasks", []):
            if task["topic"] == topic and task["status"] == "active":
                task["time_spent"] = self.generation - task.get("created", self.generation)
                task["hypotheses"] = task.get("hypotheses", 0) + hyp_count
                self._save_plan()
                return

    def _load_known_paths(self):
        try:
            path = os.path.join(os.path.dirname(__file__), "..", "data", "known_paths.txt")
            if os.path.exists(path):
                with open(path) as f:
                    self._known_paths = set(line.strip() for line in f if line.strip())
                if self._known_paths:
                    print(f"[PATHS] {len(self._known_paths)} known paths restored")
            else:
                self._known_paths = set()
        except Exception:
            self._known_paths = set()

    def _save_coincidence(self):
        try:
            active = {k: v for k, v in self._coincidence.items() if v >= 2}
            if len(active) > 200000:
                ranked = sorted(active.items(), key=lambda x: -x[1])
                active = dict(ranked[:200000])
            self._coincidence = active
            path = os.path.join(os.path.dirname(__file__), "..", "data", "coincidence.json")
            data = {f"{src}|||{dst}": count for (src, dst), count in active.items()}
            with open(path, 'w') as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception:
            pass

    def _load_coincidence(self):
        try:
            path = os.path.join(os.path.dirname(__file__), "..", "data", "coincidence.json")
            if os.path.exists(path):
                with open(path) as f:
                    data = json.load(f)
                self._coincidence = {}
                for k, v in data.items():
                    parts = k.split('|||')
                    if len(parts) == 2:
                        self._coincidence[(parts[0], parts[1])] = v
                if self._coincidence:
                    top = sorted(self._coincidence.items(), key=lambda x: -x[1])[:3]
                    top_str = ' | '.join(f'{s[:10]}->{d[:10]}:{c}' for (s,d),c in top)
                    print(f"[COINC] {len(self._coincidence)} entries | top: {top_str}")
        except Exception:
            self._coincidence = {}

    def _save_walk_memory(self):
        try:
            all_walks = []
            for cell in self.cells:
                for w in getattr(cell, 'walk_memory', []):
                    serialized = []
                    for step in w:
                        if len(step) >= 4:
                            serialized.append(list(step[:4]))
                        elif len(step) >= 3:
                            serialized.append(list(step[:3]))
                    if serialized:
                        all_walks.append(serialized)
            if all_walks:
                all_walks.sort(key=self._walk_value, reverse=True)
                all_walks = all_walks[:500]
            path = os.path.join(os.path.dirname(__file__), "..", "data", "walk_memory.json")
            with open(path, 'w') as f:
                json.dump(all_walks, f, ensure_ascii=False)
        except Exception:
            pass

    def _load_walk_memory(self):
        try:
            path = os.path.join(os.path.dirname(__file__), "..", "data", "walk_memory.json")
            if os.path.exists(path):
                with open(path) as f:
                    data = json.load(f)
                self._global_walk_memory = data
                if data:
                    print(f"[WALK_MEM] {len(data)} paths restored")
            else:
                self._global_walk_memory = []
        except Exception:
            self._global_walk_memory = []

    def _distribute_walk_memory(self):
        if not self._global_walk_memory or not self.cells:
            return
        ranked = sorted(self._global_walk_memory, key=self._walk_value, reverse=True)
        for i, cell in enumerate(self.cells):
            start = (i * 3) % len(ranked)
            cell.walk_memory = ranked[start:start + min(5, len(ranked) - start)]

    def _save_emergent_edges(self):
        try:
            edges = []
            for src, node in self.graph._cache.items():
                for law_name, dst, domain in node.get("effects", []):
                    if domain == "emergent":
                        edges.append([src, law_name, dst, domain])
            path = os.path.join(os.path.dirname(__file__), "..", "data", "emergent_edges.json")
            with open(path, 'w') as f:
                json.dump(edges, f, ensure_ascii=False)
        except Exception:
            pass

    def _load_emergent_edges(self):
        HEBBIAN_RESTORE_LIMIT = 50000  # 防止图过密导致探索崩溃
        try:
            path = os.path.join(os.path.dirname(__file__), "..", "data", "emergent_edges.json")
            if os.path.exists(path):
                with open(path) as f:
                    edges = json.load(f)
                restored = 0
                for src, law_name, dst, domain in edges[:HEBBIAN_RESTORE_LIMIT]:
                    if domain == "emergent":
                        self._ensure_node(src)
                        self._ensure_node(dst)
                        exists = any(e[1] == dst and e[2] == "emergent"
                                    for e in self.graph[src]["effects"])
                        if not exists:
                            self.graph.add_edge(src, dst, law_name, "emergent")
                            restored += 1
                if restored:
                    print(f"[EMERGENT] +{restored} Hebbian shortcuts restored")
        except Exception:
            pass

    def _has_path_in_graph(self, src: str, dst: str, max_depth: int = 10) -> bool:
        if src not in self.graph or dst not in self.graph:
            return False
        visited = {src}
        frontier = [src]
        for _ in range(max_depth):
            if not frontier:
                break
            node = frontier.pop(0)
            for _, neighbor, _ in self.graph[node]["effects"]:
                if neighbor == dst:
                    return True
                if neighbor not in visited:
                    visited.add(neighbor)
                    frontier.append(neighbor)
        return False

    # ═══════ 生长/修剪 ═══════

    def _grow_shortcuts(self):
        """Hebbian LTP: 反复共现的节点对 -> 长出直接边
        
        方向闸门: 正向coincidence必须≥2倍反向，否则是随机共现，不晋升
        拓扑塑形: 三元闭包 + 长程桥 + 枢纽友好
        """
        base_threshold = 8
        node_degree = Counter()
        active_pairs = set()
        for key_str in self.synapse.activations:
            active_pairs.add(key_str)
        for (src, dst) in self._coincidence:
            active_pairs.add((src, dst))
        for src, node in self.graph._cache.items():
            for law, dst, domain in node.get("effects", []):
                # 所有可信域都计入枢纽度 (emergent+math_verified+已知物理)
                if domain in self.VALID_EDGE_DOMAINS:
                    pair = (src, dst)
                    if pair in active_pairs or (dst, src) in active_pairs:
                        node_degree[src] += 1
                        node_degree[dst] += 1
        DIRECTION_RATIO = 1.2    # 2.0→1.2: 允许弱双向 (反馈=预测编码)
        # 泛化: 跨域不降门槛 (防止噪音晋升)
        CROSS_DOMAIN_MULT = 1.0
        def _hub_bonus(deg):
            if deg < 3: return 0          # 叶子: 无优惠
            if deg < 10: return 1          # 普通: -1
            if deg < 30: return 2          # 局部枢纽: -2
            return max(3, deg // 20 + 2)   # 全局枢纽: -3~
        def _primary_domain(node_id):
            effects = self.graph.get(node_id, {}).get("effects", [])
            if not effects:
                return None
            domains = [e[2] for e in effects if len(e) > 2]
            if not domains:
                return None
            return Counter(domains).most_common(1)[0][0]
        # 小世界: 聚类系数
        def _cluster_bonus(src, dst):
            src_neighbors = {e[1] for e in self.graph.get(src, {}).get("effects", [])}
            dst_neighbors = {e[1] for e in self.graph.get(dst, {}).get("effects", [])}
            common = len(src_neighbors & dst_neighbors)
            if common >= 3: return 3
            if common >= 2: return 2
            if common >= 1: return 1
            return 0
        
        grown = 0
        for (src, dst), count in self._coincidence.items():
            effective = base_threshold - _hub_bonus(max(node_degree[src], node_degree[dst]))
            # 层级加工: 跨域提高门槛
            d_src = _primary_domain(src)
            d_dst = _primary_domain(dst)
            if d_src and d_dst and d_src != d_dst:
                effective = int(effective * CROSS_DOMAIN_MULT)
            # 小世界: 聚类系数 — 共同邻居越多越容易建边
            effective = max(base_threshold, effective - _cluster_bonus(src, dst))
            # 长程桥: src和dst在图里很远(>4跳) → 建边收益高
            if src in self.graph and dst in self.graph:
                if not self._has_path_in_graph(src, dst, 4) and not self._has_path_in_graph(dst, src, 4):
                    effective = max(base_threshold, effective - 1)
            if count >= effective:
                rev_count = self._coincidence.get((dst, src), 0)
                if rev_count > 0 and count / max(rev_count, 1) < DIRECTION_RATIO:
                    continue
                # 防御: 确保节点在图中
                self._ensure_node(src)
                self._ensure_node(dst)
                exists = any(e[1] == dst and e[2] == "emergent" for e in self.graph[src].get("effects", []))
                if not exists:
                    self.graph.add_edge(src, dst, "hebbian_shortcut", "emergent")
                    self._emergent_birth[(src, dst)] = self.generation
                    self._edge_birth[(src, dst)] = self.generation
                    grown += 1
        if grown:
            self._save_emergent_edges()

    def _spawn_probes(self):
        """树突棘探针: 热点节点伸试探边, 偏向语义邻近节点 (类脑拓扑学习)
        
        人脑轴突沿化学梯度生长→功能相近的神经元优先连接。
        语义向量是费曼脑的化学梯度: 走过的路径塑造向量,
        功能相关的节点在向量空间中自然靠拢。
        探针优先连接邻近节点→模块涌现→小世界拓扑自发生成。
        """
        PROBES_PER_NODE = 5; PROBE_AGE_LIMIT = 300
        nodes = Counter(c.node for c in self.cells)
        hotspots = [n for n, _ in nodes.most_common(20) if nodes[n] >= 3]
        spawned = 0
        vecs_ready = len(self._node_vecs) > 20  # 语义空间成熟后才启用偏置
        for src in hotspots:
            all_nodes = list(self.graph.keys())
            # 🧹 断噪音源: 制备有效节点池 (有 VALID 域边的节点, fallback用)
            valid_nodes = []
            for n, nd in self.graph._cache.items():
                for _, _, domain in nd.get("effects", []):
                    if domain in self.VALID_EDGE_DOMAINS:
                        valid_nodes.append(n)
                        break
            if len(valid_nodes) < PROBES_PER_NODE:
                valid_nodes = list(self.graph.keys())
            # 🧠 拓扑学习: 语义邻近节点优先 — 模块自组织
            if vecs_ready and (src_vec := self._node_vecs.get(src)):
                candidates = []
                for n in all_nodes:
                    if n == src: continue
                    if (src, n) in self._probe_edges: continue
                    if any(e[1] == n for e in self.graph[src].get("effects", [])): continue
                    nv = self._node_vecs.get(n)
                    if nv:
                        dot = sum(src_vec[j]*nv[j] for j in range(self.SEMANTIC_DIM))
                        na = (sum(v*v for v in src_vec))**0.5
                        nb = (sum(v*v for v in nv))**0.5
                        sim = dot / max(na*nb, 1e-10)
                        candidates.append((n, sim))
                if len(candidates) >= PROBES_PER_NODE:
                    candidates.sort(key=lambda x: -x[1])
                    # 前50%相似节点中随机采样: 创建模块但保留探索性
                    pool = candidates[:max(PROBES_PER_NODE * 2, len(candidates)//2)]
                    chosen = random.sample(pool, min(PROBES_PER_NODE, len(pool)))
                    targets = [c[0] for c in chosen]
                else:
                    targets = random.sample(valid_nodes, min(PROBES_PER_NODE, len(valid_nodes)))
            else:
                targets = random.sample(valid_nodes, min(PROBES_PER_NODE, len(valid_nodes)))
            for dst in targets:
                if dst == src:
                    continue
                if (src, dst) in self._probe_edges:
                    continue
                existing = any(e[1] == dst for e in self.graph[src].get("effects", []))
                if existing:
                    continue
                self._ensure_node(src)
                self._ensure_node(dst)
                self.graph.add_edge(src, dst, "probe", "probe")
                self._probe_edges[(src, dst)] = self.generation
                spawned += 1
        # 修剪冷探针
        cold = [(k, v) for k, v in self._probe_edges.items() if self.generation - v > PROBE_AGE_LIMIT]
        for (src, dst), _ in cold:
            nd = self.graph.get(src, {})
            nd["effects"] = [e for e in nd.get("effects", []) if not (e[1] == dst and e[2] == "probe")]
            nd2 = self.graph.get(dst, {})
            nd2["causes"] = [e for e in nd2.get("causes", []) if not (e[0] == src and e[2] == "probe")]
            del self._probe_edges[(src, dst)]

    def _deep_prune(self):
        """大修剪: 清除僵尸边 (emergent/probe/research, 200代无活动→删)"""
        if self.generation % 100 != 0:
            return  # 每100代修剪, 比500更频繁
        if not getattr(self, '_edge_last_seen_initialized', False):
            for src, node in self.graph._cache.items():
                for _, dst, dom in node.get("effects", []):
                    if dom in ("emergent", "probe", "research"):
                        self._edge_last_seen[(src, dst)] = self.generation
            self._edge_last_seen_initialized = True
        pruned = 0
        pruned_pairs = set()  # 记录被删的(s,d)对，用于cause清理
        for src in list(self.graph.keys()):
            new_effects = []
            for law, dst, domain in self.graph[src].get("effects", []):
                if domain in ("emergent", "probe", "research"):
                    pair = (src, dst)
                    last_seen = self._edge_last_seen.get(pair, self.generation)
                    if self.generation - last_seen > 200:
                        pruned += 1
                        pruned_pairs.add(pair)
                        continue
                new_effects.append((law, dst, domain))
            self.graph[src]["effects"] = new_effects
        # 同步清理对应的 causes (之前漏了,积累幽灵引用)
        for (src, dst) in pruned_pairs:
            nd = self.graph.get(dst, {})
            nd["causes"] = [(s, l, d) for s, l, d in nd.get("causes", [])
                           if not (s == src and d in ("emergent", "probe", "research"))]
        # 活跃边续命
        for key_str in self.synapse.activations:
            if "->" in key_str:
                s, d = key_str.split("->", 1)
                self._edge_last_seen[(s, d)] = self.generation
        for (src, dst) in self._coincidence:
            if self._coincidence[(src, dst)] >= 3:
                self._edge_last_seen[(src, dst)] = self.generation
        if pruned:
            self._save_emergent_edges()
            print(f"  [PRUNE] -{pruned} stale edges (gen {self.generation})")

    def _prune_stale_emergent(self):
        """🧠 持续清理: 睡眠时摘除没人走的 emergent 标签边
        s < 0.01 → 从知识图谱移除 emergent 标签 (不删边本身，只摘标签)
        新生儿保护: 出生不足30代的 composed 边豁免"""
        pruned = 0
        NEWBORN_GRACE = 60  # 新生儿保护期(代): 60代内不杀
        for src in list(self.graph.keys()):
            node = self.graph[src]
            new_effects = []
            for law, dst, domain in node.get("effects", []):
                if domain == "emergent":
                    birth = self._composed_birth.get((src, dst), 0)
                    if birth and self.generation - birth < NEWBORN_GRACE:
                        new_effects.append((law, dst, domain))
                        continue
                    key = (src, dst)
                    act = self.synapse.activations.get(key, {})
                    s_val = act.get('s', 0) if isinstance(act, dict) else 0
                    walked = act.get('unique_neurons', 0) if isinstance(act, dict) else 0
                    # 清理死边: s<0.05 且 无人走过
                    if s_val < 0.05 and walked < 1:
                        pruned += 1
                        nd = self.graph.get(dst, {})
                        nd["causes"] = [(s, l, d) for s, l, d in nd.get("causes", [])
                                        if not (s == src and d == "emergent")]
                        continue
                new_effects.append((law, dst, domain))
            self.graph[src]["effects"] = new_effects
        if pruned:
            print(f"  [PRUNE_EM] -{pruned} stale emergent labels (gen {self.generation})")

    def _grow_abstractions(self):
        """抽象节点: 高频coincidence对 -> 复合概念"""
        if self.generation % 500 != 0:
            return
        created = 0
        hot_pairs = [(pair, count) for pair, count in self._coincidence.items()
                     if count >= self.ABSTRACTION_THRESHOLD]
        hot_pairs.sort(key=lambda x: -x[1])
        for (src, dst), count in hot_pairs[:5]:
            abs_name = f"abs:{src}__{dst}"
            if abs_name in self.graph:
                continue
            self.graph[abs_name] = {"causes": [], "effects": []}
            self._abs_birth[abs_name] = self.generation  # 记录创建代
            created += 1
            if not any(e[1] == abs_name for e in self.graph[src].get("effects", [])):
                self.graph.add_edge(src, abs_name, f"abstraction:{count}", "abstraction")
            if not any(e[1] == dst for e in self.graph[abs_name].get("effects", [])):
                self.graph.add_edge(abs_name, dst, f"abstraction:{count}", "abstraction")
            for cause_src, law, domain in self.graph[src].get("causes", []):
                if cause_src != abs_name and not any(e[1] == abs_name for e in self.graph.get(cause_src, {}).get("effects", [])):
                    self._ensure_node(cause_src)
                    self.graph.add_edge(cause_src, abs_name, f"abs_bridge:{law}", "abstraction")
            for law, effect_dst, domain in self.graph[dst].get("effects", []):
                if effect_dst != abs_name and not any(e[1] == effect_dst for e in self.graph[abs_name].get("effects", [])):
                    self.graph[abs_name]["effects"].append((f"abs_bridge:{law}", effect_dst, "abstraction"))
                    self._ensure_node(effect_dst)
                    self.graph[effect_dst]["causes"].append((abs_name, f"abs_bridge:{law}", "abstraction"))
        if created:
            print(f"  [ABSTRACT] +{created} abstraction nodes (threshold {self.ABSTRACTION_THRESHOLD})")

    def _expire_abstractions(self):
        """清理 3 个周期(1500代)内未活跃的抽象节点"""
        if self.generation % 500 != 0:
            return
        stale_age = self.generation - 1500
        # 当前活跃的 coincidence top-50 节点名
        hot_names = set()
        hot_pairs = sorted(self._coincidence.items(), key=lambda x: -x[1])[:50]
        for (src, dst), _ in hot_pairs:
            hot_names.add(src)
            hot_names.add(dst)
        expired = 0
        for abs_name, birth_gen in list(self._abs_birth.items()):
            if birth_gen > stale_age:
                continue
            # 检查抽象节点的组件是否还在热区
            parts = abs_name.replace("abs:", "").split("__", 1)
            if any(p in hot_names for p in parts):
                continue
            # 删除
            node = self.graph.pop(abs_name, None)
            if node:
                # 清理所有引用该抽象节点的边
                for src in list(self.graph.keys()):
                    effects = self.graph[src].get("effects", [])
                    self.graph[src]["effects"] = [
                        e for e in effects if e[1] != abs_name
                    ]
                # 清理 coincidence 中的引用
                dead_pairs = [p for p in self._coincidence if abs_name in p]
                for p in dead_pairs:
                    del self._coincidence[p]
                expired += 1
            del self._abs_birth[abs_name]
        if expired:
            print(f"  [ABSTRACT] -{expired} stale nodes expired")

    def _compose_paths(self, new_walk):
        """路径合成: A->B + B->C -> A->C"""
        if not hasattr(self, '_known_paths') or len(new_walk) < 2:
            return 0, []
        composed_paths = []
        new_end = new_walk[-1][2]
        new_start = new_walk[0][0]
        for known_key in list(self._known_paths)[:1000]:
            known_parts = known_key.split("->")
            if len(known_parts) < 2:
                continue
            if known_parts[-1] == new_start:
                composed = known_key + "->" + "->".join(w[2] for w in new_walk[1:])
                if composed not in self._known_paths:
                    composed_paths.append(composed)
            if known_parts[0] == new_end:
                composed = "->".join(w[2] for w in new_walk[:-1]) + "->" + known_key
                if composed not in self._known_paths:
                    composed_paths.append(composed)
        added = 0
        for cpath in composed_paths[:10]:
            self._known_paths.add(cpath)
            added += 1
        return added, composed_paths[:10]

    # ═══════ 快照 ═══════

    def snapshot_state(self) -> dict:
        cells_data = []
        for cell in self.cells:
            cells_data.append({
                "node": cell.node,
                "genome": dict(cell.genome),
                "age": cell.age,
                "total_reward": cell.total_reward,
                # 结构记忆——突触重塑的成果
                "weights": dict(getattr(cell, 'weights', {})),
                "dendrites": list(getattr(cell, 'dendrites', set())),
                "trace": dict(getattr(cell, 'trace', {})),
                "prediction_model": dict(getattr(cell, 'prediction_model', {})),
                "intrinsic_curiosity": getattr(cell, 'intrinsic_curiosity', 1.0),
                # 瞬时状态不存——walk_memory/current_walk/sensory_memory
            })
        # 边数估算: 只数缓存中的 effects (非全图扫描)
        edge_count = sum(len(n.get("effects", [])) for n in self.graph._cache.values())
        # VSA 序列化
        vsa_data = self.graph.vsa.to_dict() if hasattr(self.graph, 'vsa') else {}
        # 缓存序列化 (避免恢复时触发全量 VSA 查询)
        cache_data = {}
        for node_id, entry in self.graph._cache.items():
            cache_data[node_id] = {
                "effects": [list(e) for e in entry.get("effects", [])],
                "causes": [list(c) for c in entry.get("causes", [])],
            }
        # emergent edges: 原子绑定到快照，重启不丢
        emergent_edges = []
        for src, node in self.graph._cache.items():
            for law_name, dst, domain in node.get("effects", []):
                if domain == "emergent":
                    emergent_edges.append([src, law_name, dst, domain])
        return {
            "generation": self.generation, "cells": cells_data,
            "K": self._carrying_capacity,
            "edges": edge_count,
            "vs.graph": vsa_data,
            "vs.cache": cache_data,
            "synaptic": self.synapse.to_dict() if hasattr(self, 'synapse') else {},
            "cell_shelf": self._cell_shelf,  # ☁️ 磁盘种子库
            "emergent_edges": emergent_edges,
            "snapshot_version": 5, "timestamp": time.time(),
        }

    def save_snapshot(self, path: str):
        try:
            data = self.snapshot_state()
            data = self._clean_snapshot_data(data)
            if orjson is not None:
                with open(path, 'wb') as f:
                    f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))
            else:
                with open(path, 'w') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    @staticmethod
    def _clean_snapshot_data(data: dict) -> dict:
        """移除垃圾节点和边 (与 _ensure_node 规则一致)"""
        cache = data.get("vs.cache", {})
        if not cache:
            return data

        def _is_garbage(name: str) -> bool:
            if not name:
                return True
            if name.count(':') > 1:
                return True
            if len(name) > 40:
                return True
            if '→' in name or '->' in name or '__' in name:
                return True
            if name.count('_') > 4:
                return True
            return False

        # 收集垃圾节点
        garbage_nodes = {n for n in cache if _is_garbage(n)}

        # 清理边: 只保留经过证明的域
        # math_verified = sympy证明, 已知物理域 = 定律注入
        VALID_DOMAINS = {"math_verified", "mechanics", "electromagnetism",
                         "thermodynamics", "quantum", "optics",
                         "modern", "general_relativity", "emergent"}
        for nid, entry in cache.items():
            entry["effects"] = [
                e for e in entry.get("effects", [])
                if isinstance(e, (list, tuple)) and len(e) >= 3
                and not _is_garbage(str(e[1]))
                and e[2] in VALID_DOMAINS
            ]
            entry["causes"] = [
                c for c in entry.get("causes", [])
                if isinstance(c, (list, tuple)) and len(c) >= 3
                and not _is_garbage(str(c[0]))
                and c[2] in VALID_DOMAINS
            ]

        # 删除垃圾节点
        for n in garbage_nodes:
            cache.pop(n, None)

        # 清理细胞: 杀在垃圾节点上的细胞
        cells = data.get("cells", [])
        data["cells"] = [c for c in cells if not _is_garbage(c.get("node", ""))]

        print(f"  [CLEAN] {len(garbage_nodes)} garbage nodes, "
              f"{len(cells)-len(data['cells'])} cells purged from snapshot")
        return data

    def restore_from_snapshot(self, data: dict) -> int:
        cells_data = data.get("cells", [])
        if not cells_data:
            return 0
        # 恢复 VSA (v3+ 快照) — 仅恢复向量数据, 不预热查询矩阵
        vsa_data = data.get("vs.graph", {})
        if vsa_data and hasattr(self.graph, 'vsa'):
            self.graph.vsa.from_dict(vsa_data)
        # 恢复缓存邻接表 (v3+ 快照, 避免 VSA 全量查询)
        cache_data = data.get("vs.cache", {})
        if cache_data and hasattr(self.graph, '_cache'):
            from meta_cognition.vsa_memory import _WriteThroughList
            for node_id, entry in cache_data.items():
                self.graph._cache[node_id] = {
                    "effects": _WriteThroughList(
                        [tuple(e) for e in entry.get("effects", [])],
                        _vsa_graph=self.graph, _node_id=node_id, _direction="effects"),
                    "causes": _WriteThroughList(
                        [tuple(c) for c in entry.get("causes", [])],
                        _vsa_graph=self.graph, _node_id=node_id, _direction="causes"),
                }
            # 同步 edge_count
            self.graph._edge_count = sum(
                len(e.get("effects", [])) for e in cache_data.values()
            )
        old_count = len(self.cells)
        self.cells = []
        restored = 0
        for cd in cells_data:
            try:
                node = cd["node"]
                if node not in self.graph:
                    continue
                cell = EvolvableCell(node, self.graph, self.board,
                                    min_split_reward=self.MIN_SPLIT_REWARD)
                cell.genome = cd.get("genome", {})
                cell.age = cd.get("age", 0)
                cell.total_reward = cd.get("total_reward", 0)
                # 恢复结构记忆
                if cd.get("weights"):
                    cell.weights = cd["weights"]
                if cd.get("dendrites"):
                    cell.dendrites = set(cd["dendrites"])
                if cd.get("trace"):
                    cell.trace = cd["trace"]
                if cd.get("prediction_model"):
                    cell.prediction_model = {k: Counter(v) for k, v in cd["prediction_model"].items() if isinstance(v, dict)}
                cell.intrinsic_curiosity = cd.get("intrinsic_curiosity", 1.0)
                self.cells.append(cell)
                restored += 1
            except Exception:
                continue
        snap_gen = data.get("generation", 0)
        if snap_gen > self.generation:
            self.generation = snap_gen
        # 恢复 K 和冷热分界线
        saved_k = data.get("K", data.get("carrying_capacity", 0))
        if saved_k > self._carrying_capacity:
            self._carrying_capacity = saved_k
        self.ACTIVE_POOL = max(5000, self._carrying_capacity // 2)
        # 恢复突触层 (v2+ 快照)
        synaptic_data = data.get("synaptic", {})
        if synaptic_data and hasattr(self, 'synapse'):
            self.synapse.from_dict(synaptic_data)
        # ☁️ 恢复磁盘种子库 (v4+ 快照)
        shelf_data = data.get("cell_shelf", {})
        if shelf_data:
            self._cell_shelf = shelf_data
            self._save_cell_shelf()
        # ☁️ 一次性迁移: 冷池并入统一云
        merged = self._merge_cold_cells_on_startup()
        # 人口上限: 如果超过 ACTIVE_POOL*10, 按 reward 截断到 2x
        max_allowed = max(self.ACTIVE_POOL * 2, 15000)
        if len(self.cells) > self.ACTIVE_POOL * 10:
            self.cells.sort(key=lambda c: c.total_reward, reverse=True)
            overflow = len(self.cells) - max_allowed
            self.cells = self.cells[:max_allowed]
            print(f"☁️ 人口截断: {overflow} 低reward细胞休眠 ({max_allowed} 保留)")
        # 容量: 物理枢纽节点保底细胞数 (培养基不能空)
        self._seed_physics_hub_cells()
        # 容量: 婴儿先密后疏 — 突触层注入混沌低 s 边
        self._seed_chaotic_brain()
        # 恢复 emergent edges (v5+ 快照原子绑定)
        emergent_data = data.get("emergent_edges", [])
        if emergent_data:
            restored_em = 0
            for src, law_name, dst, domain in emergent_data:
                self._ensure_node(src)
                self._ensure_node(dst)
                exists = any(e[1] == dst and e[2] == "emergent"
                            for e in self.graph[src]["effects"])
                if not exists:
                    self.graph.add_edge(src, dst, law_name, "emergent")
                    restored_em += 1
            if restored_em:
                print(f"[EMERGENT] +{restored_em} emergent edges restored from snapshot")
        return restored

    def _inject_physics_bridges(self, max_bridges: int = 50):
        """自动注入已知物理桥: 对物理节点对调用 sympy derive,
        成功则注入 math_verified 边。纯容量——用脑自己的验证引擎。"""
        try:
            from physics.math_derive import derive as math_derive, get_symbol
        except Exception:
            return
        import random as _rnd

        # 收集所有在 cache 中的物理节点
        graph_nodes = list(getattr(self.graph, '_cache', {}).keys()) or list(self.graph.keys())
        physics_nodes = [n for n in graph_nodes if get_symbol(n)]
        if len(physics_nodes) < 2:
            return

        # 尝试注入: 随机配对, sympy 验证, 成功就加边
        injected = 0
        tried = set()
        attempts = 0
        max_attempts = min(len(physics_nodes) * 3, 200)

        while injected < max_bridges and attempts < max_attempts:
            attempts += 1
            a, b = _rnd.sample(physics_nodes, 2)
            if (a, b) in tried or (b, a) in tried:
                continue
            tried.add((a, b))

            # 检查是否已有边
            existing = [e for e in self.graph._cache.get(a, {}).get('effects', [])
                       if e[1] == b]
            if existing:
                continue

            mr = math_derive(a, b)
            if mr and mr.get("success"):
                # 注入双向边
                law = f"bridge:{mr.get('relation', '')}"[:60]
                self.graph.setdefault(a, {'effects': [], 'causes': []})
                self.graph.setdefault(b, {'effects': [], 'causes': []})
                self.graph[a].setdefault('effects', []).append((law, b, 'math_verified'))
                self.graph[b].setdefault('causes', []).append((a, law, 'math_verified'))

                key = (a, b)
                if key not in self.synapse.activations:
                    self.synapse.activations[key] = {
                        'n': set(), 'g': self.generation, 's': 0.9, 'c': 1
                    }
                injected += 1

        if injected:
            print(f"  [BRIDGE] +{injected} physics bridges injected (sympy verified)")

    def _seed_chaotic_brain(self):
        """🧠 婴儿先密后疏: 在突触层注入 29 个物理节点间的随机低 s 边。
        教科书 (vs.cache) 不变 — 只污染费曼自己的脑。
        走多了→髓鞘化, 不走→自然修剪。"""
        import random as _rnd

        # 29 个已知物理节点 + 实验 + 哲学 (所有教科书节点)
        _PHYSICS_NODES = [
            # 公式/概念
            'acceleration', 'action', 'angular_momentum', 'charge',
            'connection_coefficient', 'current', 'density', 'electric_field',
            'energy', 'entropy', 'force', 'frequency', 'magnetic_field',
            'mass', 'momentum', 'pressure', 'resistance', 'spacetime_curvature',
            'speed_of_light', 'strain', 'stress', 'temperature', 'time',
            'torque', 'velocity', 'voltage', 'volume', 'wave_function', 'wavelength',
            # 经典实验
            'photoelectric_effect', 'double_slit', 'blackbody_radiation',
            'compton_scattering', 'rutherford_gold_foil', 'michelson_morley',
            'galileo_inclined_plane', 'kepler_third_law', 'faraday_induction',
            'ohm_law_experiment', 'boyle_law', 'carnot_cycle', 'brownian_motion',
            'stern_gerlach_experiment', 'zeeman_effect', 'doppler_effect',
            'coulomb_law_experiment', 'pendulum_motion', 'archimedes_principle',
            'bernoulli_principle', 'superconductivity_onset', 'diffraction_grating',
            'equipartition_theorem', 'universal_gravitation',
            # 哲学思想实验
            'einstein_elevator', 'schrodinger_cat', 'epr_paradox',
            'maxwell_demon', 'twin_paradox', 'noether_theorem',
            'feynman_path_integral', 'wheeler_delayed_choice', 'complementarity',
            'correspondence_principle', 'laplace_demon', 'newtons_bucket',
            'galileos_ship', 'ockham_razor', 'anthropic_principle',
        ]

        graph_nodes = list(getattr(self.graph, '_cache', {}).keys()) or list(self.graph.keys())
        in_cache = set(graph_nodes)
        physics_nodes = [n for n in _PHYSICS_NODES if n in in_cache]

        if len(physics_nodes) < 3:
            if physics_nodes:
                print(f"  [CHAOS] only {len(physics_nodes)} physics nodes in cache, skipped")
            return

        # 核心物理枢纽: 12个节点 — 更高基础s值(路更宽)
        CORE_PHYSICS = {'force','mass','energy','acceleration','momentum',
                        'velocity','wavelength','frequency','current','voltage',
                        'temperature','charge'}
        
        seeded = 0
        for src in physics_nodes:
            for dst in physics_nodes:
                if src == dst:
                    continue
                key = (src, dst)
                # 物理核心之间: s=0.5~0.8 | 其余: s=0.1~0.3
                base_lo, base_hi = (0.5, 0.8) if (src in CORE_PHYSICS and dst in CORE_PHYSICS) else (0.1, 0.3)
                if key in self.synapse.activations:
                    old_s = self.synapse.activations[key].get('s', 0)
                    if old_s < base_lo:
                        self.synapse.activations[key]['s'] = _rnd.uniform(base_lo, base_hi)
                        seeded += 1
                else:
                    self.synapse.activations[key] = {
                        'n': set(), 'g': self.generation,
                        's': _rnd.uniform(base_lo, base_hi), 'c': 0
                    }
                    seeded += 1

        if seeded:
            print(f"  [CHAOS] +{seeded} chaotic edges seeded ({len(physics_nodes)} nodes, 婴儿先密后疏)")
        else:
            print(f"  [CHAOS] 0 edges — all pairs already exist in synapse")

    def _seed_chaos(self, n: int = 3):
        """轻量混沌边注入 — feed_queue 调用。随机在全局节点间撒 n 条低 s 边。"""
        import random as _rnd
        graph_nodes = list(getattr(self.graph, '_cache', {}).keys()) or list(self.graph.keys())
        if len(graph_nodes) < 3:
            return 0
        seeded = 0
        for _ in range(n * 3):  # 重试 up to 3x
            if seeded >= n:
                break
            a, b = _rnd.sample(graph_nodes, 2)
            key = (a, b)
            if key in self.synapse.activations:
                continue
            self.synapse.activations[key] = {
                'n': set(), 'g': self.generation,
                's': 0.02, 'c': 0
            }
            seeded += 1
        return seeded

    def _seed_physics_hub_cells(self, min_per_node: int = 20):
        """保证数学引擎能工作的物理节点至少有 min 个细胞。纯容量, 不给方法。"""
        try:
            from physics.math_derive import get_symbol
        except Exception:
            return
        from collections import Counter
        node_counts = Counter(c.node for c in self.cells)
        seeded = 0
        # 迭代 _cache (干净的图结构) 而不是 .keys() (VSA, 含垃圾)
        graph_nodes = list(getattr(self.graph, '_cache', {}).keys()) or list(self.graph.keys())
        for node in graph_nodes[:1000]:  # 检查前 1000 个节点, 确保覆盖所有物理节点
            sym = get_symbol(node)
            if sym is None:
                continue
            current = node_counts.get(node, 0)
            if current < min_per_node:
                need = min_per_node - current
                for _ in range(need):
                    cell = EvolvableCell(node, self.graph, self.board,
                                        min_split_reward=self.MIN_SPLIT_REWARD)
                    self.cells.append(cell)
                    seeded += 1
        if seeded:
            print(f"  [SEED] +{seeded} cells on physics hubs (保底)")
        return seeded

    @staticmethod
    def find_latest_snapshot(data_dir: str = None) -> tuple:
        import glob, re
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        # ── 第1遍: 只读前2KB提取 generation ──
        candidates = []  # (gen, is_crash, fpath)
        gen_re = re.compile(rb'"generation"\s*:\s*(\d+)')
        for fpath in glob.glob(os.path.join(data_dir, "evo_snapshot_gen*.json")):
            try:
                with open(fpath, 'rb') as f:
                    head = f.read(2048)
                m = gen_re.search(head)
                if m:
                    gen = int(m.group(1))
                    is_crash = b"_crash" in os.path.basename(fpath).encode()
                    candidates.append((gen, is_crash, fpath))
            except Exception:
                pass
        if not candidates:
            return 0, None
        # 选出最优: 非崩溃优先, 同类型选最高代
        best_gen, best_is_crash, best_path = 0, True, None
        for gen, is_crash, fpath in candidates:
            better = False
            if not is_crash and best_is_crash:
                better = True  # 非崩溃 > 崩溃
            elif is_crash == best_is_crash and gen > best_gen:
                better = True  # 同类型比代数
            if better:
                best_gen, best_is_crash, best_path = gen, is_crash, fpath
        # ── 第2遍: 只加载选中的那一个 ──
        if best_path is None:
            return 0, None
        try:
            if orjson is not None:
                with open(best_path, 'rb') as f:
                    data = orjson.loads(f.read())
            else:
                with open(best_path) as f:
                    data = json.load(f)
            return best_gen, data
        except Exception:
            return 0, None

    @staticmethod
    def cleanup_snapshots(data_dir: str = None, keep: int = None):
        import glob
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        if keep is None:
            keep = EvoColony.MAX_SNAPSHOTS
        files = sorted(glob.glob(os.path.join(data_dir, "evo_snapshot_gen*.json")), key=os.path.getmtime, reverse=True)
        for fpath in files[keep:]:
            try:
                os.remove(fpath)
            except Exception:
                pass

    # ═══════ 预测接口 ═══════

    def predict(self, node: str, top_n: int = 10) -> list:
        """给定一个概念, 预测它最可能导致什么 (置信度 0-1, 已归一化)"""
        predictions = []
        node_data = self.graph.get(node, {})
        
        # 全局最大 s 值用于归一化
        max_s = max((v.get('s', 0) for v in self.synapse.activations.values()), default=1)
        
        for effect in node_data.get("effects", []):
            if not isinstance(effect, (list, tuple)) or len(effect) < 3:
                continue
            law_name, dst_node = effect[0], effect[1]
            key = (node, dst_node)
            edge = self.synapse.activations.get(key, {})
            s = edge.get('s', 0.05)
            if s >= 0.03:
                source = "compose" if "composed" in str(law_name) else "coincidence"
                predictions.append({
                    "target": dst_node, 
                    "confidence": round(min(1.0, s / max(1, max_s)), 3),
                    "s_raw": round(s, 1), "c": edge.get('c', 1), "source": source,
                })
        
        predictions.sort(key=lambda x: -x["confidence"])
        return predictions[:top_n]

    @staticmethod
    def predict_cli(node: str, top_n: int = 10):
        """命令行入口 — 从最新快照加载"""
        colony = EvoColony()
        snap_gen, snap_data = EvoColony.find_latest_snapshot()
        if snap_data:
            colony.restore_from_snapshot(snap_data)
        if colony.generation < 100:
            print(f"脑未就绪 (gen {colony.generation})")
            return
        preds = colony.predict(node, top_n)
        if not preds:
            print(f"诺特对 '{node}' 还没有预测。")
            return
        print(f"目标: {node} (gen {colony.generation}, 置信度0-1)")
        print(f"{'目标':<35} {'置信度':>8} {'原始s':>8} {'c值':>5} {'来源':>12}")
        print("-" * 72)
        for p in preds:
            print(f"{p['target'][:35]:<35} {p['confidence']:>8.3f} {p['s_raw']:>8.1f} {p['c']:>5} {p['source']:>12}")

    def why(self, src: str, dst: str) -> str:
        """查询: 为什么 src → dst? 返回可读解释 (暴露容量, 不给方法)"""
        parts = []

        # 1. sympy 推导
        try:
            from physics.math_derive import derive as math_derive
            mr = math_derive(src, dst)
            if mr and mr.get("success"):
                parts.append(f"[数学推导]")
                for step in mr.get("steps", []):
                    parts.append(f"  {step}")
                parts.append(f"  → {mr.get('relation', '')}")
                parts.append(f"  置信度: {mr.get('confidence', 0)}")
        except Exception:
            pass

        # 2. 图中已有的边
        graph_entry = self.graph.get(src, {})
        found = []
        for e in graph_entry.get("effects", []):
            if isinstance(e, (list, tuple)) and len(e) >= 2 and e[1] == dst:
                found.append(e)

        if found:
            parts.append(f"\n[图中证据]")
            for law, _, domain in found:
                key = (src, dst)
                tier = self.synapse.tiers.get(key, 4)
                tier_name = {0: "公理", 1: "共识", 2: "主流", 3: "假说", 4: "探索"}.get(tier, f"t{tier}")
                edge = self.synapse.activations.get(key, {})
                s_val = edge.get('s', 0)
                n_val = len(edge.get('n', set()))
                validated = self.synapse.external_validated.get(key, False)
                tag = " [arXiv确认]" if validated else ""
                parts.append(f"  {src} → {dst}  domain={domain}  tier={tier}({tier_name})  s={s_val:.2f}  neurons={n_val}{tag}")

        if not parts:
            # 3. 猜测
            parts.append(f"[未知] {src} 和 {dst} 之间没有已知关系。")

        return "\n".join(parts)

    @staticmethod
    def why_cli(src: str, dst: str):
        """命令行: 查询为什么 src → dst"""
        colony = EvoColony()
        snap_gen, snap_data = EvoColony.find_latest_snapshot()
        if snap_data:
            colony.restore_from_snapshot(snap_data)
        print(colony.why(src, dst))

    def speak(self, question: str) -> str:
        """用脑自己的数据回答问题 (纯容量暴露, 不调 LLM)"""
        q = question.lower().strip()
        parts = []

        # 尝试从图中找出提到的概念
        mentioned = []
        for n in self.graph:
            n_clean = n.lower().replace('_', ' ')
            if n_clean in q or n in q:
                mentioned.append(n)

        if not mentioned:
            # 关键词匹配
            words = set(q.split())
            for n in self.graph:
                n_words = set(n.lower().replace('_', ' ').split())
                if words & n_words:
                    mentioned.append(n)

        # 去重 + 限制数量
        mentioned = list(dict.fromkeys(mentioned))[:5]

        if not mentioned:
            return "我不知道。图中没有你说的概念。"

        # 对提到的每个概念, 收集证据
        for concept in mentioned[:3]:
            parts.append(f"── {concept} ──")

            # 图统计
            entry = self.graph.get(concept, {})
            effects = entry.get("effects", [])
            causes = entry.get("causes", [])
            parts.append(f"  被 {len(causes)} 个概念影响, 影响 {len(effects)} 个概念")

            # 最强出边
            if effects:
                scored = []
                for e in effects:
                    if isinstance(e, (list, tuple)) and len(e) >= 2:
                        key = (concept, e[1])
                        s = self.synapse.activations.get(key, {}).get('s', 0)
                        scored.append((s, e))
                scored.sort(reverse=True)
                parts.append(f"  最强影响:")
                for s, e in scored[:3]:
                    dst, domain = e[1], e[2] if len(e) >= 3 else '?'
                    parts.append(f"    → {dst[:30]}  s={s:.2f}  domain={domain}")

            # 最强入边
            if causes:
                scored = []
                for c in causes:
                    if isinstance(c, (list, tuple)) and len(c) >= 2:
                        key = (c[0], concept)
                        s = self.synapse.activations.get(key, {}).get('s', 0)
                        scored.append((s, c))
                scored.sort(reverse=True)
                parts.append(f"  最强被影响:")
                for s, c in scored[:3]:
                    src, domain = c[0], c[2] if len(c) >= 3 else '?'
                    parts.append(f"    {src[:30]} →  s={s:.2f}")

            # math_verified 边 — 带公式
            math_edges = []
            for e in effects:
                if isinstance(e, (list, tuple)) and len(e) >= 3 and e[2] == 'math_verified':
                    math_edges.append(e)
            if math_edges:
                parts.append(f"  数学验证的发现 ({len(math_edges)}条):")
                try:
                    from physics.math_derive import derive as math_derive
                except Exception:
                    math_derive = None
                for e in math_edges[:3]:
                    dst = e[1]
                    formula = ""
                    if math_derive:
                        mr = math_derive(concept, dst)
                        if mr and mr.get('success'):
                            formula = f"  [{mr.get('relation', '')}]"
                    parts.append(f"    ✓ {concept} → {dst[:30]}{formula}")

            # tier 分布
            tiers = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
            for e in effects:
                if isinstance(e, (list, tuple)) and len(e) >= 2:
                    key = (concept, e[1])
                    t = self.synapse.tiers.get(key, 4)
                    tiers[t] = tiers.get(t, 0) + 1
            t_str = ", ".join(f"t{t}={c}" for t, c in sorted(tiers.items()) if c > 0)
            if t_str:
                parts.append(f"  置信分布: {t_str}")

        return "\n".join(parts)

    @staticmethod
    def speak_cli(question: str):
        """命令行: 问脑问题, 脑自己回答"""
        colony = EvoColony()
        snap_gen, snap_data = EvoColony.find_latest_snapshot()
        if snap_data:
            colony.restore_from_snapshot(snap_data)
        print(colony.speak(question))

    # ═══════ 矛盾持久化 ═══════

    def _save_contradictions(self):
        try:
            if self._contradiction_nodes:
                path = os.path.join(os.path.dirname(__file__), "..", "data", "contradictions.json")
                with open(path, 'w') as f:
                    json.dump(list(self._contradiction_nodes), f)
        except Exception:
            pass

    def _load_contradictions(self):
        try:
            path = os.path.join(os.path.dirname(__file__), "..", "data", "contradictions.json")
            if os.path.exists(path):
                with open(path) as f:
                    self._contradiction_nodes = set(json.load(f))
                print(f"  [CONTRA] {len(self._contradiction_nodes)} 矛盾恢复")
        except Exception:
            pass

    # ═══════ 矛盾持久化 ═══════

    def _save_contradictions(self):
        try:
            if self._contradiction_nodes:
                path = os.path.join(os.path.dirname(__file__), "..", "data", "contradictions.json")
                with open(path, 'w') as f:
                    json.dump(list(self._contradiction_nodes), f)
        except Exception:
            pass

    def _load_contradictions(self):
        try:
            path = os.path.join(os.path.dirname(__file__), "..", "data", "contradictions.json")
            if os.path.exists(path):
                with open(path) as f:
                    self._contradiction_nodes = set(json.load(f))
                if self._contradiction_nodes:
                    print(f"  [CONTRA] {len(self._contradiction_nodes)} 矛盾恢复")
        except Exception:
            pass
        print()

    # ═══════ 感官处理: probe (数值触觉) ═══════

    def _handle_probe(self, cell, result: dict) -> float:
        """处理 probe 动作: 调 LLM 获取数值关系, 返回惊奇奖励"""
        start = result.get("start", "")
        end = result.get("end", "")
        path_str = result.get("path", "")
        cache_key = (start, end, path_str[:40])
        
        # 缓存命中: 快速返回 (不给惊喜, 基线已给)
        if cache_key in self._sensory_cache:
            cached = self._sensory_cache[cache_key]
            cell._sensory_memory.append({
                "type": "probe", "start": start, "end": end,
                "result": cached.get("result", ""), "cached": True,
                "gen": self.generation,
            })
            return 0.0
        
        # 调 LLM 获取数值关系
        try:
            from llm.bridge import LLMBridge
            bridge = LLMBridge()
            if not bridge.is_available():
                return 0.0
            
            # 收集路径上的中间节点信息
            walk = result.get("walk", [])
            context_parts = []
            for step in walk[-4:]:
                if len(step) >= 2:
                    context_parts.append(f"{step[0]} → {step[-1]}")
            
            prompt = (
                f"You are a physics computation engine. Given a causal path in physics, "
                f"describe the QUANTITATIVE relationship between the endpoints.\n\n"
                f"Path: {path_str}\n"
                f"Start: {start}\n"
                f"End: {end}\n\n"
                f"Answer concisely in 1-3 sentences. Include specific numbers, formulas, "
                f"or scaling laws if known. If the relationship is purely qualitative, "
                f"state so and explain the nature of the dependence.\n"
                f"Reply ONLY with the analysis, no preamble."
            )
            response = bridge.client.chat(
                [{"role": "user", "content": prompt}], max_tokens=120
            )
            response = response.strip()
        except Exception:
            return 0.0
        
        if not response:
            return 0.0
        
        # 缓存结果
        self._sensory_cache[cache_key] = {
            "result": response, "gen": self.generation
        }
        # 每 5000 条清除旧缓存 (防内存泄漏)
        if len(self._sensory_cache) > 5000:
            old_keys = sorted(self._sensory_cache.items(), key=lambda x: x[1].get("gen", 0))
            self._sensory_cache = dict(old_keys[-2000:])
        
        # 存到神经元感官记忆
        cell._sensory_memory.append({
            "type": "probe", "start": start, "end": end,
            "result": response, "cached": False,
            "gen": self.generation,
        })
        
        # 惊奇 = 结果长度 / 5 (定性答案短, 定量答案长且信息量大)
        surprise = min(2.0, len(response) / 80)
        return surprise

    # ═══════ 感官处理: derive (推导通道) ═══════

    def _handle_derive(self, cell, result: dict) -> int:
        """纯符号推导: sympy 从方程库验证 start→end, 注入干净中间节点, 0次 LLM 调用"""
        start = result.get("start", "")
        end = result.get("end", "")
        if not start or not end or start == end:
            return 0

        # 缓存命中
        cache_key = (start, end)
        if cache_key in self._sensory_cache:
            cell._sensory_memory.append({
                "type": "derive", "start": start, "end": end,
                "result": "cached", "cached": True,
                "gen": self.generation,
            })
            return 0

        # 🧮 sympy 推导
        try:
            from physics.math_derive import derive as math_derive, get_symbol
        except Exception:
            return 0

        mr = math_derive(start, end)
        if not mr or not mr.get("success"):
            return 0

        # 推导成功: 从步骤中提取中间变量, 创建干净物理节点
        edges_added = 0
        prev_node = start
        self._ensure_node(start)
        self._ensure_node(end)

        # 解析 sympy 步骤, 提取中间物理量
        for step in mr.get("steps", []):
            # step 格式: "newton_2nd: Eq(F, a*m) → a = F/m"
            # 提取右边赋值的变量名作为中间节点
            if "=" in step:
                var_part = step.split("=")[0].strip()
                # 提取最后一个变量名
                var_name = var_part.split()[-1] if var_part.split() else ""
                # 尝试反向映射: sympy symbol → 物理概念名
                concept = self._reverse_symbol_lookup(var_name)
                if not concept:
                    # 用符号名本身
                    concept = var_name
                if concept and concept != prev_node and concept != end:
                    self._ensure_node(concept)
                    exists = any(e[1] == concept for e in
                                self.graph.get(prev_node, {}).get('effects', []))
                    if not exists:
                        law_name = f"math:{step[:40]}"
                        self.graph.setdefault(prev_node, {'effects': [], 'causes': []}).setdefault('effects', []).append(
                            (law_name, concept, 'math_verified'))
                        self.graph.setdefault(concept, {'effects': [], 'causes': []}).setdefault('causes', []).append(
                            (prev_node, law_name, 'math_verified'))
                        edges_added += 1
                        key = (prev_node, concept)
                        if key not in self.synapse.activations:
                            self.synapse.activations[key] = {
                                'n': set(), 'g': self.generation,
                                's': 0.9, 'c': 1
                            }
                    prev_node = concept

        # 最后: prev_node → end
        if prev_node != end:
            exists = any(e[1] == end for e in self.graph.get(prev_node, {}).get('effects', []))
            if not exists:
                self.graph.setdefault(prev_node, {'effects': [], 'causes': []}).setdefault('effects', []).append(
                    ('math:derived', end, 'math_verified'))
                self.graph.setdefault(end, {'effects': [], 'causes': []}).setdefault('causes', []).append(
                    (prev_node, 'math:derived', 'math_verified'))
                edges_added += 1
                key = (prev_node, end)
                if key not in self.synapse.activations:
                    self.synapse.activations[key] = {
                        'n': set(), 'g': self.generation,
                        's': 0.9, 'c': 1
                    }

        # 缓存
        self._sensory_cache[cache_key] = {
            "result": str(mr.get("relation", "")), "gen": self.generation
        }
        cell._sensory_memory.append({
            "type": "derive", "start": start, "end": end,
            "result": str(mr.get("relation", "")), "edges": edges_added,
            "math_verified": edges_added,
            "gen": self.generation,
        })

        # 🛣️ 全路径强化: 走过的正确路径变高速公路
        walk = result.get("walk", [])
        if walk and edges_added > 0:
            for step in walk:
                if len(step) >= 3:
                    w_src, _law, w_dst = step[0], step[1], step[2]
                    if w_src and w_dst and w_src != w_dst:
                        self.synapse.strengthen(0, w_src, w_dst, 0.3, self.generation)

        # 图变了, 重建引用
        if edges_added > 0:
            for c in self.cells:
                c.graph = self.graph

        return edges_added

    def _reverse_symbol_lookup(self, sym_name: str) -> str:
        """sympy 符号名 → 物理概念名 (反向映射). 例: 'a' → 'acceleration', 'F' → 'force'"""
        REVERSE = {
            'm': 'mass', 'F': 'force', 'a': 'acceleration',
            'v': 'velocity', 'p': 'momentum', 'E': 'energy',
            'E_energy': 'energy', 'E_k': 'kinetic_energy', 'E_p': 'potential_energy',
            'W': 'work', 'P_pow': 'power', 't': 'time',
            'd': 'displacement', 'x': 'position', 'r': 'radius',
            'q': 'charge', 'I': 'current', 'V_em': 'voltage', 'R': 'resistance',
            'G': 'gravitational_constant', 'g': 'gravitational_acceleration',
            'c': 'speed_of_light', 'h': 'planck_constant', 'hbar': 'reduced_planck_constant',
            'f': 'frequency', 'lambda': 'wavelength', 'omega': 'angular_frequency',
            'k': 'wave_number', 'k_s': 'spring_constant',
            'T': 'temperature', 'S': 'entropy', 'Q': 'heat',
            'P': 'pressure', 'V': 'volume', 'rho': 'density',
            'L_ang': 'angular_momentum', 'tau': 'torque',
            'Phi_B': 'magnetic_flux', 'n': 'refractive_index',
            'A': 'amplitude', 'theta': 'angle',
            'psi': 'wavefunction',
            # 几何/GR
            'R': 'scalar_curvature', 'T': 'stress_energy',
            'G_mn': 'einstein_tensor', 'Gamma': 'connection_coefficient',
            'a_geo': 'geodesic_acceleration', 'R_mn': 'ricci_tensor',
            'g_mn': 'metric_tensor', 'kappa': 'gravitational_coupling',
            'gamma': 'lorentz_factor',
            # 场论
            'A_mu': 'gauge_field', 'phi': 'scalar_field',
            'J_mu': 'source_current', 'g_c': 'coupling_constant',
            'L': 'lagrangian',
        }
        return REVERSE.get(sym_name, "")

    # ═══════ 感官输入 ═══════

    def stimulate(self, text: str, boost: float = 2.0, duration: int = 10):
        """🧠 外部刺激: 文本 → 匹配图谱节点 → 激活驻留细胞。
        - text: 输入文本 (如 'f=ma', 'E=mc^2', 'quantum entanglement')
        - boost: 加成因子 (EIG 乘数)
        - duration: 持续代数
        """
        import re
        tokens = set(re.findall(r'[a-zA-Z_][a-zA-Z_0-9]*', text.lower()))
        # 匹配图谱节点 (子串匹配)
        matched = []
        for node_name in self.graph._cache:
            name_lower = node_name.lower()
            # 完整命中优先
            if name_lower in text.lower() or any(t in name_lower for t in tokens if len(t) >= 2):
                matched.append(node_name)
        if not matched:
            return 0
        # 激活这些节点上的细胞
        boost_end = self.generation + duration
        count = 0
        stimulated_nodes = set(matched)
        for cell in self.cells:
            if cell.node in stimulated_nodes:
                cell._stimulus = boost
                cell._stimulus_until = boost_end
                count += 1
        print(f"  [STIMULUS] \"{text[:40]}\" → {len(matched)} 节点, {count} 细胞 ×{boost} ({duration}代)")
        return count

    # ═══════ 内存优化 ═══════

    SYNAPSE_MAX_EDGES = 500000     # 突触边上限
