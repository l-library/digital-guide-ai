"""
LLM 提示词配置加载器
从 config/prompts.yaml 读取所有提示词模板，提供格式化接口。
加载一次后缓存，避免重复 I/O。
"""
import os
import yaml

_CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
_PROMPTS_PATH = os.path.join(_CONFIG_DIR, "prompts.yaml")
_cache: dict | None = None


def _load_prompts() -> dict:
    """懒加载 + 缓存 YAML 提示词配置"""
    global _cache
    if _cache is None:
        with open(_PROMPTS_PATH, "r", encoding="utf-8") as f:
            _cache = yaml.safe_load(f)
    return _cache


# ── 公开接口 ──


def get_rag_guide_prompt(context_text: str, query: str) -> str:
    """构建 RAG 导游回答 prompt"""
    template = _load_prompts()["rag_guide"]
    return template.format(context_text=context_text, query=query)


def get_title_system_prompt() -> str:
    """获取标题生成的 system prompt"""
    return _load_prompts()["title_generation_system"]


def get_title_user_prompt(user_content: str, assistant_content: str) -> str:
    """构建标题生成的 user prompt（截取前200字）"""
    template = _load_prompts()["title_generation_user"]
    return template.format(
        user_content=user_content[:200],
        assistant_content=assistant_content[:200],
    )


def get_emotion_summary_prompt(questions_text: str) -> str:
    """构建情感摘要分析 prompt"""
    template = _load_prompts()["emotion_summary"]
    return template.format(questions_text=questions_text)


def get_service_suggestions_prompt(questions_text: str) -> str:
    """构建服务改进建议 prompt"""
    template = _load_prompts()["service_suggestions"]
    return template.format(questions_text=questions_text)
