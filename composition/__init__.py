"""
组合层 (Composition) — 模块接口 + 类型系统 + 自动对接

composer.py — ModuleInterface + CompositionDiscovery
"""

from composition.composer import (
    TypedPort, ModuleInterface, interface_from_module, CompositionDiscovery,
)

__all__ = [
    "TypedPort", "ModuleInterface", "interface_from_module",
    "CompositionDiscovery",
]
