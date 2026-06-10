"""
自主智能体 — 让它像大脑一样自己跑

核心: 不依赖用户输入, 内部持续循环。
      每个模块自己决定什么时候激活,
      没有中央调度器。

类比:
  大脑区域 (模块)  —  自发放电 (自主激活)  —  突触权重 (salience)
  下丘脑 (驱动力)  —  体内状态 (内部状态)  —  丘脑 (注意力)

循环:
  while alive:
    1. 检查内部状态 (什么在"饿"?)
    2. 激活最"饿"的模块
    3. 产生想法 / 发现问题
    4. 更新价值系统
    5. 如果有趣 → 通知用户
    6. 睡眠 (consolidate memory)
"""

from __future__ import annotations
import json, os, time, random
from typing import Dict, List, Optional

from meta_cognition.dissonance import detect_domain_boundaries, detect_scale_boundaries
from meta_cognition import values
from creative.structure_discovery import discovery
from creative.module_library import ModuleLibrary


class InternalState:
    """智能体的内部状态 — 不依赖外部输入"""

    def __init__(self):
        self.curiosity_level = 0.5
        self.coherence_drive = 0.5
        self.novelty_drive = 0.7
        self.energy = 1.0
        self.thought_count = 0
        self.last_discovery_time = time.time()
        self.focus_domain: Optional[str] = None

        # ── 失败记忆: 避免重复走死胡同 ──
        # key: "law_a|law_b|var", value: timestamp of last failure
        self.failed_tensions: Dict[str, float] = {}
        self.FAIL_COOLDOWN = 3600  # 1 小时冷却

        # ── 发现历史: 价值判断的原材料 ──
        self.discovery_history: List[Dict] = []
        self.total_discoveries = 0

        # ── 品味档案: 从历史中学习什么值得探索 ──
        self.taste_profile: Dict[str, float] = {
            "fruitful_domains": {},    # domain → success count
            "fruitful_variables": {},  # variable → success count
        }

        # ── 主动驱动力 (v2) ──
        self.pattern_hunger = 0.0       # 发现重复结构 → 想找更多
        self.frustration = 0.0          # 验证断裂 → 想打通
        self.last_discovery_vars: List[str] = []  # 链式探索

    def update(self, thought_result: Dict):
        """根据思考结果更新内部状态 (v2: 主动驱动力)"""
        rtype = thought_result.get("type", "")
        learned = thought_result.get("learned", [])
        sig = thought_result.get("significance", 0)
        interesting = thought_result.get("interesting", False)

        # ── 好奇心 ──
        if interesting:
            self.curiosity_level = min(1.0, self.curiosity_level + 0.1)
            self.last_discovery_time = time.time()
        else:
            self.curiosity_level = max(0.05, self.curiosity_level - 0.02)

        # ── 精力: 发现时兴奋, 断裂时也有挫折燃料 ──
        self.energy = max(0.05, self.energy - 0.05)
        if learned and sig > 0:
            self.energy = min(1.0, self.energy + 0.2)  # 兴奋恢复
        elif interesting and not learned:
            self.energy = min(1.0, self.energy + 0.05)  # 有趣但没产出
        # 断裂的验证: 消耗但不沮丧 (挫折转为动力)

        # ── 模式饥饿: 连续发现同类结构 → 想找更多 ──
        if rtype == "analogy":
            analogies = thought_result.get("analogies", [])
            if analogies:
                top_sim = max(a.get("similarity", 0) for a in analogies)
                self.pattern_hunger = min(1.0, self.pattern_hunger + top_sim * 0.3)
        # 没有类比时缓慢消退
        self.pattern_hunger = max(0.0, self.pattern_hunger - 0.03)

        # ── 沮丧 → 探索欲: 断裂越多越想打通 ──
        if rtype in ("dissonance", "frontier") and not learned:
            self.frustration = min(1.0, self.frustration + 0.1)
        else:
            self.frustration = max(0.0, self.frustration - 0.05)

        # 认知失调
        dissonance_count = thought_result.get("dissonance_count", 0)
        self.coherence_drive = min(1.0, 0.3 + dissonance_count * 0.1)

        # 新颖性: 饥饿+沮丧+时间 三重驱动
        hours_since = (time.time() - self.last_discovery_time) / 3600
        self.novelty_drive = min(1.0, 0.3 + hours_since * 0.1
                                 + self.pattern_hunger * 0.3
                                 + self.frustration * 0.3)

        # ── 链式探索: 记住上次发现的变量 ──
        if learned and sig > 0:
            self.last_discovery_vars = thought_result.get("variables_involved", [])[:5]

        self.thought_count += 1

        # ── 更新品味 ──
        if learned and sig > 0:
            self.total_discoveries += 1
            # 更新领域品味
            for domain in thought_result.get("domains_involved", []):
                self.taste_profile["fruitful_domains"][domain] = \
                    self.taste_profile["fruitful_domains"].get(domain, 0) + 1
            # 更新变量品味
            for var in thought_result.get("variables_involved", []):
                self.taste_profile["fruitful_variables"][var] = \
                    self.taste_profile["fruitful_variables"].get(var, 0) + 1
            # 记录发现历史
            self.discovery_history.append({
                "time": time.time(),
                "learned": learned,
                "significance": sig,
                "type": thought_result.get("type", "?"),
            })
            # 只保留最近 50 条
            if len(self.discovery_history) > 50:
                self.discovery_history = self.discovery_history[-50:]

    def rest(self):
        """休息: 恢复精力, 整理记忆"""
        self.energy = min(1.0, self.energy + 0.3)
        # 睡眠时巩固: 将今天的发现与已有知识对比
        discovery.scan()  # 更新结构联想
        # 持久记忆: 保存最近的发现
        try:
            from meta_cognition.memory import consolidate_memory, remember
            consolidate_memory()
            if self.total_discoveries > 0:
                remember("session", f"Noether ran {self.thought_count} thoughts, found {self.total_discoveries} discoveries",
                         ["autonomous", "rest"])
        except Exception:
            pass

    def summary(self) -> str:
        top_domains = sorted(
            self.taste_profile["fruitful_domains"].items(),
            key=lambda x: x[1], reverse=True
        )[:3]
        top_vars = sorted(
            self.taste_profile["fruitful_variables"].items(),
            key=lambda x: x[1], reverse=True
        )[:3]
        return (
            f"curiosity={self.curiosity_level:.2f} "
            f"energy={self.energy:.2f} "
            f"coherence={self.coherence_drive:.2f} "
            f"novelty={self.novelty_drive:.2f} "
            f"hunger={self.pattern_hunger:.2f} "
            f"frustration={self.frustration:.2f} "
            f"thoughts={self.thought_count} "
            f"discoveries={self.total_discoveries} "
            f"taste:domains={dict(top_domains)} "
            f"taste:vars={dict(top_vars)}"
        )

    def is_failed_recently(self, law_a: str, law_b: str, var: str) -> bool:
        """检查这个张力-变量组合最近是否失败过"""
        key = f"{law_a}|{law_b}|{var}"
        last_fail = self.failed_tensions.get(key, 0)
        return (time.time() - last_fail) < self.FAIL_COOLDOWN

    def record_failure(self, law_a: str, law_b: str, var: str):
        """记录一次失败"""
        key = f"{law_a}|{law_b}|{var}"
        self.failed_tensions[key] = time.time()
        # 清理过期记录
        cutoff = time.time() - self.FAIL_COOLDOWN * 2
        self.failed_tensions = {
            k: v for k, v in self.failed_tensions.items() if v > cutoff
        }


