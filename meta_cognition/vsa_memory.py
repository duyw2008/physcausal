"""
VSA (Vector Symbolic Architecture) Memory Engine — 费曼脑的 HD 记忆层

用高维向量叠加替代显式邻接表, 实现：
- 边存储 O(d) 固定，不随边数增长
- 游走查询 O(d × N_active)，不随节点度增长
- 冷池边与热池边用同一套向量，自然支持唤醒

核心操作：
  bind(a, b)     = a * b                 (element-wise 乘法, ±1)
  bundle(M, v)   = M + v                 (叠加)
  probe(M, v)    = M * v                 (解绑: 从 M 中提取与 v 相关的所有内容)
  similarity     = dot(v1, v2) / d       (余弦相似度等价, ±1 → [-1, 1])

维度 d=4096, 存储 200K 边: SNR ≈ √(d/N) ≈ 0.14
"""

from __future__ import annotations
from typing import Dict, List, Tuple, Optional, Set
import numpy as np
import random


class VSAEngine:
    """HD 向量记忆引擎"""

    DEFAULT_DIM = 4096
    DOMAINS = ["physics", "research", "probe", "emergent",
               "hypothesis", "experiment", "derive", "abstraction"]

    def __init__(self, dim: int = DEFAULT_DIM, seed: int = 42):
        self.dim = dim
        self.rng = np.random.RandomState(seed)

        # 每个神经元的固定 HD 向量 (bipolar ±1)
        self.node_vectors: Dict[str, np.ndarray] = {}

        # 方向标签 — 用于区分出边/入边
        # 出边: probe(M, V_node * V_FWD) → V_dst
        # 入边: probe(M, V_node * V_BWD) → V_src
        self.V_FWD = self._new_vector()  # 固定的出边标签
        self.V_BWD = self._new_vector()  # 固定的入边标签 (不同于 V_FWD)

        # 各域的边叠加记忆 — 方向已编码在叠加模式中
        # M_effects[domain]: 只存出边  Σ bind(V_src * V_FWD, V_dst) × s
        # M_causes[domain]:  只存入边  Σ bind(V_src * V_BWD, V_dst) × s
        self.mem_effects: Dict[str, np.ndarray] = {}
        self.mem_causes: Dict[str, np.ndarray] = {}

        # 兼容旧接口: self.memories 指向 effects (单向查询 fallback)
        self.memories: Dict[str, np.ndarray] = self.mem_effects

        # 活跃池向量矩阵: (N_active × d), 查询 top-k 时加速
        self._active_matrix: Optional[np.ndarray] = None
        self._active_nodes: List[str] = []   # 跟 _active_matrix 行对应

    # ═══════ 向量工厂 ═══════

    def _new_vector(self) -> np.ndarray:
        """生成随机 bipolar ±1 向量"""
        return self.rng.choice([-1.0, 1.0], size=self.dim).astype(np.float32)

    def get_or_create_vector(self, node_id: str) -> np.ndarray:
        """获取或创建神经元向量 (幂等)"""
        if node_id not in self.node_vectors:
            self.node_vectors[node_id] = self._new_vector()
        return self.node_vectors[node_id]

    # ═══════ 边操作 ═══════

    def add_edge(self, src: str, dst: str, domain: str, strength: float = 1.0):
        """叠加一条边: 出边存入 mem_effects, 入边存入 mem_causes"""
        if domain not in self.DOMAINS:
            domain = "emergent"

        # 出边记忆
        if domain not in self.mem_effects:
            self.mem_effects[domain] = np.zeros(self.dim, dtype=np.float32)
        # 入边记忆
        if domain not in self.mem_causes:
            self.mem_causes[domain] = np.zeros(self.dim, dtype=np.float32)

        v_src = self.get_or_create_vector(src)
        v_dst = self.get_or_create_vector(dst)

        # 出边编码: V_src * V_FWD * V_dst  →  probe(V_node * V_FWD) 解出 V_dst
        pattern_effects = v_src * self.V_FWD * v_dst
        self.mem_effects[domain] += pattern_effects.astype(np.float32) * strength

        # 入边编码: V_src * V_BWD * V_dst  →  probe(V_node * V_BWD) 解出 V_src
        pattern_causes = v_src * self.V_BWD * v_dst
        self.mem_causes[domain] += pattern_causes.astype(np.float32) * strength

    def add_edge_bidirectional(self, src: str, dst: str, domain: str, strength: float = 1.0):
        """双向边: 同时存 src→dst 和 dst→src"""

        # 单向已够——probe(M, V_src) 解出 V_dst, probe(M, V_dst) 解出 V_src
        # 对称性是 VSA 自带的好处
        self.add_edge(src, dst, domain, strength)

    # ═══════ 查询 ═══════

    def query(
        self,
        node_id: str,
        domains: Optional[List[str]] = None,
        k: int = 50,
        threshold_ratio: float = 0.3,
        direction: str = "effects"
    ) -> List[Tuple[str, str, float]]:
        """
        查询与 node_id 相关的边。

        direction: "effects" (出边) / "causes" (入边)
        返回: [(target_node, domain, score), ...] 按 score 降序
        """
        if node_id not in self.node_vectors:
            return []

        mem_dict = self.mem_effects if direction == "effects" else self.mem_causes
        tag = self.V_FWD if direction == "effects" else self.V_BWD

        if domains is None:
            domains = list(mem_dict.keys())
        domains = [d for d in domains if d in mem_dict]

        if not domains:
            return []

        v_node = self.node_vectors[node_id]

        results = []
        for domain in domains:
            # probe = M_domain * (V_node * tag)
            probe = mem_dict[domain] * v_node * tag  # (d,)

            if self._active_matrix is not None and len(self._active_nodes) > 0:
                scores = self._active_matrix @ probe  # (N_active,)

                if len(scores) > 0:
                    max_score = float(np.max(scores))
                    if max_score > 0:
                        threshold = threshold_ratio * max_score
                        k_eff = min(k, len(scores))
                        if k_eff > 0:
                            top_indices = np.argpartition(-scores, k_eff - 1)[:k_eff]
                        else:
                            top_indices = np.array([], dtype=int)

                        above_threshold = np.where(scores > threshold)[0]
                        all_indices = np.unique(np.concatenate([top_indices, above_threshold]))

                        for idx in all_indices:
                            if idx < len(self._active_nodes):
                                target = self._active_nodes[idx]
                                if target != node_id:
                                    results.append((target, domain, float(scores[idx])))

        # 去重 (同 dst 取最高分域)
        seen = {}
        for dst, domain, score in results:
            if dst not in seen or score > seen[dst][1]:
                seen[dst] = (domain, score)

        return [(dst, dom, scr) for dst, (dom, scr) in
                sorted(seen.items(), key=lambda x: -x[1][1])]

    def query_effects(self, node_id: str, domains=None, k=50, threshold_ratio=0.3):
        """查询出边"""
        return self.query(node_id, domains, k, threshold_ratio, direction="effects")

    def query_causes(self, node_id: str, domains=None, k=50, threshold_ratio=0.3):
        """查询入边"""
        return self.query(node_id, domains, k, threshold_ratio, direction="causes")

    # ═══════ 活跃池管理 ═══════

    def update_active_cache(self, active_nodes: List[str]):
        """重建活跃池向量矩阵，供 query 做批量点积"""
        self._active_nodes = list(active_nodes)
        if not self._active_nodes:
            self._active_matrix = None
            return

        # 确保所有活跃节点有向量
        vectors = []
        for nid in self._active_nodes:
            v = self.get_or_create_vector(nid)
            vectors.append(v)

        self._active_matrix = np.stack(vectors, axis=0)  # (N_active, d)

    # ═══════ 序列化 ═══════

    def to_dict(self) -> dict:
        """快照序列化 — 直接返回 numpy 数组 (orjson OPT_SERIALIZE_NUMPY 序列化, 避免 tolist 膨胀 ~850MB)"""
        return {
            "dim": self.dim,
            "node_vectors": {k: v for k, v in self.node_vectors.items()},
            "mem_effects": {k: v for k, v in self.mem_effects.items()},
            "mem_causes": {k: v for k, v in self.mem_causes.items()},
            "V_FWD": self.V_FWD,
            "V_BWD": self.V_BWD,
        }

    def from_dict(self, data: dict):
        """从快照恢复"""
        if not data:
            return
        self.dim = data.get("dim", self.DEFAULT_DIM)
        self.node_vectors = {
            k: np.array(v, dtype=np.float32)
            for k, v in data.get("node_vectors", {}).items()
        }
        self.mem_effects = {
            k: np.array(v, dtype=np.float32)
            for k, v in data.get("mem_effects", {}).items()
        }
        self.mem_causes = {
            k: np.array(v, dtype=np.float32)
            for k, v in data.get("mem_causes", {}).items()
        }
        # 恢复方向标签
        if "V_FWD" in data:
            self.V_FWD = np.array(data["V_FWD"], dtype=np.float32)
        if "V_BWD" in data:
            self.V_BWD = np.array(data["V_BWD"], dtype=np.float32)
        # 兼容
        self.memories = self.mem_effects

    # ═══════ 统计 ═══════

    def stats(self) -> dict:
        total = sum(float(np.sum(np.abs(m))) for m in self.mem_effects.values())
        total += sum(float(np.sum(np.abs(m))) for m in self.mem_causes.values())
        return {
            "dim": self.dim,
            "node_count": len(self.node_vectors),
            "domains_effects": list(self.mem_effects.keys()),
            "domains_causes": list(self.mem_causes.keys()),
            "total_abs_strength": total,
            "active_cache_size": len(self._active_nodes),
        }


