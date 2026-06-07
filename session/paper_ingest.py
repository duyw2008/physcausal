"""
论文摄入 — 从 arXiv 论文中提取因果知识

流程:
  1. 搜索 arXiv
  2. 读摘要
  3. LLM 提取因果断言 (变量→变量, 领域)
  4. forbidden 验证 + 去重
  5. 注册为 tier 3 (严肃假说)

消耗: 每篇论文 1-2 次 API 调用
"""

from __future__ import annotations
import json, re, subprocess, sys
from typing import Dict, List, Optional, Tuple


def search_arxiv(query: str, max_results: int = 5,
                 sort_by: str = "relevance") -> List[Dict]:
    """搜索 arXiv 并返回论文列表"""
    import urllib.request
    import xml.etree.ElementTree as ET

    url = (
        f"https://export.arxiv.org/api/query?"
        f"search_query=all:{urllib.request.quote(query)}"
        f"&max_results={max_results}"
        f"&sortBy={sort_by}"
        f"&sortOrder=descending"
    )

    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = resp.read().decode("utf-8")
    except Exception as e:
        return [{"error": str(e)}]

    ns = {"a": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(data)
    papers = []

    for entry in root.findall("a:entry", ns):
        title_el = entry.find("a:title", ns)
        title = title_el.text.strip().replace("\n", " ") if title_el is not None else ""
        arxiv_id = entry.find("a:id", ns).text.strip().split("/abs/")[-1]
        summary_el = entry.find("a:summary", ns)
        abstract = summary_el.text.strip()[:500] if summary_el is not None else ""
        authors_el = entry.findall("a:author", ns)
        authors = [a.find("a:name", ns).text for a in authors_el if a.find("a:name", ns) is not None]
        published = entry.find("a:published", ns).text[:10]

        papers.append({
            "arxiv_id": arxiv_id,
            "title": title,
            "authors": authors,
            "abstract": abstract,
            "published": published,
        })

    return papers


def _get_pdf_text(arxiv_id: str) -> Optional[str]:
    """通过 web_extract 读取 PDF 文本"""
    try:
        import urllib.request
        url = f"https://arxiv.org/pdf/{arxiv_id}"
        with urllib.request.urlopen(url, timeout=60) as resp:
            data = resp.read()
        # 简单提取文本 (PDF 原生文本, 不解析)
        text = data.decode("latin-1", errors="ignore")
        # 只取前 5000 字符 (摘要+引言通常在前几页)
        return text[:5000]
    except Exception:
        return None


def _get_abstract(arxiv_id: str) -> Optional[str]:
    """通过 arXiv API 获取摘要"""
    import urllib.request
    import xml.etree.ElementTree as ET

    url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = resp.read().decode("utf-8")
        ns = {"a": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(data)
        entry = root.find("a:entry", ns)
        if entry is not None:
            summary = entry.find("a:summary", ns)
            if summary is not None:
                return summary.text.strip()
    except Exception:
        pass
    return None


EXTRACTION_PROMPT = """你是一个物理学家。从以下论文摘要中提取物理因果断言。

对于每条断言，返回:
  - name: 定律或关系的简短名称 (英文)
  - domain: 领域 (quantum, general_relativity, unification, mechanics, thermodynamics, electromagnetism, optics, acoustics, fluids)
  - inputs: 原因变量列表 (英文, 小写, 用下划线)
  - outputs: 结果变量列表 (英文, 小写, 用下划线)
  - causal_direction: [[原因, 结果]] 的列表
  - confidence: 0-1 (1=论文声称已证明, 0.5=论文提出假说)

只提取论文中明确提出的物理关系。不要编造。
如果没有发现新的因果关系，返回空数组。

论文标题: {title}
论文摘要:
{abstract}

以 JSON 数组格式返回:
[{{"name": "...", "domain": "...", "inputs": [...], "outputs": [...], "causal_direction": [[..., ...]], "confidence": 0.X}}]
"""


def extract_causal_claims(paper: Dict, llm_client) -> List[Dict]:
    """用 LLM 从论文摘要中提取因果断言"""
    if not llm_client:
        return []

    prompt = EXTRACTION_PROMPT.format(
        title=paper.get("title", ""),
        abstract=paper.get("abstract", "")[:2000],
    )

    try:
        response = llm_client.chat([{"role": "user", "content": prompt}])
        # 提取 JSON 数组
        json_match = re.search(r"\[.*\]", response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            if isinstance(data, list):
                return data
    except Exception:
        pass

    return []


def ingest_paper(arxiv_id: str, llm_client) -> Dict:
    """
    摄入单篇论文: 读摘要 → 提取因果 → 入库

    Returns:
        {"paper_id": ..., "extracted": N, "registered": [names]}
    """
    from physics.laws import library, PhysicsLaw, ConstraintType
    from session.auto_learn import _save_auto_laws

    paper = {"arxiv_id": arxiv_id, "title": arxiv_id, "abstract": ""}
    abstract = _get_abstract(arxiv_id)
    if abstract:
        paper["abstract"] = abstract

    claims = extract_causal_claims(paper, llm_client)
    if not claims:
        return {"paper_id": arxiv_id, "extracted": 0, "registered": []}

    registered = []
    for c in claims:
        name = c.get("name", "")
        if not name or len(name) < 3:
            continue

        inputs = c.get("inputs", [])
        outputs = c.get("outputs", [])
        causal_dir = c.get("causal_direction", [])
        domain = c.get("domain", "unknown")

        if not inputs or not outputs:
            continue

        # 去重
        existing_vars = set(v.lower() for v in inputs + outputs)
        duplicate = False
        for law in library.list_all():
            law_vars = set(v.lower() for v in law.inputs + law.outputs)
            var_overlap = len(existing_vars & law_vars) / max(len(existing_vars | law_vars), 1)
            if var_overlap > 0.8:
                duplicate = True
                break
        if duplicate:
            continue

        # forbidden 验证
        conflict = False
        for src, dst in causal_dir:
            for law in library.list_all():
                for fd_src, fd_dst in law.forbidden_directions:
                    if fd_src.lower() in src.lower() and fd_dst.lower() in dst.lower():
                        conflict = True
                        break
                if conflict:
                    break
            if conflict:
                break
        if conflict:
            continue

        # 防重名
        final_name = name
        existing_names = {law.name for law in library.list_all()}
        suffix = 2
        while final_name in existing_names:
            final_name = f"{name}_{suffix}"
            suffix += 1

        try:
            law = PhysicsLaw(
                name=final_name,
                domain=domain,
                latex="",
                inputs=inputs,
                outputs=outputs,
                constraint_type=ConstraintType.SCM_EQUATION,
                formula=lambda *args: 0.0,
                causal_direction=[tuple(d) for d in causal_dir],
                forbidden_directions=[],
            )
            law._auto_learned = True
            law._paper_sourced = True
            law._paper_id = arxiv_id
            law._paper_title = paper.get("title", "")
            law.confidence_tier = 3  # 来自论文 = 严肃假说
            library.register(law)
            registered.append(final_name)
        except Exception:
            pass

    if registered:
        _save_auto_laws()

    return {
        "paper_id": arxiv_id,
        "extracted": len(claims),
        "registered": registered,
    }


def ingest_from_query(query: str, llm_client, max_papers: int = 3) -> Dict:
    """
    批量摄入: 搜索 arXiv → 逐个提取 → 入库

    Returns:
        {papers_found, papers_processed, total_extracted, total_registered, papers: [...]}
    """
    papers = search_arxiv(query, max_results=max_papers)
    if not papers or "error" in papers[0]:
        return {"papers_found": 0, "error": papers[0].get("error", "unknown")}

    results = []
    total_extracted = 0
    total_registered = []

    for paper in papers:
        r = ingest_paper(paper["arxiv_id"], llm_client)
        r["title"] = paper.get("title", "")
        results.append(r)
        total_extracted += r["extracted"]
        total_registered.extend(r["registered"])

    return {
        "papers_found": len(papers),
        "papers_processed": len(results),
        "total_extracted": total_extracted,
        "total_registered": total_registered,
        "papers": results,
    }
