"""
模拟数据生成脚本
- 创建 10 个普通用户
- 每个用户创建 10 段对话
- 每段对话 1-3 轮问答，AI 回复通过真实后端 API 生成
- 后端进程需在 8000 端口运行
"""

import requests
import random
import time
import sys

BASE_URL = "http://localhost:8000/api/v1"
COMMON_PASSWORD = "test123456"
TIMEOUT = 60  # 单次请求超时(秒)
RETRY_MAX = 2  # 失败重试次数

# ========== 问题库 ==========
# 每轮对话从这些随机选题（景区导览常见问题）
TOURIST_QUESTIONS = [
    "你好，请问这里有什么好玩的？",
    "这个景区的历史背景是什么？",
    "能介绍一下主要景点吗？",
    "游览这里大概需要多长时间？",
    "有什么推荐的游览路线吗？",
    "这个景区有什么特色？",
    "适合带小孩来玩吗？",
    "这里最好的参观季节是什么时候？",
    "有什么必看的地方？",
    "景区内有什么美食推荐？",
    "门票价格是多少？",
    "有什么特别的建筑值得看？",
    "能讲讲这里的历史故事吗？",
    "景区有什么自然风光？",
    "有导游服务吗？",
    "景区开放时间是什么？",
    "有什么适合拍照的地方？",
    "这里的文化底蕴如何？",
    "景区有哪些名人来过？",
    "适合老年人游览吗？",
    "有没有什么传说故事？",
    "景区内交通方便吗？",
    "周边有什么住宿推荐？",
    "有什么纪念品值得买？",
    "这里有什么独特的民俗文化？",
    "景区内有没有庙宇或古迹？",
    "最佳游览时间是早上还是下午？",
    "有没有夜游项目？",
    "这里的花草树木有什么特别的？",
    "景区是不是很大，需要走很多路吗？",
]


def api_post(path: str, data: dict):
    """调用后端 POST 接口，返回 json 或 None"""
    url = f"{BASE_URL}{path}"
    for attempt in range(RETRY_MAX + 1):
        try:
            resp = requests.post(url, json=data, timeout=TIMEOUT)
            # 409 冲突不算网络错误，直接返回响应给调用者处理
            if resp.status_code == 409:
                return resp.json()
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"  [重试 {attempt+1}/{RETRY_MAX}] {url} 失败: {e}")
            if attempt < RETRY_MAX:
                time.sleep(2)
    return None


def register_user(username: str, display_name: str) -> dict | None:
    """注册用户，返回 response data（含 user_id, token）"""
    payload = {
        "username": username,
        "password": COMMON_PASSWORD,
        "confirm_password": COMMON_PASSWORD,
        "display_name": display_name,
    }
    result = api_post("/auth/register", payload)
    if result and result.get("code") == 200:
        return result["data"]
    # 409 用户名已存在：FastAPI 返回 {"detail": "..."} 格式
    if result and ("detail" in result or result.get("code") == 409):
        print(f"    用户 {username} 已存在，尝试登录...")
        login_result = api_post("/auth/login", {
            "username": username,
            "password": COMMON_PASSWORD,
        })
        if login_result and login_result.get("code") == 200:
            return login_result["data"]
    print(f"    注册失败: {result}")
    return None


def create_conversation(user_id: int, title: str) -> int | None:
    """创建对话，返回 conversation_id"""
    result = api_post("/conversations", {
        "user_id": user_id,
        "title": title,
        "knowledge_doc_id": -1,
    })
    if result and result.get("code") == 200:
        return result["data"]["conversation_id"]
    print(f"    创建对话失败: {result}")
    return None


def send_message(conversation_id: int, content: str) -> dict | None:
    """发送消息并获取 AI 回复，返回 response data"""
    result = api_post("/chat/text", {
        "conversation_id": conversation_id,
        "content": content,
        "response_type": 0,  # 仅文字，加快速度
        "digital_human_id": 0,
    })
    if result and result.get("code") == 200:
        return result["data"]
    print(f"    发送消息失败: {result}")
    return None


def main():
    print("=" * 60)
    print("模拟数据生成脚本")
    print(f"后端地址: {BASE_URL}")
    print(f"用户数量: 10，每个用户对话数: 10，每段对话 1-3 轮")
    print("=" * 60)

    # ====== Step 1: 注册 10 个用户 ======
    print("\n[Step 1] 注册用户...")
    users = []
    for i in range(1, 11):
        username = f"testuser{i:02d}"
        display_name = f"游客{i:02d}号"
        print(f"  ({i}/10) 注册 {username}...")
        user_data = register_user(username, display_name)
        if user_data:
            users.append({
                "user_id": user_data["user_id"],
                "username": username,
                "display_name": display_name,
            })
            print(f"    ✓ user_id={user_data['user_id']}")
        else:
            print(f"    ✗ 跳过")
            return  # 出错就停

    print(f"\n✓ 成功注册/登录 {len(users)} 个用户")

    # ====== Step 2: 为每个用户创建对话并发送消息 ======
    total_conv = 0
    total_msg = 0
    overall_start = time.time()

    for u_idx, user in enumerate(users):
        user_start = time.time()
        print(f"\n[Step 2] 用户 {user['username']} (user_id={user['user_id']}) 正在生成对话...")

        # 每用户 10 段对话
        conv_titles = [
            "景区概况咨询", "历史背景了解", "游览路线推荐", "美食小吃探索",
            "拍照打卡攻略", "文化传说探秘", "自然风光欣赏", "亲子游玩建议",
            "交通出行指南", "特色体验项目",
        ]

        for c_idx, title in enumerate(conv_titles):
            conv_id = create_conversation(user["user_id"], title)
            if not conv_id:
                print(f"  ({c_idx+1}/10) 「{title}」创建失败，跳过")
                continue

            # 随机 1-3 轮问答
            num_rounds = random.randint(1, 3)
            # 从问题池随机选不重复的问题
            questions = random.sample(TOURIST_QUESTIONS, min(num_rounds, len(TOURIST_QUESTIONS)))

            print(f"  ({c_idx+1}/10) 「{title}」({num_rounds}轮)...", end=" ", flush=True)

            for q in questions:
                data = send_message(conv_id, q)
                if data:
                    total_msg += 1
                    ai_preview = data.get("content", "")[:30].replace("\n", " ")
                    print(f"[Q:{q[:15]}...→A:{ai_preview}...]", end=" ", flush=True)
                else:
                    print("[失败]", end=" ", flush=True)
                time.sleep(0.5)  # 避免请求过快

            total_conv += 1
            print("✓")

        elapsed = time.time() - user_start
        print(f"  用户 {user['username']} 完成，耗时 {elapsed:.1f}s")

    overall_elapsed = time.time() - overall_start
    print("\n" + "=" * 60)
    print(f"模拟数据生成完成！")
    print(f"  用户数:     {len(users)}")
    print(f"  对话数:     {total_conv}")
    print(f"  消息数:     {total_msg} (含 AI 回复)")
    print(f"  总耗时:     {overall_elapsed:.1f}s")
    print("=" * 60)


if __name__ == "__main__":
    main()
