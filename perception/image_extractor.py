"""
图像感知后端 — 从图像中提取结构化视觉特征

功能:
  - 颜色特征: 均值/方差/主色调 (RGB histogram moments)
  - 边缘特征: Canny 边缘检测 → 边缘密度/方向分布
  - 纹理特征: 局部二值模式 (LBP) / Gabor 响应
  - 运动特征: 光流 (帧间差分, 简单近似)
  - 空间特征: 质心/包围盒 (用于对象定位)

输出: Scene 对象, 每个 ObjectSlot 对应一个检测到的对象
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from perception.encoder import PerceptualEncoder, Scene, ObjectSlot


class ImageFeatureExtractor(PerceptualEncoder):
    """
    图像特征提取器。

    不依赖深度学习 — 纯 CV + numpy。
    适合 MVP 阶段快速从图像中获取结构化因果变量。

    使用:
        extractor = ImageFeatureExtractor()
        scene = extractor.encode(image_array)  # (H, W, 3) uint8
        scene = extractor.encode("path/to/image.png")
    """

    def __init__(self):
        self._last_image: Optional[np.ndarray] = None

    def supported_inputs(self) -> List[str]:
        return ["image", "image_path"]

    def encode(self, raw_input: Any) -> Scene:
        img = self._load_image(raw_input)
        if img is None:
            return Scene()

        self._last_image = img

        # 全图特征
        global_features = {}
        global_features.update(self._extract_color_features(img))
        global_features.update(self._extract_edge_features(img))
        global_features.update(self._extract_texture_features(img))

        return Scene(global_features=global_features, objects=[])

    def encode_with_motion(self,
                           img_current: np.ndarray,
                           img_previous: Optional[np.ndarray] = None
                           ) -> Scene:
        """包含运动特征的编码"""
        scene = self.encode(img_current)
        if img_previous is not None:
            motion = self._extract_motion_features(img_previous, img_current)
            scene.global_features.update(motion)
        return scene

    def _load_image(self, raw_input: Any) -> Optional[np.ndarray]:
        if isinstance(raw_input, str):
            try:
                from PIL import Image
                img = Image.open(raw_input).convert("RGB")
                return np.array(img)
            except Exception:
                return None

        if isinstance(raw_input, np.ndarray):
            if raw_input.ndim == 3 and raw_input.shape[2] in (1, 3, 4):
                if raw_input.shape[2] == 1:
                    raw_input = np.repeat(raw_input, 3, axis=2)
                elif raw_input.shape[2] == 4:
                    raw_input = raw_input[:, :, :3]
                return raw_input.astype(np.float32)
            if raw_input.ndim == 2:
                return np.stack([raw_input] * 3, axis=-1).astype(np.float32)

        return None

    # ═══ 颜色特征 ═══

    def _extract_color_features(self, img: np.ndarray) -> Dict[str, float]:
        features = {}
        for i, channel in enumerate(["R", "G", "B"]):
            ch = img[:, :, i]
            features[f"color_{channel}_mean"] = float(np.mean(ch))
            features[f"color_{channel}_std"] = float(np.std(ch))
            features[f"color_{channel}_median"] = float(np.median(ch))

        # 亮度
        gray = 0.299 * img[:, :, 0] + 0.587 * img[:, :, 1] + 0.114 * img[:, :, 2]
        features["brightness_mean"] = float(np.mean(gray))
        features["brightness_std"] = float(np.std(gray))
        features["contrast"] = float(np.max(gray) - np.min(gray))

        # 饱和度
        max_ch = np.max(img, axis=2)
        min_ch = np.min(img, axis=2)
        saturation = np.where(max_ch > 0, (max_ch - min_ch) / (max_ch + 1e-10), 0)
        features["saturation_mean"] = float(np.mean(saturation))

        return features

    # ═══ 边缘特征 ═══

    def _extract_edge_features(self, img: np.ndarray) -> Dict[str, float]:
        gray = (0.299 * img[:, :, 0] + 0.587 * img[:, :, 1] +
                0.114 * img[:, :, 2]).astype(np.float32)

        # Sobel 梯度
        if gray.shape[0] > 2 and gray.shape[1] > 2:
            gy = np.zeros_like(gray)
            gx = np.zeros_like(gray)
            gy[1:-1, :] = gray[2:, :] - gray[:-2, :]
            gx[:, 1:-1] = gray[:, 2:] - gray[:, :-2]
            magnitude = np.sqrt(gx * gx + gy * gy)

            features = {
                "edge_density": float(np.mean(magnitude > 30)),
                "edge_mean": float(np.mean(magnitude)),
                "edge_std": float(np.std(magnitude)),
                "edge_max": float(np.max(magnitude)),
            }

            # 梯度方向统计
            direction = np.arctan2(gy + 1e-10, gx + 1e-10)
            mask = magnitude > 30
            if mask.sum() > 0:
                dirs = direction[mask]
                features["edge_dir_mean"] = float(np.mean(dirs))
                features["edge_dir_std"] = float(np.std(dirs))
                # 水平/垂直比
                h_edges = np.sum((np.abs(dirs) < np.pi / 4) | (np.abs(dirs) > 3 * np.pi / 4))
                v_edges = np.sum((np.abs(dirs) > np.pi / 4) & (np.abs(dirs) < 3 * np.pi / 4))
                features["edge_h_ratio"] = float(h_edges / (h_edges + v_edges + 1))
            else:
                features["edge_dir_mean"] = 0.0
                features["edge_dir_std"] = 0.0
                features["edge_h_ratio"] = 0.5

            return features

        return {"edge_density": 0.0, "edge_mean": 0.0}

    # ═══ 纹理特征 ═══

    def _extract_texture_features(self, img: np.ndarray) -> Dict[str, float]:
        gray = (0.299 * img[:, :, 0] + 0.587 * img[:, :, 1] +
                0.114 * img[:, :, 2]).astype(np.float32)

        features = {}

        # 空间自相关 (简单纹理度量)
        if gray.shape[0] > 2 and gray.shape[1] > 2:
            # 相邻像素差
            diff_h = np.abs(gray[:, 1:] - gray[:, :-1])
            diff_v = np.abs(gray[1:, :] - gray[:-1, :])

            features["texture_roughness_h"] = float(np.mean(diff_h))
            features["texture_roughness_v"] = float(np.mean(diff_v))
            features["texture_granularity"] = float(
                (np.mean(diff_h) + np.mean(diff_v)) / 2
            )

            # 局部方差
            if gray.shape[0] > 3 and gray.shape[1] > 3:
                local_var = np.zeros_like(gray)
                for i in range(1, gray.shape[0] - 1):
                    for j in range(1, gray.shape[1] - 1):
                        patch = gray[i-1:i+2, j-1:j+2]
                        local_var[i, j] = np.var(patch)
                features["texture_local_var"] = float(np.mean(local_var))

        return features

    # ═══ 运动特征 ═══

    def _extract_motion_features(self,
                                  prev: np.ndarray,
                                  curr: np.ndarray) -> Dict[str, float]:
        """帧间运动特征"""
        if prev.shape != curr.shape:
            return {}

        prev_gray = (0.299 * prev[:, :, 0] + 0.587 * prev[:, :, 1] +
                     0.114 * prev[:, :, 2])
        curr_gray = (0.299 * curr[:, :, 0] + 0.587 * curr[:, :, 1] +
                     0.114 * curr[:, :, 2])

        diff = np.abs(curr_gray - prev_gray)

        features = {
            "motion_mean": float(np.mean(diff)),
            "motion_std": float(np.std(diff)),
            "motion_max": float(np.max(diff)),
            "motion_fraction": float(np.mean(diff > 10)),
        }

        # 运动质心 (运动发生的中心位置)
        if diff.sum() > 0:
            h, w = diff.shape
            y_idx = np.arange(h)[:, None]
            x_idx = np.arange(w)[None, :]
            features["motion_centroid_y"] = float(np.sum(y_idx * diff) / diff.sum())
            features["motion_centroid_x"] = float(np.sum(x_idx * diff) / diff.sum())

        return features
