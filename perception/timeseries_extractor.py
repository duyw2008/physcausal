"""
时序感知后端 — 时间序列特征提取

功能:
  - 趋势: 线性/二次趋势强度
  - 周期: 自相关峰值检测 → 主频周期
  - 波动: 方差/变异系数/极差
  - 差分: 一阶/二阶差分统计
  - 突变: 滑动窗口方差跳变检测
  - 平稳性: 均值/方差稳定性检验

输出: Scene, 每个变量对应一组时序特征
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import numpy as np

from perception.encoder import PerceptualEncoder, Scene


class TimeSeriesExtractor(PerceptualEncoder):
    """
    时间序列特征提取器。

    将时间序列数据转化为结构化特征变量。

    使用:
        extractor = TimeSeriesExtractor(window=50)
        scene = extractor.encode(timeseries_array)  # (n_timesteps, n_variables)
    """

    def __init__(self, window: int = 50, stride: int = 10):
        self.window = window
        self.stride = stride

    def supported_inputs(self) -> List[str]:
        return ["timeseries", "array"]

    def encode(self, raw_input: Any) -> Scene:
        if isinstance(raw_input, np.ndarray):
            return self._extract(raw_input)
        return Scene()

    def _extract(self, data: np.ndarray) -> Scene:
        """提取全部时序特征"""
        # 假设: data.shape = (n_timesteps, n_variables)
        if data.ndim == 1:
            data = data.reshape(-1, 1)

        n_timesteps, n_vars = data.shape
        all_features = {}

        for i in range(n_vars):
            series = data[:, i]
            prefix = f"V{i}" if n_vars > 1 else "value"
            features = self._extract_series_features(series, prefix)
            all_features.update(features)

        return Scene(global_features=all_features)

    def _extract_series_features(self,
                                  series: np.ndarray,
                                  prefix: str) -> Dict[str, float]:
        """单变量时序特征提取"""
        f = {}
        n = len(series)

        if n < 3:
            return {f"{prefix}_mean": float(np.mean(series))}

        # ═══ 基本统计 ═══
        f[f"{prefix}_mean"] = float(np.mean(series))
        f[f"{prefix}_std"] = float(np.std(series))
        f[f"{prefix}_min"] = float(np.min(series))
        f[f"{prefix}_max"] = float(np.max(series))
        f[f"{prefix}_range"] = float(np.max(series) - np.min(series))
        f[f"{prefix}_median"] = float(np.median(series))

        # 变异系数
        if abs(f[f"{prefix}_mean"]) > 1e-10:
            f[f"{prefix}_cv"] = f[f"{prefix}_std"] / abs(f[f"{prefix}_mean"])
        else:
            f[f"{prefix}_cv"] = f[f"{prefix}_std"]

        # ═══ 趋势 ═══
        t = np.arange(n)
        if n > 2:
            coeffs = np.polyfit(t, series, 1)
            f[f"{prefix}_trend_linear"] = float(coeffs[0])  # 斜率
            f[f"{prefix}_trend_r2"] = float(
                np.corrcoef(t, series)[0, 1] ** 2
            )

        # ═══ 周期 ═══
        if n > 20:
            # 自相关
            acf = self._autocorr(series, min(n // 3, 50))
            if len(acf) > 2:
                # 找第一个峰值 (排除 lag=0)
                peaks = []
                for i in range(1, len(acf) - 1):
                    if acf[i] > acf[i-1] and acf[i] > acf[i+1] and acf[i] > 0.1:
                        peaks.append((i, acf[i]))
                if peaks:
                    best_peak = max(peaks, key=lambda x: x[1])
                    f[f"{prefix}_period"] = float(best_peak[0])
                    f[f"{prefix}_period_strength"] = float(best_peak[1])
                else:
                    f[f"{prefix}_period"] = 0.0
                    f[f"{prefix}_period_strength"] = 0.0

        # ═══ 差分 ═══
        if n > 2:
            diff1 = np.diff(series)
            f[f"{prefix}_diff1_mean"] = float(np.mean(diff1))
            f[f"{prefix}_diff1_std"] = float(np.std(diff1))

        if n > 3:
            diff2 = np.diff(np.diff(series))
            f[f"{prefix}_diff2_mean"] = float(np.mean(diff2))
            f[f"{prefix}_diff2_std"] = float(np.std(diff2))

        # ═══ 突变检测 ═══
        if n > 2 * self.window:
            f[f"{prefix}_breakpoint_score"] = float(
                self._detect_breakpoint(series)
            )

        # ═══ 平稳性 ═══
        if n > 2 * self.window:
            half = n // 2
            mean_shift = abs(np.mean(series[:half]) - np.mean(series[half:]))
            f[f"{prefix}_stationarity"] = float(
                1.0 / (1.0 + mean_shift)  # 0=不稳定, 1=稳定
            )

        return f

    def _autocorr(self, series: np.ndarray, max_lag: int) -> np.ndarray:
        """自相关函数"""
        n = len(series)
        s = series - np.mean(series)
        denom = np.sum(s * s)
        if denom < 1e-10:
            return np.zeros(max_lag)

        acf = np.zeros(max_lag)
        for lag in range(max_lag):
            acf[lag] = np.sum(s[lag:] * s[:n-lag]) / denom
        return acf

    def _detect_breakpoint(self, series: np.ndarray) -> float:
        """检测时间序列中的突变点强度"""
        n = len(series)
        half = n // 2
        before = series[:half]
        after = series[half:]

        mean_diff = abs(np.mean(before) - np.mean(after))
        pooled_std = np.sqrt((np.var(before) + np.var(after)) / 2)

        if pooled_std > 1e-10:
            return float(mean_diff / pooled_std)
        return 0.0

    def sliding_window_extract(self, data: np.ndarray) -> List[Scene]:
        """滑动窗口提取 — 将长序列切分为场景片段"""
        scenes = []
        for start in range(0, len(data) - self.window, self.stride):
            window = data[start:start + self.window]
            scenes.append(self.encode(window))
        return scenes
