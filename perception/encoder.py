"""
感知层 — 原始传感器数据 → 结构化语义变量

PerceptualEncoder 是抽象接口。
MVP 阶段: SimpleFeatureExtractor — 手工特征提取
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


@dataclass
class ObjectSlot:
    """对象槽 — 场景中一个因果单元"""
    id: str
    features: Dict[str, float] = field(default_factory=dict)
    # 例如: {"x": 0.5, "y": 1.2, "vx": 2.0, "vy": 0.0, "mass": 1.0}

    def variable_dict(self) -> Dict[str, float]:
        """返回扁平化的变量字典，用于因果发现"""
        result = {}
        for k, v in self.features.items():
            result[f"{self.id}_{k}"] = v
        return result


@dataclass
class Scene:
    """场景 — 一帧中的所有对象"""
    objects: List[ObjectSlot] = field(default_factory=list)
    global_features: Dict[str, float] = field(default_factory=dict)

    def variable_dict(self) -> Dict[str, float]:
        result = dict(self.global_features)
        for obj in self.objects:
            result.update(obj.variable_dict())
        return result

    def variable_names(self) -> List[str]:
        return list(self.variable_dict().keys())


class PerceptualEncoder(ABC):
    """感知编码器抽象接口"""

    @abstractmethod
    def encode(self, raw_input: Any) -> Scene:
        """原始输入 → 结构化场景"""
        ...

    @abstractmethod
    def supported_inputs(self) -> List[str]:
        """返回支持的输入类型: ['image', 'video', 'array', ...]"""
        ...


# ═══════════════════════════════════════════════════════════════
# MVP 实现: SimpleFeatureExtractor — 手工特征提取
# ═══════════════════════════════════════════════════════════════

class SimpleFeatureExtractor(PerceptualEncoder):
    """
    MVP 感知前端。
    接受 numpy array 或 CSV 格式的结构化数据，
    直接转换为 Scene 对象。
    
    使用方式:
        extractor = SimpleFeatureExtractor(
            variable_names=["x_A", "y_A", "vx_A", "vy_A", "x_B", "y_B"]
        )
        scene = extractor.encode(np.array([[1.0, 0.5, 2.0, 0.0, 5.0, 3.0]]))
    """

    def __init__(self, variable_names: Optional[List[str]] = None,
                 object_groups: Optional[Dict[str, List[str]]] = None):
        """
        Args:
            variable_names: 扁平化的变量名列表
            object_groups:  变量名到对象 ID 的分组
                            例如: {"A": ["x_A", "y_A", "vx_A"], "B": ["x_B"]}
        """
        self.variable_names = variable_names or []
        self.object_groups = object_groups or {}

    def supported_inputs(self) -> List[str]:
        return ["array", "dict", "csv"]

    def encode(self, raw_input: Any) -> Scene:
        if isinstance(raw_input, dict):
            return Scene(global_features=dict(raw_input))
        
        if isinstance(raw_input, np.ndarray):
            arr = raw_input.reshape(-1)  # 展平
            if len(self.variable_names) != len(arr):
                raise ValueError(
                    f"Expected {len(self.variable_names)} values, got {len(arr)}"
                )
            features = dict(zip(self.variable_names, arr.astype(float)))
            return self._group_into_objects(features)

        raise TypeError(f"Unsupported input type: {type(raw_input)}")

    def _group_into_objects(self, features: Dict[str, float]) -> Scene:
        """根据 object_groups 将变量分组为 ObjectSlot"""
        if not self.object_groups:
            return Scene(global_features=features)

        objects = []
        assigned = set()
        for obj_id, var_names in self.object_groups.items():
            obj_features = {}
            for vn in var_names:
                if vn in features:
                    obj_features[vn.replace(f"{obj_id}_", "")] = features[vn]
                    assigned.add(vn)
            objects.append(ObjectSlot(id=obj_id, features=obj_features))

        # 未分配的变量放入 global_features
        remaining = {k: v for k, v in features.items() if k not in assigned}
        return Scene(objects=objects, global_features=remaining)

    def encode_batch(self, data: np.ndarray) -> List[Scene]:
        """批量编码: (n_samples, n_features) → List[Scene]"""
        return [self.encode(data[i]) for i in range(data.shape[0])]
