"""
对象分解器 — 场景 → 独立因果单元 (Object Slots)

Object-centric 感知的核心:
  场景不是一维向量，而是多个独立对象的集合。
  每个对象有自己的属性 (位置/速度/颜色/大小)。
  对象之间的交互 = 因果边。

当前实现: 简单连通分量 + 启发式特征
未来扩展: Slot Attention / DETR 风格的对象查询
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from perception.encoder import PerceptualEncoder, Scene, ObjectSlot


class ObjectDetector(PerceptualEncoder):
    """
    对象检测器 — 从场景中分解出独立对象。

    使用方式:
        detector = ObjectDetector(n_objects=3)
        scene = detector.encode(image_array)
        # scene.objects = [ObjectSlot("obj_0", {...}), ...]
    """

    def __init__(self, n_objects: int = 5,
                 min_area: int = 100,
                 use_color_segmentation: bool = True):
        self.n_objects = n_objects
        self.min_area = min_area
        self.use_color_segmentation = use_color_segmentation

    def supported_inputs(self) -> List[str]:
        return ["image", "array"]

    def encode(self, raw_input: Any) -> Scene:
        if isinstance(raw_input, np.ndarray) and raw_input.ndim == 3:
            return self._detect_from_image(raw_input)
        return Scene()

    def _detect_from_image(self, img: np.ndarray) -> Scene:
        """从图像中检测对象"""
        gray = (0.299 * img[:, :, 0] + 0.587 * img[:, :, 1] +
                0.114 * img[:, :, 2]).astype(np.float32)

        # 前景/背景分割 — 同时检测暗前景和亮前景
        binary_dark = (gray < np.mean(gray) - 10).astype(np.uint8)
        binary_bright = (gray > np.mean(gray) + 10).astype(np.uint8)
        binary = binary_dark | binary_bright

        # 连通分量
        regions = self._find_connected_regions(binary)

        # 取最大的 n_objects 个区域
        regions.sort(key=lambda r: r["area"], reverse=True)
        regions = regions[:self.n_objects]

        objects = []
        for i, region in enumerate(regions):
            features = self._extract_region_features(region, img, gray)
            obj = ObjectSlot(id=f"obj_{i}", features=features)
            objects.append(obj)

        return Scene(objects=objects)

    def _find_connected_regions(self, binary: np.ndarray) -> List[Dict]:
        """简单连通分量检测 (flood fill 近似)"""
        h, w = binary.shape
        visited = np.zeros_like(binary, dtype=bool)
        regions = []

        for y in range(h):
            for x in range(w):
                if binary[y, x] and not visited[y, x]:
                    # BFS
                    stack = [(y, x)]
                    pixels = []
                    while stack:
                        cy, cx = stack.pop()
                        if (0 <= cy < h and 0 <= cx < w and
                                binary[cy, cx] and not visited[cy, cx]):
                            visited[cy, cx] = True
                            pixels.append((cy, cx))
                            for dy, dx in [(-1,0),(1,0),(0,-1),(0,1)]:
                                stack.append((cy+dy, cx+dx))

                    if len(pixels) >= self.min_area:
                        ys, xs = zip(*pixels)
                        regions.append({
                            "pixels": pixels,
                            "area": len(pixels),
                            "y_min": min(ys), "y_max": max(ys),
                            "x_min": min(xs), "x_max": max(xs),
                            "centroid_y": np.mean(ys),
                            "centroid_x": np.mean(xs),
                        })

        return regions

    def _extract_region_features(self, region: Dict,
                                  img: np.ndarray,
                                  gray: np.ndarray) -> Dict[str, float]:
        """从区域提取特征"""
        features = {}

        # 位置和大小
        features["x"] = region["centroid_x"] / max(img.shape[1], 1)
        features["y"] = region["centroid_y"] / max(img.shape[0], 1)
        features["width"] = (region["x_max"] - region["x_min"]) / max(img.shape[1], 1)
        features["height"] = (region["y_max"] - region["y_min"]) / max(img.shape[0], 1)
        features["area"] = region["area"] / (img.shape[0] * img.shape[1])

        # 颜色
        for i, ch in enumerate(["R", "G", "B"]):
            vals = img[:, :, i]
            region_vals = [vals[y, x] for y, x in region["pixels"][:500]]
            features[f"color_{ch}"] = float(np.mean(region_vals)) if region_vals else 0.0

        # 亮度
        region_gray = [gray[y, x] for y, x in region["pixels"][:500]]
        features["brightness"] = float(np.mean(region_gray)) if region_gray else 0.0

        # 形状特征
        w = region["x_max"] - region["x_min"] + 1
        h = region["y_max"] - region["y_min"] + 1
        features["aspect_ratio"] = float(w / h) if h > 0 else 1.0
        features["compactness"] = float(
            region["area"] / (w * h)
        ) if w * h > 0 else 0.0

        return features


class MultiFrameObjectTracker:
    """
    多帧对象跟踪器 — 跨帧关联同一对象。

    用于视频输入: 每帧的对象 → 跨帧关联 → 每个对象的时间序列
    """

    def __init__(self, max_distance: float = 0.1):
        self.max_distance = max_distance
        self.tracks: Dict[str, List[Dict[str, float]]] = {}

    def update(self, frame_objects: List[ObjectSlot],
               frame_id: int) -> Dict[str, ObjectSlot]:
        """关联当前帧对象到已有轨迹"""
        assignments = {}

        for obj in frame_objects:
            best_track = None
            best_dist = float("inf")

            for track_id, track_history in self.tracks.items():
                if track_history:
                    last = track_history[-1]
                    dist = self._distance(obj.features, last)
                    if dist < best_dist and dist < self.max_distance:
                        best_dist = dist
                        best_track = track_id

            if best_track:
                assignments[best_track] = obj
                self.tracks[best_track].append(obj.features)
            else:
                new_id = f"obj_{len(self.tracks)}"
                assignments[new_id] = obj
                self.tracks[new_id] = [obj.features]

        return assignments

    def _distance(self, f1: Dict[str, float],
                  f2: Dict[str, float]) -> float:
        """两个对象特征向量之间的距离"""
        keys = set(f1.keys()) & set(f2.keys())
        if not keys:
            return float("inf")
        return np.sqrt(sum((f1[k] - f2[k]) ** 2 for k in keys) / len(keys))

    def get_trajectory(self, track_id: str) -> List[Dict[str, float]]:
        return self.tracks.get(track_id, [])
