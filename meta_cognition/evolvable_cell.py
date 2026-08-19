"""
可进化细胞 — 诺特自进化的基础单元

每个细胞有一个基因组 (行为权重向量)，决定它如何行动。
没有硬编码的"学习"、"教学"、"压缩"——
这些是细胞在自然选择中自己发现的策略。

原子操作:
  1. step_forward  — 沿出边走一步
  2. step_backward — 沿入边回溯一步
  3. mark          — 在当前节点注册黑板
  4. echo          — 回应已有的黑板信号
  5. split         — 分裂到邻居节点
  6. rest          — 不动 (浪费一代)
  7. intervene     — 反事实干预: 屏蔽低信息边走高的
  8. probe         — 数值触觉: 探测当前walk路径的定量关系
  9. derive        — 推导通道: 请求推导walk两端的物理机制

强化信号:
  - 如果 mark 后黑板共振 → 奖励
  - 如果 echo 匹配已有信号 → 奖励
  - 每走一步 → 微弱奖励
  - 死亡 → 基因组消失

突变: 繁殖时基因组有小幅随机扰动
"""

from __future__ import annotations
from typing import Dict, List, Tuple, Optional
import random, time
from collections import Counter
from meta_cognition.walk_fingerprint import walk_fingerprint


Action = str  # 'step_forward' | 'step_backward' | 'mark' | 'echo' | 'split' | 'rest' | 'intervene'

ACTIONS: List[Action] = ['step_forward', 'step_backward', 'mark', 'echo', 'split', 'rest', 'intervene', 'probe', 'derive']

# 白名单域: 细胞走边时优先走这些域 (纯容量 — 倾向不是强制)
WHITELIST_DOMAINS = {"math_verified", "mechanics", "electromagnetism",
                     "thermodynamics", "quantum", "optics",
                     "modern", "general_relativity", "emergent", "philosophy"}


