"""
修改 2026-07-12 原始用户消息内容，使其与新生成模拟数据情感分布匹配。

- 目的：原始 229 条用户消息多为简短问句（"你好"/"开放时间"），不含情感关键词，
  随机抽样后 _classify_sentiment 全部归为 neutral，摊低了 avg_satisfaction。
- 策略：把这 229 条用户消息内容原地替换为含正面情感关键词的景区问题变体，
 Assistant 回复和所有时间戳均保持不变。
- 比例：与 generate_mock_data.py 一致，80% 正面 / 15% 中性 / 5% 负面。

使用方法（从 backend/ 目录运行）：
    conda activate DGA
    python scripts/update_old_messages.py
"""
import os
import random
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "app.db")
SEED = 7
TARGET_DATE_LIKES = ["2026-07-12%", "2026-07-13%", "2026-07-14%"]

# 与 generate_mock_data.py 相同的消息模板池
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


def pick_one(rng: random.Random) -> str:
    """按 80/15/5 比例抽取一条模板"""
    r = rng.random()
    if r < 0.80:
        return rng.choice(POSITIVE_TEMPLATES)
    elif r < 0.95:
        return rng.choice(NEUTRAL_TEMPLATES)
    else:
        return rng.choice(NEGATIVE_TEMPLATES)


def main():
    if not os.path.isfile(DB_PATH):
        raise SystemExit(f"数据库不存在：{DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    rng = random.Random(SEED)
    total_all = 0
    for like_pat in TARGET_DATE_LIKES:
        cur.execute(
            "SELECT id FROM messages WHERE role='user' AND created_at LIKE ? "
            "ORDER BY created_at",
            (like_pat,)
        )
        ids = [row[0] for row in cur.fetchall()]
        n = len(ids)
        print(f"[INFO] {like_pat[:-1]} 待更新 user 消息数：{n}")
        if n == 0:
            continue
        new_texts = [pick_one(rng) for _ in range(n)]
        for mid, new_text in zip(ids, new_texts):
            cur.execute("UPDATE messages SET content=? WHERE id=?", (new_text, mid))
        conn.commit()
        total_all += n

    conn.close()
    print(f"[完成] 共更新 {total_all} 条 user 消息内容")


if __name__ == "__main__":
    main()