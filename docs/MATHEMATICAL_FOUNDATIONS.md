# 数学与算法基础

> PhysCausal 中所有数学模型的形式化定义

---

## 一、因果推断

### 1.1 结构因果模型 (SCM)

**定义**: 一个 SCM 是一个四元组 $\langle U, V, F, P(u) \rangle$

- $U$: 外生变量 (不可观测的噪声/个体差异)
- $V$: 内生变量 (可观测)
- $F$: 结构方程集合 $\{f_i\}_{i=1}^{|V|}$，每个 $v_i = f_i(pa(v_i), u_i)$
- $P(u)$: 外生变量的分布

**关键性质**: 结构方程是**自主的**——干预一个变量不影响其他方程。

---

### 1.2 do-演算 (do-calculus)

**干预**: $do(X=x)$ 切断指向 $X$ 的所有箭头，强制 $X=x$。

**三条规则** (Pearl, 1995):

**Rule 1** (忽略观测):
$$P(y|do(x), z, w) = P(y|do(x), w) \quad \text{if } Y \perp\!\!\!\perp Z | X, W \text{ in } G_{\overline{X}}$$

**Rule 2** (行动/观测交换):
$$P(y|do(x), do(z), w) = P(y|do(x), z, w) \quad \text{if } Y \perp\!\!\!\perp Z | X, W \text{ in } G_{\overline{X}\underline{Z}}$$

**Rule 3** (忽略行动):
$$P(y|do(x), do(z), w) = P(y|do(x), w) \quad \text{if } Y \perp\!\!\!\perp Z | X, W \text{ in } G_{\overline{XZ(W)}}$$

**识别策略**:
- 后门准则: 调整 $pa(T)$ 或其子集满足后门条件
- 前门准则: 当后门不可用时，通过中介变量
- 工具变量: 当两者都不可用时
- 穷举搜索: 在所有可能调整集中找满足 Rule 1-3 的

---

### 1.3 反事实推理 — Pearl 三步法

**Step 1 — Abduction (溯因)**:
给定观测证据 $E=e$，更新外生变量分布:
$$P(u|E=e)$$

**Step 2 — Action (干预)**:
修改 SCM，施加反事实干预 $do(X=x)$:
$$M \rightarrow M_x$$

**Step 3 — Prediction (预测)**:
在修改后的模型中，使用更新后的 $P(u|E=e)$ 计算:
$$P(Y_{x}|E=e)$$

**示例**: 张三上了大学 (Education=16)，收入 3 万。如果没上大学 (Education=12) 会怎样？
1. Abduction: $U_{\text{张三}} = 3\text{万} - \beta \cdot 16$
2. Action: $do(\text{Education}=12)$
3. Prediction: $\text{Income}_{cf} = \beta \cdot 12 + U_{\text{张三}}$

---

### 1.4 因果发现

**PC 算法**:

输入: 数据 $D$，所有变量 $V$
输出: CPDAG (部分有向无环图)

算法:
1. 从完全无向图开始
2. 对每对变量 $(X,Y)$，搜索条件集 $S$ 使得 $X \perp\!\!\!\perp Y | S$
3. 如果找到这样的 $S$，删除边 $X-Y$
4. V-structure 定向: 如果 $X-Z-Y$ 但 $X \not\perp Y | Z$，则 $X \rightarrow Z \leftarrow Y$
5. Meek 规则传播方向

**因果方向判定 — Markov 等价类**:

三条规则产生相同条件独立性模式的不同 DAG:
- Fork: $X \leftarrow Z \rightarrow Y$ — $X \perp\!\!\!\perp Y | Z$
- Chain: $X \rightarrow M \rightarrow Y$ — $X \perp\!\!\!\perp Y | M$
- Collider: $X \rightarrow Z \leftarrow Y$ — $X \perp\!\!\!\perp Y$ (无条件), $X \not\perp\!\!\!\perp Y | Z$

Fork 和 Chain 的等价类中，**纯观测数据无法区分因果方向**。需要:
- 干预实验
- 领域知识 (物理定律)
- 熵增方向 (因果方向 = 熵增方向)

---

### 1.5 因果中介分析

**自然直接效应 (NDE)**:
$$NDE = E[Y(1, M(0)) - Y(0, M(0))]$$

**自然间接效应 (NIE)**:
$$NIE = E[Y(1, M(1)) - Y(1, M(0))]$$

**总效应分解**:
$$TE = NDE + NIE$$

---

### 1.6 ATE 估计

**平均处理效应 (ATE)**:
$$ATE = E[Y(1) - Y(0)]$$

估计器:
- 线性回归: $\hat{ATE} = \hat{\beta}_{T}$
- 分层: 在每个层次内加权平均
- 匹配: 倾向得分匹配
- 双重稳健 (DR): 结合倾向得分 + 结果模型
- 逆概率加权 (IPW): $w_i = T_i/\hat{e}_i + (1-T_i)/(1-\hat{e}_i)$

**标准误**: 自举法 (Bootstrap) 估计

---

### 1.7 敏感性分析

