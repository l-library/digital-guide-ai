from openai import OpenAI
import os

# 使用环境变量获取API KEY
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com/v1"
)


# 与deepseek chat对话
def chat_with_ai(user_input, tem=0.7):
    response = client.chat.completions.create(
        model="deepseek-chat", messages=user_input, temperature=tem, max_tokens=2048
    )
    # 获取最终答案
    content = response.choices[0].message.content
    return content


# 与deepseek-reasoner对话
def chat_with_deepseek_reasoner(user_input, tem=0.7):
    response = client.chat.completions.create(
        model="deepseek-reasoner", messages=user_input, temperature=tem, max_tokens=2048
    )
    # 获取思考过程和最终答案
    reasoning_content = response.choices[0].message.reasoning_content
    content = response.choices[0].message.content
    return reasoning_content, content
