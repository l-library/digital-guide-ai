import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()  # 读取.env文件，把里面的变量加载到环境变量里

# 从环境变量读取配置，而不是写死在代码里
_client = OpenAI(
    api_key=os.getenv("LLM_API_KEY"),
    base_url=os.getenv("LLM_BASE_URL"),   # 国产模型需要这个
)

MODEL_NAME = os.getenv("LLM_MODEL_NAME")


def generate(prompt: str) -> str:
    """
    接收完整prompt，返回LLM的回答文本。
    rag_service.py 构建好prompt后调用这个函数。
    """
    response = _client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=1000,
    )
    return response.choices[0].message.content