import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()  # 读取.env文件，把里面的变量加载到环境变量里

MODEL_NAME = os.getenv("LLM_MODEL_NAME")

_client = None


def _get_client():
    """懒加载 OpenAI 客户端，避免模块导入时因缺少 .env 而报错"""
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL"),
        )
    return _client


def generate(prompt: str) -> str:
    """
    接收完整prompt，返回LLM的回答文本。
    rag_service.py 构建好prompt后调用这个函数。
    """
    response = _get_client().chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=1000,
    )
    return response.choices[0].message.content


def generate_stream(messages: list[dict]) -> any:
    """
    流式生成：接收 messages 列表（含历史对话），逐 token 产出。
    用于 WebSocket 推送打字机效果。
    """
    stream = _get_client().chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0.7,
        max_tokens=1000,
        stream=True,
    )
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content