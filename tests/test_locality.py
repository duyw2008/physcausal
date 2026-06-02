"""
局域因果测试 — SpacetimeEvent + LocalityValidator + TemporalOrder
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from meta_physics.locality import (
    SpacetimeEvent, LocalityValidator, TemporalOrder, CausalLocalityBridge,
)


class TestSpacetimeEvent:

    def test_same_point_lightlike(self):
        """同一点 → 类光间隔 (Δs²=0)"""
        a = SpacetimeEvent("A", t=0.0, x=0.0)
        b = SpacetimeEvent("B", t=0.0, x=0.0)
        assert abs(a.interval_to(b)) < 1e-10

    def test_timelike_separation(self):
        """类时间隔: 足够大的 Δt"""
        a = SpacetimeEvent("A", t=0.0, x=0.0)
        b = SpacetimeEvent("B", t=2.0, x=1.0)  # Δt=2 > Δx=1
        assert a.is_timelike_to(b)
        assert a.is_in_past_lightcone_of(b)

    def test_spacelike_separation(self):
        """类空间隔: Δx > Δt"""
        a = SpacetimeEvent("A", t=0.0, x=0.0)
        b = SpacetimeEvent("B", t=1.0, x=3.0)  # Δx=3 > Δt=1
        assert a.is_spacelike_to(b)
        assert not a.is_in_past_lightcone_of(b)

    def test_past_lightcone(self):
        """过去光锥判断"""
        past = SpacetimeEvent("past", t=0.0, x=0.0)
        future = SpacetimeEvent("future", t=2.0, x=1.0)
        assert past.is_in_past_lightcone_of(future)
        assert not future.is_in_past_lightcone_of(past)

    def test_future_lightcone(self):
        """未来光锥判断"""
        past = SpacetimeEvent("past", t=0.0, x=0.0)
        future = SpacetimeEvent("future", t=2.0, x=1.0)
        assert future.is_in_future_lightcone_of(past)
        assert not past.is_in_future_lightcone_of(future)


class TestLocalityValidator:

    def setup_method(self):
        self.validator = LocalityValidator()

    def test_valid_timelike_edges(self):
        """类时边应通过验证"""
        spacetime = {
            "A": SpacetimeEvent("A", t=0.0, x=0.0),
            "B": SpacetimeEvent("B", t=2.0, x=1.0),
            "C": SpacetimeEvent("C", t=4.0, x=2.0),
        }
        edges = [("A", "B"), ("B", "C")]
        report = self.validator.validate_dag(edges, spacetime)
        assert report.is_valid
        assert report.valid_edges == 2

    def test_spacelike_edge_rejected(self):
        """类空间隔的边应被拒绝"""
        spacetime = {
            "A": SpacetimeEvent("A", t=0.0, x=0.0),
            "B": SpacetimeEvent("B", t=1.0, x=5.0),  # spacelike!
        }
        edges = [("A", "B")]
        report = self.validator.validate_dag(edges, spacetime)
        assert not report.is_valid
        assert len(report.spacelike_violations) > 0

    def test_time_reversed_edge_rejected(self):
        """时间反向的边应被拒绝"""
        spacetime = {
            "A": SpacetimeEvent("A", t=5.0, x=0.0),  # later
            "B": SpacetimeEvent("B", t=1.0, x=0.0),  # earlier
        }
        edges = [("A", "B")]  # 从晚到早!
        report = self.validator.validate_dag(edges, spacetime)
        assert not report.is_valid

    def test_superluminal_edge_rejected(self):
        """超光速的边应被拒绝"""
        validator = LocalityValidator(speed_of_causation=1.0)
        spacetime = {
            "A": SpacetimeEvent("A", t=0.0, x=0.0),
            "B": SpacetimeEvent("B", t=1.0, x=5.0),  # v=5 > c=1
        }
        edges = [("A", "B")]
        report = validator.validate_dag(edges, spacetime)
        # May be spacelike or superluminal — either way should be rejected
        assert not report.is_valid or len(report.spacelike_violations) > 0

    def test_must_be_d_separated(self):
        """类空间隔的变量必须 d-separated"""
        a = SpacetimeEvent("A", t=0.0, x=0.0)
        b = SpacetimeEvent("B", t=1.0, x=5.0)
        must, reason = self.validator.must_be_d_separated(a, b)
        assert must, reason


class TestTemporalOrder:

    def setup_method(self):
        self.to = TemporalOrder()

    def test_assign_temporal_labels(self):
        """DAG → 时间标签"""
        edges = [("A", "B"), ("A", "C"), ("B", "C")]
        vars_ = ["A", "B", "C"]
        times = self.to.assign_temporal_labels(edges, vars_)
        assert times["A"] < times["B"] < times["C"]

    def test_validate_temporal_order(self):
        """时间序验证"""
        edges = [("A", "B"), ("B", "C")]
        times = {"A": 0.0, "B": 1.0, "C": 2.0}
        ok, violations = self.to.validate_temporal_order(edges, times)
        assert ok
        assert len(violations) == 0

    def test_validate_temporal_order_violation(self):
        """时间序违规"""
        edges = [("B", "A")]  # 从晚到早
        times = {"A": 0.0, "B": 1.0}
        ok, violations = self.to.validate_temporal_order(edges, times)
        assert not ok
        assert len(violations) == 1

    def test_time_cones(self):
        """光锥分区"""
        event = SpacetimeEvent("X", t=2.0, x=1.0)
        spacetime = {
            "X": event,
            "past": SpacetimeEvent("past", t=0.0, x=0.5),
            "future": SpacetimeEvent("future", t=4.0, x=1.5),
            "far": SpacetimeEvent("far", t=2.0, x=10.0),
        }
        cones = self.to.time_cones(event, spacetime)
        assert "past" in cones["past_lightcone"]
        assert "future" in cones["future_lightcone"]
        assert "far" in cones["spacelike_separated"]


class TestCausalLocalityBridge:

    def setup_method(self):
        self.bridge = CausalLocalityBridge()

    def test_verify_valid_dag(self):
        """合法 DAG 通过验证"""
        edges = [("A", "B"), ("B", "C")]
        vars_ = ["A", "B", "C"]
        report = self.bridge.verify_causal_graph(edges, vars_)
        assert report.is_valid

    def test_filter_spacelike_edges(self):
        """过滤类空间隔的边"""
        spacetime = {
            "A": SpacetimeEvent("A", t=0.0, x=0.0),
            "B": SpacetimeEvent("B", t=2.0, x=1.0),   # 类时
            "C": SpacetimeEvent("C", t=1.0, x=10.0),  # 类空
        }
        edges = [("A", "B"), ("A", "C")]
        filtered = self.bridge.filter_spacelike_edges(edges, spacetime)
        assert ("A", "B") in filtered
        assert ("A", "C") not in filtered
