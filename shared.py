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
    "L": "length", "g": "gravity", "T": "period",
    "k": "elastic_constant", "m": "mass", "omega": "angular_velocity",
    "m1": "mass", "m2": "mass", "v1": "velocity", "v2": "velocity",
    "v1p": "velocity", "v2p": "velocity",
    "flux_change": "magnetic_flux_change", "coil_turns": "coil_turns",
    "induced_emf": "induced_emf",
    "n1": "refractive_index", "theta1": "incident_angle",
    "n2": "refractive_index", "theta2": "refraction_angle",
    "source_freq": "source_frequency", "source_vel": "source_velocity",
    "observer_vel": "observer_velocity", "observed_freq": "observed_frequency",
}


def physics_prior(variables: list):
    """从物理定律库获取已知因果结构 (零计算代价)"""
    from physics.laws import library
    vars_en = [ZH_MAP.get(v, v.lower()) for v in variables]
    edges = set()
    for law in library.list_all():
        for src, dst in law.causal_direction:
            if src in vars_en and dst in vars_en:
                si = vars_en.index(src)
                di = vars_en.index(dst)
                edges.add((variables[si], variables[di]))
    return list(edges) if edges else []
