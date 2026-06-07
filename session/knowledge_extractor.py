"""
会话知识提取 — LLM 驱动的因果断言提取

核心: 每轮对话后, 用 LLM 提取回答中的因果断言,
      物理验证后自动加入模块库, 实现"越聊越胖"。

两层:
  1. LLM 提取 (主) — 一次 LLM 调用, 捕获所有断言
  2. 正则 fallback — LLM 不可用时的降级方案
"""

from __future__ import annotations
import json as _json
import re
from typing import Dict, List

from creative.module_library import ModuleLibrary, CausalModule


def extract_via_llm(answer: str, client) -> List[Dict]:
    """
    用 LLM 从回答中提取因果断言。

    Returns:
        [{source, target, direction, confidence}, ...]
    """
    if not client:
        return []

    prompt = (
        "从以下物理推导文本中提取所有明确的因果断言。\n\n"
        f"文本:\n{answer[:3000]}\n\n"
        "以 JSON 数组格式返回, 每个断言包含:\n"
        '{"source": "原因变量", "target": "结果变量", '
        '"direction": "forward" 或 "forbidden", '
        '"confidence": 0.0-1.0}\n\n'
        "只返回 JSON 数组, 不要其他文字。最多 10 条。"
    )
    try:
        response = client.chat([{"role": "user", "content": prompt}])
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if json_match:
            assertions = _json.loads(json_match.group())
            result = []
            for a in assertions:
                if a.get("source") and a.get("target"):
                    result.append({
                        "source": str(a["source"]).strip(),
                        "target": str(a["target"]).strip(),
                        "direction": a.get("direction", "forward"),
                        "confidence": float(a.get("confidence", 0.7)),
                    })
            return result
    except Exception:
        pass
    return []


# 中文因果断言模式 (LLM 不可用时的 fallback)
CAUSAL_PATTERNS = [
    (r'(\S+?)\s*→\s*(\S+)', 'arrow'),
    (r'(\S+?)\s*导致\s*(\S+)', 'lead_to'),
    (r'(\S+?)\s*是\s*(\S+?)\s*的(?:原因|因)', 'is_cause_of'),
    (r'(\S+?)\s*决定\s*(\S+)', 'determines'),
    (r'(\S+?)\s*影响\s*(\S+)', 'affects'),
    (r'(\S+?)\s*引起\s*(\S+)', 'causes'),
    (r'禁止[：:]\s*(\S+?)\s*→\s*(\S+)', 'forbidden'),
    (r'(\w+)\s*->\s*(\w+)', 'english_arrow'),
]


def extract_causal_assertions(text: str) -> List[Dict]:
    """从文本中提取因果断言 (正则 fallback)"""
    assertions = []
    for pattern, ptype in CAUSAL_PATTERNS:
        for match in re.finditer(pattern, text):
            src = match.group(1).strip()
            dst = match.group(2).strip()
            if len(src) < 1 or len(dst) < 1:
                continue
            if src in ('→', '->', '-') or dst in ('→', '->', '-'):
                continue
            if src.isdigit() or dst.isdigit():
                continue
            if any(c in src for c in '，。！？；：、') or any(c in dst for c in '，。！？；：、'):
                continue
            direction = "forward" if ptype != "forbidden" else "forbidden"
            assertions.append({
                "source": src, "target": dst,
                "direction": direction, "pattern": ptype,
            })

    seen = set()
    unique = []
    for a in assertions:
        key = (a["source"], a["target"], a["direction"])
        if key not in seen:
            seen.add(key)
            unique.append(a)
    return unique


def validate_and_add(assertions: List[Dict], domain: str = "extracted") -> Dict:
    """
    物理验证断言并加入模块库。
    """
    from physics.laws import library

    lib = ModuleLibrary()
    added, rejected, pending = [], [], []

    for a in assertions:
        src, dst = a["source"], a["target"]
        edge = (src, dst)

        validated, rejected_flag, matched_law = False, False, None
        for law in library.list_all():
            for fd in law.forbidden_directions:
                if (fd[0] in src and fd[1] in dst) or (fd[0] == src.lower() and fd[1] == dst.lower()):
                    rejected_flag = True; matched_law = law.name; break
            if rejected_flag:
                break
            for cd in law.causal_direction:
                if (cd[0] in src and cd[1] in dst) or (cd[0] == src.lower() and cd[1] == dst.lower()):
                    validated = True; matched_law = law.name; break
            if validated:
                break

        result = {"edge": edge, "source": src, "target": dst,
                   "validated": validated, "rejected": rejected_flag, "matched_law": matched_law}

        if rejected_flag:
            rejected.append(result)
        elif validated:
            try:
                mod = CausalModule(
                    name=f"extracted_{src}_{dst}",
                    domain=domain,
                    variables={src: src, dst: dst},
                    edges=[list(edge)],
                    type_signatures={src: "scalar", dst: "scalar"},
                )
                lib.register(mod)
                result["module_added"] = True
                added.append(result)
            except Exception:
                result["module_added"] = False
                pending.append(result)
        else:
            pending.append(result)

    return {"added": added, "rejected": rejected, "pending": pending, "total": len(assertions)}


def extract_from_answer(answer: str, client=None, domain: str = "extracted") -> Dict:
    """从 LLM 回答中提取并验证因果知识 (LLM 优先, 正则 fallback)"""
    # 优先试用 LLM 提取
    assertions = extract_via_llm(answer, client)
    if not assertions:
        assertions = extract_causal_assertions(answer)
    return validate_and_add(assertions, domain)