# ═══════════════════════════════════════════════
# VSAGraph — 适配层: 对外暴露 dict-like 接口
# graph[node]["effects"].append(...) 自动同步 VSA
# 内部走 VSA 查询, 内存 O(d) 固定
# ═══════════════════════════════════════════════

class _WriteThroughList(list):
    """write-through 代理: append() 自动同步到 VSA"""
    __slots__ = ('_vsa_graph', '_node_id', '_direction')

    def __init__(self, *args, _vsa_graph=None, _node_id=None, _direction=None):
        super().__init__(*args)
        self._vsa_graph = _vsa_graph
        self._node_id = _node_id
        self._direction = _direction  # "effects" or "causes"

    def append(self, item):
        super().append(item)
        if self._vsa_graph is None or not self._node_id:
            return
        # 解析 item: effects=(law, dst, domain), causes=(src, law, domain)
        if self._direction == "effects" and len(item) >= 2:
            law, dst = item[0], item[1]
            domain = item[2] if len(item) > 2 else "emergent"
            self._vsa_graph._sync_edge(self._node_id, dst, law, domain)
        elif self._direction == "causes" and len(item) >= 2:
            src, law = item[0], item[1]
            domain = item[2] if len(item) > 2 else "emergent"
            self._vsa_graph._sync_edge(src, self._node_id, law, domain)

    def __setitem__(self, index, item):
        super().__setitem__(index, item)
        # 原地修改 (blocked ↔ unblocked) 也触发同步
        if self._vsa_graph is not None and self._node_id:
            if self._direction == "effects" and len(item) >= 2:
                law, dst = item[0], item[1]
                domain = item[2] if len(item) > 2 else "emergent"
                self._vsa_graph._sync_edge(self._node_id, dst, law, domain)

    # NOTE: extend, insert, remove 等更复杂操作不走 VSA,
    # 但现有代码只用了 append 和 __setitem__


