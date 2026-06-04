"""Tests for sensitivity analysis and physics engine."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from causal.graph import CausalDAG
from causal.discovery import generate_linear_data
from causal.estimation import estimate_effect
from causal.sensitivity import e_value, rosenbaum_bounds, full_sensitivity_report


class TestSensitivity:
    @classmethod
    def setup_class(cls):
        dag = CausalDAG(["G", "D", "R"], [("G", "D"), ("G", "R"), ("D", "R")])
        data = generate_linear_data(dag, 1000, seed=42)
        cls.est = estimate_effect(data, ["G", "D", "R"], "D", "R", ["G"], "linear")

    def test_evalue_positive(self):
        ev = e_value(self.est.ate, self.est.std_error)
        assert ev.e_value > 1.0

    def test_evalue_ci_positive(self):
        ev = e_value(self.est.ate, self.est.std_error)
        assert ev.e_value_ci is not None

    def test_rosenbaum_threshold(self):
        rb = rosenbaum_bounds(self.est.ate, self.est.std_error)
        assert rb.gamma_threshold >= 1.0

    def test_full_report(self):
        report = full_sensitivity_report(self.est.ate, self.est.std_error)
        assert "SENSITIVITY" in report
        assert "E-value" in report
        assert "Rosenbaum" in report


class TestPhysics:
    def test_library_counts(self):
        from physics.laws import library
        laws = library.list_all()
        assert len(laws) >= 22

    def test_domain_list(self):
        from physics.laws import library
        domains = set(l.domain for l in library.list_all())
        assert "mechanics" in domains
        assert "electromagnetism" in domains
        assert "optics" in domains
        assert "acoustics" in domains

    def test_find_relevant(self):
        from physics.laws import library
        laws = library.find_relevant(["force", "mass", "acceleration"])
        assert len(laws) >= 1

    def test_forbidden_edges(self):
        from physics.laws import library
        forbidden = library.forbidden_edges(["temperature", "kinetic_energy"])
        assert ("temperature", "kinetic_energy") in forbidden