**E-value** (VanderWeele & Ding, 2017):

$$E\text{-value} = RR_{obs} + \sqrt{RR_{obs}(RR_{obs} - 1)}$$

其中 $RR_{obs}$ 是观测风险比。E-value 度量: 需要一个未观测混淆变量有多强才能将观测效应归零。

**Rosenbaum 界限**:

$$\Gamma \geq \frac{ATE}{SE}$$

$\Gamma$ 阈值: 未观测混淆能改变优势比的最小倍数。

---

## 二、贝叶斯推断

### 2.1 结构后验 P(G|D)

**目标**: 不是选一个最优 DAG，而是给每个候选 DAG 一个后验概率。

$$P(G|D) \propto P(D|G) \cdot P(G)$$

- 先验 $P(G)$: 物理约束 (禁止边 = 0 概率) + 稀疏偏好
- 似然 $P(D|G)$: BIC 得分

**BIC 得分**:
$$BIC = -2\ln(L) + k\ln(n)$$

其中 $L$ 为似然，$k$ 为参数数量，$n$ 为样本数。BIC 越小 (越负) 越好。

**Bootstrap 近似**:
1. 数据重采样 $B$ 次
2. 每次运行 PC/FCI 算法
3. 边置信度 = 边在 $B$ 次采样中出现的频率

---

### 2.2 参数后验 P(θ|G,D)

$$P(\theta|G,D) \propto P(D|G,\theta) \cdot P(\theta|G)$$

**共轭先验**: 当似然是高斯分布时，使用 Normal-Inverse-Gamma 先验:
$$\beta|\sigma^2 \sim N(\mu_0, \sigma^2\Sigma_0)$$
$$\sigma^2 \sim IG(a_0, b_0)$$

**物理先验注入**:
$$F=ma \Rightarrow \beta_{a, F} \sim N(1/m, \sigma^2_{\text{small}})$$
物理定律作为强先验——均值固定，方差极小。

---

### 2.3 主动实验设计

**信息价值 (VOI)**:

$$VOI(X) = H(G|D) - E[H(G|D \cup do(X=x))]$$

即: 干预 $X$ 能减少多少图分布的熵？最大 $VOI$ 的变量是最该做实验的。

**实验计划**:
1. 选 VOI 最大的变量
2. 设值 (按类型取典型值)
3. 收集干预后数据
4. 更新 $P(G|D)$
5. 重复直到所有边置信度 > 阈值

---

## 三、谱方法

### 3.1 主成分分析 (PCA)

**输入**: 数据矩阵 $X \in \mathbb{R}^{n \times d}$
**输出**: 主成分方向 $v_1, ..., v_d$

$$C = \frac{1}{n-1}X^TX$$
$$C v_i = \lambda_i v_i$$

保留 $k$ 个主成分 ($k$ 由累积方差解释率 $\geq 95\%$ 决定)。

**有效秩**:
$$\text{eff\_rank} = \exp\left(-\sum_i p_i \ln p_i\right), \quad p_i = \frac{\lambda_i}{\sum_j \lambda_j}$$

---

### 3.2 奇异值分解 (SVD)

$$X = U\Sigma V^T$$

- $U$: 左奇异向量 (行空间)
- $\Sigma$: 奇异值 (重要性)
- $V$: 右奇异向量 (列空间)

---

### 3.3 谱图论

**图拉普拉斯**:
$$L = D - A$$

其中 $D$ 为度矩阵, $A$ 为邻接矩阵。

**代数连通度**: $L$ 的第二个最小特征值 — 图的连通性度量。

**谱聚类**: $L$ 的特征向量 → k-means → 图分区。

---

### 3.4 Koopman 算子

将非线性动力学映射到线性空间:
$$\mathcal{K}g(x) = g(f(x))$$

在观测函数 $\psi(x)$ 下，动力学近似为:
$$\psi(x_{t+1}) \approx K \cdot \psi(x_t)$$

$K$ 的特征值和特征向量揭示: 不变子空间 + 频率/增长率。

---

## 四、信息论

### 4.1 Shannon 熵

$$H(X) = -\sum_x p(x) \log p(x)$$

联合熵: $H(X,Y) = -\sum_{x,y} p(x,y) \log p(x,y)$

条件熵: $H(Y|X) = H(X,Y) - H(X)$

---

### 4.2 互信息

$$I(X;Y) = H(X) + H(Y) - H(X,Y)$$

$$= \sum_{x,y} p(x,y) \log\frac{p(x,y)}{p(x)p(y)}$$

在因果推断中: 条件独立性检验 $X \perp\!\!\!\perp Y | Z$ 等价于 $I(X;Y|Z) = 0$。

---

### 4.3 KL 散度

$$D_{KL}(P\|Q) = \sum_x P(x) \log\frac{P(x)}{Q(x)}$$

变分推断的核心: 最小化 $KL(q\|p_{posterior})$。

---

### 4.4 信息瓶颈

$$T^* = \arg\min_T I(T;X) - \beta \cdot I(T;Y)$$

