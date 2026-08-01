"""
殖民地投票系统 — 细胞集体决定自发现边的置信层级

原则:
  tier 0-2: 物理学家领地 (公理/共识/主流理论) — 殖民地不能动
  tier 3:   严肃物理假说 — 殖民地高共识可设
  tier 4:   探索性编码 — 殖民地初始产出，默认层级

边从无到有的生命历程:
  1. 细胞发现路径 → 注册为 grown_edge (tier 4)
  2. 细胞反复走过同一条边 → 投票积累
  3. 投票超过阈值 → 升为 tier 3 (严肃假说)
  4. arXiv/人工验证通过 → 升为 tier 2 (主流理论)
  5. tier 0-1 永远不对殖民地开放

降级机制:
  - 长期无细胞经过的边 → 投票衰减
  - 衰减到零 → 边被修剪 (回到无)
"""

from __future__ import annotations
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import time


class EdgeVote:
    """细胞对一条边的一次投票"""
    def __init__(self, cell_id: int, src: str, dst: str, confidence: float,
                 generation: int):
        self.cell_id = cell_id
        self.src = src
        self.dst = dst
        self.confidence = confidence  # 细胞走这条边时的信心 (0-1)
        self.generation = generation
        self.timestamp = time.time()


class ColonyBallot:
    """殖民地投票箱 — 管理边的集体投票和置信层级"""
    
    # 升级阈值
    TIER4_TO_TIER3_VOTES = 10    # 至少10个不同细胞投票
    TIER3_TO_TIER2_VOTES = 50    # 至少50个不同细胞 + 外部验证
    TIER3_TO_TIER2_EXTERNAL = True  # 需要外部验证标志
    
    # 衰减参数
    VOTE_DECAY_GENERATIONS = 300  # 300代无新投票 → 开始衰减 (原100, 太短)
    PRUNE_THRESHOLD = 3           # 总票数低于此值 → 修剪
    
    def __init__(self):
        # {(src, dst): [EdgeVote, ...]}
        self.votes: Dict[Tuple[str, str], List[EdgeVote]] = defaultdict(list)
        # {(src, dst): current_tier}
        self.tiers: Dict[Tuple[str, str], int] = {}
        # {(src, dst): external_validated}
        self.external_validated: Dict[Tuple[str, str], bool] = {}
        # 投票历史用于衰减计算
        self._last_vote_gen: Dict[Tuple[str, str], int] = {}
        self._physics_results: Dict[Tuple[str, str], dict] = {}  # 物理验证结果
    
    def cast_vote(self, cell_id: int, src: str, dst: str,
                  confidence: float, generation: int):
        """细胞对一条边投票"""
        key = (src, dst)
        vote = EdgeVote(cell_id, src, dst, confidence, generation)
        self.votes[key].append(vote)
        self._last_vote_gen[key] = generation
        
        # 新边默认 tier 4
        if key not in self.tiers:
            self.tiers[key] = 4
        
        # 检查升级
        self._check_promotion(key, generation)
    
    def _check_promotion(self, key: Tuple[str, str], generation: int):
        """检查边的置信层级是否需要升级"""
        current = self.tiers.get(key, 4)
        edge_votes = self.votes[key]
        
        unique_cells = len({v.cell_id for v in edge_votes})
        
        # tier 4 → tier 3: 足够多的独立细胞投票
        if current == 4 and unique_cells >= self.TIER4_TO_TIER3_VOTES:
            self.tiers[key] = 3
            # 触发物理二次确认
            self._physics_check(key)
        
        # tier 3 → tier 2: 需要外部验证
        if current == 3 and unique_cells >= self.TIER3_TO_TIER2_VOTES:
            if self.external_validated.get(key, False):
                self.tiers[key] = 2
    
    def _physics_check(self, key: Tuple[str, str]):
        """物理二次确认: tier3 假说是否违反已知物理定律"""
        src, dst = key
        
        try:
            from physics.constraints import PhysicsConstrainedDAG
            from physics.laws import library
            
            # 收集图中所有变量
            all_vars = set()
            for law in library._laws:
                for s, d in law.causal_direction:
                    all_vars.add(s)
                    all_vars.add(d)
            
            constraint = PhysicsConstrainedDAG(list(all_vars))
            
            issues = []
            
            # 检查1: forbidden_directions
            for f_src, f_dst in constraint.forbidden_edges:
                if f_src == src and f_dst == dst:
                    issues.append(f"forbidden: {f_src} → {f_dst}")
                    break
            
            # 检查2: 自环
            if src == dst:
                issues.append("self-loop")
            
            # 检查3: 域兼容性 — 图中有已知路径吗?
            if not issues:
                has_path = self._has_verified_path(src, dst)
                if has_path:
                    issues.append("path_exists")  # 路径已存在 → 只是确认
            
            # 记录结果
            self._physics_results[key] = {
                "passed": len([i for i in issues if i != "path_exists"]) == 0,
                "issues": issues,
                "checked_at": self._vote_gen(key),
            }
            
        except Exception as e:
            self._physics_results[key] = {
                "passed": False,
                "issues": [f"check_error: {e}"],
            }
    
    def _has_verified_path(self, src: str, dst: str, max_depth: int = 10) -> bool:
        """BFS: 验证图中 src→dst 是否有路径"""
        try:
            from physics.laws import library
            graph = {}
            for law in library._laws:
                for s, d in law.causal_direction:
                    graph.setdefault(s, []).append(d)
            
            if src not in graph or dst not in graph:
                return False
            
            visited = {src}
            frontier = [src]
            for _ in range(max_depth):
                if not frontier:
                    break
                node = frontier.pop(0)
                for neighbor in graph.get(node, []):
                    if neighbor == dst:
                        return True
                    if neighbor not in visited:
                        visited.add(neighbor)
                        frontier.append(neighbor)
        except Exception:
            pass
        return False
    
    def _vote_gen(self, key: Tuple[str, str]) -> int:
        return self._last_vote_gen.get(key, 0)
    
    def validate_externally(self, src: str, dst: str):
        """外部验证通过 (arXiv/gap_resolver)"""
        key = (src, dst)
        self.external_validated[key] = True
        if self.tiers.get(key, 4) == 3:
            # 重新检查升级
            self._check_promotion(key, 0)
    
    def decay(self, generation: int):
        """衰减: 长期无投票的边降低有效票数"""
        to_prune = []
        
        for key, last_gen in list(self._last_vote_gen.items()):
            age = generation - last_gen
            if age > self.VOTE_DECAY_GENERATIONS:
                # 衰减: 保留一半票数
                decay_factor = 0.5 ** (age / self.VOTE_DECAY_GENERATIONS)
                # 简化: 直接减少票数
                current_votes = self.votes[key]
                keep_count = max(1, int(len(current_votes) * decay_factor))
                self.votes[key] = current_votes[-keep_count:]
                
                # 检查是否需要降级
                unique = len({v.cell_id for v in self.votes[key]})
                current = self.tiers.get(key, 4)
                if current == 3 and unique < self.TIER4_TO_TIER3_VOTES:
                    self.tiers[key] = 4  # 降回 tier 4
                
                # 检查是否需要修剪
                if len(self.votes[key]) < self.PRUNE_THRESHOLD:
                    to_prune.append(key)
        
        for key in to_prune:
            del self.votes[key]
            del self._last_vote_gen[key]
            if key in self.tiers:
                del self.tiers[key]
        
        return to_prune
    
    def get_tier(self, src: str, dst: str) -> int:
        """获取一条边的当前置信层级"""
        return self.tiers.get((src, dst), 4)
    
    def get_top_hypotheses(self, n: int = 5) -> List[Dict]:
        """获取投票最高的假说"""
        scored = []
        for key, edge_votes in self.votes.items():
            unique = len({v.cell_id for v in edge_votes})
            total = sum(v.confidence for v in edge_votes)
            tier = self.tiers.get(key, 4)
            external = self.external_validated.get(key, False)
            phys = self._physics_results.get(key, {})
            
            scored.append({
                "src": key[0], "dst": key[1],
                "unique_voters": unique,
                "total_confidence": round(total, 1),
                "tier": tier,
                "external_validated": external,
                "physics_passed": phys.get("passed"),
                "physics_issues": phys.get("issues", []),
            })
        
        scored.sort(key=lambda x: -x["unique_voters"])
        return scored[:n]
    
    def status(self) -> str:
        """投票箱状态"""
        total_edges = len(self.votes)
        by_tier = defaultdict(int)
        for key in self.votes:
            by_tier[self.tiers.get(key, 4)] += 1
        
        lines = [f"🗳 投票箱: {total_edges}条边"]
        for tier in [4, 3, 2, 1, 0]:
            if by_tier[tier]:
                tier_name = {0:"公理", 1:"共识", 2:"主流", 3:"假说", 4:"探索"}[tier]
                lines.append(f"   tier {tier} ({tier_name}): {by_tier[tier]}条")
        
        return "\n".join(lines)


# ── 集成到进化殖民地 ──

def integrate_ballot(colony) -> ColonyBallot:
    """给殖民地安装投票箱"""
    ballot = ColonyBallot()
    colony.ballot = ballot
    return ballot


def cell_vote_on_path(cell, ballot: ColonyBallot, generation: int):
    """细胞对自己走过的路径中的每条边投票"""
    for step in cell.current_walk:
        if len(step) >= 3:
            src, law, dst = step[0], step[1], step[2]
            # 信心 = 路径长度归一化
            confidence = min(1.0, len(cell.current_walk) / 10.0)
            ballot.cast_vote(id(cell) % 10000, src, dst, confidence, generation)
