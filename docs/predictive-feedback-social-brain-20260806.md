# Predictive Feedback + Social Brain (2026-08-06)

## Problem

Gen 3000+: 64% 概念节点孤立，均度 1.9，无髓鞘边（0 条边被 ≥2 细胞走过）。
细胞各走各的路，1 万细胞走出 1 万条单行道，没有共享高速公路。

根因：评分函数全是"个体奖励"（EIG 偏爱新奇、私有权重只记住自己的历史），
没有"集体奖励"——细胞之间没有社会性。

## Three Fixes

### 1. 预测反馈 (Predictive Feedback)

**人脑对应**：皮层向下输出预测，丘脑向上传偏差——预测编码环路。

**机制**：
- breathe 阶段：细胞从 A 走到 B 后，比较 A→B 的实际 s 值和 A 所有 outgoing 的平均预测 s
- Δs > 0.15 → 登记为 `reverse_candidate`
- sleep 阶段：合并累计 Δs，>0.25 触发 sympy derive(effect→cause)
- 成功 → 补反向边 (tier 1, axomatic 域防 pruning)
- 每次最多 5 条，去重防重复

**文件**：`evo_colony.py:_predictive_feedback`, `_step_neurons` (偏差检测)

**效果**：双向因果从 0 → 8 对（gen 3571），收敛趋势明显（Δs 递减）。

### 2. 多巴胺广播 (Dopamine Broadcast)

**人脑对应**：中脑多巴胺不是单播给找到食物的那个神经元——是广播给所有最近活跃的神经元。

**机制**：
- `_active_cohort`: 最近 200 个走过路的细胞（滑动窗口）
- 每代奖励增量的 15% 平均分给池子里所有细胞
- "你找到好东西，大家都沾光" → 细胞不用自己发现所有路径

**文件**：`evo_colony.py:_active_cohort`, `_step_neurons` (广播)

### 3. 人气梯度 + 髓鞘降阈 (Popularity Gradient + Myelin Threshold)

**人脑对应**：LTP——"一起放电，一起变强"；髓鞘化——高频使用的主干道被脂质包裹加速传导。

**机制**：
- `_popularity_map`: 每条边 0~1 人气值（被走过细胞数 / max(20, 最大人气)）
- 选边时 `eig *= 1 + pop × 2`（0→1x, 1→3x 平滑梯度）
- 髓鞘门槛 50→10：10 个细胞走过就进快车道（999x 直接跃迁）

**文件**：`evo_colony.py:_popularity_map`, `_myelin_set`; `evolvable_cell.py:_step_forward`

## Design Philosophy

"给容量不给方法" — 不硬编码"细胞应该走哪条路"。
人气梯度让热门路径自然吸引更多流量，但不强制。
多巴胺广播让发现行为受益于他人的探索，但不预设谁受益。
低髓鞘门槛让高速公路在流量充足时自然涌现，而非等待。

预测反馈是"一致性逼迫"的结构约束（对称性→双边），
社会脑是"共享信号"的动力学增强（LTP→人气）。
二者互补：反馈建骨架，社会填流量。

## Expected Effects

| 指标 | 修复前 | 预期 |
|------|:---:|:---:|
| edges ≥2 neurons | 276/3243 (8.5%) | ↑ |
| edges ≥5 neurons | 2/3243 | ↑ |
| 髓鞘快车道 | 0 | >0 |
| 孤立节点 | 64% | ↓ |
| 均度 | 1.9 | ↑ |
| 双向因果 | 8 | ↑ |
