"""
工作记忆 — 前额叶模拟

每个细胞持有一个 small active_buffer (3-5 概念)，
概念在 buffer 中持续放电维持，需多巴胺供能。
buffer 中的概念可被组合推理。

与电脑内存的区别:
  - buffer 不是"存储"，是"持续放电重新生成"
  - 不 rehears 就消散 (decay)
  - 容量是带宽瓶颈 (干扰随数量指数增长)
  - 内容寻址: 部分线索恢复完整表征

只在 EvolvableCell 上加轻薄 hook，不改架构。
"""

from __future__ import annotations
from typing import List, Optional, Set
import random


class WorkingMemory:
    """细胞级工作记忆 — PFC 的 recurrent firing 模拟"""

    # 容量上限
    MAX_BUFFER = 3
    # 每代维持成本 (多巴胺消耗)
    MAINTENANCE_COST = 0.02
    # 衰减概率 (无多巴胺时)
    DECAY_PROB = 0.15
    # 新概念进入概率
    ENCODE_PROB = 0.05

    def __init__(self):
        self.buffer: List[str] = []         # 当前活跃概念
        self._buffer_ages: List[int] = []   # 每个概念的代龄

    # ═══ 细胞接口 ═══

    def maintain(self, dopamine: float):
        """每代调用: 用多巴胺维持 buffer，衰减旧项"""
        if not self.buffer:
            return

        # 多巴胺充能: 延缓衰减
        if dopamine > 0.1:
            # 充足多巴胺 → 不减龄, 甚至刷新最老的
            return

        # 衰减: 每个概念代龄+1, 超过 5 代掉落
        new_buffer = []
        new_ages = []
        for concept, age in zip(self.buffer, self._buffer_ages):
            if random.random() > self.DECAY_PROB:
                new_age = age + 1
                if new_age < 5:  # 5代内不rehearse就掉
                    new_buffer.append(concept)
                    new_ages.append(new_age)
        self.buffer = new_buffer
        self._buffer_ages = new_ages

    def encode(self, concept: str, dopamine: float) -> bool:
        """尝试将概念编码进 buffer。返回是否成功。"""
        if not concept or concept in self.buffer:
            return False

        # 多巴胺越高越容易编码
        prob = self.ENCODE_PROB * (1.0 + dopamine)
        if random.random() > prob:
            return False

        # 容量管理: buffer 满时替换最老的
        if len(self.buffer) >= self.MAX_BUFFER:
            # 找最老的
            oldest_idx = self._buffer_ages.index(max(self._buffer_ages))
            self.buffer.pop(oldest_idx)
            self._buffer_ages.pop(oldest_idx)

        self.buffer.append(concept)
        self._buffer_ages.append(0)  # 新概念代龄 0
        return True

    def contains(self, concept: str) -> bool:
        """内容寻址: 概念是否在 buffer 中"""
        return concept in self.buffer

    def any_match(self, concepts: Set[str]) -> bool:
        """buffer 中是否有任何概念匹配"""
        return bool(set(self.buffer) & concepts)

    def is_full(self) -> bool:
        return len(self.buffer) >= self.MAX_BUFFER

    def size(self) -> int:
        return len(self.buffer)

    def peek(self) -> List[str]:
        return list(self.buffer)

    # ═══ 组合推理 ═══

    def get_pairs(self) -> List[tuple]:
        """返回 buffer 中所有概念对，用于组合推理"""
        pairs = []
        for i in range(len(self.buffer)):
            for j in range(i + 1, len(self.buffer)):
                pairs.append((self.buffer[i], self.buffer[j]))
        return pairs

    # ═══ 序列化 ═══

    def to_dict(self) -> dict:
        return {
            "buffer": list(self.buffer),
            "ages": list(self._buffer_ages),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorkingMemory":
        wm = cls()
        if data:
            wm.buffer = data.get("buffer", [])[:cls.MAX_BUFFER]
            wm._buffer_ages = data.get("ages", [])[:len(wm.buffer)]
        return wm
