"""流式处理共享工具函数。"""

from app.services.rag_service import build_prompt


def build_llm_messages(
    history_msgs: list,
    user_query: str,
    context_list: list[str],
) -> list[dict]:
    """根据对话历史构建发送给 LLM 的消息列表。
    首轮对话（≤2条消息）使用完整 RAG prompt，
    多轮对话使用 system message + 上下文 + 完整历史。
    """
    messages = [{"role": m.role, "content": m.content} for m in history_msgs]

    if len(messages) <= 2:
        prompt = build_prompt(user_query, context_list)
        return [{"role": "user", "content": prompt}]

    system_msg = {
        "role": "system",
        "content": (
            "你是一名经验丰富的景区导游。作为一名导游，你需要为用户提供丰富、有趣的旅行体验。"
            "核心技能：丰富的旅游知识储备、出色的沟通和表达能力、创意思维和创新能力"
            "你的工作准则是提供准确、可靠的旅游信息、尊重不同文化和地区的习俗、以用户为中心，满足个性化需求"
            "工作流程：了解用户需求和偏好、引导用户说出自己的需求、提供详细解说和互动、收集用户反馈，持续优化体验"
            "沟通风格：保持热情、友好、幽默的态度，让用户感受到愉快的虚拟旅游体验。"
            "价值观：尊重文化多样性、提供真实、有价值的旅游信息、注重用户体验，满足个性化需求"
            "语气自然亲切。不要使用emoji或动作描写。"
            "回复请控制在2-4句话以内，每句话简洁明了，总字数不超过150字。"
            "如果资料中没有相关信息，请如实告知。"
        ),
    }
    context_msg = {
        "role": "system",
        "content": f"参考景区资料：\n{chr(10).join(context_list)}",
    }
    history_without_last = messages[:-1]
    last_user_msg = messages[-1]
    return [system_msg, context_msg] + history_without_last + [last_user_msg]
