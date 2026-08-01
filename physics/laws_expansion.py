"""
物理定律扩张 — EM/光学/声学/现代物理/相对论/尺度桥接

被 physics/laws.py 的 _register_default_laws() 尾部调用。
"""

from __future__ import annotations
import numpy as np
from physics.laws import PhysicsLaw, ConstraintType


def register_expansion_laws(library) -> int:
    """返回注册的定律数"""
    count = 0

    # ═══════════════════════════════════════════════════════
    # 电磁学扩展 (8)
    # ═══════════════════════════════════════════════════════

    library.register(PhysicsLaw(
        name="Maxwell-Faraday", domain="electromagnetism",
        latex=r"\nabla \times \mathbf{E} = -\frac{\partial \mathbf{B}}{\partial t}",
        inputs=["magnetic_field_change"],
        outputs=["induced_e_field"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda dBdt: -dBdt,
        causal_direction=[("magnetic_field_change", "induced_e_field")],
    )); count += 1

    library.register(PhysicsLaw(
        name="Maxwell-Ampere", domain="electromagnetism",
        latex=r"\nabla \times \mathbf{B} = \mu_0 \mathbf{J} + \mu_0 \epsilon_0 \frac{\partial \mathbf{E}}{\partial t}",
        inputs=["current_density", "e_field_change"],
        outputs=["magnetic_field"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda J, dEdt: J + dEdt,
        causal_direction=[("current_density", "magnetic_field"),
                          ("e_field_change", "magnetic_field")],
    )); count += 1

    library.register(PhysicsLaw(
        name="EM Wave", domain="electromagnetism",
        latex=r"\frac{\partial^2 \mathbf{E}}{\partial t^2} = c^2 \nabla^2 \mathbf{E}",
        inputs=["e_field_oscillation", "magnetic_field_oscillation"],
        outputs=["em_radiation"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda E, B: np.sqrt(E**2 + B**2),
        causal_direction=[("e_field_oscillation", "em_radiation"),
                          ("magnetic_field_oscillation", "em_radiation")],
    )); count += 1

    library.register(PhysicsLaw(
        name="Dipole Radiation", domain="electromagnetism",
        latex=r"P = \frac{\mu_0 p_0^2 \omega^4}{12\pi c}",
        inputs=["dipole_moment", "frequency"],
        outputs=["radiated_power"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda p, f: p**2 * f**4,
        causal_direction=[("dipole_moment", "radiated_power"),
                          ("frequency", "radiated_power")],
    )); count += 1

    library.register(PhysicsLaw(
        name="Gauss-Electric", domain="electromagnetism",
        latex=r"\oint \mathbf{E} \cdot d\mathbf{A} = \frac{Q}{\epsilon_0}",
        inputs=["charge"],
        outputs=["e_field_flux"],
        constraint_type=ConstraintType.CONSERVATION,
        formula=lambda Q: Q,
        causal_direction=[("charge", "e_field_flux")],
    )); count += 1

    library.register(PhysicsLaw(
        name="Gauss-Magnetic", domain="electromagnetism",
        latex=r"\oint \mathbf{B} \cdot d\mathbf{A} = 0",
        inputs=[],
        outputs=["no_magnetic_monopole"],
        constraint_type=ConstraintType.CONSERVATION,
        formula=lambda: 0.0,
        causal_direction=[],
    )); count += 1

    library.register(PhysicsLaw(
        name="Waveguide Cutoff", domain="electromagnetism",
        latex=r"f_c = \frac{c}{2a}",
        inputs=["waveguide_width", "frequency"],
        outputs=["propagation_mode"],
        constraint_type=ConstraintType.BOUNDARY,
        formula=lambda a, f: 1.0 if f > 1.0/(2*a) else 0.0,
        causal_direction=[("waveguide_width", "propagation_mode"),
                          ("frequency", "propagation_mode")],
    )); count += 1

    library.register(PhysicsLaw(
        name="Plasma Frequency", domain="electromagnetism",
        latex=r"\omega_p = \sqrt{\frac{n_e e^2}{\epsilon_0 m_e}}",
        inputs=["electron_density"],
        outputs=["plasma_frequency"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda ne: np.sqrt(ne),
        causal_direction=[("electron_density", "plasma_frequency")],
    )); count += 1

    # ═══════════════════════════════════════════════════════
    # 光学扩展 (6)
    # ═══════════════════════════════════════════════════════

    library.register(PhysicsLaw(
        name="Interference", domain="optics",
        latex=r"I = I_1 + I_2 + 2\sqrt{I_1 I_2}\cos\Delta\phi",
        inputs=["path_difference", "wavelength"],
        outputs=["intensity_pattern"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda dx, wl: np.cos(2*np.pi*dx/wl),
        causal_direction=[("path_difference", "intensity_pattern"),
                          ("wavelength", "intensity_pattern")],
    )); count += 1

    library.register(PhysicsLaw(
        name="Diffraction", domain="optics",
        latex=r"d\sin\theta = m\lambda",
        inputs=["aperture_size", "wavelength"],
        outputs=["diffraction_angle"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda d, wl: np.arcsin(wl/d) if d > wl else np.pi/2,
        causal_direction=[("aperture_size", "diffraction_angle"),
                          ("wavelength", "diffraction_angle")],
    )); count += 1

    library.register(PhysicsLaw(
        name="Polarization-Malus", domain="optics",
        latex=r"I = I_0 \cos^2\theta",
        inputs=["incident_intensity", "polarization_angle"],
        outputs=["transmitted_intensity"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda I0, theta: I0 * np.cos(theta)**2,
        causal_direction=[("incident_intensity", "transmitted_intensity"),
                          ("polarization_angle", "transmitted_intensity")],
    )); count += 1

    library.register(PhysicsLaw(
        name="Brewster", domain="optics",
        latex=r"\theta_B = \arctan(n_2/n_1)",
        inputs=["n1", "n2"],
        outputs=["brewster_angle"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda n1, n2: np.arctan(n2/n1),
        causal_direction=[("n1", "brewster_angle"), ("n2", "brewster_angle")],
    )); count += 1

    library.register(PhysicsLaw(
        name="ThinFilm", domain="optics",
        latex=r"2nd\cos\theta = m\lambda",
        inputs=["film_thickness", "refractive_index", "wavelength"],
        outputs=["interference_color"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda d, n, wl: np.cos(2*np.pi*2*n*d/wl),
        causal_direction=[("film_thickness", "interference_color"),
                          ("refractive_index", "interference_color"),
                          ("wavelength", "interference_color")],
    )); count += 1

    library.register(PhysicsLaw(
        name="Grating", domain="optics",
        latex=r"d(\sin\theta_i + \sin\theta_m) = m\lambda",
        inputs=["groove_spacing", "wavelength"],
        outputs=["diffraction_order"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda d, wl: int(d/wl) if wl > 0 else 0,
        causal_direction=[("groove_spacing", "diffraction_order"),
                          ("wavelength", "diffraction_order")],
    )); count += 1

    # ═══════════════════════════════════════════════════════
    # 声学扩展 (5)
    # ═══════════════════════════════════════════════════════

    library.register(PhysicsLaw(
        name="WaveEquation", domain="acoustics",
        latex=r"\frac{\partial^2 p}{\partial t^2} = c_s^2 \nabla^2 p",
        inputs=["bulk_modulus", "density"],
        outputs=["sound_speed"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda K, rho: np.sqrt(K/rho),
        causal_direction=[("bulk_modulus", "sound_speed"),
                          ("density", "sound_speed")],
    )); count += 1

    library.register(PhysicsLaw(
        name="Resonance-Tube", domain="acoustics",
        latex=r"f_n = n\frac{c}{2L}",
        inputs=["tube_length", "sound_speed"],
        outputs=["resonant_frequency"],
        constraint_type=ConstraintType.BOUNDARY,
        formula=lambda L, c: c/(2*L),
        causal_direction=[("tube_length", "resonant_frequency"),
                          ("sound_speed", "resonant_frequency")],
    )); count += 1

    library.register(PhysicsLaw(
        name="StandingWave", domain="acoustics",
        latex=r"p(x,t) = 2A\cos(kx)\sin(\omega t)",
        inputs=["frequency", "sound_speed"],
        outputs=["node_positions"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda f, c: c/(2*f),
        causal_direction=[("frequency", "node_positions"),
                          ("sound_speed", "node_positions")],
    )); count += 1

    library.register(PhysicsLaw(
        name="SoundLevel", domain="acoustics",
        latex=r"L = 10\log_{10}(I/I_0)",
        inputs=["sound_intensity"],
        outputs=["sound_level_dB"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda I: 10*np.log10(max(I, 1e-12)),
        causal_direction=[("sound_intensity", "sound_level_dB")],
    )); count += 1

    library.register(PhysicsLaw(
        name="AcousticImpedance", domain="acoustics",
        latex=r"Z = \rho c",
        inputs=["density", "sound_speed"],
        outputs=["acoustic_impedance"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda rho, c: rho * c,
        causal_direction=[("density", "acoustic_impedance"),
                          ("sound_speed", "acoustic_impedance")],
    )); count += 1

    # ═══════════════════════════════════════════════════════
    # 现代物理扩展 (6)
    # ═══════════════════════════════════════════════════════

    library.register(PhysicsLaw(
        name="NuclearBinding", domain="modern",
        latex=r"B = a_v A - a_s A^{2/3} - a_c Z(Z-1)/A^{1/3} - a_a (A-2Z)^2/A",
        inputs=["nucleon_count", "proton_count"],
        outputs=["binding_energy"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda A, Z: 15.75*A - 17.8*A**(2/3),
        causal_direction=[("nucleon_count", "binding_energy"),
                          ("proton_count", "binding_energy")],
    )); count += 1

    library.register(PhysicsLaw(
        name="RadioactiveDecay", domain="modern",
        latex=r"N(t) = N_0 e^{-\lambda t}",
        inputs=["half_life", "time"],
        outputs=["remaining_fraction"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda T, t: np.exp(-np.log(2)*t/T),
        causal_direction=[("half_life", "remaining_fraction"),
                          ("time", "remaining_fraction")],
    )); count += 1

    library.register(PhysicsLaw(
        name="BandGap", domain="modern",
        latex=r"E_g = f(\text{crystal})",
        inputs=["crystal_structure"],
        outputs=["energy_gap"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda s: 1.0,
        causal_direction=[("crystal_structure", "energy_gap")],
    )); count += 1

    library.register(PhysicsLaw(
        name="Superconductivity", domain="modern",
        latex=r"T < T_c \Rightarrow R = 0",
        inputs=["temperature", "critical_temperature"],
        outputs=["electrical_resistance"],
        constraint_type=ConstraintType.BOUNDARY,
        formula=lambda T, Tc: 0.0 if T < Tc else 1.0,
        causal_direction=[("temperature", "electrical_resistance"),
                          ("critical_temperature", "electrical_resistance")],
    )); count += 1

    library.register(PhysicsLaw(
        name="ComptonScattering", domain="modern",
        latex=r"\Delta\lambda = \frac{h}{m_e c}(1-\cos\theta)",
        inputs=["scattering_angle"],
        outputs=["wavelength_shift"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda theta: 0.00243*(1-np.cos(theta)),
        causal_direction=[("scattering_angle", "wavelength_shift")],
    )); count += 1

    library.register(PhysicsLaw(
        name="PairProduction", domain="modern",
        latex=r"E_\gamma \geq 2m_e c^2",
        inputs=["photon_energy"],
        outputs=["electron_creation", "positron_creation"],
        constraint_type=ConstraintType.BOUNDARY,
        formula=lambda E: 1.0 if E > 1.022 else 0.0,
        causal_direction=[("photon_energy", "electron_creation"),
                          ("photon_energy", "positron_creation")],
    )); count += 1

    # ═══════════════════════════════════════════════════════
    # 相对论扩展 (4)
    # ═══════════════════════════════════════════════════════

    library.register(PhysicsLaw(
        name="TimeDilation", domain="relativity",
        latex=r"\Delta t = \gamma \Delta t_0",
        inputs=["velocity"],
        outputs=["time_dilation_factor"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda v: 1/np.sqrt(max(1-v**2, 1e-10)) if v < 1 else float('inf'),
        causal_direction=[("velocity", "time_dilation_factor")],
    )); count += 1

    library.register(PhysicsLaw(
        name="LengthContraction", domain="relativity",
        latex=r"L = L_0 / \gamma",
        inputs=["velocity"],
        outputs=["length_contraction_factor"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda v: np.sqrt(max(1-v**2, 1e-10)),
        causal_direction=[("velocity", "length_contraction_factor")],
    )); count += 1

    library.register(PhysicsLaw(
        name="RelativisticEnergy", domain="relativity",
        latex=r"E = \gamma m c^2",
        inputs=["mass", "velocity"],
        outputs=["relativistic_energy"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda m, v: m/np.sqrt(max(1-v**2, 1e-10)),
        causal_direction=[("mass", "relativistic_energy"),
                          ("velocity", "relativistic_energy")],
    )); count += 1

    library.register(PhysicsLaw(
        name="GravitationalRedshift", domain="relativity",
        latex=r"\frac{\Delta\lambda}{\lambda} = \frac{GM}{Rc^2}",
        inputs=["mass", "radius"],
        outputs=["wavelength_shift"],
        constraint_type=ConstraintType.SCM_EQUATION,
        formula=lambda M, R: M/R if R > 0 else 0,
        causal_direction=[("mass", "wavelength_shift"),
                          ("radius", "wavelength_shift")],
    )); count += 1

    return count
