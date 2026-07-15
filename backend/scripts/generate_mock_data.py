"""
生成均匀时间分布的模拟数据，用于数据大屏展示验证。

- 时间窗口：最近 14 天（UTC），覆盖 dashboard 的 today / week / month 视图
- 数据来源：调用本机 8000 端口 /chat 端点获取真实 AI 回复
- 影响指标：服务人次 / 访客数 / 满意度 / 推荐次数 / 热门问答 / 服务趋势 / 满意度趋势
- 用户消息池：80% 含正面情感词（自然嵌入景区问题），15% 中性景区问题，5% 负面反馈
  → 满意度（正面/总数 × 5）预期 ~4.0，体现指标视觉效果

使用方法（从 backend/ 目录运行）：
    conda activate DGA
    python scripts/generate_mock_data.py

注意：脚本读 DB_PATH 为相对路径 backend/data/app.db，须从仓库根运行。
已有数据不会被修改，仅追加新对话与消息；建议先做备份。
"""
import json
import os
import random
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta

# ----------------------- 配置 -----------------------
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "app.db")
BACKEND_URL = "http://localhost:8000/api/v1/chat"

DAYS_BACK = 14                 # 时间窗口长度（天数）
CONVS_PER_USER = 4             # 每个游客用户生成的对话数
TURNS_PER_CONV = 5             # 每个对话的轮数（用户消息数）
REC_PROB_PER_CONV = 0.5        # 每个对话生成推荐日志的概率
SEED = 42                      # 随机种子（保证可复现）

# 游客用户 ID（admin 不参与）
USER_IDS = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11]

# 消息模板池（80% 正面 / 15% 中性 / 5% 负面）
# 正面模板：景区问题 + 正面关键词（谢谢/帮助/清楚/方便/好/棒/满意 等）
POSITIVE_TEMPLATES = [
    "灵山胜境门票多少钱？谢谢帮助",
    "灵山大佛有多高？讲解得很清楚，谢谢",
    "梵宫开放时间是什么？很方便问您",
    "灵山胜境有什么景点？说得真棒",
    "万佛殿位置在哪？太好了，谢谢",
    "景区怎么走，麻烦讲清楚，谢谢",
    "灵山胜境的历史是怎么样的？讲得真棒",
    "好的，灵山胜境几点关门？方便告诉吗",
    "灵山胜境有多大面积？谢谢，知道了",
    "讲解很满意，灵山胜境的特色是什么？",
    "灵山胜境附近酒店，谢谢推荐，很实用",
    "灵山胜境停车场怎么走？讲解清楚",
    "感谢讲解，灵山胜境美食推荐？",
    "明白了，灵山胜境最佳游览路线？",
    "灵山胜境适合带小朋友吗？谢谢帮助",
]

NEUTRAL_TEMPLATES = [
    "灵山胜境门票多少钱",
    "灵山胜境几点开门",
    "梵宫开放时间",
    "灵山大佛多高",
    "万佛殿位置",
    "灵山胜境有停车场吗",
    "灵山胜境面积多大",
    "灵山胜境最佳游览路线",
    "灵山胜境附近美食",
    "灵山胜境附近酒店",
]

NEGATIVE_TEMPLATES = [
    "讲解的完全不对",
    "听不懂你的回答",
    "都说错了，太差",
    "这个答案不行，没用",
]


