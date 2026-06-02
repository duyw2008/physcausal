"""
感知层测试 — engine + image + object_detector + timeseries
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from perception.engine import PerceptionEngine
from perception.image_extractor import ImageFeatureExtractor
from perception.object_detector import ObjectDetector
from perception.timeseries_extractor import TimeSeriesExtractor
from perception.encoder import SimpleFeatureExtractor


class TestPerceptionEngine:

    def setup_method(self):
        self.engine = PerceptionEngine(backend="auto")

    def test_available_backends(self):
        backends = self.engine.available_backends()
        assert "simple" in backends
        assert "image" in backends
        assert "timeseries" in backends

    def test_encode_array(self):
        engine = PerceptionEngine(backend="simple")
        # need to configure SimpleFeatureExtractor with variable names
        engine._backends["simple"] = SimpleFeatureExtractor(
            variable_names=[f"V{i}" for i in range(10)]
        )
        data = np.random.randn(10).reshape(1, 10)
        scene = engine.encode(data)
        assert len(scene.variable_dict()) > 0

    def test_encode_dict(self):
        scene = self.engine.encode({"x": 1.0, "y": 2.0})
        assert scene.global_features["x"] == 1.0

    def test_to_data_matrix(self):
        scenes = [
            self.engine.encode({"x": 1.0, "y": 2.0}),
            self.engine.encode({"x": 3.0, "y": 4.0}),
        ]
        data, names = self.engine.to_data_matrix(scenes)
        assert data.shape == (2, 2)
        assert "x" in names


class TestImageFeatureExtractor:

    def setup_method(self):
        self.extractor = ImageFeatureExtractor()

    def test_supported_inputs(self):
        assert "image" in self.extractor.supported_inputs()

    def test_encode_random_image(self):
        img = np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)
        scene = self.extractor.encode(img)
        features = scene.variable_dict()
        assert "color_R_mean" in features
        assert "edge_density" in features
        assert "brightness_mean" in features

    def test_encode_grayscale_as_rgb(self):
        img = np.random.randint(0, 255, (32, 32), dtype=np.uint8)
        scene = self.extractor.encode(img)
        assert len(scene.variable_dict()) > 0

    def test_motion_features(self):
        img1 = np.zeros((32, 32, 3), dtype=np.uint8)
        img2 = np.ones((32, 32, 3), dtype=np.uint8) * 100
        scene = self.extractor.encode_with_motion(img2, img1)
        assert "motion_mean" in scene.global_features
        assert scene.global_features["motion_mean"] > 0


class TestObjectDetector:

    def setup_method(self):
        self.detector = ObjectDetector(n_objects=3, min_area=50)

    def test_detect_blobs(self):
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        # 画三个方块
        img[10:30, 10:30] = 200
        img[50:70, 50:70] = 200
        img[70:90, 20:40] = 200
        scene = self.detector.encode(img)
        assert len(scene.objects) >= 1

    def test_extracted_features(self):
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        img[20:40, 20:40] = 255
        scene = self.detector.encode(img)
        if scene.objects:
            obj = scene.objects[0]
            assert "x" in obj.features
            assert "y" in obj.features
            assert "area" in obj.features

    def test_empty_image(self):
        img = np.ones((100, 100, 3), dtype=np.uint8) * 128
        scene = self.detector.encode(img)
        # 均匀图像可能检测不到对象 — 这是正常的


class TestTimeSeriesExtractor:

    def setup_method(self):
        self.extractor = TimeSeriesExtractor(window=50)

    def test_basic_features(self):
        t = np.linspace(0, 10, 200)
        x = np.sin(2 * np.pi * 0.5 * t) + 0.1 * np.random.randn(200)
        scene = self.extractor.encode(x)
        features = scene.variable_dict()
        assert "value_mean" in features
        assert "value_std" in features

    def test_trend_detection(self):
        n = 200
        x = np.linspace(0, 10, n) + 0.1 * np.random.randn(n)
        # 2D shape (n, 1) — single variable
        scene = self.extractor.encode(x.reshape(-1, 1))
        features = scene.variable_dict()
        # 线性趋势应被检测到 — prefix is "V0" for 2D
        assert "V0_trend_linear" in features or "value_trend_linear" in features
        trend_key = "V0_trend_linear" if "V0_trend_linear" in features else "value_trend_linear"
        assert features[trend_key] > 0
        r2_key = "V0_trend_r2" if "V0_trend_r2" in features else "value_trend_r2"
        assert features[r2_key] > 0.5

    def test_period_detection(self):
        t = np.linspace(0, 10, 300)
        x = np.sin(2 * np.pi * 0.3 * t)
        scene = self.extractor.encode(x)
        features = scene.variable_dict()
        assert "value_period" in features

    def test_sliding_window(self):
        t = np.linspace(0, 20, 500)
        x = np.sin(t) + 0.1 * np.random.randn(500)
        scenes = self.extractor.sliding_window_extract(x.reshape(-1, 1))
        assert len(scenes) > 0
