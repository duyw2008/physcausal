"""
信息质检员 — 监控每步压缩的信息损失

信息流的租用关系:
  1. 感知提取特征 → spectral 降维 → information 质检
  2. 因果发现 → information 度量模型质量
  3. 效应估计 → information 评估不确定性

核心指标:
  - I(T;X): 压缩表示 T 保留了原始信号 X 的多少信息
  - I(T;Y): 压缩表示 T 保留了目标变量 Y 的多少信息
  - bottleneck_score = I(T;Y) - β·I(T;X)  (β 大=更激进压缩)
  - loss_ratio: 每步压缩损失了多少因果信息
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import numpy as np


class InformationGate:
    """
    信息质检员 — 监控管道中的信息流动。

    在每一步压缩后检查:
      1. 是否丢失了因果信息? (I(T;Y) 是否下降)
      2. 压缩是否有效? (噪声是否被正确丢弃)
      3. 是否需要回退? (损失太大 → 保留更多维度)
    """

    def __init__(self, beta: float = 0.5):
        """
        Args:
            beta: 压缩激进程度 (0=保守不压缩, 1=激进压缩)
        """
        self.beta = beta
        self.history: List[Dict] = []
        self.warnings: List[str] = []

    def measure_compression(self,
                            original: np.ndarray,
                            compressed: np.ndarray,
                            target: Optional[np.ndarray] = None,
                            step_name: str = "") -> Dict:
        """
        测量一步压缩的信息损失。

        Args:
            original: 压缩前的数据 (n × d_original)
            compressed: 压缩后的数据 (n × d_compressed)  
            target: 目标变量 (n × 1) — 可选
            step_name: 步骤名称

        Returns:
            {i_tx, i_ty, bottleneck, loss_ratio, verdict}
        """
        from information.shannon import ShannonEntropy

        n = len(original)
        if n < 5 or len(compressed) != n:
            return {"verdict": "skip", "step": step_name}

        # I(T;X) — 压缩表示保留了原信号的多少信息
        # 用互信息近似: 每维独立贡献
        i_tx = 0.0
        d_orig = original.shape[1]
        d_comp = compressed.shape[1]
        for j in range(d_comp):
            max_corr = 0.0
            for i in range(d_orig):
                try:
                    corr = abs(np.corrcoef(original[:, i], compressed[:, j])[0, 1])
                    if not np.isnan(corr):
                        max_corr = max(max_corr, corr)
                except Exception:
                    pass
            i_tx += max_corr
        i_tx = min(1.0, i_tx / d_comp)  # 归一化

        # I(T;Y) — 压缩表示保留了目标的多少信息
        i_ty = 0.0
        if target is not None and len(target) == n:
            target_flat = target.ravel() if target.ndim > 1 else target
            for j in range(d_comp):
                try:
                    corr = abs(np.corrcoef(compressed[:, j], target_flat)[0, 1])
                    if not np.isnan(corr):
                        i_ty = max(i_ty, corr)
                except Exception:
                    pass

        # 瓶颈得分
        # 高 i_ty + 低 i_tx = 好 (保留了因果信息, 丢掉了冗余)
        bottleneck = i_ty - self.beta * i_tx

        # 损失比
        prev = self.history[-1] if self.history else None
        if prev and prev.get("i_ty", 0) > 1e-10:
            loss_ratio = (prev["i_ty"] - i_ty) / prev["i_ty"]
        else:
            loss_ratio = 0.0

        verdict = self._verdict(loss_ratio, i_ty, bottleneck)

        entry = {
            "step": step_name,
            "d_original": d_orig,
            "d_compressed": d_comp,
            "i_tx": round(i_tx, 4),
            "i_ty": round(i_ty, 4),
            "bottleneck": round(bottleneck, 4),
            "loss_ratio": round(loss_ratio, 4),
            "verdict": verdict,
        }
        self.history.append(entry)

        if verdict == "warning":
            self.warnings.append(
                f"High info loss at '{step_name}': "
                f"I(Y) dropped {loss_ratio:.1%}, "
                f"consider retaining more dimensions"
            )

        return entry

    def _verdict(self, loss_ratio: float, i_ty: float, bottleneck: float) -> str:
        if loss_ratio > 0.3:
            return "warning"       # 丢失太多因果信息
        if i_ty < 0.3:
            return "warning"       # 压缩后的表示和 Y 几乎无关
        if bottleneck > 0.5:
            return "excellent"     # 高信息保留 + 低冗余
        if bottleneck > 0.2:
            return "good"
        return "pass"

    def report(self) -> str:
        """生成信息流报告"""
        lines = ["=== Information Flow Report ==="]
        lines.append(f"  Beta (compression aggressiveness): {self.beta}")

        if not self.history:
            lines.append("  (no measurements)")
            return "\n".join(lines)

        lines.append(f"  {'Step':<20s} {'Orig':>5s} {'Comp':>5s} "
                     f"{'I(T;X)':>7s} {'I(T;Y)':>7s} {'Bottleneck':>10s} {'Verdict':>10s}")
        lines.append("  " + "-" * 65)

        for h in self.history:
            verdict_mark = {
                "excellent": "★★★",
                "good": "★★",
                "pass": "★",
                "warning": "⚠",
                "skip": "—",
            }.get(h["verdict"], "?")
            lines.append(
                f"  {h['step']:<20s} {h['d_original']:>5d} {h['d_compressed']:>5d} "
                f"{h['i_tx']:>7.3f} {h['i_ty']:>7.3f} {h['bottleneck']:>10.3f} "
                f"{verdict_mark:>10s}"
            )

        if self.warnings:
            lines.append(f"\n  ⚠ Warnings ({len(self.warnings)}):")
            for w in self.warnings[:3]:
                lines.append(f"    - {w}")

        final_compression = (
            self.history[0]["d_original"] / max(self.history[-1]["d_compressed"], 1)
            if self.history else 1.0
        )
        lines.append(f"\n  Total compression: {final_compression:.1f}x")

        return "\n".join(lines)

    def auto_threshold(self, compressed: np.ndarray,
                       target: np.ndarray,
                       max_dim: int,
                       min_dim: int = 2) -> int:
        """
        自动选择最优压缩维度。

        逐步减少维度, 直到 I(T;Y) 开始下降 >10%。

        Returns:
            最佳维度数
        """
        from spectral.spectral import SpectralDecomposer

        sd = SpectralDecomposer()
        best_k = max_dim
        best_ity = 0.0

        for k in range(max_dim, min_dim - 1, -1):
            _, _, reduced = sd.pca(compressed, n_components=k)
            # 近似 I(T;Y): 前 k 个主成分对 Y 的最大相关性
            ity = 0.0
            for j in range(k):
                try:
                    corr = abs(np.corrcoef(reduced[:, j], target.ravel())[0, 1])
                    if not np.isnan(corr):
                        ity = max(ity, corr)
                except Exception:
                    pass

            if ity >= best_ity * 0.95:  # 损失 < 5% → 可以继续降
                best_k = k
                best_ity = ity
            else:
                break  # 损失 > 5% → 停在这里

        return best_k
