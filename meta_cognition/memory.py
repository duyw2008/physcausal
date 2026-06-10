"""
持久记忆 — 发现归档 + 跨 session 检索

让 Noether 记住过去的发现, 在新 session 中回忆。
"""

from __future__ import annotations
from typing import Dict, List, Optional
import json, os, time
from data_paths import data_path


_MEMORY_FILE = data_path("memory.json")


def _load() -> List[Dict]:
    try:
        with open(_MEMORY_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save(entries: List[Dict]):
    os.makedirs(os.path.dirname(_MEMORY_FILE), exist_ok=True)
    with open(_MEMORY_FILE, "w") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def remember(category: str, content: str, tags: List[str] = None):
    """存储一条记忆"""
    entries = _load()
    entries.append({
        "time": time.time(),
        "date": time.strftime("%Y-%m-%d %H:%M"),
        "category": category,
        "content": content,
        "tags": tags or [],
    })
    _save(entries)


def recall(query: str = "", n: int = 10, category: str = "") -> List[Dict]:
    """检索记忆 (关键词匹配)"""
    entries = _load()
    if not query and not category:
        return entries[-n:]

    results = []
    for e in entries:
        if category and e.get("category") != category:
            continue
        if query:
            text = e.get("content", "") + " " + " ".join(e.get("tags", []))
            if query.lower() in text.lower():
                results.append(e)
        else:
            results.append(e)

    return results[-n:]


def memory_report(n: int = 10) -> str:
    """记忆报告"""
    all_entries = _load()
    by_cat = {}
    for e in all_entries:
        cat = e.get("category", "other")
        by_cat[cat] = by_cat.get(cat, 0) + 1

    lines = [f"═══ Noether 记忆 ({len(all_entries)} 条) ═══"]
    for cat, count in sorted(by_cat.items()):
        lines.append(f"  {cat}: {count}")

    recent = all_entries[-n:]
    if recent:
        lines.append("")
        lines.append(f"  最近 {len(recent)} 条:")
        for e in reversed(recent):
            lines.append(f"  [{e['date']}] [{e['category']}] {e['content'][:80]}")

    return "\n".join(lines)


def consolidate_memory():
    """整理记忆 — 在 rest() 时调用, 清理旧记录"""
    entries = _load()
    cutoff = time.time() - 30 * 24 * 3600  # 30 天
    entries = [e for e in entries if e.get("time", 0) > cutoff]
    _save(entries)