class AutonomousAgent:
    """自主智能体: 不依赖用户输入, 自己跑"""

    from data_paths import autonomous_state_path
    STATE_FILE = autonomous_state_path()

    def __init__(self):
        self.internal = InternalState()
        self._load_state()

    def _load_state(self):
        """加载上次的运行状态"""
        try:
            with open(self.STATE_FILE) as f:
                data = json.load(f)
                s = self.internal
                s.curiosity_level = data.get("curiosity", 0.5)
                s.thought_count = data.get("thoughts", 0)
                s.total_discoveries = data.get("discoveries", 0)
                s.failed_tensions = data.get("failed_tensions", {})
                s.taste_profile = data.get("taste_profile", {
                    "fruitful_domains": {}, "fruitful_variables": {},
                })
                s.discovery_history = data.get("discovery_history", [])
                s.energy = data.get("energy", 1.0)
                s.coherence_drive = data.get("coherence", 0.5)
                s.novelty_drive = data.get("novelty", 0.7)
                s.pattern_hunger = data.get("hunger", 0.0)
                s.frustration = data.get("frustration", 0.0)
                s.last_discovery_vars = data.get("last_discovery_vars", [])
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def _save_state(self):
        os.makedirs(os.path.dirname(self.STATE_FILE), exist_ok=True)
        s = self.internal
        with open(self.STATE_FILE, "w") as f:
            json.dump({
                "curiosity": s.curiosity_level,
                "thoughts": s.thought_count,
                "discoveries": s.total_discoveries,
                "failed_tensions": s.failed_tensions,
                "taste_profile": s.taste_profile,
                "discovery_history": s.discovery_history[-20:],
                "energy": s.energy,
                "coherence": s.coherence_drive,
                "novelty": s.novelty_drive,
                "hunger": s.pattern_hunger,
                "frustration": s.frustration,
                "last_discovery_vars": s.last_discovery_vars,
                "last_run": time.time(),
            }, f, ensure_ascii=False)

    # ═══ 大脑的核心循环 ═══

    def think(self, verbose: bool = True, llm_bridge=None) -> Optional[Dict]:
        """
        一次自发的思考。

        随机选择一个"饿"的模块激活, 产生一个想法。
        如果想法足够有趣, 返回给调用者。
        llm_bridge 可选 — 不传则纯零 token 运行。
        """
        if self.internal.energy < 0.2:
            if verbose:
                print("  😴 too tired, resting...")
            self.internal.rest()
            return None

        # 根据内部状态选择哪个模块激活
        # 均衡权重: 前沿/失调/联想三分天下, 结构/反思辅助
        s = self.internal
        drives = {
            "frontier":   s.novelty_drive * 1.5,      # 探索未知
            "analogy":    s.curiosity_level * 1.2 + s.pattern_hunger * 1.0,  # 模式饥饿
            "dissonance": s.coherence_drive * 1.3 + s.frustration * 0.5,     # 沮丧驱动
            "associate":  min(s.curiosity_level, 0.7),
            "structure":  s.novelty_drive * 0.6,
            "reflect":    min(s.curiosity_level, 0.7) * 0.5,
        }

        # 加权随机选择
        total = sum(drives.values())
        r = random.random() * total
        cumulative = 0
        chosen = "reflect"
        for module, weight in drives.items():
            cumulative += weight
            if r <= cumulative:
                chosen = module
                break

        # 激活模块
        if chosen == "dissonance":
            result = self._think_dissonance(verbose)
        elif chosen == "frontier":
            result = self._think_frontier(verbose)
        elif chosen == "analogy":
            result = self._think_associate(verbose)
        elif chosen == "structure":
            result = self._think_structure(verbose)
        elif chosen == "associate":
            result = self._think_associate(verbose)
        else:
            result = self._think_reflect(verbose)

        # 关键: 有趣的发现 → 学习 (必须在 update 之前, 因为 update 需要 learned 数据)
        if result.get("interesting"):
            learned = self._learn_from(result, llm_bridge, verbose)
            result["learned"] = learned
            if verbose and learned:
                self._report_discovery(result)

        self.internal.update(result)
        self._save_state()

        return result

    def run(self, max_thoughts: int = 10, sleep_between: float = 1.0,
            verbose: bool = True, llm_bridge=None):
        """运行自主循环"""
        if verbose:
            print("=== PhysCausal Autonomous Agent ===")
            print(f"  Internal state: {self.internal.summary()}")
            print("  Running autonomous thoughts...")
            print()

        discoveries = []
        for i in range(max_thoughts):
            if verbose:
                dots = "." * (i % 4 + 1)
                print(f"\r  Thinking{dots:<4}", end="", flush=True)

            result = self.think(verbose=False, llm_bridge=llm_bridge)
            if result and result.get("interesting"):
                discoveries.append(result)

            if self.internal.energy < 0.15:
                if verbose:
                    print(f"\n  😴 Tired after {i+1} thoughts. Resting.")
                self.internal.rest()

            time.sleep(sleep_between)

        if verbose:
            print(f"\r  Done. {len(discoveries)} interesting thoughts.")
            self.internal.summary()
            print(f"\n  Final state: {self.internal.summary()}")

        return discoveries

    # ═══ 模块: 认知失调思考 ═══

    def _think_dissonance(self, verbose: bool) -> Dict:
        """思考: 定律库中有什么矛盾值得研究? 带失败记忆和品味偏好。"""
        domain_issues = detect_domain_boundaries()
        scale_issues = detect_scale_boundaries()
        all_issues = domain_issues + scale_issues
        total = len(all_issues)

        if total == 0:
            return {"interesting": False, "dissonance_count": 0}

        # ── 过滤最近失败的张力 ──
        candidates = []
        for issue in all_issues:
            law_a = issue.get("law_a", "")
            law_b = issue.get("law_b", "")
            overlap = issue.get("overlap", [])
            # 检查是否所有 overlap 变量都失败过
            all_failed = overlap and all(
                self.internal.is_failed_recently(law_a, law_b, v)
                for v in overlap
            )
            if not all_failed:
                candidates.append(issue)

        # 全部在冷却中 → 跳过
        if not candidates:
            if verbose:
                print(f"\n  ⏳ All {total} tensions in cooldown. Skipping.")
            return {"interesting": False, "dissonance_count": total}

        # ── 品味加权选择 ──
        taste = self.internal.taste_profile
        fruitful_domains = taste.get("fruitful_domains", {})
        fruitful_vars = taste.get("fruitful_variables", {})

        # ── 聚焦偏置 ──
        focus_vars = set()
        focus_domains = set()
        try:
            from meta_cognition.research_directions import bias_by_focus
            fb = bias_by_focus()
            if fb.get("active"):
                focus_vars = set(fb.get("key_variables", []))
                focus_domains = set(fb.get("key_domains", []))
        except Exception:
            pass

        def taste_score(issue: Dict) -> float:
            base = 1.0
            # 领域加分
            for field in [issue.get("domain_a", ""), issue.get("domain_b", ""),
                          issue.get("scale_a", ""), issue.get("scale_b", "")]:
                if field in fruitful_domains:
                    base += 0.3 * fruitful_domains[field]
                if field in focus_domains:
                    base += 1.0  # 聚焦域强加分
            # 变量加分
            for var in issue.get("overlap", []):
                if var in fruitful_vars:
                    base += 0.2 * fruitful_vars[var]
                if var in focus_vars:
                    base += 1.5  # 聚焦变量强加分
            return base

        scores = [taste_score(c) for c in candidates]
        total_score = sum(scores)
        # 加权随机
        r = random.random() * total_score
        cumulative = 0
        issue = candidates[-1]
        for c, s in zip(candidates, scores):
            cumulative += s
            if r <= cumulative:
                issue = c
                break

        question = issue.get("question", "")
        interesting = total > 0
        skipped = len(all_issues) - len(candidates)

        if verbose and interesting:
            cooldown_note = f" (skipped {skipped} in cooldown)" if skipped else ""
            print(f"\n  💡 {question}{cooldown_note}")

        return {
            "interesting": interesting,
            "dissonance_count": total,
            "type": "dissonance",
            "question": question[:200],
            "issue_law_a": issue.get("law_a", ""),
            "issue_law_b": issue.get("law_b", ""),
            "issue_overlap": issue.get("overlap", []),
            "issue_type": issue.get("type", ""),
            "candidates_available": len(candidates),
            "candidates_skipped": skipped,
        }

    # ═══ 模块: 前沿探索 ═══

    def _think_frontier(self, verbose: bool) -> Dict:
        """从前沿地图中选最有希望的方向探索。"""
        from meta_cognition.frontier import FrontierMap

        fm = FrontierMap()
        fm.build()
        top = fm.top_frontiers(5)

        if not top:
            return {"interesting": False, "dissonance_count": 0, "type": "frontier"}

        # 按类型加权: 尺度裂缝 > 稀疏区 > 断头路
        type_weights = {"scale_gap": 3.0, "sparse_zone": 2.0, "dead_end": 1.0}

        # 聚焦偏置: 涉及聚焦变量的前沿获得更高权重
        focus_vars = set()
        try:
            from meta_cognition.research_directions import bias_by_focus
            fb = bias_by_focus()
            if fb.get("active"):
                focus_vars = set(fb.get("key_variables", []))
        except Exception:
            pass

        scores = []
        for f in top:
            s = f["score"] * type_weights.get(f["type"], 1.0)
            var = f.get("variable", "")
            if var in focus_vars:
                s *= 3.0  # 聚焦变量前沿权重×3
            scores.append(s)
        total_score = sum(scores)
        r = random.random() * total_score
        cumulative = 0
        chosen = top[-1]
        for f, s in zip(top, scores):
            cumulative += s
            if r <= cumulative:
                chosen = f
                break

        ftype = chosen["type"]
        interesting = True

        if verbose:
            if ftype == "sparse_zone":
                var = chosen["variable"]
                absent = chosen["domains_absent"]
                print(f"\n  🗺️  sparse: {var} 缺席 {absent}")
            elif ftype == "scale_gap":
                print(f"\n  ⚡ scale gap: {chosen['scale_a']}↔{chosen['scale_b']} {chosen['variable']}")
            elif ftype == "dead_end":
                print(f"\n  🛑 dead end: {chosen['start_variable']}→{chosen['dead_variable']} [d={chosen['depth']}]")

        return {
            "interesting": interesting,
            "dissonance_count": 0,
            "type": "frontier",
            "frontier_type": ftype,
            "frontier_data": chosen,
        }

    # ═══ 模块: 结构联想 ═══

    def _think_structure(self, verbose: bool) -> Dict:
        """思考: 有没有新的同构结构?"""
        before = len(discovery.groups)
        discovery.scan()
        after = len(discovery.groups)

        new_groups = after - before
        interesting = new_groups > 0

        if verbose and interesting:
            print(f"\n  🔗 {new_groups} new structural groups found!")

        return {
            "interesting": interesting,
            "dissonance_count": 0,
            "type": "structure",
            "new_groups": new_groups,
        }

    # ═══ 模块: 联想 ═══

    def _think_associate(self, verbose: bool) -> Dict:
        """思考: 因果链类比 — 发现跨域结构同构"""
        from creative.causal_analogy import find_causal_analogies

        analogies = find_causal_analogies(max_chains=10, min_similarity=0.5)
        interesting = len(analogies) > 0

        if verbose and interesting:
            top = analogies[0]
            print(f"\n  🔗 [{top['similarity']:.0%}] {top['chain_a_start']} ↔ {top['chain_b_start']}")
            print(f"     {top['insight'][:100]}")

        return {
            "interesting": interesting,
            "dissonance_count": 0,
            "type": "analogy",
            "analogies": analogies[:3],
            "count": len(analogies),
        }

    # ═══ 模块: 反思 ═══

    def _think_reflect(self, verbose: bool) -> Dict:
        """思考: 盘点已有知识, 找最值得深入的方向"""
        top_laws = values.top("law", 3)
        top_modules = values.top("module", 3)

        interesting = len(top_laws) > 0

        if verbose and interesting:
            names = [name for name, _, _ in top_laws[:2]]
            print(f"\n  🧠 Most salient: {', '.join(names)}")

        return {
            "interesting": interesting,
            "dissonance_count": 0,
            "type": "reflect",
            "top_laws": [name for name, _, _ in top_laws],
        }

    # ═══ 学习: 从想法中提取知识 ═══

    def _learn_from(self, result: Dict, llm_bridge=None, verbose: bool = True) -> List[str]:
        """
        从有趣的发现中学习。

        dissonance → chain (0 token) → learn_from_chain (0 token)
                     → 如果无产出且 LLM 可用 → auto_learn (1 API call)
        associate → 标记同构关系
        structure → 新同构组入库
        reflect   → 标记重点领域
        """
        learned = []
        rtype = result.get("type", "")

        if rtype == "dissonance":
            # ── 零 token 路径: chain → learn_from_chain ──
            overlap_vars = result.get("issue_overlap", [])
            law_a_name = result.get("issue_law_a", "")
            law_b_name = result.get("issue_law_b", "")

            # 如果 issue 本身没有 overlap (如 scale boundary),
            # 从定律库查找两条定律的共享变量
            if not overlap_vars:
                if law_a_name and law_b_name:
                    from physics.laws import library
                    vars_a, vars_b = set(), set()
                    for law in library.list_all():
                        if law.name == law_a_name:
                            vars_a = set(law.inputs + law.outputs)
                        if law.name == law_b_name:
                            vars_b = set(law.inputs + law.outputs)
                    overlap_vars = sorted(vars_a & vars_b)

            chain_learned = []
            best_chain = []
            all_failed_vars = []

            if overlap_vars:
                from inference.counterfactual_chain import propagate
                from session.auto_learn import learn_from_chain

                for var in overlap_vars[:3]:  # 最多试 3 个重叠变量
                    chain = propagate(var, "变化", max_depth=5)
                    if not chain or "error" in chain[0]:
                        all_failed_vars.append(var)
                        continue
                    r = learn_from_chain(chain)
                    if r.get("success"):
                        chain_learned.extend(r.get("learned", []))
                        if len(chain) > len(best_chain):
                            best_chain = chain
                        if verbose:
                            print(f"     [0 token] chain discovered: {r['learned']}")
                    elif r.get("blocked_by_tier"):
                        # 发现了但被层级保护阻止
                        blocked = [l for l in r.get("learned", []) if "[blocked:" in str(l)]
                        if verbose and blocked:
                            print(f"     [blocked:tier{r.get('max_chain_tier',3)}] 发现但未入库: {blocked}")
                        # ── 多层对比: 探索链 vs 公理链 ──
                        if var:
                            from inference.counterfactual_chain import propagate_tiered, format_tiered_comparison
                            tiered = propagate_tiered(var, max_depth=5)
                            score = tiered.get("validation_score", 0)
                            convs = tiered.get("convergences", [])
                            if convs and verbose:
                                print(f"     [tiered] validation_score={score} convergences={[c['variable'] for c in convs]}")
                            if score >= 0.3:
                                result["tiered_validation"] = score
                                result["tiered_convergences"] = [c["variable"] for c in convs]

                            # ── 升级检查: 连续高分 → 提升置信层级 ──
                            if score >= 0.7:
                                self._maybe_upgrade_tier(blocked, score)
                    else:
                        all_failed_vars.append(var)

                if chain_learned:
                    learned.extend(chain_learned)
                    # 计算显著性
                    sig_info = self._compute_significance(
                        chain_learned, best_chain, law_a_name, law_b_name
                    )
                    result["significance"] = sig_info["score"]
                    result["sig_reason"] = sig_info["reason"]
                    result["domains_involved"] = sig_info["domains"]
                    result["variables_involved"] = sig_info["variables"]
                    result["chain_depth"] = max(
                        (s.get("depth", 0) for s in best_chain), default=0
                    )

            # ── 记录失败: 没产出的变量记入冷却 ──
            if not chain_learned and all_failed_vars:
                for var in all_failed_vars:
                    self.internal.record_failure(law_a_name, law_b_name, var)
            elif not chain_learned and overlap_vars:
                # chain 跑了但没发现: 也记录
                for var in overlap_vars[:3]:
                    self.internal.record_failure(law_a_name, law_b_name, var)

            # ── LLM 回退: 只有零 token 路径无产出时才调用 ──
            if not learned and llm_bridge and llm_bridge.is_available():
                question = result.get("question", "")
                if question and verbose:
                    print(f"     [1 API call] asking LLM about: {question[:60]}...")
                try:
                    from session.auto_learn import auto_learn
                    class FakeAgent:
                        llm = llm_bridge
                    r = auto_learn(FakeAgent(), question, question)
                    if r.get("success"):
                        learned.extend(r.get("learned", []))
                except Exception:
                    pass

        elif rtype == "frontier":
            # ── 从 frontier 方向探索: chain + learn_from_chain ──
            ftype = result.get("frontier_type", "")
            fdata = result.get("frontier_data", {})

            from inference.counterfactual_chain import propagate
            from session.auto_learn import learn_from_chain

            chain_learned = []
            best_chain = []

            if ftype == "sparse_zone":
                var = fdata.get("variable", "")
                if var:
                    chain = propagate(var, "变化", max_depth=5)
                    if chain and "error" not in chain[0]:
                        r = learn_from_chain(chain)
                        if r.get("success"):
                            chain_learned = r.get("learned", [])
                            best_chain = chain

            elif ftype == "scale_gap":
                var = fdata.get("variable", "")
                if var:
                    chain = propagate(var, "变化", max_depth=5)
                    if chain and "error" not in chain[0]:
                        r = learn_from_chain(chain)
                        if r.get("success"):
                            chain_learned = r.get("learned", [])
                            best_chain = chain

            elif ftype == "dead_end":
                dead_var = fdata.get("dead_variable", "")
                start_var = fdata.get("start_variable", "")
                if dead_var:
                    chain = propagate(dead_var, "变化", max_depth=3)
                    if chain and "error" not in chain[0]:
                        r = learn_from_chain(chain)
                        if r.get("success"):
                            chain_learned = r.get("learned", [])
                            best_chain = chain
                if not chain_learned and start_var:
                    chain = propagate(start_var, "变化", max_depth=5)
                    if chain and "error" not in chain[0]:
                        r = learn_from_chain(chain)
                        if r.get("success"):
                            chain_learned = r.get("learned", [])
                            best_chain = chain

            if chain_learned:
                learned.extend(chain_learned)
                if verbose:
                    print(f"     [0 token] frontier discovered: {chain_learned}")
                sig_info = self._compute_significance(
                    chain_learned, best_chain,
                    fdata.get("variable", ""), fdata.get("dead_variable", "")
                )
                result["significance"] = sig_info["score"]
                result["sig_reason"] = sig_info["reason"]
                result["domains_involved"] = sig_info["domains"]
                result["variables_involved"] = sig_info["variables"]
            else:
                if verbose:
                    print(f"     [0 token] frontier explored, no new structure found")

        elif rtype in ("analogy", "associate"):
            analogies = result.get("analogies", [])
            if analogies:
                for a in analogies[:3]:
                    learned.append(f"analogy:{a['chain_a_start']}↔{a['chain_b_start']}({a['similarity']:.0%})")
                    if verbose:
                        print(f"     [analogy] {a['chain_a_start']} ↔ {a['chain_b_start']} ({a['similarity']:.0%})")

        elif rtype == "structure":
            learned.append(f"groups:{len(discovery.groups)}")

        elif rtype == "reflect":
            for name in result.get("top_laws", [])[:2]:
                values.verify(name, "law")
                learned.append(f"verify:{name}")

        return learned

    def _compute_significance(self, learned_names: List[str], chain_data: List[Dict],
                              law_a: str, law_b: str) -> Dict:
        """评估一次发现的意义。返回 {score, reason, domains, variables}"""
        if not learned_names or not chain_data:
            return {"score": 0, "reason": "no discovery", "domains": [], "variables": []}

        score = 0.0
        reasons = []
        domains_involved = set()
        variables_involved = set()

        # 跨域加分
        for step in chain_data:
            d = step.get("domain", "")
            if d and d not in ("unknown", "auto"):
                domains_involved.add(d)
            for field in ["variable", "effect_variable"]:
                v = step.get(field, "")
                if v:
                    variables_involved.add(v)

        n_domains = len(domains_involved)
        if n_domains >= 3:
            score += 1.5
            reasons.append(f"spans {n_domains} domains")
        elif n_domains >= 2:
            score += 0.8
            reasons.append(f"connects {n_domains} domains")

        # 汇聚路径加分 (Convergence 类发现)
        conv_count = sum(1 for name in learned_names if "Convergence" in name)
        if conv_count > 0:
            score += conv_count * 1.0
            reasons.append(f"{conv_count} convergences found")

        # 链深度加分
        max_depth = max((s.get("depth", 0) for s in chain_data), default=0)
        if max_depth >= 4:
            score += 0.6
            reasons.append(f"deep chain (depth {max_depth})")
        elif max_depth >= 2:
            score += 0.3

        # 新颖性加分: 检查是否与已有发现重复
        from physics.laws import library
        existing_names = {law.name for law in library.list_all()}
        truly_new = [n for n in learned_names if n not in existing_names]
        if truly_new:
            score += 0.5
            reasons.append("novel pattern")

        # 涉及基础变量加分 (mass, energy, time 等)
        fundamental = {"mass", "energy", "time", "force", "temperature", "velocity"}
        fundamental_hit = variables_involved & fundamental
        if fundamental_hit:
            score += 0.4
            reasons.append(f"involves fundamental vars: {sorted(fundamental_hit)}")

        return {
            "score": round(score, 1),
            "reason": "; ".join(reasons) if reasons else "basic discovery",
            "domains": sorted(domains_involved),
            "variables": sorted(variables_involved),
        }

    def trend_report(self) -> str:
        """生成趋势报告 — 品味进化、冷却状态"""
        s = self.internal
        lines = []

        history = s.discovery_history
        if len(history) >= 2:
            domains = s.taste_profile.get("fruitful_domains", {})
            if domains:
                top = sorted(domains.items(), key=lambda x: x[1], reverse=True)[:3]
                lines.append(f"  品味偏好: {dict(top)}")

        failed = s.failed_tensions
        if failed:
            now = time.time()
            expiring = sum(1 for v in failed.values()
                          if 0 < (s.FAIL_COOLDOWN - (now - v)) < 600)
            lines.append(f"  冷却中: {len(failed)} 条死胡同, {expiring} 条即将过期")

        lines.append(f"  累计: {s.thought_count} 次思考, {s.total_discoveries} 条发现")

        return "\n".join(lines) if lines else "  (首次运行, 趋势数据不足)"

    # ── 升级机制: 探索性定律通过验证后自动升层 ──

    # key: law_name, value: {count, last_score, last_upgrade}
    _upgrade_tracker: Dict[str, Dict] = {}

    def _maybe_upgrade_tier(self, blocked_names: List[str], score: float):
        """如果被阻断的发现连续高分通过验证, 注册为严肃假说 (tier 3)"""
        from physics.laws import library, PhysicsLaw, ConstraintType

        for name in blocked_names:
            clean = name.split("]")[-1] if "]" in name else name
            if not clean:
                continue

            tracker = self._upgrade_tracker.setdefault(clean, {
                "validation_count": 0, "best_score": 0.0
            })
            tracker["validation_count"] += 1
            tracker["best_score"] = max(tracker["best_score"], score)

            if tracker["validation_count"] >= 3 and tracker["best_score"] >= 0.7:
                # 检查是否已入库
                exists = any(law.name == clean for law in library.list_all())
                if exists:
                    # 已存在: 升级层级
                    for law in library.list_all():
                        if law.name == clean and law.confidence_tier >= 3:
                            old_tier = law.confidence_tier
                            law.confidence_tier = max(2, old_tier - 1)
                            print(f"\n  ⬆️  UPGRADE: {clean} tier {old_tier} → tier {law.confidence_tier}")
                            break
                else:
                    # 不存在: 作为假说注册
                    # 从 chain 数据重建候选定律
                    print(f"\n  ⬆️  PROMOTE: {clean} — 通过验证, 注册为 tier 3 假说")
                    print(f"     validation_count={tracker['validation_count']} score={tracker['best_score']:.2f}")
                    try:
                        # 创建最小假说定律
                        law = PhysicsLaw(
                            name=clean,
                            domain="unification",
                            latex="",
                            inputs=["kinetic_energy", "energy"],
                            outputs=["geodesic_path"],
                            constraint_type=ConstraintType.SCM_EQUATION,
                            formula=lambda *args: 0.0,
                            causal_direction=[("kinetic_energy", "geodesic_path"),
                                            ("energy", "geodesic_path")],
                            forbidden_directions=[],
                        )
                        law._auto_learned = True
                        law._chain_discovered = True
                        law._discovery_note = (
                            f"Promoted from tier 4 after {tracker['validation_count']} "
                            f"validations (score={tracker['best_score']:.2f}). "
                            f"Convergence of kinetic_energy and energy on geodesic_path "
                            f"confirmed consistent with axiom chain."
                        )
                        law.confidence_tier = 3
                        library.register(law)
                        from session.auto_learn import _save_auto_laws
                        _save_auto_laws()
                        print(f"     Registered: {law.inputs} → {law.outputs} [tier 3]")
                    except Exception as e:
                        print(f"     Failed to register: {e}")

                tracker["validation_count"] = 0

    def _report_discovery(self, result: Dict):
        """向用户报告有趣的发现"""
        rtype = result.get("type", "")
        if rtype == "dissonance" or rtype == "frontier":
            sig = result.get("significance", 0)
            sig_reason = result.get("sig_reason", "")
            depth = result.get("chain_depth", 0)
            if sig >= 2.0:
                stars = "★★★"
            elif sig >= 1.0:
                stars = "★★"
            else:
                stars = "★"

            if rtype == "dissonance":
                print(f"    研究问题: {result.get('question', '')[:120]}")
            elif rtype == "frontier":
                ftype = result.get("frontier_type", "")
                fdata = result.get("frontier_data", {})
                if ftype == "sparse_zone":
                    print(f"    前沿: {fdata.get('variable','?')} 缺席 {fdata.get('domains_absent',[])}")
                elif ftype == "scale_gap":
                    print(f"    前沿: {fdata.get('scale_a','?')}↔{fdata.get('scale_b','?')} {fdata.get('variable','?')}")
                elif ftype == "dead_end":
                    print(f"    前沿: {fdata.get('start_variable','?')}→{fdata.get('dead_variable','?')}")

            if result.get("learned"):
                print(f"    发现: {result.get('learned', [])}")
                if sig > 0:
                    print(f"    显著性: {stars} ({sig}) depth={depth} — {sig_reason}")
                # ── 哲学透镜 ──
                from meta_cognition.lenses import match_for_context, explain_discovery
                domains_involved = result.get("domains_involved", [])
                variables_involved = result.get("variables_involved", [])
                learned = result.get("learned", [])
                lens_text = explain_discovery(learned, variables_involved, domains_involved)
                if lens_text:
                    print(lens_text)
        elif rtype == "structure":
            print(f"    新同构组: {result.get('new_groups', 0)}")
        elif rtype == "associate":
            mods = result.get("modules", [])
            print(f"    跨域同构: {mods[0] if mods else '?'} ↔ {mods[1] if len(mods)>1 else '?'}")
