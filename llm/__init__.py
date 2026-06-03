"""
LLM 层 — DeepSeek 自然语言接口

bridge.py — LLM ↔ PhysCausal 五步管道:
  1. LLM 提取因果图 (语言→结构)
  2. 数据生成 (DAG→SCM→采样)
  3. 物理约束 (元物理过滤)
  4. 效应估计 (识别→ATE)
  5. LLM 自然语言解读 (数字→中文)
"""

from llm.bridge import LLMBridge

__all__ = ["LLMBridge"]
