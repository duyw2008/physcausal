"""
会话知识提取 — 从 LLM 回答中自动提取因果断言并入库

核心: 每轮对话后, 扫描 LLM 回答中的因果断言,
      物理验证后自动加入模块库, 实现"越聊越胖"。
"""

from __future__ import annotations
import re
from typing import Dict, List, Optional, Tuple

from creative.module_library import ModuleLibrary, CausalModule


# 中文因果断言模式
CAUSAL_PATTERNS = [
    # "X → Y" or "X→Y"
    (r'(\S+?)\s*→\s*(\S+)', 'arrow'),
    # "X 导致 Y"
    (r'(\S+?)\s*导致\s*(\S+)', 'lead_to'),
    # "X 是 Y 的(原因|因)"
    (r'(\S+?)\s*是\s*(\S+?)\s*的(?:原因|因)', 'is_cause_of'),
    # "X 决定 Y"
    (r'(\S+?)\s*决定\s*(\S+)', 'determines'),
    # "X 影响 Y" (弱因果)
    (r'(\S+?)\s*影响\s*(\S+)', 'affects'),
    # "X 引起 Y"
    (r'(\S+?)\s*引起\s*(\S+)', 'causes'),
    # "禁止: X → Y" (forbidden direction)
    (r'禁止[：:]\s*(\S+?)\s*→\s*(\S+)', 'forbidden'),
    # "X -> Y" (English arrow in Chinese text)
    (r'(\w+)\s*->\s*(\w+)', 'english_arrow'),
]


def extract_causal_assertions(text: str) -> List[Dict]:
    """
    从文本中提取因果断言。

    Returns:
        [{source, target, direction, pattern_type, raw_match}, ...]
    """
    assertions = []

    for pattern, ptype in CAUSAL_PATTERNS:
        for match in re.finditer(pattern, text):
            src = match.group(1).strip()
            dst = match.group(2).strip()

            # 过滤噪声: 太短的变量名, 纯数字, 箭头本身
            if len(src) < 1 or len(dst) < 1:
                continue
            if src in ('→', '->', '—') or dst in ('→', '->', '—'):
                continue
            if src.isdigit() or dst.isdigit():
                continue
            # 过滤标点
            if any(c in src for c in '，。！？；：、') or any(c in dst for c in '，。！？；：、'):
                continue

            direction = "forward" if ptype != "forbidden" else "forbidden"
            assertions.append({
                "source": src,
                "target": dst,
                "direction": direction,
                "pattern": ptype,
            })

    # 去重
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

    验证规则:
      1. 如果断言的方向与物理定律 forbidden_directions 冲突 → 拒绝
      2. 如果断言的方向与物理定律 causal_direction 一致 → 通过
      3. 否则标记为未验证 (保留但低置信)

    Returns:
        {added, rejected, pending}
    """
    from physics.laws import library

    lib = ModuleLibrary()
    added = []
    rejected = []
    pending = []

    for a in assertions:
        src, dst = a["source"], a["target"]
        edge = (src, dst)
        reverse = (dst, src)

        # 物理验证
        validated = False
        rejected_flag = False
        matched_law = None

        for law in library.list_all():
            # 检查 forbidden: 如果当前断言方向被禁止 → 拒绝
            for fd in law.forbidden_directions:
                if (fd[0] in src and fd[1] in dst) or (fd[0] == src.lower() and fd[1] == dst.lower()):
                    rejected_flag = True
                    matched_law = law.name
                    break
            if rejected_flag:
                break

            # 检查 causal: 如果当前断言方向被确认 → 通过
            for cd in law.causal_direction:
                if (cd[0] in src and cd[1] in dst) or (cd[0] == src.lower() and cd[1] == dst.lower()):
                    validated = True
                    matched_law = law.name
                    break
            if validated:
                break

        result = {
            "edge": edge,
            "source": src,
            "target": dst,
            "validated": validated,
            "rejected": rejected_flag,
            "matched_law": matched_law,
        }

        if rejected_flag:
            rejected.append(result)
        elif validated:
            # 加入模块库
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

    return {
        "added": added,
        "rejected": rejected,
        "pending": pending,
        "total": len(assertions),
    }


def extract_from_answer(answer: str, domain: str = "extracted") -> Dict:
    """从 LLM 回答中提取并验证因果知识 (一站式)"""
    assertions = extract_causal_assertions(answer)
    return validate_and_add(assertions, domain)
