"""
共享配置 — 去重 ZH_MAP + physics_prior

避免三份重复代码:
  - llm/bridge.py
  - active_experiment/active_learner.py  
  - reinforcement/causal_rl.py
"""

ZH_MAP = {
    "力": "force", "质量": "mass", "加速度": "acceleration",
    "速度": "velocity", "位移": "displacement", "时间": "time",
    "能量": "energy", "动量": "momentum", "功": "work",
    "电压": "voltage", "电流": "current", "电阻": "resistance",
    "功率": "power", "温度": "temperature", "压力": "pressure",
    "体积": "volume", "密度": "density", "长度": "length",
    "频率": "frequency", "周期": "period",
    "分子运动": "kinetic_energy", "动能": "kinetic_energy",
    "分子动能": "kinetic_energy", "分子运动加剧": "kinetic_energy",
    "波长": "wavelength", "声速": "wave_speed",
    "入射角": "incident_angle", "折射角": "refraction_angle",
    "反射角": "reflection_angle", "焦距": "focal_length",
    "物距": "object_distance", "像距": "image_distance",
    "截面积": "cross_section", "流速": "flow_rate",
    "磁通量": "magnetic_flux_change", "感应电流": "induced_current",
    "热量": "heat_power", "声源速度": "source_velocity",
    "观测频率": "observed_frequency",
    # 仿真环境变量名映射
    "V": "voltage", "R": "resistance", "I": "current",
    "L": "length", "g": "g", "T": "period",
    "k": "elastic_constant", "omega": "angular_velocity",
    # collision — 保持原名以匹配动量守恒定律
    "v1p": "v1_prime", "v2p": "v2_prime",
    "flux_change": "magnetic_flux_change", "coil_turns": "coil_turns",
    "induced_emf": "induced_emf",
    "n1": "n1", "theta1": "incident_angle",
    "n2": "n2", "theta2": "refraction_angle",
    "source_freq": "source_frequency", "source_vel": "source_velocity",
    "observer_vel": "observer_velocity", "observed_freq": "observed_frequency",
    # 新环境
    "temp": "temperature", "pres": "pressure", "vol": "volume",
    "fluid_density": "fluid_density", "buoyant_force": "buoyant_force",
    "charge": "charge", "magnetic_field": "magnetic_field", "lorentz_force": "lorentz_force",
    # 量子/GR 新环境
    "momentum": "momentum", "wavelength": "wavelength",
    "quantum_number": "quantum_number", "energy_level": "energy_level",
    "schwarzschild_radius": "schwarzschild_radius",
    "dilated_time": "dilated_time",
    "frequency_shift": "frequency_shift",
    "height": "height",
    # 量子测量
    "波函数": "wave_function", "测量": "measurement",
    "本征值": "eigenvalue", "本征态": "post_measurement_state",
    "坍缩": "post_measurement_state", "测量后状态": "post_measurement_state",
    "环境": "environment_coupling", "退相干": "mixed_state",
    "混合态": "mixed_state",
    "粒子数": "particle_count", "坍缩概率": "collapse_probability",
    "客观坍缩": "collapse_probability",
    # Jacobi / Kaluza-Klein
    "测地线": "geodesic_path", "势能": "potential_energy",
    "高维度规": "higher_d_metric", "紧致维": "compact_dimension",
    "规范场": "gauge_field", "标量场": "scalar_field",
    "投影": "geodesic_path", "高维": "higher_d_metric",
}


def physics_prior(variables: list):
    """从物理定律库获取已知因果结构 (零计算代价)

    支持多对一映射: 当多个 env 变量映射到同一个 law 变量时
    (如 m1,m2 → "mass")，生成所有组合边。
    """
    from physics.laws import library
    vars_en = [ZH_MAP.get(v, v.lower()) for v in variables]
    edges = set()
    for law in library.list_all():
        for src, dst in law.causal_direction:
            src_indices = [i for i, v in enumerate(vars_en) if v == src]
            dst_indices = [i for i, v in enumerate(vars_en) if v == dst]
            for si in src_indices:
                for di in dst_indices:
                    if si != di:  # 排除自环
                        edges.add((variables[si], variables[di]))
    return list(edges) if edges else []
