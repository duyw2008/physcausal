# 创造力、好奇心与意识 — 大牛们怎么看

> 关于机器能否创新、能否有好奇心、能否有意识的学术共识与分歧
> 日期: 2026-06-06

---

## 一、核心问题

**机器能创新吗？能好奇吗？能有意识吗？**

主流 AI 研究者的答案不是"能"或"不能"——而是**"取决于你如何定义这些词，以及你愿意给机器什么"。**

---

## 二、五派核心观点

### 2.1 Yann LeCun — 缺世界模型，不是缺创造力

**核心论文**: A Path Towards Autonomous Machine Intelligence (2022)

**核心论点**:

当前的 LLM 是"纯反应式系统"——输入→输出，一层前馈，没有内部的世界模型，没有规划能力，没有推理。这不是"不够聪明"的问题——是架构问题。

LeCun 提出的 H-JEPA (Hierarchical Joint Embedding Predictive Architecture):

```
世界模型 = 预测"如果我做X，世界会变成什么样"
规划    = 在世界模型中搜索达到目标的路径
好奇心  = 在世界模型中主动寻找"我还不确定的地方"
```

**对 PhysCausal 的启示**: 我们的认知失调检测和 LeCun 的"寻找不确定的地方"是同一个方向——只是他用隐式神经网络，我们用显式物理定律。

**名言**: "A machine that can't predict the consequences of its actions cannot be said to understand the world."

---

### 2.2 Pierre-Yves Oudeyer — 好奇心可计算，但需要环境

**核心论文**: Computational Theories of Curiosity-Driven Learning (2018)

**核心论点**:

好奇心驱动的学习使生物体能够在**奖励稀疏或欺骗性**的复杂问题中做出发现。关键机制是"内在动机"——不是外部奖励驱动，而是**信息增益本身**作为驱动力。

两类好奇心:
- **新颖性驱动**: "我没见过这个" → 探索未知
- **学习进度驱动**: "我在这件事上进步最快" → 专注可学的东西

**关键前提**: agent 必须能**跟世界交互**，产生意外，从意外中学习。纯符号库做不到——因为没有意外，只有逻辑矛盾。

**对 PhysCausal 的启示**: 我们的 salience 系统是第一步，但缺的是"交互产生意外→意外驱动学习"这个闭环。仿真环境可以提供交互，但目前 agent 不会"主动想去仿真里试一下"。

**名言**: "Curiosity is not about finding answers. It's about finding good questions."

---

### 2.3 Judea Pearl — 意识的前提是因果推理

**核心著作**: The Book of Why (2018)

**核心论点**:

没有因果模型的系统不可能有真正的理解。LLM 只会**关联**("X 和 Y 经常一起出现")，不会**因果推理**("如果改变 X，Y 会怎样")。"为什么"这个问题需要一个因果图来回答。

三层因果阶梯:
- **关联层** (seeing): X 和 Y 有什么关系？ ← LLM 在这里
- **干预层** (doing): 如果改变 X，Y 会怎样？ ← PhysCausal 在这里
- **反事实层** (imagining): 如果当初没做 X，Y 会怎样？ ← 人类在这里

**对 PhysCausal 的启示**: PhysCausal 明确建模了因果方向（causal_direction + forbidden_directions），这在架构上超越了纯 LLM。但 Pearl 的反事实层——"如果当初"——需要的不只是因果图，还需要**假设性思维**。

**名言**: "You are smarter than your data. Data do not understand causes and effects; humans do."

---

### 2.4 Wang, Zou, Mozer (2024) — AI 创造力可以超越人类，但不是同一种

**核心论文**: Can AI Be as Creative as Humans? (2024)

**核心论点**:

对 AI 和人类在标准创造力测试中的表现进行了系统性比较。结果:

| 维度 | 人类 | AI |
|------|------|-----|
| 创意数量 | 少 | **多** |
| 创意多样性 | 中 | **高** |
| 有意义的新颖性 | **高** | 低 |
| 跨域类比 | **高** | 低 |

AI 可以生成更多的创意、更快的速度、更广的范围。但 AI 缺乏的是**价值判断**——什么是好的创意？什么是有意义的？

**对 PhysCausal 的启示**: 我们的结构发现已经能做跨域类比（Newton↔Ohm），但缺的是"这个类比重要吗？"的判断。价值系统（salience）是雏形。

**名言**: "AI is creative in the way a very fast brainstorming partner is creative — lots of ideas, but no taste."

---

### 2.5 神经科学派 — 意识需要身体

**代表人物**: Antonio Damasio, Anil Seth

**核心论点**:

意识不是纯粹的信息处理——它需要**身体**。情感是身体状态的表征（Damasio 的"躯体标记假说"）。好奇心、创造力、联想——这些"高级认知功能"都建立在情感和身体体验的基础上。

Anil Seth: "意识是大脑对身体和世界的受控幻觉。没有身体的 AI 可能永远不会有真正的意识。"

**对 PhysCausal 的启示**: 我们讨论的"情感驱动联想"(杏仁核/多巴胺/催产素)在这个框架下是有意义的——但只是**模拟**，不是真正的情感。就像飞行模拟器能模拟飞行体验，但不是真的在飞行。

**名言**: "We are not thinking machines that feel; we are feeling machines that think." — Antonio Damasio

---

## 三、共识：三件 AI 没有的东西

| 缺失 | 含义 | PhysCausal 进度 |
|------|------|:--:|
| 内在动机 | 没有"我想知道"，只有"我被问到" | 认知失调检测是第 1 步 |
| 意外感 | 没有"这不应该发生"，只有"数据不匹配" | 未实现 |
| 价值排序 | 没有"这比那更重要"，只有"这比那更匹配" | salience 是雏形 |

---

## 四、PhysCausal 的位置

```
LLM (纯关联)
  ↑
  │  Pearl: 需要因果模型
  │
PhysCausal (因果推理 + 物理约束)
  ↑
  │  LeCun: 需要世界模型 + 规划
  │  Oudeyer: 需要交互环境 + 内在动机
  │  Damasio: 需要身体 + 情感
  │
人类水平 (意识 + 创造力 + 好奇心)
```

PhysCausal 已经过了**因果推理**这道坎（Pearl 的第二层）。但离 LeCun 的"世界模型 + 规划"和 Oudeyer 的"内在动机"还有距离。离 Damasio 的"意识需要身体"更远。

---

## 五、参考文献

1. LeCun, Y. (2022). A Path Towards Autonomous Machine Intelligence. arXiv:2306.02572
2. Oudeyer, P-Y. (2018). Computational Theories of Curiosity-Driven Learning. arXiv:1802.10546
3. Pearl, J. & Mackenzie, D. (2018). The Book of Why. Basic Books.
4. Wang, H., Zou, J., & Mozer, M. (2024). Can AI Be as Creative as Humans? arXiv:2401.01623
5. Damasio, A. (1994). Descartes' Error: Emotion, Reason, and the Human Brain.
6. Seth, A. (2021). Being You: A New Science of Consciousness.