# ----------------------- 工具 -----------------------
def call_chat(question: str, timeout: int = 60) -> str:
    """调用后端 /chat 端点获取 AI 回复（单轮、无持久化）"""
    body = json.dumps({"question": question}).encode("utf-8")
    req = urllib.request.Request(
        BACKEND_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data.get("answer", "")


def random_time_on_day(base_date: datetime, hour_range=(9, 18)) -> datetime:
    """在某天的小时范围内随机返回时刻"""
    hour = random.uniform(*hour_range)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return base_date.replace(hour=int(hour), minute=minute, second=second)


def clamp_to_past(dt: datetime, now: datetime) -> datetime:
    """如果时间晚于 now，往前推到 now 之前 1 小时之内"""
    if dt > now:
        dt = now - timedelta(minutes=random.randint(5, 55))
    return dt


# ----------------------- 主流程 -----------------------
def main():
    random.seed(SEED)

    # 检查 DB 与后端
    if not os.path.isfile(DB_PATH):
        sys.exit(f"数据库不存在：{DB_PATH}")
    try:
        probe = call_chat("测试连接", timeout=10)
        print(f"[OK] 后端连通，回复样例：{probe[:30]}...")
    except Exception as e:
        sys.exit(f"无法连接后端 {BACKEND_URL}：{e}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 获取当前最大 ID 作起点
    cur.execute("SELECT MAX(id) FROM conversations")
    max_conv_id = cur.fetchone()[0] or 0
    cur.execute("SELECT MAX(id) FROM messages")
    max_msg_id = cur.fetchone()[0] or 0
    cur.execute("SELECT MAX(id) FROM recommend_logs")
    max_rec_id = cur.fetchone()[0] or 0

    print(f"[INFO] 初始状态：conv_id={max_conv_id}, msg_id={max_msg_id}, rec_id={max_rec_id}")

    # ---------------- 计算所有对话起点 ----------------
    # 对话均匀分布在 14 天，平均每天 ~3 个对话（来自不同用户）
    # 实现策略：为每个用户填入 4 个对话，分别落在 14 天的均匀分段上
    now = datetime.utcnow()
    start_date = now - timedelta(days=DAYS_BACK)

    plan = []  # [(user_id, day_offset, hour_offset_idx, conv_index_for_user)]
    for u in USER_IDS:
        # 4 个对话均匀铺在 14 天上：base = [1, 5, 9, 13]
        # 最后一个对话（index=3）有 50% 概率落在 today (day_offset=DAYS_BACK)
        # hour_range 限制在 0-7 UTC，确保在 now 之前
        day_offsets = []
        for c in range(CONVS_PER_USER):
            base = c * (DAYS_BACK // CONVS_PER_USER) + 1
            jitter = random.randint(-1, 1)
            d = min(max(base + jitter, 0), DAYS_BACK - 1)
            day_offsets.append(d)
        # 50% 用户：把最后一个对话推到 today
        if random.random() < 0.5:
            day_offsets[-1] = DAYS_BACK  # today
        for c, d in enumerate(day_offsets):
            plan.append((u, d, c))

    random.shuffle(plan)  # 打乱以模拟真实顺序
    # 按 day_offset 排序，便于日志查看进度
    plan.sort(key=lambda x: x[1])

    print(f"[INFO] 待生成对话数：{len(plan)}，预计用户消息数：{len(plan) * TURNS_PER_CONV}")

    # ---------------- 逐个生成 ----------------
    conv_id = max_conv_id
    msg_id = max_msg_id
    rec_id = max_rec_id
    total_msgs = 0
    total_recs = 0
    total_calls = 0
    failed_calls = 0

    for idx, (u, day_offset, conv_index_for_user) in enumerate(plan):
        day_dt = start_date + timedelta(days=day_offset)
        # today (day_offset == DAYS_BACK) 时刻限制在 0-7 UTC，确保在 now 之前
        if day_offset >= DAYS_BACK:
            conv_start = random_time_on_day(day_dt, hour_range=(0, 7))
            conv_start = clamp_to_past(conv_start, now)
        else:
            conv_start = random_time_on_day(day_dt)

        # 标题随机取该用户第一条消息的截断
        conv_id += 1
        first_question = random.choice(POSITIVE_TEMPLATES + NEUTRAL_TEMPLATES)
        title = first_question[:20]

        cur.execute(
            "INSERT INTO conversations (id, user_id, title, knowledge_doc_id, created_at, updated_at) "
            "VALUES (?, ?, ?, -1, ?, ?)",
            (conv_id, u, title, conv_start, conv_start)
        )

        prev_time = conv_start
        # 第一轮用上面预选的 first_question，后续轮在 3 类中按比例抽样
        questions = [first_question]
        for _ in range(TURNS_PER_CONV - 1):
            r = random.random()
            if r < 0.80:
                q = random.choice(POSITIVE_TEMPLATES)
            elif r < 0.95:
                q = random.choice(NEUTRAL_TEMPLATES)
            else:
                q = random.choice(NEGATIVE_TEMPLATES)
            questions.append(q)

        for q in questions:
            user_time = prev_time + timedelta(seconds=random.randint(25, 90))

            # 调用后端获取真实 AI 回复
            total_calls += 1
            try:
                answer = call_chat(q)
            except Exception as e:
                failed_calls += 1
                answer = f"（AI 回复失败：{e}）"

            # 写入用户消息
            msg_id += 1
            cur.execute(
                "INSERT INTO messages (id, conversation_id, role, content, audio_url, created_at) "
                "VALUES (?, ?, 'user', ?, NULL, ?)",
                (msg_id, conv_id, q, user_time)
            )
            total_msgs += 1

            # 写入 AI 回复（间隔 2-6 秒）
            ai_time = user_time + timedelta(seconds=random.randint(2, 6))
            msg_id += 1
            cur.execute(
                "INSERT INTO messages (id, conversation_id, role, content, audio_url, created_at) "
                "VALUES (?, ?, 'assistant', ?, NULL, ?)",
                (msg_id, conv_id, answer, ai_time)
            )
            total_msgs += 1
            prev_time = ai_time + timedelta(seconds=random.randint(5, 20))

        # 推荐日志
        if random.random() < REC_PROB_PER_CONV:
            rec_time = conv_start + timedelta(minutes=random.randint(10, 40))
            # 推荐时间必须在 now 之前
            if rec_time > now:
                rec_time = now - timedelta(minutes=random.randint(1, 30))
            rec_id += 1
            interests = random.choice([
                '["历史", "建筑"]',
                '["文化", "建筑"]',
                '["美食", "建筑"]',
                '["历史", "文化"]',
            ])
            cur.execute(
                "INSERT INTO recommend_logs (id, user_id, interests_used, created_at) "
                "VALUES (?, ?, ?, ?)",
                (rec_id, u, interests, rec_time)
            )
            total_recs += 1

        # 更新会话 updated_at
        cur.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (prev_time, conv_id)
        )

        conn.commit()
        print(f"  [{idx+1}/{len(plan)}] 用户 {u} 第 {conv_index_for_user+1} 个对话："
              f"conv_id={conv_id}, day-0={day_offset}, 时间={conv_start.hour:02d}:{conv_start.minute:02d}，"
              f"累计消息={total_msgs}")

    conn.commit()
    conn.close()

    print()
    print("=" * 60)
    print(f"[完成] 新增对话：{len(plan)} 个")
    print(f"[完成] 新增消息：{total_msgs} 条（含 AI 回复）")
    print(f"[完成] 新增推荐日志：{total_recs} 条")
    print(f"[完成] 后端调用：{total_calls} 次，失败：{failed_calls} 次")
    print(f"[完成] 时间窗口：过去 {DAYS_BACK} 天（UTC）")


if __name__ == "__main__":
    main()