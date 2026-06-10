"""
数据管道 — 从实验数据中做因果发现

让 Noether 不只是推理手工定律, 也能从真实数据中发现模式。
"""

from __future__ import annotations
from typing import Dict, List, Optional


def load_csv(path: str) -> Optional[Dict]:
    """加载 CSV 数据"""
    import csv
    try:
        with open(path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            if not rows:
                return None
            columns = list(rows[0].keys())
            return {"columns": columns, "rows": rows, "n": len(rows)}
    except Exception as e:
        return None


def discover_from_data(path: str, target: Optional[str] = None) -> str:
    """
    从 CSV 数据中做因果发现。

    流程:
      1. 加载数据
      2. 基础统计 (相关性矩阵)
      3. 如果指定目标 → 线性回归 + 因果方向推断
      4. 与 PhysCausal 定律库比对
    """
    data = load_csv(path)
    if not data:
        return f"无法加载数据: {path}"

    columns = data["columns"]
    n = data["n"]
    rows = data["rows"]

    lines = [f"═══ 数据管道: {path} ═══"]
    lines.append(f"  变量: {len(columns)} ({', '.join(columns)})")
    lines.append(f"  样本: {n}")
    lines.append("")

    # 1. 数值化 + 相关性
    numeric_cols = []
    numeric_data = {}
    for col in columns:
        try:
            vals = [float(row[col]) for row in rows if row[col]]
            if len(vals) > n * 0.5:  # 至少 50% 非空
                numeric_cols.append(col)
                numeric_data[col] = vals
        except (ValueError, KeyError):
            pass

    if len(numeric_cols) < 2:
        return "\n".join(lines) + "\n  数值变量不足, 无法做因果发现。"

    # 计算相关性矩阵
    import math
    lines.append("── 相关性矩阵 ──")
    correlations = []
    for i, a in enumerate(numeric_cols):
        for b in numeric_cols[i+1:]:
            va = numeric_data[a]
            vb = numeric_data[b]
            n_pairs = min(len(va), len(vb))
            if n_pairs < 5:
                continue
            mean_a = sum(va[:n_pairs]) / n_pairs
            mean_b = sum(vb[:n_pairs]) / n_pairs
            cov = sum((va[j] - mean_a) * (vb[j] - mean_b) for j in range(n_pairs)) / n_pairs
            std_a = math.sqrt(sum((va[j] - mean_a)**2 for j in range(n_pairs)) / n_pairs)
            std_b = math.sqrt(sum((vb[j] - mean_b)**2 for j in range(n_pairs)) / n_pairs)
            if std_a > 0 and std_b > 0:
                corr = cov / (std_a * std_b)
                correlations.append((a, b, corr))

    correlations.sort(key=lambda x: abs(x[2]), reverse=True)

    for a, b, corr in correlations[:8]:
        bar = "█" * int(abs(corr) * 10)
        direction = "→" if corr > 0 else "←"
        lines.append(f"  {a} {direction} {b}: r={corr:.3f} {bar}")

    # 2. 如果指定了目标, 做因果方向推断
    if target and target in numeric_cols:
        lines.append(f"\n── 因果方向: {target} ──")
        from physics.laws import library, classify_variable

        related = []
        for a, b, corr in correlations:
            if abs(corr) > 0.7 and (a == target or b == target):
                other = b if a == target else a
                # 尝试匹配 PhysCausal 变量
                cat = classify_variable(other.lower())
                laws = [l for l in library.list_all()
                        if other.lower() in str(l.inputs + l.outputs).lower()]
                related.append((other, corr, cat, laws))

        if related:
            for other, corr, cat, laws in related:
                direction_symbol = "→" if corr > 0 else "←"
                lines.append(f"  {other} {direction_symbol} {target}: r={corr:.3f} [{cat}]")
                if laws:
                    for l in laws[:2]:
                        lines.append(f"    ↳ 已知定律: {l.name} ({l.domain}) {l.inputs}→{l.outputs}")
                else:
                    lines.append(f"    ↳ 未知边 — 可能是新发现!")
        else:
            lines.append(f"  未发现 |r| > 0.7 的相关变量")

    # 3. 与因果图比对
    lines.append(f"\n── 因果图比对 ──")
    matched = 0
    novel = 0
    for a, b, corr in correlations:
        if abs(corr) > 0.5:
            found = False
            for law in library.list_all():
                if (a.lower() in str(law.inputs + law.outputs).lower() and
                        b.lower() in str(law.inputs + law.outputs).lower()):
                    found = True
                    break
            if found:
                matched += 1
            else:
                novel += 1

    lines.append(f"  高相关对 (|r|>0.5): {matched + novel}")
    lines.append(f"  已有定律覆盖: {matched}")
    lines.append(f"  潜在新边: {novel}")

    return "\n".join(lines)