class _DummyVSA:
    """deepcopy 中间态占位 — VSAGraph.__init__ 未跑完时所有 VSA 操作都是 no-op"""
    node_vectors: dict = {}
    def add_edge(self, *a, **kw): pass
    def get_or_create_vector(self, *a, **kw): pass
    def query_effects(self, *a, **kw): return []
    def query_causes(self, *a, **kw): return []
    def update_active_cache(self, *a, **kw): pass
    def __contains__(self, k): return False
    def __len__(self): return 0
    def __iter__(self): return iter([])
    def keys(self): return iter([])


class VSAGraph:
    """VSA 支持的图, 对外接口完全兼容 dict[node_id] → {effects, causes}"""

    BLOCKED_DOMAIN = "blocked"

    def __new__(cls, *args, **kwargs):
        instance = super().__new__(cls)
        instance.vsa = _DummyVSA()  # deepcopy 安全: __init__ 未跑时所有 VSA 操作都是 no-op
        return instance

    def __init__(self, vsa: Optional[VSAEngine] = None):
        self.vsa = vsa or VSAEngine()  # 覆盖 __new__ 里的 _DummyVSA
        self._cache: Dict[str, dict] = {}
        self._dirty: Set[str] = set()

    # ═══ 内部: VSA 同步 ═══

    def _sync_edge(self, src: str, dst: str, law_name: str, domain: str):
        """纯 VSA 同步, 不改缓存 (缓存由 WriteThroughList 已更新)"""
        if domain == self.BLOCKED_DOMAIN:
            return
        self.vsa.add_edge(src, dst, domain)

    # ═══ dict-like 读接口 ═══

    def __getitem__(self, node_id: str) -> dict:
        if node_id not in self._cache:
            # 懒初始化: 不触发 VSA 查询
            # VSA 仅用于冷池唤醒和相似度检索, 日常游走走显式缓存
            self._cache[node_id] = {
                "causes": _WriteThroughList([],
                    _vsa_graph=self, _node_id=node_id, _direction="causes"),
                "effects": _WriteThroughList([],
                    _vsa_graph=self, _node_id=node_id, _direction="effects"),
                "explore_count": 0,  # 🆕 节点被探索次数 (EIG 价值消耗)
            }
        elif node_id in self._dirty:
            self._rebuild_cache(node_id)
        return self._cache[node_id]

    def get(self, node_id: str, default=None):
        if node_id in self.vsa.node_vectors:
            return self[node_id]
        return default

    def __contains__(self, node_id: str) -> bool:
        return node_id in self.vsa.node_vectors

    def __len__(self):
        return len(self.vsa.node_vectors)

    def values(self):
        """迭代所有节点的缓存数据 (需要时触发 VSA 查询)"""
        for k in self.vsa.node_vectors:
            yield self[k]

    def keys(self):
        return self.vsa.node_vectors.keys()

    def __iter__(self):
        return iter(self.vsa.node_vectors)

    def items(self):
        for k in self.vsa.node_vectors:
            yield (k, self[k])

    # ═══ dict-like 写接口 ═══

    def setdefault(self, node_id: str, default=None):
        self.vsa.get_or_create_vector(node_id)
        if node_id not in self._cache:
            entry = default or {"causes": [], "effects": []}
            # 把普通 list 转成 write-through
            entry["effects"] = _WriteThroughList(
                entry.get("effects", []),
                _vsa_graph=self, _node_id=node_id, _direction="effects")
            entry["causes"] = _WriteThroughList(
                entry.get("causes", []),
                _vsa_graph=self, _node_id=node_id, _direction="causes")
            self._cache[node_id] = entry
        return self._cache[node_id]

    def __setitem__(self, node_id: str, value: dict):
        self.vsa.get_or_create_vector(node_id)
        value.setdefault("explore_count", 0)  # 🆕 外部条目兜底
        # 确保 lists 是 write-through
        value["effects"] = _WriteThroughList(
            value.get("effects", []),
            _vsa_graph=self, _node_id=node_id, _direction="effects")
        value["causes"] = _WriteThroughList(
            value.get("causes", []),
            _vsa_graph=self, _node_id=node_id, _direction="causes")
        self._cache[node_id] = value

    def add_edge(self, src: str, dst: str, law_name: str, domain: str,
                 strength: float = 1.0):
        """显式加边: VSA + 缓存双写"""
        if domain == self.BLOCKED_DOMAIN:
            return
        self.vsa.add_edge(src, dst, domain, strength)
        # 缓存写入
        s = self.setdefault(src, {"causes": [], "effects": []})
        d = self.setdefault(dst, {"causes": [], "effects": []})
        s["effects"].append((law_name, dst, domain))
        d["causes"].append((src, law_name, domain))

    @property
    def edge_count(self) -> int:
        return sum(len(n.get("effects", [])) for n in self._cache.values())

    def ensure_node(self, node_id: str):
        self.setdefault(node_id, {"causes": [], "effects": []})

    # ═══ 缓存管理 ═══

    def _rebuild_cache(self, node_id: str):
        effects_raw = self.vsa.query_effects(node_id)
        causes_raw = self.vsa.query_causes(node_id)
        # 因果域优先: δS=0 变分(axomatic/physics/derive)决定意义, 词共现(emergent)作背景
        # 细胞读 graph 时因果邻居排前面 → walk 偏向因果网, 不被词共现糊糊带偏
        _CAUSAL_DOMAINS = {'axomatic', 'physics', 'derive'}
        def _rank(item):
            # item = (target, domain, score): 因果域排前, 同域按 score 降序
            return (0 if item[1] in _CAUSAL_DOMAINS else 1, -item[2])
        effects_raw.sort(key=_rank)
        causes_raw.sort(key=_rank)
        effects = [(domain, dst, domain) for dst, domain, _ in effects_raw]
        causes = [(src, domain, domain) for src, domain, _ in causes_raw]

        _prev_ec = self._cache.get(node_id, {}).get("explore_count", 0)
        self._cache[node_id] = {
            "causes": _WriteThroughList(causes,
                _vsa_graph=self, _node_id=node_id, _direction="causes"),
            "effects": _WriteThroughList(effects,
                _vsa_graph=self, _node_id=node_id, _direction="effects"),
            "explore_count": _prev_ec,  # 🆕 重建缓存保留探索计数
        }
        self._dirty.discard(node_id)

    def invalidate(self, node_id: str):
        self._dirty.add(node_id)

    def update_active_cache(self, active_nodes: List[str]):
        self.vsa.update_active_cache(active_nodes)
        # 不预热全部缓存: O(N_active) 次矩阵乘法太贵
        # 让游走自然触发单节点懒加载
