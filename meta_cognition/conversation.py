"""
对话记忆 — 跨对话上下文

Noether 记住聊过什么, 下次见面能接上。
"""

from __future__ import annotations
from typing import Dict, List, Optional
import json, os, time
from data_paths import data_path

_CONVO_FILE = data_path("conversation_memory.json")


def _load() -> List[Dict]:
    try:
        with open(_CONVO_FILE) as f:
            return json.load(f)
    except:
        return []


def _save(entries: List[Dict]):
    with open(_CONVO_FILE, "w") as f:
        json.dump(entries[-100:], f, ensure_ascii=False, indent=2)


def remember_conversation(topic: str, insight: str, tags: List[str] = None):
    """记住一次对话的要点"""
    entries = _load()
    entries.append({
        "time": time.time(),
        "date": time.strftime("%Y-%m-%d %H:%M"),
        "topic": topic,
        "insight": insight[:200],
        "tags": tags or [],
    })
    _save(entries)


def recall_context(n: int = 10) -> List[Dict]:
    """回忆最近的对话上下文"""
    return _load()[-n:]


def context_summary() -> str:
    """对话上下文摘要"""
    entries = _load()
    if not entries:
        return "  还没有对话记忆。"

    recent = entries[-5:]
    tags_count = {}
    for e in entries:
        for t in e.get("tags", []):
            tags_count[t] = tags_count.get(t, 0) + 1

    lines = [f"═══ 对话记忆 ({len(entries)} 条) ═══"]
    
    # 热门话题
    top_tags = sorted(tags_count.items(), key=lambda x: x[1], reverse=True)[:5]
    if top_tags:
        lines.append(f"  热门: {', '.join(f'{t}({c})' for t,c in top_tags)}")

    lines.append("")
    lines.append("  最近对话:")
    for e in reversed(recent):
        lines.append(f"  [{e['date']}] {e['topic'][:60]}")
        lines.append(f"    {e['insight'][:80]}")

    return "\n".join(lines)


def greet_with_context() -> str:
    """带上下文的问候"""
    entries = _load()
    if not entries:
        return "你好。我是 Noether (诺特)。今天我们第一次见面。"

    recent = entries[-3:]
    last = recent[-1]

    topics = [e["topic"] for e in recent]
    tags = set()
    for e in recent:
        for t in e.get("tags", []):
            tags.add(t)

    return (
        f"你好。上次我们聊了: {', '.join(topics[-2:])}。\n"
        f"当前关注: {', '.join(sorted(tags)[:5])}。\n"
        f"准备继续。"
    )
