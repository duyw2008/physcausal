"""
参数后验 — P(θ|G,D): SCM 参数的不确定性

给定因果图 G，结构方程参数 θ 的后验分布。
这是效应估计的不确定性量化基础。

核心:
  P(θ|G,D) ∝ P(D|G,θ) · P(θ|G)

  先验 P(θ|G):
    - 物理定律作为强先验: F=ma → β(Acceleration|Force) ~ N(1/m, σ²_small)
    - 无物理先验时: 弱信息先验 N(0, σ²_large)
    - 稀疏先验: Laplace(0, λ) → L1 正则化等价

  似然 P(D|G,θ):
    - 高斯: Y ~ N(f(X;θ), σ²)

  后验:
    - 共轭 (高斯先验 + 高斯似然): 解析解
    - 非共轭: MCMC (Metropolis-Hastings)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np


@dataclass
class ParameterPosterior:
    """SCM 参数后验"""
    variable: str                    # 响应变量
    parents: List[str]               # 父节点
    coefficients: Dict[str, Posterior]  # 系数名 → 后验分布
    noise_variance: Posterior        # 噪声方差的后验
    effective_sample_size: int


@dataclass
class Posterior:
    """单参数的后验分布"""
    name: str
    mean: float
    std: float
    ci_lower: float                  # 95% 可信区间下界
    ci_upper: float                  # 95% 可信区间上界
    prior_mean: Optional[float] = None
    prior_std: Optional[float] = None
    significance: float = 1.0        # P(θ≠0|D) — 后验包含 0 的概率


class ParameterInference:
    """
    参数推断 — P(θ|G,D)

    两种模式:
      conjugate:  共轭先验 (高斯-逆Gamma) — 解析解, 快
      mcmc:       Metropolis-Hastings — 通用, 慢
    """

    def __init__(self, method: str = "conjugate"):
        self.method = method

    def infer(self,
              data: np.ndarray,
              variable_names: List[str],
              edges: List[Tuple[str, str]],
              prior_equations: Optional[Dict[str, Dict[str, Tuple[float, float]]]] = None,
              ) -> Dict[str, ParameterPosterior]:
        """
        对因果图中每个变量推断参数后验。

        Args:
            data: (n_samples × n_features)
            variable_names: 变量名
            edges: 因果边列表
            prior_equations: 物理先验 {var: {parent: (mean, std)}}
                             例如: {"Acceleration": {"Force": (1.0, 0.01)}}

        Returns:
            {variable_name: ParameterPosterior}
        """
        from causal.graph import CausalDAG

        dag = CausalDAG(variable_names, edges)
        result = {}

        for var in variable_names:
            parents = list(dag.parents(var))
            var_idx = variable_names.index(var)

            if not parents:
                # 无父节点 → 仅截距
                y = data[:, var_idx]
                n = len(y)

                # 共轭: N(μ, σ²), 先验 μ ~ N(0, 10²), σ² ~ InvGamma
                post_mean = np.mean(y)
                post_std = np.std(y) / np.sqrt(n)

                result[var] = ParameterPosterior(
                    variable=var, parents=[],
                    coefficients={
                        "intercept": Posterior(
                            name="intercept",
                            mean=post_mean, std=post_std,
                            ci_lower=post_mean - 1.96 * post_std,
                            ci_upper=post_mean + 1.96 * post_std,
                            significance=1.0 if abs(post_mean) > 2 * post_std else 0.0,
                        )
                    },
                    noise_variance=Posterior(
                        name="σ²", mean=np.var(y),
                        std=np.var(y) / np.sqrt(2 * n),
                        ci_lower=0, ci_upper=np.var(y) * 2,
                    ),
                    effective_sample_size=n,
                )
                continue

            # 有父节点 → 回归
            p_indices = [variable_names.index(p) for p in parents]
            X = data[:, p_indices]
            y = data[:, var_idx]
            n = len(y)
            k = len(parents)

            X_design = np.column_stack([np.ones(n), X])

            # 共轭贝叶斯线性回归
            # 先验: β ~ N(β₀, τ²I), σ² ~ InvGamma(a₀, b₀)
            beta_prior_mean = np.zeros(k + 1)
            beta_prior_prec = 0.01 * np.eye(k + 1)  # 弱先验 τ²=100

            # 物理先验注入
            if prior_equations and var in prior_equations:
                for j, parent in enumerate(parents):
                    if parent in prior_equations[var]:
                        mu, std = prior_equations[var][parent]
                        beta_prior_mean[j + 1] = mu
                        beta_prior_prec[j + 1, j + 1] = 1.0 / (std * std)

            # 后验: β|σ²,D ~ N(β̂, σ²V)
            prec_data = X_design.T @ X_design
            prec_post = prec_data + beta_prior_prec

            try:
                V_post = np.linalg.inv(prec_post)
                beta_post_mean = V_post @ (X_design.T @ y + beta_prior_prec @ beta_prior_mean)

                resid = y - X_design @ beta_post_mean
                sse = resid @ resid

                # σ² 后验: InvGamma(a_post, b_post)
                a_post = (n + k + 1) / 2
                b_post = (sse + beta_post_mean @ beta_prior_prec @ beta_post_mean) / 2

                sigma2_mean = b_post / (a_post - 1) if a_post > 1 else b_post
                sigma2_var = b_post**2 / ((a_post - 1)**2 * (a_post - 2)) if a_post > 2 else 1.0

                coeffs = {}
                beta_names = ["intercept"] + parents
                for j, name in enumerate(beta_names):
                    beta_mean = beta_post_mean[j]
                    beta_std = np.sqrt(V_post[j, j] * sigma2_mean)

                    ci_l = beta_mean - 1.96 * beta_std
                    ci_u = beta_mean + 1.96 * beta_std

                    # 显著性: P(β≠0|D) = 后验不包含 0 的概率
                    z = abs(beta_mean) / (beta_std + 1e-10)
                    sig = 2 * (1 - self._normal_cdf(z))

                    coeffs[name] = Posterior(
                        name=name,
                        mean=float(beta_mean),
                        std=float(beta_std),
                        ci_lower=float(ci_l), ci_upper=float(ci_u),
                        prior_mean=float(beta_prior_mean[j]),
                        prior_std=float(1.0 / np.sqrt(beta_prior_prec[j, j])),
                        significance=float(1 - sig),
                    )

                result[var] = ParameterPosterior(
                    variable=var, parents=parents,
                    coefficients=coeffs,
                    noise_variance=Posterior(
                        name="σ²",
                        mean=float(sigma2_mean),
                        std=float(np.sqrt(sigma2_var)),
                        ci_lower=0, ci_upper=float(sigma2_mean * 2),
                    ),
                    effective_sample_size=n,
                )
            except Exception:
                continue

        return result

    def _normal_cdf(self, x):
        """标准正态 CDF 近似"""
        return 0.5 * (1 + np.tanh(np.sqrt(2 / np.pi) * (x + 0.044715 * x**3)))

    def ate_posterior(self,
                      param_posterior: Dict[str, ParameterPosterior],
                      treatment: str,
                      outcome: str) -> Posterior:
        """
        从参数后验推导 ATE 的后验分布。

        ATE = E[Y|do(T=1)] - E[Y|do(T=0)]

        在线性 SCM 中: ATE = β_{treatment}
        """
        if outcome not in param_posterior:
            raise ValueError(f"Outcome {outcome} not in parameter posteriors")

        pp = param_posterior[outcome]
        if treatment in pp.coefficients:
            return pp.coefficients[treatment]

        raise ValueError(f"Treatment {treatment} not a coefficient of {outcome}")

    def report(self, param_posterior: Dict[str, ParameterPosterior]) -> str:
        """生成参数后验报告"""
        lines = ["=== Parameter Posterior Report ==="]

        for var, pp in param_posterior.items():
            lines.append(f"\n  {var}:")
            if not pp.parents:
                lines.append("    (no parents — independent)")
            else:
                lines.append(f"    parents: {', '.join(pp.parents)}")
                for name, posterior in pp.coefficients.items():
                    sig_marker = "***" if posterior.significance > 0.99 else \
                                 "** " if posterior.significance > 0.95 else \
                                 "*  " if posterior.significance > 0.90 else "   "
                    lines.append(
                        f"    {sig_marker} {name}: "
                        f"{posterior.mean:.4f} ± {posterior.std:.4f} "
                        f"[{posterior.ci_lower:.4f}, {posterior.ci_upper:.4f}]"
                        f"  P(≠0)={posterior.significance:.3f}"
                    )
            lines.append(f"    σ²: {pp.noise_variance.mean:.4f} ± {pp.noise_variance.std:.4f}")

        return "\n".join(lines)
