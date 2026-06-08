"""
价值系统 — 显著性排序 (模拟杏仁核/多巴胺功能)

给每个知识实体打显著性标签, 决定"什么值得关注"。

机制:
  - accessed: 每次被访问/引用 +0.05
  - verified: 在仿真中验证成功 +0.15
  - user_asked: 用户直接问过 +0.20
  - linked: 被结构联想连接 +0.05
  - prediction_error: 预测错误 -0.10
  - recency: 按时间衰减 (7天半衰期)

存储: ~/.hermes/physcausal_salience.json

所谓"情感驱动联想"——就是按 salience 排序而非语义距离排序。
"""

from __future__ import annotations
import json, os, time
from typing import Dict, List, Optional


class ValueSystem:
    """给实体打显著性标注的元认知层"""

    from data_paths import salience_path
    STORE_PATH = salience_path()

    def __init__(self):
        self._data: Dict[str, dict] = self._load()

    def _load(self) -> dict:
        try:
            with open(self.STORE_PATH) as f:
                data = json.load(f)
            # 迁移旧格式
            if isinstance(data, list):
                data = {}
            return data
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save(self):
        os.makedirs(os.path.dirname(self.STORE_PATH), exist_ok=True)
        with open(self.STORE_PATH, "w") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def _ensure_entity(self, entity_id: str, entity_type: str = "unknown"):
        """确保实体有记录"""
        if entity_id not in self._data:
            self._data[entity_id] = {
                "type": entity_type,
                "salience": 0.5,  # 中性初始值
                "accessed": 0,
                "verified": 0,
                "user_asked": 0,
                "linked": 0,
                "prediction_errors": 0,
                "first_seen": time.time(),
                "last_accessed": time.time(),
            }

    # ═══ 标注方法 ═══

    def access(self, entity_id: str, entity_type: str = "unknown"):
        """标记为被访问过"""
        self._ensure_entity(entity_id, entity_type)
        e = self._data[entity_id]
        e["accessed"] += 1
        e["last_accessed"] = time.time()
        e["salience"] = self._compute_salience(e)
        self._save()

    def verify(self, entity_id: str, entity_type: str = "law"):
        """标记为验证成功 (仿真/测试通过)"""
        self._ensure_entity(entity_id, entity_type)
        e = self._data[entity_id]
        e["verified"] += 1
        e["salience"] = self._compute_salience(e)
        self._save()

    def user_interest(self, entity_id: str, entity_type: str = "law"):
        """标记为用户直接提问过"""
        self._ensure_entity(entity_id, entity_type)
        e = self._data[entity_id]
        e["user_asked"] += 1
        e["salience"] = self._compute_salience(e)
        self._save()

    def link(self, entity_id: str, linked_to: str):
        """标记为被结构联想连接"""
        self._ensure_entity(entity_id, "module")
        self._ensure_entity(linked_to, "module")
        e = self._data[entity_id]
        e["linked"] += 1
        if "links" not in e:
            e["links"] = []
        if linked_to not in e["links"]:
            e["links"].append(linked_to)
        e["salience"] = self._compute_salience(e)
        self._save()

    def prediction_error(self, entity_id: str):
        """标记为预测错误"""
        self._ensure_entity(entity_id)
        e = self._data[entity_id]
        e["prediction_errors"] += 1
        e["salience"] = self._compute_salience(e)
        self._save()

    # ═══ 查询 ═══

    def salience(self, entity_id: str) -> float:
        """获取实体的当前显著性"""
        if entity_id not in self._data:
            return 0.5
        e = self._data[entity_id]
        return self._compute_salience(e)

    def top(self, entity_type: str = None, n: int = 5) -> List[tuple]:
        """返回显著性最高的 N 个实体"""
        candidates = []
        for eid, e in self._data.items():
            if entity_type and e.get("type") != entity_type:
                continue
            s = self._compute_salience(e)
            candidates.append((eid, s, e))
        candidates.sort(key=lambda x: -x[1])
        return candidates[:n]

    def rank(self, entities: List[str]) -> List[str]:
        """按显著性对实体列表排序"""
        scored = [(eid, self.salience(eid)) for eid in entities]
        scored.sort(key=lambda x: -x[1])
        return [eid for eid, _ in scored]

    # ═══ 内部 ═══

    def _compute_salience(self, entry: dict) -> float:
        """计算综合显著性"""
        base = 0.5
        accessed_bonus = min(entry.get("accessed", 0) * 0.05, 0.3)
        verified_bonus = min(entry.get("verified", 0) * 0.15, 0.6)
        asked_bonus = min(entry.get("user_asked", 0) * 0.20, 0.6)
        linked_bonus = min(entry.get("linked", 0) * 0.05, 0.2)
        error_penalty = min(entry.get("prediction_errors", 0) * 0.10, 0.3)

        # Recency: 7天半衰期
        last = entry.get("last_accessed", time.time())
        days_ago = (time.time() - last) / 86400
        recency = max(0, 0.15 - days_ago * 0.02)

        salience = (
            base + accessed_bonus + verified_bonus + asked_bonus
            + linked_bonus + recency - error_penalty
        )
        return round(max(0.05, min(0.99, salience)), 4)

    def summary(self) -> str:
        """人类可读的摘要"""
        lines = ["=== Value System (显著性排序) ==="]
        lines.append(f"跟踪实体: {len(self._data)}")
        lines.append("")

        by_type = {}
        for eid, e in self._data.items():
            t = e.get("type", "unknown")
            by_type.setdefault(t, []).append((eid, self._compute_salience(e)))

        for t, items in sorted(by_type.items()):
            items.sort(key=lambda x: -x[1])
            lines.append(f"  [{t}]")
            for eid, s in items[:5]:
                bar = "█" * int(s * 15) + "░" * (15 - int(s * 15))
                lines.append(f"    {bar} {s:.3f}  {eid}")
            lines.append("")

        return "\n".join(lines)


# 全局单例
values = ValueSystem()
