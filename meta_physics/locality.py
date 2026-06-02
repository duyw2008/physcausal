"""
局域因果 — 因果箭头的速度限制

元物理层 Tier 1 — 过程约束 ④

核心:
  因果传播必须满足局域性 (locality):
    - 原因必须在结果的光锥之内 (类时间隔)
    - 类空间隔的事件不能有直接因果联系
    - 因果箭头必须沿时间正向

在因果推断中的应用:
  1. DAG 边验证: 每条边 source→target 必须满足 t_source < t_target
  2. 光锥检查: 两个变量若为类空间隔 → 必定 d-separated
  3. 时序约束: 无环性 = 拓扑序存在 = 局域因果的必要条件
  4. 超距作用检测: 发现 DAG 中违反局域性的边 → 标记为可疑

与其他元物理模块的关系:
  locality ← least_action:  Lagrange 密度必须是局域的 (L 只依赖于场在同一点的值)
  locality ← entropy:       熵增过程必须沿类时方向
  locality ← symmetry:      局域对称性 → 规范场 (所有基本相互作用)
  locality → causal/graph:  DAG 的边必须通过光锥验证
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
import numpy as np


# ═══════════════════════════════════════════════════════════════
# Core: Spacetime Event & Light Cone
# ═══════════════════════════════════════════════════════════════

@dataclass
class SpacetimeEvent:
    """时空事件 — 一个因果变量在时空中的定位"""
    variable: str
    t: float          # 时间坐标
    x: float = 0.0    # 空间坐标 (1D 简化)
    y: float = 0.0
    z: float = 0.0

    def interval_to(self, other: "SpacetimeEvent") -> float:
        """
        时空间隔: Δs² = c²Δt² - Δx² - Δy² - Δz²

        Δs² > 0  → 类时间隔 (可以有因果联系)
        Δs² = 0  → 类光间隔 (光速传播)
        Δs² < 0  → 类空间隔 (不能有直接因果联系!)
        """
        c = 1.0  # 自然单位
        dt = self.t - other.t
        dx = self.x - other.x
        dy = self.y - other.y
        dz = self.z - other.z
        return c * c * dt * dt - dx * dx - dy * dy - dz * dz

    def is_timelike_to(self, other: "SpacetimeEvent") -> bool:
        return self.interval_to(other) > 0

    def is_spacelike_to(self, other: "SpacetimeEvent") -> bool:
        return self.interval_to(other) < 0

    def is_in_past_lightcone_of(self, other: "SpacetimeEvent") -> bool:
        """self 是否在 other 的过去光锥内 (self 可以因果影响 other)"""
        return self.t < other.t and self.is_timelike_to(other)

    def is_in_future_lightcone_of(self, other: "SpacetimeEvent") -> bool:
        """self 是否在 other 的未来光锥内"""
        return self.t > other.t and self.is_timelike_to(other)


# ═══════════════════════════════════════════════════════════════
# Locality Validator
# ═══════════════════════════════════════════════════════════════

@dataclass
class LocalityReport:
    """局域性验证报告"""
    total_edges: int
    valid_edges: int
    spacelike_violations: List[Tuple[str, str, str]]  # [(src, dst, reason), ...]
    timelike_valid: List[Tuple[str, str]]
    is_valid: bool
    notes: str = ""


class LocalityValidator:
    """
    局域因果验证器。

    验证因果图是否满足局域性:
      1. 所有边必须沿时间正向  t_source < t_target
      2. 类空间隔的事件之间不能有直接边
      3. 图必须无环 (DAG) — 由 causal/graph.py 保证

    这是五条元物理原则中「局域因果」的核心实现。
    """

    def __init__(self, speed_of_causation: float = 1.0):
        """
        Args:
            speed_of_causation: 因果传播速度 (自然单位中=1, 即光速)
        """
        self.c = speed_of_causation

    def validate_dag(self,
                     edges: List[Tuple[str, str]],
                     spacetime: Dict[str, SpacetimeEvent]) -> LocalityReport:
        """
        验证因果图的局域性。

        Args:
            edges: 因果边列表 [(source, target), ...]
            spacetime: 每个变量的时空坐标

        Returns:
            LocalityReport 包含违规详情
        """
        spacelike_violations = []
        timelike_valid = []

        for src, dst in edges:
            if src not in spacetime or dst not in spacetime:
                # 无时空标签的变量跳过检查 (假设有效)
                timelike_valid.append((src, dst))
                continue

            src_ev = spacetime[src]
            dst_ev = spacetime[dst]

            # 检查 1: 时间序
            if src_ev.t >= dst_ev.t:
                spacelike_violations.append((
                    src, dst,
                    f"t({src})={src_ev.t:.2f} ≥ t({dst})={dst_ev.t:.2f} — 果不能在因之前"
                ))
                continue

            # 检查 2: 类空间隔
            if src_ev.is_spacelike_to(dst_ev):
                spacelike_violations.append((
                    src, dst,
                    f"类空间隔 Δs²={src_ev.interval_to(dst_ev):.4f} < 0 — 不能有直接因果"
                ))
                continue

            # 检查 3: 因果传播速度
            dx = abs(src_ev.x - dst_ev.x)
            dt = dst_ev.t - src_ev.t
            if dx / (dt + 1e-10) > self.c:
                spacelike_violations.append((
                    src, dst,
                    f"因果速度 {dx/dt:.2f} > c={self.c} — 超光速!"
                ))
                continue

            timelike_valid.append((src, dst))

        is_valid = len(spacelike_violations) == 0
        notes = (
            f"✓ All {len(timelike_valid)} edges satisfy locality"
            if is_valid else
            f"✗ {len(spacelike_violations)}/{len(edges)} edges violate locality"
        )

        return LocalityReport(
            total_edges=len(edges),
            valid_edges=len(timelike_valid),
            spacelike_violations=spacelike_violations,
            timelike_valid=timelike_valid,
            is_valid=is_valid,
            notes=notes,
        )

    def must_be_d_separated(self,
                            var_a: SpacetimeEvent,
                            var_b: SpacetimeEvent) -> Tuple[bool, str]:
        """
        判断两个变量是否必须 d-separated (因为它们处于类空间隔)。

        如果 A 和 B 是类空间隔, 则:
          - 不存在因果路径连接它们
          - 任何声称 A→B 或 B→A 的边都是假的
          - 在因果图中, A 和 B 必须由某个条件集 d-separated
        """
        if var_a.is_spacelike_to(var_b):
            return True, f"类空间隔 Δs²={var_a.interval_to(var_b):.4f} — 必须 d-separated"
        elif var_a.is_in_past_lightcone_of(var_b):
            return False, f"{var_a.variable} 在 {var_b.variable} 的过去光锥内 — 可以有因果"
        elif var_b.is_in_past_lightcone_of(var_a):
            return False, f"{var_b.variable} 在 {var_a.variable} 的过去光锥内 — 可以有因果"
        else:
            return True, "时间序不确定 — 保守估计必须 d-separated"


# ═══════════════════════════════════════════════════════════════
# Temporal Ordering
# ═══════════════════════════════════════════════════════════════

class TemporalOrder:
    """
    时间序约束 — 确保因果边沿时间正向。

    对所有因果推断的基础约束:
      - 拓扑序存在 = 因果图无环 = 时间正向性满足
      - Kahn 拓扑排序隐式编码了时间序
      - 显式时间标签提供更强的验证 (不只是序, 还有速度限制)
    """

    def __init__(self):
        pass

    def validate_temporal_order(self,
                                edges: List[Tuple[str, str]],
                                var_times: Dict[str, float]) -> Tuple[bool, List[str]]:
        """
        验证所有边是否满足 t_source < t_target。

        Returns:
          (is_valid, violation_messages)
        """
        violations = []
        for src, dst in edges:
            t_src = var_times.get(src)
            t_dst = var_times.get(dst)
            if t_src is not None and t_dst is not None:
                if t_src >= t_dst:
                    violations.append(
                        f"{src}→{dst}: t({src})={t_src:.2f} ≥ t({dst})={t_dst:.2f}"
                    )

        return len(violations) == 0, violations

    def assign_temporal_labels(self,
                               edges: List[Tuple[str, str]],
                               variables: List[str]) -> Dict[str, float]:
        """
        从 DAG 拓扑序生成时间标签。

        对 DAG 做拓扑排序后, 按序赋值 t=0,1,2,...
        这确保了每条边 source→target 满足 t_source < t_target。
        
        这是无显式时间数据时的最小假设。
        """
        # 拓扑序 (简化: Kahn 算法)
        in_degree = {v: 0 for v in variables}
        adj = {v: [] for v in variables}
        for src, dst in edges:
            if src in in_degree and dst in in_degree:
                adj[src].append(dst)
                in_degree[dst] += 1

        # 初始入度为 0 的节点
        queue = [v for v in variables if in_degree[v] == 0]
        order = []

        while queue:
            v = queue.pop(0)
            order.append(v)
            for neighbor in adj[v]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # 赋值时间标签
        times = {}
        for i, v in enumerate(order):
            times[v] = float(i)

        # 如果有环, 未包含的变量赋值无穷大
        for v in variables:
            if v not in times:
                times[v] = float('inf')

        return times

    def time_cones(self,
                   event: SpacetimeEvent,
                   spacetime: Dict[str, SpacetimeEvent]) -> Dict[str, List[str]]:
        """
        计算事件的光锥分区。

        Returns:
          {
            "past_lightcone": [...],     # 能因果影响 event 的事件
            "future_lightcone": [...],   # event 能因果影响的事件
            "spacelike_separated": [...], # 不能有因果联系的事件
          }
        """
        past = []
        future = []
        spacelike = []

        for var, other in spacetime.items():
            if var == event.variable:
                continue
            if other.is_in_past_lightcone_of(event):
                past.append(var)
            elif other.is_in_future_lightcone_of(event):
                future.append(var)
            else:
                spacelike.append(var)

        return {
            "past_lightcone": past,
            "future_lightcone": future,
            "spacelike_separated": spacelike,
        }


# ═══════════════════════════════════════════════════════════════
# Causal Graph Locality Bridge
# ═══════════════════════════════════════════════════════════════

class CausalLocalityBridge:
    """
    连接局域因果和 causal/graph.py 的桥接器。

    在 causal/graph.py 的 CausalDAG 之上添加局域性验证层。
    """

    def __init__(self, validator: Optional[LocalityValidator] = None):
        self.validator = validator or LocalityValidator()
        self.temporal = TemporalOrder()

    def verify_causal_graph(self,
                            edges: List[Tuple[str, str]],
                            variables: List[str],
                            var_times: Optional[Dict[str, float]] = None,
                            var_positions: Optional[Dict[str, Tuple[float, ...]]] = None
                            ) -> LocalityReport:
        """
        全面验证因果图的局域性。

        如果没有显式时空坐标:
          1. 从 DAG 拓扑序生成时间标签
          2. 假设所有变量在空间同一点 (最宽松假设)
          3. 只验证时间序约束

        如果有显式时空坐标:
          1. 完整的光锥检查
          2. 因果速度验证
          3. 类空间隔检测
        """
        if var_times is None:
            var_times = self.temporal.assign_temporal_labels(edges, variables)

        if var_positions is None:
            # 所有变量假设在空间原点 (最宽松)
            spacetime = {
                v: SpacetimeEvent(variable=v, t=var_times.get(v, 0.0))
                for v in variables
            }
        else:
            spacetime = {
                v: SpacetimeEvent(
                    variable=v,
                    t=var_times.get(v, 0.0),
                    x=var_positions[v][0] if len(var_positions[v]) > 0 else 0.0,
                    y=var_positions[v][1] if len(var_positions[v]) > 1 else 0.0,
                    z=var_positions[v][2] if len(var_positions[v]) > 2 else 0.0,
                )
                for v in variables
            }

        return self.validator.validate_dag(edges, spacetime)

    def filter_spacelike_edges(self,
                               edges: List[Tuple[str, str]],
                               spacetime: Dict[str, SpacetimeEvent]) -> List[Tuple[str, str]]:
        """
        从因果图中移除所有类空间隔的边。

        这是因果发现的后处理步骤:
          先跑 PC/FCI 得到候选边 →
          再用局域因果过滤掉物理上不可能的边。
        """
        valid_edges = []
        for src, dst in edges:
            if src in spacetime and dst in spacetime:
                src_ev = spacetime[src]
                dst_ev = spacetime[dst]
                if not src_ev.is_spacelike_to(dst_ev) and src_ev.t < dst_ev.t:
                    valid_edges.append((src, dst))
            else:
                # 无时空标签 → 保留 (无法验证)
                valid_edges.append((src, dst))
        return valid_edges
