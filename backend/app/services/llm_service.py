import asyncio
import os
from openai import OpenAI, AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()  # 读取.env文件，把里面的变量加载到环境变量里
import logging
logger = logging.getLogger(__name__)

MODEL_NAME = os.getenv("LLM_MODEL_NAME")

_client = None
_async_client = None


def _get_client():
    """懒加载同步 OpenAI 客户端，避免模块导入时因缺少 .env 而报错"""
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL"),
        )
    return _client


def _get_async_client() -> AsyncOpenAI:
    """懒加载异步 OpenAI 客户端，用于流式生成"""
    global _async_client
    if _async_client is None:
        _async_client = AsyncOpenAI(
            api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL"),
        )
    return _async_client


def generate(prompt: str, timeout: float = 60, max_tokens: int = 1000) -> str:
    """
    接收完整prompt，返回LLM的回答文本。
    rag_service.py 构建好prompt后调用这个函数。
    timeout 参数控制请求超时时间（秒），默认 60 秒。
    max_tokens 参数控制最大生成 token 数，默认 1000。
    注意：DeepSeek 推理模型的 reasoning_content 也消耗 max_tokens 配额，
    生成复杂 JSON 时需传更大的值（如 4000）避免截断。
    """
    response = _get_client().chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=max_tokens,
        timeout=timeout,
    )
    content = response.choices[0].message.content
    # DeepSeek 推理模型偶尔 content 为空，回退到 reasoning_content
    if not content:
        content = getattr(response.choices[0].message, "reasoning_content", None) or ""
    return content


async def generate_stream_async(messages: list[dict]):
    """
    异步流式生成：接收 messages 列表（含历史对话），逐 token 产出。
    用于 WebSocket 和 SSE 流式推送。
    """
    client = _get_async_client()
    stream = await client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0.7,
        max_tokens=1000,
        stream=True,
    )
    async for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


async def generate_title_async(user_content: str, assistant_content: str) -> str:
    """
    根据第一轮对话内容自动生成简洁标题。
    截取内容前200字避免过长输入，标题限制20字，空时回退到"新对话"。
    使用同步客户端 + run_in_executor，避免 AsyncOpenAI 非流式响应中 content 为空的问题。
    """
    client = _get_client()  # 同步客户端（generate() 已验证可用）

    def _call():
        from app.config.prompt_loader import get_title_system_prompt, get_title_user_prompt

        return client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": get_title_system_prompt()},
                {"role": "user", "content": get_title_user_prompt(user_content, assistant_content)},
            ],
            temperature=0.3,
            max_tokens=50,
            extra_body={"thinking": {"type": "disabled"}}
        )

    response = await asyncio.to_thread(_call)
    content = response.choices[0].message.content

    # 兼容 DeepSeek 推理模型：reasoning_content 可能有值而 content 为空
    if not content:
        msg = response.choices[0].message
        content = getattr(msg, "reasoning_content", None)

    if not content:
        return "新对话"
    title = content.strip().strip('"').strip("'")
    if len(title) > 20:
        title = title[:20]
    return title if title else "新对话"
