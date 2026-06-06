"""
层次化抽象 — 因果涌现 (Hoel 2013)

核心: 粗粒化微观变量后, 宏观层面的因果有效信息 (EI) 可能反而更高。
      EI_macro > EI_micro → 涌现发生。

三步:
  1. coarse_grain: 互信息聚类, 将微观变量合并为宏观变量
  2. effective_info: 计算微观/宏观的 EI
  3. hierarchy: 迭代粗粒化, 构建多尺度因果图
"""

from __future__ import annotations
import numpy as np
from typing import Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════
# Coarse-graining: 基于互信息聚类的变量合并
# ═══════════════════════════════════════════════════════════════

def mutual_information(x: np.ndarray, y: np.ndarray, n_bins: int = 10) -> float:
    """离散互信息 I(X;Y)"""
    x_disc = np.digitize(x, np.linspace(x.min(), x.max(), n_bins))
    y_disc = np.digitize(y, np.linspace(y.min(), y.max(), n_bins))

    joint = np.zeros((n_bins, n_bins))
    for i in range(len(x)):
        xi = min(x_disc[i], n_bins - 1)
        yi = min(y_disc[i], n_bins - 1)
        joint[xi, yi] += 1
    joint /= len(x)

    px = joint.sum(axis=1)
    py = joint.sum(axis=0)
    mi = 0.0
    for i in range(n_bins):
        for j in range(n_bins):
            if joint[i, j] > 0 and px[i] > 0 and py[j] > 0:
                mi += joint[i, j] * np.log(joint[i, j] / (px[i] * py[j]))
    return max(0, mi)


def coarse_grain(data: np.ndarray, var_names: List[str],
                  mi_threshold: float = 0.3) -> Dict:
    """
    基于互信息聚类将微观变量合并为宏观变量。

    Args:
        data: (n_samples, n_vars) 微观数据
        var_names: 微观变量名
        mi_threshold: 互信息阈值, 高于此值的变量对合并

    Returns:
        {
            macro_vars: ['macro_0', 'macro_1', ...],
            mapping: {macro_var: [micro_var_indices]},
            macro_data: (n_samples, n_macro) array
        }
    """
    n_vars = len(var_names)
    if n_vars <= 2:
        return {
            "macro_vars": var_names,
            "mapping": {v: [i] for i, v in enumerate(var_names)},
            "macro_data": data.copy(),
        }

    # 计算互信息矩阵
    mi_matrix = np.zeros((n_vars, n_vars))
    for i in range(n_vars):
        for j in range(i + 1, n_vars):
            mi = mutual_information(data[:, i], data[:, j])
            mi_matrix[i, j] = mi_matrix[j, i] = mi

    # 贪婪聚类: 高 MI 的变量合并
    merged = set()
    groups = []

    for i in range(n_vars):
        if i in merged:
            continue
        group = [i]
        for j in range(i + 1, n_vars):
            if j in merged:
                continue
            if mi_matrix[i, j] > mi_threshold:
                group.append(j)
                merged.add(j)
        merged.add(i)
        groups.append(group)

    # 构建宏观变量 (组内取平均)
    macro_data = np.zeros((data.shape[0], len(groups)))
    mapping = {}
    macro_vars = []

    for g_idx, group in enumerate(groups):
        macro_name = f"macro_{g_idx}"
        macro_vars.append(macro_name)
        mapping[macro_name] = group
        if len(group) == 1:
            macro_data[:, g_idx] = data[:, group[0]]
        else:
            macro_data[:, g_idx] = data[:, group].mean(axis=1)

    return {
        "macro_vars": macro_vars,
        "mapping": mapping,
        "macro_data": macro_data,
        "mi_matrix": mi_matrix,
        "n_groups": len(groups),
    }


# ═══════════════════════════════════════════════════════════════
# Effective Information (Hoel 2013)
# ═══════════════════════════════════════════════════════════════

def effective_information(data: np.ndarray, var_names: List[str],
                           n_interventions: int = 20) -> Dict:
    """
    计算系统的有效信息 (EI) — 因果影响度量。

    对每个变量: 随机干扰一半样本, 测量对其他变量的平均绝对相关变化。
    EI 越高 = 该系统变量的因果影响力越强。

    Returns:
        {ei, per_variable_ei, total}
    """
    n_vars = len(var_names)
    n_samples = len(data)

    if n_vars < 2 or n_samples < 10:
        return {"ei": 0.0, "per_variable_ei": {}, "total": 0.0}

    total_ei = 0.0
    per_var_ei = {}

    for vi in range(n_vars):
        var_ei = 0.0
        count = 0
        half = n_samples // 2

        for _ in range(min(n_interventions, 10)):
            # Shuffle this variable for half the samples (simulates intervention)
            idx = np.random.choice(n_samples, half, replace=False)
            shuffled = data.copy()
            shuffled[idx, vi] = np.random.permutation(shuffled[idx, vi])

            # Measure: how much does this change affect others?
            for vj in range(n_vars):
                if vj == vi:
                    continue
                # Correlation between original and intervened
                orig_corr = abs(np.corrcoef(data[:, vi], data[:, vj])[0, 1])
                interv_corr = abs(np.corrcoef(shuffled[:, vi], shuffled[:, vj])[0, 1])
                # Causal influence = how much correlation drops when we break the causal link
                influence = max(0, orig_corr - interv_corr)
                var_ei += influence
                count += 1

        if count > 0:
            var_ei /= count
            per_var_ei[var_names[vi]] = round(var_ei, 4)
            total_ei += var_ei

    return {
        "ei": round(total_ei, 4),
        "per_variable_ei": per_var_ei,
        "total": total_ei,
    }


# ═══════════════════════════════════════════════════════════════
# Hierarchy Builder
# ═══════════════════════════════════════════════════════════════

def build_hierarchy(data: np.ndarray, var_names: List[str],
                     max_layers: int = 3, mi_threshold: float = 0.3) -> Dict:
    """
    迭代粗粒化, 构建多尺度因果层次。

    流程:
      1. 计算当前层的 EI
      2. 粗粒化 → 上一层
      3. 计算上一层的 EI
      4. 如果 EI_macro > EI_micro → 涌现确认
      5. 继续迭代

    Returns:
        {
            layers: [{level, n_vars, ei, emergence}, ...],
            best_level: int (EI 最大的层),
            emergent: bool
        }
    """
    layers = []
    current_data = data.copy()
    current_vars = list(var_names)
    ei_max = -np.inf
    best_level = 0
    emergent = False

    for level in range(max_layers):
        n_vars = current_data.shape[1]

        if n_vars < 2:
            break

        # 计算当前层的 EI
        ei_result = effective_information(current_data, current_vars)
        ei = ei_result["ei"]

        layers.append({
            "level": level,
            "n_vars": n_vars,
            "var_names": current_vars,
            "ei": ei,
        })

        if ei > ei_max:
            ei_max = ei
            best_level = level

        # 粗粒化
        cg = coarse_grain(current_data, current_vars, mi_threshold)
        if cg.get("n_groups", len(cg.get("macro_vars", []))) >= n_vars:
            break

        current_data = cg["macro_data"]
        current_vars = cg["macro_vars"]

    # 涌现检测: 上层 EI > 下层 EI
    for i in range(1, len(layers)):
        if layers[i]["ei"] > layers[i-1]["ei"]:
            layers[i]["emergence"] = True
            emergent = True
        else:
            layers[i]["emergence"] = False

    return {
        "layers": layers,
        "best_level": best_level,
        "emergent": emergent,
        "n_layers": len(layers),
    }
