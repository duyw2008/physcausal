"""
arXiv 论文抓取 + 细胞共识闸门

架构:
  1. arxiv_fetch.py (cron) → 搜新论文 → LLM 提取概念对 → 写入 reading_list
  2. 细胞 walk 时概率"瞥一眼" reading_list
  3. 同一概念对 ≥2 个不同细胞走过 → 晋升为弱边进入主图
  4. 进图后靠 STDP 自然筛选

闸门设计 (与 tier 4→3 精神一致):
  - reading_list = 书架 (tier 4 沙盒)
  - 细胞共识 ≥2 → 进入主图 (s=0.01, domain=arxiv_research)
  - STDP 自然筛选 → 走得多的涨, 没人走的消
"""

from __future__ import annotations
import json, os, time, random, re
from typing import Dict, List, Optional, Tuple, Set
from collections import defaultdict

# LLM 提取的论文结构标签 / 非物理概念黑名单 (防 Abstract 等误当成物理概念)
# 与 synaptic_layer._LLM_JUNK_WORDS 保持一致
_PAPER_JUNK = frozenset({
    'abstract', 'analyzing', 'analyze', 'mediators', 'introduction',
    'conclusion', 'references', 'robot_foot', '未在给定', 'todo',
    'undefined', 'example', 'placeholder', 'xxx', 'nan', 'none',
})


def _is_junk(name: str) -> bool:
    """token 级匹配 (按 :|_ 分割), 避免误杀 null_boundary/cross_section"""
    return any(t in _PAPER_JUNK for t in re.split(r'[:|_]+', str(name).lower()))


class ArxivReadingList:
    """arXiv 待阅书架 — 论文概念对暂存区, 等待细胞共识"""

    # 晋升阈值: 多少不同细胞"看过"才能进图
    PROMOTION_THRESHOLD = 2
    # 细胞瞥一眼的概率
    GLANCE_PROBABILITY = 0.02

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        self.data_dir = data_dir
        self.list_path = os.path.join(data_dir, "arxiv_reading_list.jsonl")
        self.promoted_path = os.path.join(data_dir, "arxiv_promoted.jsonl")
        self._entries: List[Dict] = []
        self._concept_index: Dict[Tuple[str, str], List[int]] = defaultdict(list)
        self._loaded = False

    # ═══ 写入 (cron 调用) ═══

    def add_paper(self, paper: Dict, concepts: List[Dict], colony=None):
        """添加一篇论文及其提取的概念对到书架。
        
        同时将概念作为弱节点注入 colony 的图，让细胞能 walk 到它们。
        """
        entry = {
            "arxiv_id": paper.get("arxiv_id", ""),
            "title": paper.get("title", ""),
            "published": paper.get("published", ""),
            "concepts": [
                {
                    "src": c.get("src", c.get("inputs", [""])[0] if c.get("inputs") else ""),
                    "dst": c.get("dst", c.get("outputs", [""])[0] if c.get("outputs") else ""),
                    "confidence": c.get("confidence", 0.5),
                }
                for c in concepts
            ],
            "extracted_at": time.time(),
            "glanced_by": [],
            "glance_count": 0,
            "promoted": False,
        }
        # 只保留有有效概念对的论文 (过滤论文结构标签 Abstract 等垃圾词)
        valid = [c for c in entry["concepts"] if c["src"] and c["dst"]
                 and not _is_junk(c["src"]) and not _is_junk(c["dst"])]
        if not valid:
            return
        entry["concepts"] = valid

        # 去重
        if self._is_duplicate(entry["arxiv_id"]):
            return

        # 注入概念节点到图 — 从已有活跃节点桥接，不死端
        if colony:
            # 找图中活跃概念作为桥接入口
            import random
            active_nodes = list(colony.graph._cache.keys())[:200]
            bridge_src = random.choice(active_nodes) if active_nodes else None
            
            for c in valid:
                for name in (c["src"], c["dst"]):
                    clean = name.lower().replace(" ", "_")
                    if clean not in colony.graph:
                        colony._ensure_node(clean)
                    # 从活跃节点建极弱边让细胞能 walk 过来
                    if bridge_src and clean != bridge_src:
                        colony.synapse.strengthen(
                            0, bridge_src, clean, 0.01, colony.generation
                        )

        self._append(entry)
        self._load(force=True)

    def _is_duplicate(self, arxiv_id: str) -> bool:
        """检查是否已存在"""
        if not os.path.exists(self.list_path):
            return False
        try:
            with open(self.list_path) as f:
                for line in f:
                    try:
                        e = json.loads(line)
                        if e.get("arxiv_id") == arxiv_id:
                            return True
                    except json.JSONDecodeError:
                        pass
        except Exception:
            pass
        return False

    def _append(self, entry: Dict):
        try:
            with open(self.list_path, "a") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

    # ═══ 细胞交互 (breathe 中调用) ═══

    def cell_glance(self, cell_node: str, cell_id: int, colony=None) -> Optional[Dict]:
        """细胞瞥一眼书架。概率 GLANCE_PROBABILITY。

        匹配时自动将概念节点注入图，让后续细胞能 walk 到。
        """
        if random.random() > self.GLANCE_PROBABILITY:
            return None

        self._load()
        if not self._entries:
            return None

        unread = [e for e in self._entries if not e.get("promoted")]
        if not unread:
            return None

        entry = random.choice(unread)
        idx = self._entries.index(entry)

        for c in entry["concepts"]:
            src = c["src"].lower().replace(" ", "_")
            dst = c["dst"].lower().replace(" ", "_")
            node_lower = cell_node.lower()

            # 宽松匹配: 任意单词级别的交集
            node_tokens = set(cell_node.lower().replace("_", " ").split())
            concept_tokens = set(src.replace("_", " ").split()) | set(dst.replace("_", " ").split())
            if node_tokens & concept_tokens:
                # 匹配 — 注入概念到图
                if colony:
                    for name in (src, dst):
                        if name not in colony.graph:
                            colony._ensure_node(name)
                        # 从当前细胞节点建弱边
                        if name != cell_node:
                            colony.synapse.strengthen(
                                0, cell_node, name, 0.02, colony.generation
                            )

                if cell_id not in entry["glanced_by"]:
                    entry["glanced_by"].append(cell_id)
                    entry["glance_count"] += 1
                    self._rewrite_entry(idx, entry)

                    return {
                        "arxiv_id": entry["arxiv_id"],
                        "concept": c,
                        "glance_count": entry["glance_count"],
                    }
        return None

    def check_promotions(self, colony) -> int:
        """检查是否有概念对达到晋升阈值, 喂入主图。

        返回晋升数量。
        """
        self._load()
        promoted_count = 0

        for idx, entry in enumerate(self._entries):
            if entry.get("promoted"):
                continue
            if entry.get("glance_count", 0) < self.PROMOTION_THRESHOLD:
                continue

            # 检查唯一细胞数 (不只是总次数)
            unique_cells = set(entry.get("glanced_by", []))
            if len(unique_cells) < self.PROMOTION_THRESHOLD:
                continue

            # 晋升: 每个概念对喂入图
            for c in entry["concepts"]:
                src = c["src"].lower().replace(" ", "_")
                dst = c["dst"].lower().replace(" ", "_")
                if src and dst and src != dst:
                    colony._ensure_node(src)
                    colony._ensure_node(dst)
                    law = f"arxiv:{entry['arxiv_id']}"
                    colony.graph.add_edge(src, dst, law, "arxiv_research")
                    key = (src, dst)
                    if key not in colony.synapse.activations:
                        colony.synapse.activations[key] = {
                            'n': set(), 'g': colony.generation,
                            's': 0.01, 'c': 0  # 极低初始 s
                        }
                    promoted_count += 1

            entry["promoted"] = True
            self._rewrite_entry(idx, entry)

            # 记录到 promoted 日志
            self._log_promoted(entry)

        if promoted_count:
            print(f"  [ARXIV-GATE] +{promoted_count} edges promoted "
                  f"({len(unique_cells)} cells consensus)")
        return promoted_count

    # ═══ 内部 ═══

    def _load(self, force: bool = False):
        if self._loaded and not force:
            return
        self._entries = []
        self._concept_index.clear()
        if not os.path.exists(self.list_path):
            self._loaded = True
            return
        try:
            with open(self.list_path) as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        self._entries.append(entry)
                        # 建索引
                        for c in entry.get("concepts", []):
                            key = (c.get("src", ""), c.get("dst", ""))
                            self._concept_index[key].append(len(self._entries) - 1)
                    except json.JSONDecodeError:
                        pass
        except Exception:
            pass
        self._loaded = True

    def _rewrite_entry(self, idx: int, entry: Dict):
        """重写单条 (全量重写文件 — 简单但低频, 可接受)"""
        self._entries[idx] = entry
        try:
            tmp = self.list_path + ".tmp"
            with open(tmp, "w") as f:
                for e in self._entries:
                    f.write(json.dumps(e, ensure_ascii=False) + "\n")
            os.replace(tmp, self.list_path)
        except Exception:
            pass

    def _log_promoted(self, entry: Dict):
        """记录已晋升的论文"""
        try:
            log_entry = {
                "arxiv_id": entry["arxiv_id"],
                "title": entry["title"],
                "promoted_at": time.time(),
                "glance_count": entry.get("glance_count", 0),
                "unique_cells": len(set(entry.get("glanced_by", []))),
            }
            with open(self.promoted_path, "a") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def stats(self) -> Dict:
        """书架统计"""
        self._load()
        total = len(self._entries)
        promoted = sum(1 for e in self._entries if e.get("promoted"))
        total_concepts = sum(len(e.get("concepts", [])) for e in self._entries)
        return {
            "total_papers": total,
            "promoted": promoted,
            "pending": total - promoted,
            "total_concepts": total_concepts,
        }


# ═══ Cron 抓取脚本 ═══

def fetch_arxiv_batch(categories: List[str] = None, max_results: int = 10,
                      llm_client=None, reading_list: ArxivReadingList = None,
                      colony=None):
    """抓取一批 arXiv 新论文 → 提取概念 → 写入书架 + 注入图节点。"""
    from session.paper_ingest import search_arxiv, extract_causal_claims

    if categories is None:
        categories = ["hep-th", "gr-qc", "quant-ph", "hep-ph", "astro-ph.CO"]

    if reading_list is None:
        reading_list = ArxivReadingList()

    added = 0
    for cat in categories:
        query = f"cat:{cat}"
        try:
            papers = search_arxiv(query, max_results=max_results,
                                  sort_by="submittedDate")
        except Exception as e:
            print(f"  [ARXIV-FETCH] {cat} error: {e}")
            continue

        for paper in papers:
            if "error" in paper:
                continue
            try:
                concepts = extract_causal_claims(paper, llm_client)
                if concepts:
                    reading_list.add_paper(paper, concepts, colony=colony)
                    added += 1
            except Exception as e:
                print(f"  [ARXIV-EXTRACT] {paper.get('arxiv_id','?')} error: {e}")

    if added:
        print(f"  [ARXIV-FETCH] +{added} papers → reading list ({len(categories)} categories)")
    return added
