#!/usr/bin/env python3
"""
费曼脑论文摄入 (cron 任务执行脚本)
- 读取 arxiv_reading_list.jsonl 中本轮新增的 31 篇论文 (索引 193+)
- 用 arXiv API 拉取全文摘要 (web_extract 不可用时的回退)
- 已有概念对 (arxiv_fetch.py 的 LLM 提取) 作为基础边
- 对概念对 < 3 的论文, 用 LLM 从摘要补充提取因果边
- 归一化 + 去重 (跨论文 + 全局) 后写入 feed_queue.jsonl (edge 类型)
"""
import json, os, sys, time, re, urllib.request
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from causal.llm_client import DeepSeekClient

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
READING = os.path.join(DATA, "arxiv_reading_list.jsonl")
FEEDQ = os.path.join(DATA, "feed_queue.jsonl")
NEW_START = 269  # 本轮新增论文起始索引 (fetch 前 269 条, +32 条)

SUPPLEMENT_PROMPT = """You are a theoretical physicist. Given the title and abstract of a paper, extract PHYSICAL CAUSAL RELATIONSHIPS between physical variables/concepts (variable -> variable).

For each relationship, return a JSON object with:
  - "src": cause variable (lowercase, underscores, e.g. dark_matter_density)
  - "dst": effect variable (lowercase, underscores)
  - "confidence": 0-1 (1=proven in paper, 0.5=hypothesized)

Extract 3 to 8 distinct, non-trivial relationships. Include well-known physical relations implied by the abstract (e.g. mass -> gravitational_field, strain -> energy_level_shift). Prefer physical-variable pairs over methodological/vague ones. If the abstract genuinely supports fewer than 3 relationships, return only what is supported.

Return ONLY a JSON array, no markdown fences.

Title: {title}
Abstract: {abstract}

JSON array:"""


def norm(name):
    if not name:
        return ""
    n = re.sub(r"\s+", "_", name.strip().lower())
    n = re.sub(r"[^a-z0-9_]", "", n)
    n = re.sub(r"_+", "_", n).strip("_")
    return n


def fetch_abstracts(ids):
    """用 arXiv API 拉取摘要 (batch id_list)。返回 {arxiv_id: abstract}"""
    bases = sorted({i.split("v")[0] for i in ids})
    out = {}
    for i in range(0, len(bases), 25):
        chunk = bases[i:i + 25]
        url = ("https://export.arxiv.org/api/query?id_list="
               + ",".join(chunk) + "&max_results=50")
        try:
            data = urllib.request.urlopen(url, timeout=60).read().decode("utf-8")
            ns = {"a": "http://www.w3.org/2005/Atom"}
            root = ET.fromstring(data)
            for entry in root.findall("a:entry", ns):
                aid = entry.find("a:id", ns).text.strip().split("/abs/")[-1]
                base = aid.split("v")[0] if "v" in aid else aid
                s = entry.find("a:summary", ns)
                out[base] = s.text.strip() if s is not None else ""
        except Exception as e:
            print(f"  [ABSTRACT-ERR] chunk {chunk[:3]}... : {e}")
        time.sleep(1.0)
    return out


def llm_supplement(client, title, abstract):
    """LLM 补充提取因果边。失败返回 []"""
    if not client or not abstract:
        return []
    prompt = SUPPLEMENT_PROMPT.format(title=title, abstract=abstract[:2500])
    try:
        resp = client.chat([{"role": "user", "content": prompt}],
                           temperature=0.1, max_tokens=1500)
        resp = resp.strip()
        resp = re.sub(r"^```(?:json)?\s*", "", resp)
        resp = re.sub(r"```\s*$", "", resp)
        m = re.search(r"\[.*\]", resp, re.DOTALL)
        if m:
            data = json.loads(m.group())
            if isinstance(data, list):
                return data
    except Exception as e:
        print(f"  [LLM-ERR] {e}")
    return []


def load_global_edges():
    """已有 feed_queue 中的全局 (src,dst) 集合 + 本轮已写"""
    seen = set()
    if os.path.exists(FEEDQ):
        with open(FEEDQ) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    it = json.loads(line)
                    d = it.get("data", {})
                    seen.add((d.get("src", ""), d.get("dst", "")))
                except Exception:
                    pass
    return seen


def main():
    if not os.path.exists(READING):
        print("[INGEST] no reading list"); return
    with open(READING) as f:
        papers = [json.loads(l) for l in f if l.strip()]

    new_papers = papers[NEW_START:]
    print(f"[INGEST] new papers this round: {len(new_papers)}")

    if not new_papers:
        print("[INGEST] nothing new"); return

    # 拉摘要
    abstracts = fetch_abstracts([p["arxiv_id"] for p in new_papers])
    print(f"[INGEST] abstracts fetched: {len(abstracts)}")

    # LLM client
    client = DeepSeekClient()
    llm_ok = bool(getattr(client, "api_key", ""))
    print(f"[INGEST] LLM available: {llm_ok}")

    global_seen = load_global_edges()
    os.makedirs(DATA, exist_ok=True)

    paper_count = 0
    total_edges = 0
    domain_map = {
        "quant": "quantum", "gr": "general_relativity", "cosmo": "cosmology",
        "astro": "astrophysics", "hep": "high_energy",
    }

    with open(FEEDQ, "a") as fq:
        for p in new_papers:
            aid = p["arxiv_id"]
            title = p.get("title", "")
            base = aid.split("v")[0]
            abstract = abstracts.get(base, "")
            domain = "arxiv_research"

            # 收集边: (src_norm, dst_norm, confidence)
            edges = {}
            for c in p.get("concepts", []):
                s, d = norm(c.get("src", "")), norm(c.get("dst", ""))
                if s and d and s != d:
                    edges[(s, d)] = c.get("confidence", 0.5)

            # 概念不足 → 用 LLM 从摘要补充
            if len(edges) < 3 and abstract and llm_ok:
                extra = llm_supplement(client, title, abstract)
                for c in extra:
                    s, d = norm(c.get("src", "")), norm(c.get("dst", ""))
                    if s and d and s != d:
                        edges.setdefault((s, d), c.get("confidence", 0.5))
                print(f"  [SUPP] {aid}: {len(edges)} edges after supplement")

            written = 0
            paper_seen = set()
            for (s, d), conf in edges.items():
                if (s, d) in paper_seen:
                    continue
                paper_seen.add((s, d))
                # 全局去重 (跨论文完全相同的边不重复喂)
                if (s, d) in global_seen:
                    continue
                initial_s = round(0.02 + float(conf) * 0.06, 3)
                item = {
                    "source": f"arxiv:{aid}",
                    "type": "edge",
                    "data": {
                        "src": s, "dst": d,
                        "law": f"arxiv:{aid}",
                        "domain": domain,
                        "initial_s": initial_s,
                    },
                    "ts": time.time(),
                }
                fq.write(json.dumps(item, ensure_ascii=False) + "\n")
                global_seen.add((s, d))
                written += 1

            if written > 0:
                paper_count += 1
                total_edges += written
                print(f"  {aid}: {written} edges | {title[:55]}")

    print(f"\n[INGEST] DONE: {paper_count} papers -> {total_edges} causal edges -> feed_queue.jsonl")


if __name__ == "__main__":
    main()
