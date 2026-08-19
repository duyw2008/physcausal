#!/usr/bin/env python3
"""
费曼脑论文摄入 (cron): 读新论文摘要 → 提取物理因果概念对 → 喂入 feed_queue.jsonl。

流程:
  1. 找 arxiv_reading_list.jsonl 中未喂过 (不在 .arxiv_fed_state.json) 的论文
  2. 逐篇通过 arXiv export API 读摘要
  3. 用 DeepSeek LLM 提取 3-10 条 src→dst 因果边 (变量→变量)
  4. 写 feed_queue.jsonl 为 "edge" 类型 feed, 并标记 fed 状态
"""
import json, os, re, sys, time, urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

DATA = os.path.join(ROOT, "data")
READING_LIST = os.path.join(DATA, "arxiv_reading_list.jsonl")
QUEUE = os.path.join(DATA, "feed_queue.jsonl")
FED_STATE = os.path.join(DATA, ".arxiv_fed_state.json")

NS = {"a": "http://www.w3.org/2005/Atom"}


def load_fed():
    if os.path.exists(FED_STATE):
        try:
            return set(json.load(open(FED_STATE)))
        except Exception:
            return set()
    return set()


def save_fed(s):
    with open(FED_STATE, "w") as f:
        json.dump(sorted(s), f)


def fetch_abstract(arxiv_id):
    url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            data = r.read().decode("utf-8")
        root = ET.fromstring(data)
        e = root.find("a:entry", NS)
        if e is None:
            return None
        summ = e.find("a:summary", NS)
        return summ.text.strip() if summ is not None else None
    except Exception as ex:
        print(f"    [abstract-err] {arxiv_id}: {ex}")
        return None


EXTRACT_PROMPT = """你是理论物理学家。从以下论文摘要中提取物理因果概念对 (变量→变量)。

每条边是一个 (src → dst) 物理因果/依赖关系, src 是原因变量, dst 是结果变量。
- 变量名用英文小写下划线 (如 dark_matter_density, spectral_index, entropy, black_hole_spin)
- 只提取摘要中明确或强隐含的物理关系 (包括众所周知的物理关系)
- confidence: 0.5-1.0 (1.0=论文已证明/陈述, 0.7=强支持, 0.5=假说)
- 提取 3 到 10 条边, 宁缺毋滥, 但要尽量覆盖摘要的核心物理机制
- 禁止 src == dst

以 JSON 数组返回, 不要 markdown 代码块:
[{{"src": "...", "dst": "...", "confidence": 0.9}}, ...]

论文标题: {title}
论文摘要:
{abstract}

JSON 数组:"""


def extract_edges(title, abstract, client):
    prompt = EXTRACT_PROMPT.format(title=title, abstract=abstract[:2000])
    try:
        resp = client.chat([{"role": "user", "content": prompt}],
                           temperature=0.1, max_tokens=2048)
        resp = re.sub(r'^```(?:json)?\s*\n?', '', resp.strip())
        resp = re.sub(r'\n?```\s*$', '', resp)
        m = re.search(r"\[.*\]", resp, re.DOTALL)
        if not m:
            return []
        data = json.loads(m.group())
        if not isinstance(data, list):
            return []
        edges = []
        for c in data:
            src = str(c.get("src", "")).strip().lower().replace(" ", "_")
            dst = str(c.get("dst", "")).strip().lower().replace(" ", "_")
            if not src or not dst or src == dst:
                continue
            try:
                conf = float(c.get("confidence", 0.6))
            except Exception:
                conf = 0.6
            conf = max(0.2, min(1.0, conf))
            edges.append({"src": src, "dst": dst, "confidence": round(conf, 2)})
        # 去重 (保序)
        seen, uniq = set(), []
        for e in edges:
            k = (e["src"], e["dst"])
            if k not in seen:
                seen.add(k)
                uniq.append(e)
        return uniq[:10]
    except Exception as ex:
        print(f"    [extract-err]: {ex}")
        return []


def append_edges(arxiv_id, title, edges):
    n = 0
    with open(QUEUE, "a") as f:
        for e in edges:
            item = {
                "source": "arxiv_feed",
                "type": "edge",
                "data": {
                    "src": e["src"],
                    "dst": e["dst"],
                    "law": f"arxiv:{arxiv_id}",
                    "domain": "physics_research",
                    "initial_s": round(e["confidence"] * 0.2, 3),
                },
                "ts": time.time(),
            }
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            n += 1
    return n


def main():
    from causal.llm_client import DeepSeekClient
    client = DeepSeekClient()
    if not client.api_key:
        print("[FEED] DeepSeek key missing, abort")
        return

    fed = load_fed()
    papers = []
    with open(READING_LIST) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                p = json.loads(line)
            except json.JSONDecodeError:
                continue
            if p.get("arxiv_id") not in fed:
                papers.append(p)

    # 只处理最近一批 (按 extracted_at 排序取最后 N 篇)
    papers.sort(key=lambda p: p.get("extracted_at", 0))
    if not papers:
        print("[FEED] No new papers.")
        return

    total_papers = 0
    total_edges = 0
    for p in papers:
        aid = p["arxiv_id"]
        title = p.get("title", aid)
        abstract = fetch_abstract(aid)
        if not abstract:
            print(f"[FEED] skip {aid} (no abstract)")
            continue
        edges = extract_edges(title, abstract, client)
        if not edges:
            print(f"[FEED] {aid} -> 0 edges (skip, not marked fed)")
            continue
        n = append_edges(aid, title, edges)
        fed.add(aid)
        save_fed(fed)
        total_papers += 1
        total_edges += n
        print(f"[FEED] {aid} '{title[:50]}' -> {n} edges")

    print(f"\n[FEED-DONE] {total_papers} papers -> {total_edges} causal edges into feed_queue.jsonl")


if __name__ == "__main__":
    main()
