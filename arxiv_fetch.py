#!/usr/bin/env python3
"""
arXiv 论文抓取脚本 — cron 定时运行

每 N 小时拉取 astro-ph/hep-th/hep-ph/gr-qc/quant-ph 最新论文
→ LLM 提取概念对 → 写入 arxiv_reading_list.jsonl

用法:
    python arxiv_fetch.py [--max 10] [--categories hep-th,gr-qc]
"""

import sys, os, json, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CATEGORIES = ["hep-th", "gr-qc", "quant-ph", "hep-ph", "astro-ph.CO"]
MAX_RESULTS = 5  # 每类 5 篇


def main():
    from session.arxiv_gate import ArxivReadingList, fetch_arxiv_batch
    from llm.bridge import LLMBridge

    max_results = MAX_RESULTS
    categories = CATEGORIES

    # 解析参数
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--max" and i + 1 < len(args):
            max_results = int(args[i + 1])
            i += 2
        elif args[i] == "--categories" and i + 1 < len(args):
            categories = [c.strip() for c in args[i + 1].split(",")]
            i += 2
        else:
            i += 1

    # LLM 客户端
    bridge = LLMBridge()
    if not bridge.is_available():
        print("[ARXIV-FETCH] LLM not available, skipping")
        return

    reading_list = ArxivReadingList()
    stats_before = reading_list.stats()

    added = fetch_arxiv_batch(
        categories=categories,
        max_results=max_results,
        llm_client=bridge.client,  # DeepSeekClient 有 .chat() 方法
        reading_list=reading_list,
    )

    stats_after = reading_list.stats()
    print(f"[ARXIV-FETCH] done: +{added} papers, "
          f"shelf: {stats_after['total_papers']} papers, "
          f"{stats_after['pending']} pending, {stats_after['promoted']} promoted")


if __name__ == "__main__":
    main()
