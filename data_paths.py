"""
PhysCausal 数据路径解析 — 所有持久化文件统一放在 physcausal/data/

不再散落在 ~/.hermes/ 下。
"""

import os

# data/ 目录 (相对于 physcausal 根目录)
_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def ensure_data_dir():
    os.makedirs(_DATA_DIR, exist_ok=True)


def data_path(filename: str) -> str:
    """获取 data/ 下的文件路径"""
    ensure_data_dir()
    return os.path.join(_DATA_DIR, filename)


# ── 所有数据文件路径 ──

def auto_laws_path() -> str:
    return data_path("auto_laws.json")


def cv_summary_path() -> str:
    return data_path("cv_summary.json")


def completed_suggestions_path() -> str:
    return data_path("completed_suggestions.json")


def focus_path() -> str:
    return data_path("focus.json")


def scores_path() -> str:
    return data_path("scores.json")


def salience_path() -> str:
    return data_path("salience.json")


def autonomous_state_path() -> str:
    return data_path("autonomous_state.json")


# ── 跨模块共享工具 ──

def save_cv_summary(report: dict):
    """追加一条交叉验证结果到汇总文件 (去重)"""
    import json
    path = cv_summary_path()
    try:
        with open(path) as f:
            existing = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        existing = []
    key = (report.get("discovery", ""), report.get("target_domain", ""))
    existing = [r for r in existing
                if (r.get("discovery", ""), r.get("target_domain", "")) != key]
    existing.append(report)
    with open(path, "w") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)


def load_cv_summary() -> list:
    """加载交叉验证汇总"""
    import json
    try:
        with open(cv_summary_path()) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []
