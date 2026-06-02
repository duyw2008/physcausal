"""
PhysCausal Agent 配置管理
"""

import os
import json
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class PhysCausalConfig:
    """全局配置"""

    # 项目路径
    project_root: str = os.path.dirname(os.path.abspath(__file__))

    # 物理层配置
    physics_domains: List[str] = field(default_factory=lambda: [
        "mechanics", "electromagnetism", "thermodynamics", "fluids"
    ])
    physics_tolerance: float = 0.02  # 物理定律验证容差

    # 因果层配置
    discovery_alpha: float = 0.05      # CI 检验显著性水平
    discovery_method: str = "pc"        # pc / fci / ges
    bootstrap_samples: int = 50         # 边置信度自举次数
    auto_method_selection: bool = True  # 自动选择估计器

    # 感知层配置
    perception_backend: str = "simple"  # simple / dinov2 / slot_attn
    feature_dim: int = 128

    # LLM 配置
    llm_provider: str = "deepseek"
    llm_model: str = "deepseek-chat"
    llm_config_path: str = os.path.expanduser("~/.hermes/causal_config.json")

    @property
    def llm_api_key(self) -> Optional[str]:
        if os.getenv("DEEPSEEK_API_KEY"):
            return os.getenv("DEEPSEEK_API_KEY")
        try:
            with open(self.llm_config_path) as f:
                return json.load(f).get("DEEPSEEK_API_KEY")
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return None


# 全局单例
config = PhysCausalConfig()