$T$ 是 $X$ 的压缩表示，使得:
- $I(T;X)$ 尽量小 (压缩 = 丢弃不相关信息)
- $I(T;Y)$ 尽量大 (保留与 $Y$ 相关的信息)

这完全描述了感知层的工作: 扔掉噪声 (Low $I(T;X)$)，保留结构 (High $I(T;Y)$)。

---

### 4.5 最大熵原理 (Jaynes)

在满足约束 $\langle f_k(x) \rangle = c_k$ 的所有分布中，最大熵分布是:

$$p^*(x) = \frac{1}{Z} \exp\left(\sum_k \lambda_k f_k(x)\right)$$

当约束是均值和方差时 → 正态分布。
当约束只有均值时 → 指数分布。
当约束只有取值范围时 → 均匀分布。

---

### 4.6 Landauer 极限

获取 1 bit 信息的最小能量消耗:
$$E_{\min} = kT \ln 2 \approx 2.87 \times 10^{-21} \text{J/bit (室温)}$$

这是信息边界在经典物理中的表达——每一次测量 (获取信息) 至少消耗这么多能量。

---

### 4.7 传递熵

$$TE_{X \rightarrow Y} = I(X_{t}; Y_{t+1} | Y_t, Z_t)$$

时间序列中 $X$ 到 $Y$ 的因果信息流——Granger 因果的信息论版本。

---

## 五、元物理

### 5.1 最小作用量原理

$$S[q] = \int_{t_1}^{t_2} L(q, \dot{q}, t) dt$$

真实路径使作用量取极值:
$$\delta S = 0 \Rightarrow \frac{d}{dt}\frac{\partial L}{\partial \dot{q}} - \frac{\partial L}{\partial q} = 0$$

---

### 5.2 Noether 定理

每个连续对称性对应一个守恒量:
- 时间平移对称性 → 能量守恒
- 空间平移对称性 → 动量守恒
- 旋转对称性 → 角动量守恒

---

### 5.3 第二热力学定律

$$\Delta S_{\text{universe}} \geq 0$$

因果箭头: 原因 → 结果的熵总是增加的。

---

### 5.4 局域因果

类空间隔的事件不能有直接因果联系:
$$\Delta s^2 = c^2\Delta t^2 - \Delta x^2$$
只在 $\Delta s^2 \geq 0$ (类时间隔) 时才可能有因果联系。

---

### 5.5 信息边界

获取信息 = 可能性空间的投影:

| 尺度 | 表达 |
|------|------|
| 量子 | $\vert\psi\rangle \rightarrow \vert\phi_k\rangle$ (坍缩) |
| 经典 | $P(Y) \rightarrow P(Y\mid X=x)$ (条件化) |
| 因果 | $E[Y] \rightarrow E[Y\mid do(x)]$ (干预) |
| 信息 | $E_{\min} = kT\ln 2$ (Landauer) |

---

## 六、创造性联想

### 6.1 结构变异

**加权变异**: 不是均匀随机，而是在结构相容的邻域内加权采样。

变异算子:
- add_edge: 在类型兼容的节点对之间加边
- delete_edge: 删除置信度最低的边
- reverse_edge: 反转方向 (仅当不创建环)
- substitute_var: 替换变量 (保持类型)
- skeleton_transfer: 从骨架库实例化

---

### 6.2 三层过滤

**Tier 0 (硬杀)**: 物理定律 + 守恒律 + 局域因果 → 违反即丢弃

**Tier 1 (评分)**: BIC 得分 + 简洁性 (边越少越好)

**Tier 2 (筛选)**: 新颖性 — 和已知模块太像 → 不创新 → 丢弃

---

### 6.3 进化搜索

**模拟退火**:
$$T(g) = T_0 \cdot (T_{\text{end}}/T_0)^{g/G}$$

高温 → 大变异，探索空间
低温 → 小变异，精细搜索

**精英保留**: 前 20% 直接进入下一代

**锦标赛选择**: 随机选 2 个，分高者胜

---

### 6.4 组合泛化

每个模块有类型化接口:
$$\text{ModuleInterface} = (\text{Inputs}, \text{Outputs}, \text{Edges}, \text{TypeSignatures})$$

组合条件: $A$ 的输出类型 == $B$ 的输入类型

$$A \circ B = (\text{Inputs}_A \cup \text{Inputs}_B', \text{Outputs}_A \cup \text{Outputs}_B', \text{Edges}_A \cup \text{Edges}_B')$$

---

## 七、压缩与理解

### 7.1 Kolmogorov 复杂度

$$K(x) = \min\{|p| : U(p) = x\}$$

生成 $x$ 的最短程序长度。

### 7.2 Solomonoff 归纳

$$P(x) = \sum_{p: U(p) = x} 2^{-|p|}$$

在所有解释数据的程序中，最短的 (= 抓住了规律的) 权重最大。

### 7.3 Occam 剃刀

$$P(h|D) \propto P(D|h) \cdot 2^{-K(h)}$$

描述越短 → 先验越大 → 越可能是正确假说。
