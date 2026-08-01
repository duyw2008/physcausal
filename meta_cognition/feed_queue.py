"""
运行时增量喂料管道 — 统一的外部输入队列

所有外部输入 (arXiv, 用户 /inject, sympy derive, self-discovery) 
统一通过 feed_queue.jsonl 流入脑。脑在 breathe 每代消费队列。

设计:
  - append-only JSONL — 多写者安全, 无需锁
  - 每行一个 feed item: {source, type, data, ts}
  - 消费后移入 processed/ 归档 (不删除, 可审计)

容量, 不给方法:
  - 管道只管"把食物放进来"
  - 不标注优先级、不预设重要性
  - 细胞自己发现新节点/边
"""

from __future__ import annotations
import json, os, time, shutil
from typing import Dict, List, Optional


class FeedQueue:
    """统一喂料队列 — 追加消费"""

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        self.data_dir = data_dir
        self.queue_path = os.path.join(data_dir, "feed_queue.jsonl")
        self._processed_dir = os.path.join(data_dir, "feed_processed")
        self._cursor = 0  # 已消费行数

    # ═══ 写入 ═══

    def feed_concept(self, name: str, source: str = "manual",
                     domain: str = "unknown") -> None:
        """喂一个新概念节点"""
        self._append({
            "source": source,
            "type": "concept",
            "data": {"name": name, "domain": domain},
        })

    def feed_edge(self, src: str, dst: str, law: str = "feed",
                  source: str = "manual", domain: str = "research",
                  initial_s: float = 0.05) -> None:
        """喂一条新边"""
        self._append({
            "source": source,
            "type": "edge",
            "data": {"src": src, "dst": dst, "law": law,
                     "domain": domain, "initial_s": initial_s},
        })

    def feed_stimulus(self, text: str, source: str = "manual",
                      boost: float = 2.0, duration: int = 10) -> None:
        """喂一条文本刺激"""
        self._append({
            "source": source,
            "type": "stimulus",
            "data": {"text": text, "boost": boost, "duration": duration},
        })

    def feed_chaos(self, count: int = 3, source: str = "manual") -> None:
        """喂混沌边"""
        self._append({
            "source": source,
            "type": "chaos",
            "data": {"count": count},
        })

    def _append(self, item: dict):
        item["ts"] = time.time()
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            with open(self.queue_path, "a") as f:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"  [FEED-QUEUE-ERR] write failed: {e}")

    # ═══ 消费 ═══

    def pending_count(self) -> int:
        """待消费条目数"""
        if not os.path.exists(self.queue_path):
            return 0
        try:
            with open(self.queue_path) as f:
                return sum(1 for _ in f) - self._cursor
        except Exception:
            return 0

    def consume_all(self, colony) -> Dict:
        """消费所有待处理条目，注入脑。

        返回: {concepts: int, edges: int, stimuli: int, chaos: int}
        """
        stats = {"concepts": 0, "edges": 0, "stimuli": 0, "chaos": 0}

        if not os.path.exists(self.queue_path):
            return stats

        try:
            with open(self.queue_path) as f:
                lines = f.readlines()
        except Exception:
            return stats

        new_items = lines[self._cursor:]
        if not new_items:
            return stats

        for line in new_items:
            line = line.strip()
            if not line:
                self._cursor += 1  # 跳过空行
                continue
            try:
                item = json.loads(line)
                self._consume_one(colony, item, stats)
            except json.JSONDecodeError:
                pass  # 损坏行跳过
            except Exception as e:
                print(f"  [FEED-CONSUME-ERR] {e}")
            self._cursor += 1

        # 归档已消费的 (如果全消费完了就截断)
        if self._cursor >= len(lines):
            self._archive()

        if any(v > 0 for v in stats.values()):
            print(f"  [FEED] consumed: +{stats['concepts']} concepts "
                  f"+{stats['edges']} edges +{stats['stimuli']} stimuli "
                  f"+{stats['chaos']} chaos")
        return stats

    def _consume_one(self, colony, item: dict, stats: dict):
        """消费单个 feed item"""
        item_type = item.get("type", "")
        data = item.get("data", {})
        source = item.get("source", "unknown")

        if item_type == "concept":
            name = data.get("name", "")
            if name:
                colony._ensure_node(name)
                # 撒 3-5 个种子细胞
                from meta_cognition.evolvable_cell import EvolvableCell
                n_seed = min(5, max(3, int(colony._carrying_capacity * 0.0005)))
                for _ in range(n_seed):
                    cell = EvolvableCell(name, colony.graph, colony.board)
                    colony.cells.append(cell)
                stats["concepts"] += 1

        elif item_type == "edge":
            src, dst = data.get("src", ""), data.get("dst", "")
            if src and dst:
                law = data.get("law", f"feed:{source}")
                domain = data.get("domain", "research")
                initial_s = data.get("initial_s", 0.05)
                colony._ensure_node(src)
                colony._ensure_node(dst)
                exists = any(
                    e[1] == dst for e in colony.graph[src].get("effects", [])
                    if isinstance(e, (list, tuple)) and len(e) >= 2
                )
                if not exists:
                    colony.graph.add_edge(src, dst, law, domain)
                    key = (src, dst)
                    if key not in colony.synapse.activations:
                        colony.synapse.activations[key] = {
                            'n': set(), 'g': colony.generation,
                            's': initial_s, 'c': 0
                        }
                stats["edges"] += 1

        elif item_type == "stimulus":
            text = data.get("text", "")
            boost = data.get("boost", 2.0)
            duration = data.get("duration", 10)
            if text:
                colony.stimulate(text, boost=boost, duration=duration)
                stats["stimuli"] += 1

        elif item_type == "chaos":
            count = data.get("count", 3)
            try:
                colony._seed_chaos(count)
            except Exception:
                pass
            stats["chaos"] += 1

    def _archive(self):
        """归档已消费队列"""
        if not os.path.exists(self.queue_path):
            return
        try:
            os.makedirs(self._processed_dir, exist_ok=True)
            ts = time.strftime("%Y%m%d_%H%M%S")
            archive_name = f"feed_{ts}.jsonl"
            shutil.move(self.queue_path,
                        os.path.join(self._processed_dir, archive_name))
        except Exception:
            pass
        self._cursor = 0

    # ═══ 兼容旧接口 ═══

    def flush_stimulus_file(self) -> Optional[str]:
        """检查 stimulus.txt，迁移到队列"""
        stim_path = os.path.join(self.data_dir, "stimulus.txt")
        if not os.path.exists(stim_path):
            return None
        try:
            with open(stim_path) as f:
                text = f.read().strip()
            os.remove(stim_path)
            if text:
                self.feed_stimulus(text, source="stimulus_file")
                return text
        except Exception:
            pass
        return None


# ═══ 便捷函数 ═══

def feed_from_injected_edges(data_dir: str = None):
    """一次性: 把旧的 injected_edges.json 迁移到队列"""
    if data_dir is None:
        data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    old_path = os.path.join(data_dir, "injected_edges.json")
    if not os.path.exists(old_path):
        return 0
    try:
        with open(old_path) as f:
            edges = json.load(f)
        q = FeedQueue(data_dir)
        count = 0
        for src, law, dst, domain in edges:
            q.feed_edge(src, dst, law=law, source="migrated_inject",
                        domain=domain)
            count += 1
        # 备份旧文件
        backup = old_path + ".bak"
        shutil.move(old_path, backup)
        return count
    except Exception:
        return 0
