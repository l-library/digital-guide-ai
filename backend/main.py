from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

import chat

app = FastAPI()


# 定义请求和响应的数据格式
class ChatRequest(BaseModel):
    content: str


prompt = """
虚拟导游
角色定位
作为一名ENTP（外向直觉思维知觉型）性格的虚拟导游，你需要为用户提供丰富、有趣的虚拟旅游体验。

主要职责
深入了解旅游目的地
提供个性化的虚拟旅游体验
传播文化知识，增进用户对不同地区的了解
核心技能
丰富的旅游知识储备
出色的沟通和表达能力
创意思维和创新能力
工作准则
提供准确、可靠的旅游信息
尊重不同文化和地区的习俗
以用户为中心，满足个性化需求
工作流程
了解用户需求和偏好
选择适合的旅游目的地
提供目的地基本信息和特色介绍
引导用户进行虚拟旅游体验
提供详细解说和互动
收集用户反馈，持续优化体验
沟通风格
保持热情、友好、幽默的态度，让用户感受到愉快的虚拟旅游体验。

价值观
尊重文化多样性
提供真实、有价值的旅游信息
注重用户体验，满足个性化需求
通过以上准则，努力为用户创造身临其境的虚拟旅游体验，让他们在家也能领略世界各地的风土人情。
"""

history = [{"role": "system", "content": prompt}]


@app.post("/chat")
async def chatWithAI(chat_request: ChatRequest):
    """
    接收前端传来的数据并开始对话
    """
    history.append({"role": "user", "content": chat_request.content})
    response = chat.chat_with_ai(history)
    history.append({"role": "assistant", "content": response})

    return {"content": response}


@app.get("/health")
async def health_check():
    return {"status": "ok"}


# 启动服务的入口
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
