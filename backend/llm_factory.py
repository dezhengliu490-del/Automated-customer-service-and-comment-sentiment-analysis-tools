"""LLM 工厂：根据配置实例化具体的 LLM 服务提供者。"""

import os
from llm_base import LLMService

def get_llm_service(
    provider: str | None = None,
    api_key: str | None = None,
    model: str | None = None
) -> LLMService:
    """
    根据给定的提供商返回具体的 LLM 实例。
    如果未提供参数，则从环境变量中读取。
    """
    from config import get_llm_provider
    
    # 优先使用传入参数，其次使用环境变量
    active_provider = (provider or get_llm_provider()).lower().strip()

    if active_provider == "gemini":
        from gemini_service import GeminiService
        return GeminiService(api_key=api_key, model=model)

    elif active_provider == "deepseek":
        from deepseek_service import DeepSeekService
        return DeepSeekService(api_key=api_key, model=model)

    elif active_provider == "openai":
        from openai_service import OpenAIService
        return OpenAIService(api_key=api_key, model=model)

    else:
        raise ValueError(f"不受支持的 LLM 提供商: {active_provider}")
