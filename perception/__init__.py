"""
感知层 (Perception) — 多后端感知编码

后端:
  simple         — 结构化数据 (array/dict/csv)
  image          — 图像 (CV特征: 颜色/边缘/纹理/运动)
  timeseries     — 时间序列 (趋势/周期/差分/突变)
  object_detect  — 对象分解 (场景→独立因果单元)

引擎:
  PerceptionEngine — 自动选择后端 + 统一接口

接口:
  raw_input → Scene → variable_dict → causal analysis
"""

from perception.encoder import (
    PerceptualEncoder, Scene, ObjectSlot, SimpleFeatureExtractor,
)
from perception.engine import PerceptionEngine
from perception.image_extractor import ImageFeatureExtractor
from perception.object_detector import ObjectDetector, MultiFrameObjectTracker
from perception.timeseries_extractor import TimeSeriesExtractor

__all__ = [
    # Core
    "PerceptualEncoder", "Scene", "ObjectSlot",
    "SimpleFeatureExtractor",
    # Engine
    "PerceptionEngine",
    # Backends
    "ImageFeatureExtractor",
    "TimeSeriesExtractor",
    # Object-centric
    "ObjectDetector", "MultiFrameObjectTracker",
]