class EvolvableCell:
    """基因组驱动的可进化细胞"""
    
    MAX_AGE = 120
    GENOME_MAX = 3.0            # 单基因权重上限 (防止 runaway)
    MAX_WALK_MEMORY = 10
    MAX_WALK_CANDIDATES = 200  # 积分-触发: 游走时只取前 N 条最强边

    _cell_id_counter = 0

    @classmethod
    def _next_cell_id(cls) -> int:
        cls._cell_id_counter += 1
        return cls._cell_id_counter

    def __init__(self, node_id: str, graph: Dict, board: 'Blackboard',
                 genome: Optional[Dict[str, float]] = None,
                 myelin=None, neuro=None, min_split_reward: float = 0.5):
        self.node = node_id
        self.cell_id = EvolvableCell._next_cell_id()  # 稳定唯一ID, 替代 id()%10000 的碰撞/复用
        self.graph = graph
        self.board = board
        self.age = 0
        self.memory: List[Tuple[str, str, str, str, int]] = []  # (src, law, dst, dom, dw)
        self.goal: Optional[str] = None  # 持久意图: 冷池唤醒后继续追
        self.min_split_reward = min_split_reward  # 分裂能量门槛 (由外部设置)
        
        # 基因组: 每个原子操作的权重
        if genome is None:
            total = len(ACTIONS)
            self.genome = {a: 1.0 / total for a in ACTIONS}
            # 元学习参数: curiosity 调节探索/深耕倾向 (0.3=深耕, 1.0=均衡, 3.0=探索)
            self.genome["curiosity"] = 1.0
            # 元学习: 学习规则本身可进化
            self.genome["reinforce_rate"] = 0.12   # 多巴胺敏感度 (0.05-0.30)
            self.genome["decay_rate"] = 0.005      # 遗忘速度 (0.001-0.02)
            self.genome["mutation_rate"] = 0.10    # 变异幅度 (0.02-0.25)
            # 脑区分化: niche 0=内部游走偏好, 1=外部输入偏好
            self.genome["niche"] = random.uniform(0.1, 0.9)
        else:
            self.genome = dict(genome)
            # 兼容旧快照（无这些字段时补默认值）
            self.genome.setdefault("curiosity", 1.0)
            self.genome.setdefault("reinforce_rate", 0.12)
            self.genome.setdefault("decay_rate", 0.005)
            self.genome.setdefault("mutation_rate", 0.10)
            # 新感官动作: 旧快照无此基因时给初始权重
            self.genome.setdefault("probe", 1.0 / len(ACTIONS))
            self.genome.setdefault("derive", 1.0 / len(ACTIONS))

        # 适应度跟踪
        self.total_reward = 0.0
        self.last_action: Optional[Action] = None
        # 🧠 私有突触: 每边走独立权重 + 树突 + 轴突
        self.weights: Dict[str, float] = {}  # target_node → 累积权重
        self.dendrites: set = set()           # 树突: 我听哪些概念
        self.axons: set = set()               # 轴突: 我投射了哪些突触边 (src, dst) tuples
        self.myelin: Dict[tuple, float] = {}   # 髓鞘: 每条边的传导速度 (频繁走→变厚→更快)
        self.last_rewarded = False

        # 资格迹
        self.trace: Dict[str, float] = {}
        # 🧩 内在好奇: 预测落差驱动探索
        self.prediction_model: Dict[str, Counter] = {}  # node → {next_node: count}
        self.prediction_error: float = 0.0              # 最近一次预测误差
        self._prev_pe: float = 0.0                      # 上一次预测误差 (消化检测: 落空→命中=学会)
        self.intrinsic_curiosity: float = 1.0           # 累积好奇 (>1.0=探索, <1.0=深耕)
        # 路径记忆
        self.current_walk: List[Tuple[str, str, str]] = []
        self.walk_memory: List[List[Tuple[str, str, str]]] = []
        self._sensory_memory: List[Dict] = []
        
        # 工作记忆: 前额叶 active_buffer
        from meta_cognition.working_memory import WorkingMemory
        self.wm = WorkingMemory()

    @property
    def axon(self):
        if not self.weights:
            return None
        best = max(self.weights, key=self.weights.get)
        return (best, self.weights[best])

    def to_seed(self) -> dict:
        """序列化为磁盘种子 — 只保留基因组和元数据，walk_memory 不存盘"""
        return {
            "node": self.node,
            "genome": dict(self.genome),
            "age": self.age,
            "total_reward": self.total_reward,
            "last_action": self.last_action,
            "wm": self.wm.to_dict(),  # 工作记忆持久化
        }

    @classmethod
    def from_seed(cls, seed: dict, graph, board, min_split_reward=0.5) -> "EvolvableCell":
        """从磁盘种子孵化细胞"""
        cell = cls(seed["node"], graph, board,
                   genome=seed.get("genome"),
                   min_split_reward=min_split_reward)
        cell.age = seed.get("age", 0)
        cell.total_reward = seed.get("total_reward", 0)
        cell.last_action = seed.get("last_action", "step_forward")
        return cell
    
    def act(self) -> Dict:
        """选择行动: 按基因组权重随机选, curiosity调制探索/深耕"""
        # age由colony的_step_neurons统一管理, 不在这里递增
        
        # 工作记忆维持: 多巴胺来自 curiosity 代理
        dopamine_proxy = self.genome.get("curiosity", 1.0) * 0.3
        self.wm.maintain(dopamine_proxy)
        
        # 加权随机选择
        actions = list(self.genome.keys())
        # 排除元参数 (不是行动)
        META_PARAMS = {"curiosity", "reinforce_rate", "decay_rate", "mutation_rate", "niche"}
        action_keys = [a for a in actions if a not in META_PARAMS]
        weights = [max(0.01, self.genome.get(a, 1.0 / len(ACTIONS))) for a in action_keys]

        # 🏠 密度依赖: 全局细胞越多 → split 权重越低 (生态位竞争)
        density = getattr(self, '_density_pressure', 1.0)
        for i, a in enumerate(action_keys):
            if a == 'split':
                weights[i] *= density

        # 振荡节律: dopa群内临时加倍行动权重
        osc = getattr(self, '_osc_boost', 1.0)
        if osc > 1.0:
            weights = [w * osc for w in weights]
            self._osc_boost = max(1.0, osc - 0.05)  # 逐步衰减
        
        # 元学习: curiosity 调制探索 vs 深耕
        curiosity = self.genome.get("curiosity", 1.0)
        for i, a in enumerate(action_keys):
            if a in ("step_forward", "step_backward"):
                weights[i] *= max(0.1, curiosity)            # 高好奇→多探索
            elif a == "mark":
                weights[i] *= max(0.3, 2.0 - curiosity)      # 高好奇→少标记
        # 脑区分化: niche调制探索vs深耕 (0=内部深耕, 1=外部探索)
        niche = self.genome.get("niche", 0.5)
        for i, a in enumerate(action_keys):
            if a in ("step_forward", "step_backward"):
                weights[i] *= 0.5 + niche                   # 高niche→多走动
            elif a in ("mark", "echo"):
                weights[i] *= 1.5 - niche                   # 低niche→多标记/深耕
        
        total = sum(weights)
        r = random.random() * total
        cumulative = 0
        chosen = action_keys[-1]
        for a, w in zip(action_keys, weights):
            cumulative += w
            if r <= cumulative:
                chosen = a
                break
        
        self.last_action = chosen
        
        # 资格迹: 衰减旧痕迹, 当前动作标记为 1.0
        for a in list(self.trace.keys()):
            self.trace[a] *= 0.6
            if self.trace[a] < 0.01:
                del self.trace[a]
        self.trace[chosen] = 1.0
        
        # 执行
        if chosen == 'step_forward':
            result = self._step_forward()
        elif chosen == 'step_backward':
            result = self._step_backward()
        elif chosen == 'mark':
            result = self._mark()
        elif chosen == 'echo':
            result = self._echo()
        elif chosen == 'split':
            result = self._split()
        elif chosen == 'intervene':
            result = self._intervene()
        elif chosen == 'probe':
            result = self._probe()
        elif chosen == 'derive':
            result = self._derive()
        else:  # rest → 记忆巩固
            result = self._rest()
        
        return result
        # 执行
    
    def _rest(self) -> Dict:
        """休息 = 记忆巩固: 重放 walk_memory 中最有价值的路径"""
        if not self.walk_memory:
            return {"type": "rest", "node": self.node, "replay": None}
        # 选路径长度最大的 (跨域多的优先)
        best = max(self.walk_memory, key=lambda w: len(w) + 
                   len(set(s[3] for s in w if len(s)>=4)) * 2)
        return {"type": "rest", "node": self.node, "replay": best}
    
    def give_energy(self, amount: float):
        """ATP: 纯能量, 用于生存和分裂, 不影响行为权重"""
        self.total_reward += amount
    
    def receive_reward(self, amount: float):
        """多巴胺: 资格迹分配 — last_action 得70%, 其余有trace的动作按trace分摊30%"""
        if not self.last_action:
            return
        rr = self.genome.get("reinforce_rate", 0.12)
        if self.last_action not in self.genome:
            self.genome[self.last_action] = 1.0 / len(ACTIONS)
        
        # 主奖励: last_action 拿 70%
        main_portion = amount * rr * 0.70
        self.genome[self.last_action] += main_portion
        self.genome[self.last_action] = max(0.005, min(self.genome[self.last_action], self.GENOME_MAX))
        self.total_reward += amount
        
        # 资格迹分配: 其余有 trace 的动作分摊 30%
        other_traces = {a: t for a, t in self.trace.items() if a != self.last_action and t > 0.01}
        if other_traces:
            total_trace = sum(other_traces.values())
            trace_portion = amount * rr * 0.30
            for a, t in other_traces.items():
                if a not in self.genome:
                    self.genome[a] = 1.0 / len(ACTIONS)
                share = trace_portion * (t / total_trace)
                self.genome[a] = max(0.005, min(self.genome[a] + share, self.GENOME_MAX))
        
        self.last_rewarded = True
    
    def apply_decay(self):
        """每代统一衰减 + 归一化: 所有动作平分衰退后重新归一化到1.0"""
        dr = self.genome.get("decay_rate", 0.001)
        META = {"curiosity", "reinforce_rate", "decay_rate", "mutation_rate", "niche"}
        for a in list(self.genome.keys()):
            if a not in META:
                self.genome[a] = max(0.005, self.genome[a] - dr)
        # 归一化: 动作权重和为1.0，防止无界膨胀
        action_total = sum(v for k, v in self.genome.items() if k not in META)
        if action_total > 0.001:
            for k in self.genome:
                if k not in META:
                    self.genome[k] = max(0.005, self.genome[k] / action_total)
    
    # ── 原子操作 ──
    
    def _dendritic_sense(self) -> Dict[str, Dict]:
        """🧠 树突预处理: 感知当前节点的邻域结构。
        对每个邻居节点计算: 是否跨域桥接、未探索程度、emergent邻域。
        返回 dict: {neighbor_id: {cross_domain, frontier, emergent_nearby}}"""
        result = {}
        node = self.graph.get(self.node, {"causes": [], "effects": []})
        # 当前节点的域 (从出边域标签推断)
        my_domains = set()
        for _, _, dom in node.get("effects", []):
            if dom and dom not in ("emergence", "blocked", "synapse"):
                my_domains.add(dom)
        for _, _, dom in node.get("causes", []):
            if dom and dom not in ("emergence", "blocked", "synapse"):
                my_domains.add(dom)

        for law, dst, dom in node.get("effects", []):
            if dom in ("emergence", "blocked"):
                continue
            nd = self.graph.get(dst, {"causes": [], "effects": []})
            nb_domains = set()
            nb_emergent = 0
            nb_total_edges = 0
            for _, _, ed in nd.get("effects", []):
                if ed and ed not in ("emergence", "blocked", "synapse"):
                    nb_domains.add(ed)
                if ed == "emergent":
                    nb_emergent += 1
                nb_total_edges += 1
            for _, _, ed in nd.get("causes", []):
                if ed and ed not in ("emergence", "blocked", "synapse"):
                    nb_domains.add(ed)

            # 跨域: 邻居的域与当前节点的域有交集外的域
            cross = len(nb_domains - my_domains) > 0 if my_domains else len(nb_domains) > 1
            # 未探索: 邻居的出边数少
            frontier = max(0, 5 - min(nb_total_edges, 5))
            result[dst] = {
                "cross_domain": cross,
                "frontier": frontier,
                "emergent_nearby": nb_emergent > 0,
            }
        return result

    def _learn_and_curate(self, src: str, dst: str, dom: str):
        """内在好奇: 预测'从 src 会去哪'→ 对比实际 → 落差驱动好奇"""
        # 学会检测: 更新前的主流预测 (most_common 翻转 = 学习事件)
        if src not in self.prediction_model:
            self.prediction_model[src] = Counter()
        prev_model = self.prediction_model[src]
        prev_predicted = prev_model.most_common(1)[0][0] if prev_model else None
        # 学习: 更新预测模型 — 自环不算"去向"预测 (src→src 是停留, 不参与主流竞争, 防枢纽节点刷翻转)
        if dst != src:
            self.prediction_model[src][dst] += 1
        # 限制模型大小
        if len(self.prediction_model) > 50:
            self.prediction_model.pop(next(iter(self.prediction_model)))
        
        # 预测: 之前在这走了什么
        if len(self.memory) >= 2:
            prev_node = self.memory[-2][2]  # 两个 move 前的源节点
            if prev_node in self.prediction_model:
                expected = self.prediction_model[prev_node]
                predicted = expected.most_common(1)[0][0] if expected else None
                # 保存旧误差 (供观察, 奖励改用翻转检测)
                self._prev_pe = self.prediction_error
                # 预测误差: 预测"从 prev_node 会去哪" vs 实际去的 dst
                self.prediction_error = 0.3 if predicted != dst else 0.0
            else:
                self._prev_pe = self.prediction_error
                self.prediction_error = 0.2  # 全新探索
        
        # 好奇累积: 预测误差驱动探索欲 (>1.0 更多探索, <1.0 深耕)
        self.intrinsic_curiosity *= 0.95  # 衰减
        self.intrinsic_curiosity += self.prediction_error * 0.5
        self.intrinsic_curiosity = max(0.3, min(3.0, self.intrinsic_curiosity))

        # 🧩 学会奖励 (规则, 非管道): 主流预测翻转为 dst = 这条转移成为细胞的主流认知
        # 门槛: 必须先形成过主流认知 (prev_predicted 非空) 再被反超, 一次采样不算学会
        # 自环翻转 (src→src) 不奖: 学会打转是坏习惯, 跟习惯化刹车对着干
        new_model = self.prediction_model[src]
        new_predicted = new_model.most_common(1)[0][0] if new_model else None
        if (dst != src and prev_predicted is not None and new_predicted is not None
                and prev_predicted != dst and new_predicted == dst):
            return 1.0   # 学习事件: 一次只发一次 (主流已翻转后不再触发)
        return 0.0

    def _expected_info_gain(self, dst: str) -> float:
        """局部预期信息增益: 只基于图结构和自身记忆
        
        走之前评估每条边的预期学习价值。只靠神经元自己
        能看到的: 图结构 + walk_memory。不给全局视角。
        """
        score = 1.0
        nd = self.graph.get(dst, {"causes": [], "effects": []})
        in_d = len(nd["causes"]); out_d = len(nd["effects"])
        deg = in_d + out_d
        # 1. 结构缺口: 低度=未开发→高信息
        if deg <= 1:      score *= 1.6
        elif deg <= 3:    score *= 1.3
        elif deg >= 15:   score *= 0.8  # 枢纽→信息冗余
        # 2. 域新颖度: 少访问的域→高信息
        recent_domains = set()
        for mem in self.walk_memory[-10:]:
            for step in mem:
                if len(step) >= 4: recent_domains.add(step[3])
        dst_domains = {e[2] for e in nd.get("effects", []) if len(e)>2}
        dst_domains |= {e[2] for e in nd.get("causes", []) if len(e)>2}
        if dst_domains and recent_domains:
            novel = dst_domains - recent_domains
            if novel: score *= 1.0 + 0.15 * len(novel)
        # 3. 最近访问: 走过的目的地→低信息
        recent_dests = set()
        for mem in self.walk_memory[-5:]:
            for step in mem:
                if len(step) >= 3: recent_dests.add(step[2])
        if dst in recent_dests: score *= 0.7
        # 🏠 重访奖励: walk_memory 中出现过的节点→熟悉=值得强化 (coincidence 积累)
        familiar_count = 0
        for mem in self.walk_memory:
            for step in mem:
                if len(step) >= 3 and step[2] == dst:
                    familiar_count += 1
        if familiar_count > 0:
            score *= 1.0 + min(0.5, familiar_count * 0.05)  # 熟悉节点→+5%~50% 概率提升
        # 4. 结构角色: 孤儿/死胡同→缺口引力
        if in_d == 0 and out_d > 0:  score *= 1.2
        elif out_d == 0 and in_d > 0: score *= 1.2
        return score

    def _step_forward(self) -> Dict:
        """沿一条出边走到目标节点。
        髓鞘加权选择 + 神经递质探索偏向 + 🧠 树突预处理。
        私有网络优先, 图边降级为 fallback。
        小概率: 跳到任意节点 (随机连接形成)。"""
        node = self.graph.get(self.node, {"causes": [], "effects": []})
        verified = [(n, d, dm) for n, d, dm in node["effects"] if dm not in ("emergence", "blocked")]

        # 🧠 突触补路: 总是补上高 s 突触边
        fallback = getattr(self, '_synapse_fallback', [])
        if fallback:
            existing_dsts = {d for _, d, _ in verified}
            for dst, s_val in fallback:
                if dst not in existing_dsts and dst != self.node:
                    verified.append((f"syn:{s_val:.1f}", dst, "synapse"))
                    existing_dsts.add(dst)

        # 🧠 私有网络优先: 轴突+树突目标并入候选集 (top priority)
        my_edges = set()
        if self.axon:
            a_tgt = self.axon[0]
            # 如果轴突目标在图中有边可达, 追加到候选集
            if a_tgt in {d for _, d, _ in verified}:
                my_edges.add(a_tgt)
            elif a_tgt in self.graph:
                # 轴突目标不在出边里但存在 → 虚拟边 (跨图跳跃)
                my_edges.add(a_tgt)
                verified.append((f"axon:{self.axon[1]:.1f}", a_tgt, "private"))
        # 树突中的节点, 如果从当前节点可达 → 追加
        if self.dendrites:
            reachable = self.dendrites & {d for _, d, _ in verified}
            for d in reachable:
                if d not in {dst for _, dst, _ in verified}:
                    verified.append(("dendrite", d, "private"))
                my_edges.add(d)

        # 🧠 树突预处理: 感知邻域结构, 调整偏好
        dendritic = self._dendritic_sense() if len(verified) >= 2 else {}

        # 随机连接形成: 15%概率跳到图中任意节点 (创意跳跃)
        if random.random() < 0.15:
            all_nodes = list(self.graph.keys())
            if all_nodes:
                new_node = random.choice(all_nodes)
                old = self.node
                self.node = new_node
                self.current_walk.append((old, "creative_leap", new_node))
                return {"type": "creative_leap", "from": old, "to": new_node}

        if not verified:
            return {"type": "step_forward", "result": "dead_end", "node": self.node}
        
        # 注意力: 如果有目标, 直接连向目标的边优先 (集体聚焦)
        if getattr(self, 'goal', None):
            goal_edges = [(n, d, dm) for n, d, dm in verified if d == self.goal]
            if goal_edges and random.random() < 0.6:
                law, dst, dom = random.choice(goal_edges)
                old = self.node
                self.node = dst
                self.current_walk.append((old, law, dst))
                self.memory.append((old, law, dst, dom, +1))
                if len(self.memory) > 200:
                    self.memory = self.memory[-200:]
                return {"type": "step_forward", "from": old, "to": dst, "via": law, "goal_hit": True}
            if len(verified) >= 2:
                goal_neighbors = self.graph.get(self.goal, {}).get("causes", []) + \
                                 self.graph.get(self.goal, {}).get("effects", [])
                goal_related = {e[0] for e in goal_neighbors} | {e[1] for e in goal_neighbors}
                toward = [(n, d, dm) for n, d, dm in verified if d in goal_related]
                if toward and random.random() < 0.3:
                    law, dst, dom = random.choice(toward)
                    old = self.node
                    self.node = dst
                    self.current_walk.append((old, law, dst))
                    self.memory.append((old, law, dst, dom, +1))
                    if len(self.memory) > 200:
                        self.memory = self.memory[-200:]
                    return {"type": "step_forward", "from": old, "to": dst, "via": law}

        # 🧩 内在好奇: 预测落差驱动探索 (替代外部调制)
        curiosity = self.intrinsic_curiosity
        if self.genome.get("curiosity", 1.0) != 1.0:
            curiosity *= self.genome["curiosity"]  # 基因组微调
        # 仍保留外部刺激接口但降低权重
        _stim = getattr(self, '_stimulus', 1.0)
        if _stim > 1.0:
            curiosity *= (1.0 + (_stim - 1.0) * 0.5)
            self._stimulus_until = max(getattr(self, '_stimulus_until', 0), self.age + 20)
        scored = []
        _myelin = getattr(self, '_myelin', set())
        # 🧠 私有权重加成: 每边有独立权重
        _w = self.weights
        for law, dst, dom in verified:
            # 🧠 髓鞘快车道: 高频边直接跃迁
            if (self.node, dst) in _myelin:
                scored.append((law, dst, dom, 999.0))
                continue
            eig = self._expected_info_gain(dst)
            if curiosity != 1.0:
                eig = eig ** curiosity
            if dom in WHITELIST_DOMAINS:
                eig *= 2.0
            # 🧠 独立权重加成: 每边走自己的历史权重
            wt = _w.get(dst, 0)
            eig *= 1.0 + wt  # 权重连续性加成
            # 🧠 人气加成: 被越多细胞走过的边越值得走
            pop = getattr(self, '_popularity', {}).get((self.node, dst), 0)
            eig *= 1.0 + pop * 2.0  # 0→1x, 1→3x
            # 🧠 髓鞘加成: 我自己频繁走的边→高速公路 (习惯化)
            mye = self.myelin.get((self.node, dst), 0)
            eig *= 1.0 + mye * 2.0  # 0→1x, 3.0→7x
            # 🧠 私有网络加成: 我的边 > 图边
            if dst in my_edges:
                eig *= 1.5
            # 🧠 树突调制: 邻域特征加成
            nb = dendritic.get(dst, {})
            # 🧠 树突熟悉度: 目标在自己的监听集里 → 偏好
            if self.dendrites and dst in self.dendrites:
                eig *= 1.8
            if nb.get("cross_domain"):
                eig *= 1.5
            if nb.get("frontier") and nb["frontier"] > 0:
                eig *= 1.0 + 0.15 * min(nb["frontier"], 3)
            if nb.get("emergent_nearby"):
                eig *= 1.3
            scored.append((law, dst, dom, eig))
        # ε-贪心探索: 概率 ε 均匀随机选边, 覆盖未探索区域
        # 从0.3衰减到0.15保底 (500代后不再降), 防止长跑后探索完全死亡
        epsilon = max(0.15, 0.3 / (1.0 + self.age / 500.0))
        if random.random() < epsilon:
            law, dst, dom = random.choice([(law, dst, dom) for law, dst, dom, _ in scored])
        # 🧠 随机突触新生: 1%概率跳到图中任意节点, 创建全新连接
        # 不同于ε-greedy(随机选已有边), 这是跨越式探索——连接原本无关联的概念
        elif random.random() < 0.01:
            all_nodes = list(self.graph.keys())
            if all_nodes:
                dst = random.choice(all_nodes)
                law = "random_jump"
                dom = "emergent"
            else:
                law, dst, dom = random.choice([(l, d, dm) for l, d, dm, _ in scored])
        else:
            total_eig = sum(s[3] for s in scored)
            if total_eig > 0:
                r2 = random.random() * total_eig
                cum = 0
                for law, dst, dom, eig in scored:
                    cum += eig
                    if r2 <= cum:
                        chosen = (law, dst, dom)
                        break
                else:
                    chosen = scored[-1][:3]
                law, dst, dom = chosen
            else:
                law, dst, dom = random.choice([(l, d, dm) for l, d, dm, _ in scored])
        
        old = self.node
        self.node = dst
        dw = +1  # 🧠 STDP: step_forward = 同向强化
        self.current_walk.append((old, law, dst))
        self.memory.append((old, law, dst, dom, dw))
        if len(self.memory) > 200:
            self.memory = self.memory[-200:]
        # 🧠 独立突触权重: 每走一次 STDP 强化
        self.weights[dst] = self.weights.get(dst, 0) + 0.3
        # 🧠 权重衰减: 每5步所有连接衰减5%
        self._weight_steps = getattr(self, '_weight_steps', 0) + 1
        if self._weight_steps % 5 == 0:
            for k in list(self.weights.keys()):
                self.weights[k] *= 0.95
                if self.weights[k] < 0.01:
                    del self.weights[k]
        # 🧠 私有树突: 每10代刷新入边监听集 (最多20条)
        if not self.dendrites or self.age % 10 == 0:
            nd = self.graph.get(dst, {"causes": []})
            causes = [s for s, _, _ in nd.get("causes", []) if s != self.node]
            if causes:
                self.dendrites = set(random.sample(causes, min(20, len(causes))))
        
        # 🧩 内在好奇: 预测学习 + 好奇心更新
        settle = self._learn_and_curate(old, dst, dom)
        return {"type": "step_forward", "from": old, "to": dst, "via": law,
                "settle": settle,
                "axon": self.axon[0] if self.axon else None,
                "axon_strength": self.axon[1] if self.axon else 0}
    

    def _intervene(self) -> Dict:
        """🧪 实验: 用公式库验证当前歩行的因果假说 (do-calculus 触觉)
        
        cell 走过一段路径 A→...→B, 选 intervene 时用公式库验证:
        - 物理定律支持 A→B → confirmed (effect=+1.0)
        - 物理定律禁止 A→B → refuted (effect=-1.0)
        - 有相关公式但因果方向不确定 → partial (effect=+0.3)
        
        这是"感官"不是"方法" — cell 自己决定何时 intervene, 结果走已有 reward 通道。
        """
        walk = list(self.current_walk) if self.current_walk else []
        if len(walk) < 2:
            if self.walk_memory:
                walk = max(self.walk_memory, key=len)
            else:
                self.current_walk = []
                return {"type": "intervene", "result": "no_walk", "node": self.node}
        if len(walk) < 2:
            self.current_walk = []
            return {"type": "intervene", "result": "no_walk", "node": self.node}

        start = walk[0][0]
        end = walk[-1][2] if len(walk[-1]) >= 3 else walk[-1][0]
        path_nodes = [start] + [w[2] for w in walk if len(w) >= 3]
        
        # 查询公式库: 有没有定律关联这两个概念?
        from physics.laws import library
        variable_names = [start, end]
        
        # 归一化: 去掉前缀, 拆成单词方便跟公式库匹配
        def _clean_words(s):
            for pfx in ('abs:', 'hyp:', 'emergent:', 'native:'):
                if s.startswith(pfx):
                    s = s[len(pfx):]
            # 拆下划线和冒号, 过滤空串和太短的
            return {w for w in s.lower().replace(' ', '_').replace(':', '_').split('_') if len(w) >= 2}
        
        start_words = _clean_words(start)
        end_words = _clean_words(end)
        all_words = start_words | end_words
        relevant = library.find_relevant(list(all_words))
        
        # 检查强制/禁止因果边 (也按单词匹配)
        forced = library.forced_edges(list(all_words))
        forbidden = library.forbidden_edges(list(all_words))
        
        def _match(f_src, f_dst, src_words, dst_words):
            """方向敏感匹配: 因果方向 f_src→f_dst 必须与 walk 方向 start→end 一致。

            f_src 只能在 start 侧, f_dst 只能在 end 侧; 反方向不匹配。
            依据: 因果方向唯一来源是 δS=0 变分 (定律库 causal_direction), 词共现≠因果。
            """
            return (f_src in src_words) and (f_dst in dst_words)
        
        confirmed = any(_match(f_src, f_dst, start_words, end_words) for f_src, f_dst in forced)
        refuted = any(_match(f_src, f_dst, start_words, end_words) for f_src, f_dst in forbidden)
        
        effect = 0.0
        if confirmed:
            effect = 1.0   # 物理定律直接支持此因果方向
        elif refuted:
            effect = -1.0  # 物理定律明确禁止此因果方向
        elif relevant:
            effect = 0.3   # 有相关公式, 但因果方向需进一步确认
        elif any(w in (i for l in library._laws for i in l.inputs + l.outputs) for w in all_words):
            effect = 0.1   # 至少一端是已知物理量, 值得关注
        
        self.current_walk = []
        
        return {
            "type": "intervene",
            "from": start, "to": end,
            "path": " → ".join(path_nodes[-5:]),
            "confirmed": confirmed,
            "refuted": refuted,
            "relevant_laws": [l.name for l in relevant[:5]],
            "effect": round(effect, 2),
            "node": self.node,
        }

    def _probe(self) -> Dict:
        """数值触觉: 探测当前walk路径的定量关系。
        神经元把问题提交给 colony, colony 调用 LLM 获取数值答案。
        这里只打包问题, 不负责调用 LLM。
        """
        walk = list(self.current_walk)
        if len(walk) < 2:
            if self.walk_memory:
                walk = max(self.walk_memory, key=len)
            else:
                self.current_walk = []
                return {"type": "probe", "result": "no_walk"}
        if len(walk) < 2:
            self.current_walk = []
            return {"type": "probe", "result": "no_walk"}
        start = walk[0][0]
        end = walk[-1][2] if len(walk[-1]) >= 3 else walk[-1][0]
        path_nodes = [start] + [w[2] for w in walk if len(w) >= 3]
        path_str = " → ".join(path_nodes[-6:])
        self.current_walk = []
        return {"type": "probe", "start": start, "end": end,
                "path": path_str, "walk": walk, "node": self.node}

    def _derive(self) -> Dict:
        """推导通道: 请求推导walk两端的物理机制。
        derive 要求完整推理链, 不是数值答案。
        """
        walk = list(self.current_walk)
        if len(walk) < 2:
            if self.walk_memory:
                walk = max(self.walk_memory, key=len)
            else:
                self.current_walk = []
                return {"type": "derive", "result": "no_walk"}
        if len(walk) < 3:
            self.current_walk = []
            return {"type": "derive", "result": "walk_too_short",
                    "start": self.node, "end": self.node}
        start = walk[0][0]
        end = walk[-1][2] if len(walk[-1]) >= 3 else walk[-1][0]
        path_nodes = [start] + [w[2] for w in walk if len(w) >= 3]
        path_str = " → ".join(path_nodes[-8:])
        self.current_walk = []
        return {"type": "derive", "start": start, "end": end,
                "path": path_str, "walk": walk, "node": self.node}

    def _step_backward(self) -> Dict:
        """沿一条入边回溯"""
        node = self.graph.get(self.node, {"causes": [], "effects": []})
        verified = [(s, n, dm) for s, n, dm in node["causes"] if dm != "emergence"]
        
        if not verified:
            return {"type": "step_backward", "result": "orphan", "node": self.node}
        
        src, law, dom = random.choice(verified)
        old = self.node
        self.node = src
        self.memory.append((src, law, old, dom, -1))  # 🧠 STDP: 反向 = 削弱
        if len(self.memory) > 200:
            self.memory = self.memory[-200:]
        
        return {"type": "step_backward", "from": old, "to": src, "via": law}
    
    def _mark(self) -> Dict:
        """在当前节点注册黑板信号。如果走过路径，把路径也注册。
        同节点神经元间通信: 看见一个邻居的记忆片段。
        自提问: 如果当前节点有结构问题 → 注册疑问。"""
        # 注册当前位置
        self.board.register_expectation(
            f"cell:{id(self)}@{self.node}",
            f"标记: 在 {self.node} (记忆{len(self.memory)}条)",
            importance=0.3,
            location=self.node,
        )
        
        # 自提问: 感知到结构缺陷 → 注册疑问
        env = self.perceive() if hasattr(self, 'perceive') else {}
        if not env:
            node_data = self.graph.get(self.node, {"causes": [], "effects": []})
            env = {
                "is_orphan": len(node_data["causes"]) == 0 and len(node_data["effects"]) > 0,
                "is_dead_end": len(node_data["effects"]) == 0 and len(node_data["causes"]) > 0,
                "conserved_no_sym": self.node in {"energy","momentum","charge","angular_momentum"}
                    and len(node_data["causes"]) > 0
                    and not any("symmetry" in c[0].lower() or "gauge" in c[0].lower() or "noether" in c[0].lower()
                               for c in node_data["causes"]),
            }
        
        if env.get("is_orphan"):
            self.board.register_expectation(
                f"question:why_{self.node}",
                f"❓ 为什么 {self.node} 没有来源？",
                importance=2.0,
                location=f"questions",
            )
        if env.get("is_dead_end"):
            self.board.register_expectation(
                f"question:where_{self.node}",
                f"❓ {self.node} 的去向是什么？",
                importance=2.0,
                location=f"questions",
            )
        if env.get("conserved_no_sym"):
            syms = {"energy":"time_translation","momentum":"space_translation",
                    "charge":"U1_gauge","angular_momentum":"rotation"}
            sym = syms.get(self.node, "?")
            self.board.register_expectation(
                f"question:sym_{self.node}",
                f"❓ 守恒量 {self.node} 为什么没有 {sym} 对称性？",
                importance=3.0,
                location=f"questions",
            )
        
        # 同节点通信: 随机看见一个邻居的记忆
        if hasattr(self, '_neighbors_cache'):
            peers = [c for c in self._neighbors_cache if c is not self]
            if peers and random.random() < 0.3:
                peer = random.choice(peers)
                if peer.memory:
                    mem_sample = random.choice(peer.memory)
                    if mem_sample not in self.memory:
                        self.memory.append(mem_sample)
                        if len(self.memory) > 200:
                            self.memory = self.memory[-200:]
        
        # 如果有完成的路径，也注册
        if len(self.current_walk) >= 2:
            path_str = "→".join(w[2] for w in self.current_walk[-4:])
            self.board.register_expectation(
                f"path:{self.current_walk[0][0]}->{self.current_walk[-1][2]}",
                f"路径: {self.current_walk[0][0]}→...→{path_str}",
                importance=0.8,
                location=self.current_walk[0][0],
            )
            # 注册 walk 形状指纹: 不同具体路径但相同形状 → 结构类比
            fp = walk_fingerprint(self.current_walk)
            if fp:
                self.board.register_expectation(
                    f"shape:{fp}",
                    f"形状: {fp}",
                    importance=0.6,
                    location=f"fp:{fp}",
                )
            if len(self.current_walk) >= 4 or self.node == self.current_walk[0][0]:
                self.current_walk = []
        
        return {"type": "mark", "node": self.node, "memory": len(self.memory),
                "axon": self.axon[0] if self.axon else None,
                "axon_strength": self.axon[1] if self.axon else 0,
                "dendrites": list(self.dendrites) if self.dendrites else []}
    
    def _echo(self) -> Dict:
        """回应黑板: 找到关于当前节点的已有信号并加强它们"""
        recent = self.board.expectations[-100:]
        relevant = [e for e in recent if e["location"] == self.node]
        
        if not relevant:
            return {"type": "echo", "result": "no_match", "node": self.node}
        
        # 加强最相关的信号
        top = max(relevant, key=lambda e: e["importance"])
        self.board.register_expectation(
            f"echo:{top['id']}",
            f"回应: {top['desc'][:60]}",
            importance=top["importance"] * 0.3,  # 回声比原信号弱
            location=self.node,
        )
        
        return {"type": "echo", "matched": top["id"][:30], "node": self.node}
    
    def _split(self) -> Dict:
        """分裂: 在邻居节点创建一个子细胞。
        
        两道闸门:
        1. 能量门槛: total_reward >= min_split_reward
        2. 局部密度: 同节点细胞越多，分裂概率越低
           — 资源竞争内生约束，不靠全局参数
        """
        if self.total_reward < self.min_split_reward:
            return {"type": "split", "result": "insufficient_energy", "node": self.node}
        # 🏠 局部密度约束: 同节点上细胞越多→越难分裂 (生态位竞争)
        local_peers = 1
        if hasattr(self, '_neighbors_cache'):
            local_peers = max(1, sum(1 for c in self._neighbors_cache if c.node == self.node))
        # 5个同节点细胞=基准, 超过则指数衰减成功率
        if local_peers > 5:
            density_success = (5.0 / local_peers) ** 0.5  # sqrt衰减, 不硬砍
            if random.random() > density_success:
                return {"type": "split", "result": "too_crowded", "node": self.node}
        node = self.graph.get(self.node, {"causes": [], "effects": []})
        neighbors = set()
        for _, dst, _ in node["effects"]:
            neighbors.add(dst)
        for src, _, _ in node["causes"]:
            neighbors.add(src)
        
        if not neighbors:
            return {"type": "split", "result": "no_neighbors", "node": self.node}
        
        target = random.choice(list(neighbors))
        
        # 5% 概率: 随机基因组 (多样性注入)
        if random.random() < 0.05:
            child_genome = {a: random.random() for a in ACTIONS}
            total = sum(child_genome.values())
            for a in child_genome:
                child_genome[a] = child_genome[a] / max(0.01, total)
            # 元参数也随机
            child_genome["curiosity"] = random.uniform(0.3, 3.0)
            child_genome["reinforce_rate"] = random.uniform(0.05, 0.30)
            child_genome["decay_rate"] = random.uniform(0.001, 0.02)
            child_genome["mutation_rate"] = random.uniform(0.02, 0.25)
            child_genome["niche"] = random.uniform(0.0, 1.0)
            inherited = False
        else:
            # 继承父代基因组 + 突变 (split 同样继承, 不再随机)
            mr = self.genome.get("mutation_rate", 0.10)
            child_genome = {}
            for a in ACTIONS:
                if a == 'split':
                    child_genome[a] = max(0.005, self.genome.get(a, 1.0/len(ACTIONS)) + random.uniform(-mr, mr))
                    child_genome[a] = min(child_genome[a], self.GENOME_MAX)
                else:
                    child_genome[a] = self.genome.get(a, 1.0 / len(ACTIONS)) + random.uniform(-mr, mr)
                    child_genome[a] = max(0.01, child_genome[a])
                    child_genome[a] = min(child_genome[a], self.GENOME_MAX)
            # 不归一化: 让权重自由演化, GENOME_MAX + decay 提供边界
            # 元参数继承 + 突变 (不参与归一化)
            child_genome["curiosity"] = self._mutate_meta("curiosity", 0.2, 3.0, mr)
            child_genome["reinforce_rate"] = self._mutate_meta("reinforce_rate", 0.05, 0.30, mr)
            child_genome["decay_rate"] = self._mutate_meta("decay_rate", 0.001, 0.02, mr)
            child_genome["mutation_rate"] = self._mutate_meta("mutation_rate", 0.02, 0.25, mr)
            child_genome["niche"] = self._mutate_meta("niche", 0.0, 1.0, mr)
            inherited = True
        
        child = EvolvableCell(target, self.graph, self.board, child_genome,
                              min_split_reward=self.min_split_reward)
        child.memory = []
        child.current_walk = []
        child.walk_memory = []   # 记忆不继承
        child._sensory_memory = []  # 感官记忆也不继承
        
        # 🏠 分裂消耗: 亲代付出能量代价 (抑制无限繁殖)
        SPLIT_COST = 3.0   # ↑1.5→3.0: 代谢税下高分裂代价
        self.total_reward = max(0, self.total_reward - SPLIT_COST)
        
        return {"type": "split", "child": child, "target": target,
                "inherited_genome": inherited}
    
    def _mutate_meta(self, key: str, lo: float, hi: float, mr: float) -> float:
        """突变元学习参数: 继承 + 小幅随机扰动"""
        val = self.genome.get(key, (lo + hi) / 2)
        val += random.uniform(-mr * 0.3, mr * 0.3)
        return max(lo, min(hi, val))
    
    def status(self) -> str:
        top = sorted(self.genome.items(), key=lambda x: -x[1])
        top_str = " ".join(f"{a[:4]}:{w:.2f}" for a, w in top[:3])
        return (f"Cell(age={self.age}, node={self.node[:15]}, "
                f"reward={self.total_reward:.1f}, mem={len(self.memory)}, "
                f"genome=[{top_str}])")


def genome_diversity(cells: List[EvolvableCell]) -> float:
    """计算群体基因组多样性 (平均成对差异)"""
    if len(cells) < 2:
        return 0.0
    
    diffs = []
    for i in range(min(len(cells), 20)):
        for j in range(i + 1, min(len(cells), 20)):
            diff = sum(abs(cells[i].genome.get(a, 0) - cells[j].genome.get(a, 0))
                      for a in ACTIONS)
            diffs.append(diff)
    
    return sum(diffs) / max(len(diffs), 1)
