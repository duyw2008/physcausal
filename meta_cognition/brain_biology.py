"""
脑模拟层 — 髓鞘、胶质、睡眠、神经递质

补充诺特脑中缺失的大脑元件。
"""

from __future__ import annotations
from typing import Dict, Tuple
from collections import defaultdict
import random


class MyelinSheath:
    """髓鞘: 频繁遍历的边被包裹，后续遍历时优先选择。
    边走过次数越多 → weight越高 → 被选中概率越大。"""
    
    BASE_WEIGHT = 1.0
    MYELIN_PER_USE = 0.3     # 每次遍历增加的髓鞘厚度
    MAX_MYELIN = 10.0         # 最大髓鞘厚度
    DECAY_RATE = 0.01         # 每代微量衰减
    
    def __init__(self):
        self.weights: Dict[Tuple[str, str], float] = defaultdict(lambda: self.BASE_WEIGHT)
    
    def use(self, src: str, dst: str):
        """走过这条边 → 髓鞘加厚"""
        key = (src, dst)
        self.weights[key] = min(self.MAX_MYELIN,
                                self.weights[key] + self.MYELIN_PER_USE)
    
    def choose(self, src: str, candidates: list) -> tuple:
        """髓鞘加权选择: 权重高的边优先。candidates = [(law, dst, dom), ...]"""
        if not candidates:
            return None
        
        weights = [self.weights.get((src, dst), self.BASE_WEIGHT)
                   for _, dst, _ in candidates]
        total = sum(weights)
        r = random.random() * total
        cumulative = 0
        for i, (_, _, _) in enumerate(candidates):
            cumulative += weights[i]
            if r <= cumulative:
                return candidates[i]
        return candidates[-1]
    
    def decay(self, generation: int):
        """微量全局衰减"""
        if generation % 10 == 0:
            for key in list(self.weights.keys()):
                self.weights[key] = max(self.BASE_WEIGHT,
                                        self.weights[key] - self.DECAY_RATE)


class GlialCells:
    """胶质细胞: 定期清理没有突触支撑的弱连接。
    图中的边如果长期没有神经元走过 → 标记为弱边 → 可能被修剪。"""
    
    CHECK_INTERVAL = 100    # 每N代清理一次
    WEAK_THRESHOLD = 3      # 激活次数 < 此值 → 弱边
    
    def __init__(self):
        self.clean_count = 0
    
    def clean(self, graph: Dict, synapse) -> int:
        """清理死突触。返回清理数。"""
        self.clean_count += 1
        removed = 0
        
        # 统计突触层的激活
        active_edges = set(synapse.activations.keys())
        
        # 找图中存在但突触层没有激活的边
        for node_id, node in list(graph.items()):
            new_effects = []
            for edge_name, dst, domain in node["effects"]:
                key = (node_id, dst)
                # 突触激活次数
                acts = len(synapse.activations.get(key, []))
                if acts >= self.WEAK_THRESHOLD or domain == "emergence":
                    new_effects.append((edge_name, dst, domain))
                else:
                    removed += 1
            if len(new_effects) < len(node["effects"]):
                node["effects"] = new_effects
        
        return removed


class SleepCycle:
    """睡眠周期: 周期性暂停探索 → 回放强化 → 修剪弱突触。
    模拟 REM + 慢波睡眠。"""
    
    SLEEP_INTERVAL = 200     # 每N代睡一次
    SLEEP_DURATION = 10      # 睡眠持续代
    REPLAY_STRENGTH = 0.5    # 回放强化系数
    
    def __init__(self):
        self.total_sleeps = 0
        self.sleeping = False
        self.sleep_timer = 0
    
    def should_sleep(self, generation: int) -> bool:
        return generation % self.SLEEP_INTERVAL == 0
    
    def sleep_cycle(self, brain, generation: int) -> dict:
        """执行一次睡眠: 暂停正常活动 → 回放强突触 → 修剪弱突触"""
        self.sleeping = True
        stats = {"replayed": 0, "pruned": 0}
        
        # 回放: 遍历突触层中的强激活边
        for key, acts in brain.synapse.activations.items():
            if len(acts) < 5:
                continue
            src, dst = key
            # 强化: 给髓鞘加一层
            for _ in range(min(len(acts), 3)):
                brain.myelin.use(src, dst)
                stats["replayed"] += 1
        
        # 修剪: LTD 加速
        pruned = brain.synapse.decay(generation)
        stats["pruned"] = len(pruned)
        
        self.sleeping = False
        self.total_sleeps += 1
        return stats


class Neurotransmitters:
    """神经递质: 全局调控探索/利用平衡。
    多巴胺(高=利用) vs 去甲肾上腺素(高=探索)。
    根据路径发现率自动调节。"""
    
    DOPAMINE = 0.5          # 利用倾向 (0-1)
    NORADRENALINE = 0.5     # 探索倾向 (0-1)
    ADJUST_RATE = 0.05      # 调节速度
    
    def __init__(self):
        self._recent_discoveries = []
    
    def update(self, new_paths: int):
        """根据最近发现率调整神经递质"""
        self._recent_discoveries.append(new_paths)
        if len(self._recent_discoveries) > 10:
            self._recent_discoveries = self._recent_discoveries[-10:]
        
        avg = sum(self._recent_discoveries) / max(len(self._recent_discoveries), 1)
        
        if avg < 3:
            # 发现率低 → 多探索
            self.NORADRENALINE = min(1.0, self.NORADRENALINE + self.ADJUST_RATE)
            self.DOPAMINE = max(0.1, self.DOPAMINE - self.ADJUST_RATE)
        else:
            # 发现率高 → 多利用
            self.DOPAMINE = min(1.0, self.DOPAMINE + self.ADJUST_RATE)
            self.NORADRENALINE = max(0.1, self.NORADRENALINE - self.ADJUST_RATE)
    
    def explore_bias(self) -> float:
        """当前探索偏向 (0=纯利用, 1=纯探索)"""
        return self.NORADRENALINE / max(self.DOPAMINE + self.NORADRENALINE, 0.01)
