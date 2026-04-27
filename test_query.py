import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from services.rag_service import retrieve_context, build_prompt
from services.llm_service import generate
from services.rag_service import _get_stores  # 引入预热函数

if __name__ == "__main__":
    print("正在本地脚本中预热模型...")
    _get_stores()  # 手动触发加载
    print("预热完毕，开始测速！\n")
def test(query: str):
    print(f"问题：{query}")
    print("=" * 40)

    start = time.time()

    # 第一阶段：检索
    t1 = time.time()
    context_list = retrieve_context(query)
    t2 = time.time()
    print(f"检索耗时：{t2 - t1:.2f}秒，命中{len(context_list)}个父节")

    # 第二阶段：构建prompt
    prompt = build_prompt(query, context_list)

    # 第三阶段：LLM生成
    t3 = time.time()
    answer = generate(prompt)
    t4 = time.time()
    print(f"LLM耗时：{t4 - t3:.2f}秒")

    print(f"总耗时：{t4 - start:.2f}秒")
    print(f"\n回答：{answer}")

if __name__ == "__main__":
    test("门票多少钱")
    print("\n")
    test("九龙灌浴几点有表演")
    print("\n")
    test("自然风光爱好者路线怎么走")
