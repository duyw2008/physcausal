"""
感知引擎 — 多后端感知调度器

支持的后端:
  simple     — 结构化数据 (array/dict/csv)
  image      — 图像 (CV 特征提取: 边缘/颜色/纹理/运动)
  timeseries — 时间序列 (趋势/周期/自相关/差分)
  learner    — 学习式特征 (DINOv2/Slot Attn, stub)

所有后端统一接口: raw_input → Scene → variable dict
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from perception.encoder import (
    PerceptualEncoder, Scene, ObjectSlot, SimpleFeatureExtractor
)


class PerceptionEngine:
    """
    多后端感知引擎。

    根据输入类型自动选择最佳后端:
      - numpy array → simple (结构化)
      - image path / array[H,W,C] → image
      - time series → timeseries
      - raw pixels → learner (future)
    """

    def __init__(self,
                 backend: str = "auto",
                 config: Optional[Dict] = None):
        self.config = config or {}
        self.backend_name = backend
        self._backends: Dict[str, PerceptualEncoder] = {}
        self._init_backends()

    def _init_backends(self):
        """初始化所有后端"""
        # Simple — 总是可用
        self._backends["simple"] = SimpleFeatureExtractor()

        # Image — 按需加载
        try:
            from perception.image_extractor import ImageFeatureExtractor
            self._backends["image"] = ImageFeatureExtractor()
        except ImportError:
            pass

        # Time series — 按需加载
        try:
            from perception.timeseries_extractor import TimeSeriesExtractor
            self._backends["timeseries"] = TimeSeriesExtractor()
        except ImportError:
            pass

    def available_backends(self) -> List[str]:
        return list(self._backends.keys())

    def encode(self, raw_input: Any,
               backend: Optional[str] = None) -> Scene:
        """
        感知编码: raw_input → Scene。

        自动检测输入类型并选择后端。
        """
        if backend and backend in self._backends:
            return self._backends[backend].encode(raw_input)

        if backend == "auto" or backend is None:
            # 自动检测
            if isinstance(raw_input, np.ndarray):
                if raw_input.ndim == 2 and raw_input.shape[1] < 100:
                    return self._backends["simple"].encode(raw_input)
                elif raw_input.ndim == 3:
                    if "image" in self._backends:
                        return self._backends["image"].encode(raw_input)
                    return self._backends["simple"].encode(raw_input)
                else:
                    return self._backends["simple"].encode(raw_input)

            if isinstance(raw_input, str):
                if raw_input.endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                    if "image" in self._backends:
                        return self._backends["image"].encode(raw_input)
                if "timeseries" in self._backends:
                    return self._backends["timeseries"].encode(raw_input)
                return self._backends["simple"].encode(raw_input)

            if isinstance(raw_input, dict):
                return self._backends["simple"].encode(raw_input)

            if isinstance(raw_input, list):
                return self._backends["simple"].encode(np.array(raw_input))

        raise ValueError(f"No suitable backend for input type {type(raw_input)}")

    def encode_batch(self, raw_inputs: List[Any],
                     backend: Optional[str] = None) -> List[Scene]:
        return [self.encode(x, backend) for x in raw_inputs]

    def extract_variables(self, scene: Scene) -> Dict[str, float]:
        """Scene → 扁平变量字典"""
        return scene.variable_dict()

    def extract_variable_names(self, scene: Scene) -> List[str]:
        return scene.variable_names()

    def to_data_matrix(self, scenes: List[Scene]) -> Tuple[np.ndarray, List[str]]:
        """
        场景列表 → (data_matrix, variable_names)

        data_matrix: (n_scenes × n_features)
        """
        if not scenes:
            return np.array([]), []

        var_names = scenes[0].variable_names()
        data = np.zeros((len(scenes), len(var_names)))

        for i, scene in enumerate(scenes):
            vd = scene.variable_dict()
            for j, vn in enumerate(var_names):
                data[i, j] = vd.get(vn, 0.0)

        return data, var_names
