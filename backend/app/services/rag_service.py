import os
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

VECTOR_STORE_PATH = "vector_store/lingshan"

model_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "models", "bge-small-zh-v1.5"
)

# 1. 意图识别
# 根据问题关键词判断应该在哪个category里检索
# 不识别时返回None，表示全库检索

def detect_intent(query: str) -> str | None:
    if any(kw in query for kw in ["路线", "怎么玩", "行程", "游览顺序", "几小时"]):
        return "游览路线"
    if any(kw in query for kw in ["门票", "价格", "多少钱", "几点", "开放时间",
                                   "表演时间", "住宿", "餐饮", "交通", "贴士"]):
        return "实用信息"
    if any(kw in query for kw in ["介绍", "是什么", "在哪", "特色", "文化",
                                   "历史", "建筑", "怎么样"]):
        return "景点介绍"
    return None   # 兜底：不加过滤，全库检索


# 2. 初始化vectorstore连接
# 用函数包装，避免模块加载时就初始化（占内存，且可能路径还没就绪）

_embeddings = None
_child_store = None
_parent_store = None

def _get_stores():
    global _embeddings, _child_store, _parent_store
    if _child_store is not None:
        return _child_store, _parent_store   # 已初始化，直接返回

    _embeddings = HuggingFaceEmbeddings(
        model_name=model_path,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    _child_store = Chroma(
        persist_directory=VECTOR_STORE_PATH,
        embedding_function=_embeddings,
        collection_name="guide_children",
    )
    _parent_store = Chroma(
        persist_directory=VECTOR_STORE_PATH,
        embedding_function=_embeddings,
        collection_name="guide_parents",
    )
    return _child_store, _parent_store


# 3. 核心检索函数

def retrieve_context(query: str, k: int = 3) -> list[str]:
    """
    输入用户问题，返回相关的父节完整内容列表。
    这个列表直接拼接后送给LLM。
    """
    child_store, parent_store = _get_stores()

    # 意图识别，决定是否加filter
    intent = detect_intent(query)
    search_filter = {"category": intent} if intent else None

    # 第一步：子chunk相似度检索
    child_results = child_store.similarity_search(
        query,
        k=k,
        filter=search_filter,
    )

    if not child_results:
        # 如果加了filter没检索到，退回全库检索
        child_results = child_store.similarity_search(query, k=k)

    # 第二步：通过parent_id取父节完整内容，去重
    seen_parents = set()
    context_list = []

    for doc in child_results:
        pid = doc.metadata.get("parent_id")
        if not pid or pid in seen_parents:
            continue
        seen_parents.add(pid)

        result = parent_store.get(where={"parent_id": pid})
        if result and result["documents"]:
            context_list.append(result["documents"][0])

    return context_list


def build_prompt(query: str, context_list: list[str]) -> str:
    """
    把检索到的上下文和用户问题拼成完整prompt。
    llm_service.py 里直接调用这个函数拿到prompt再送给LLM。
    """
    context_text = "\n\n---\n\n".join(context_list)

    prompt = f"""你是灵山胜境景区的AI导游，请根据以下景区资料回答游客的问题。
要求：
- 回答简洁，挑重点说，尽量控制在150字内
- 语气自然亲切，像真人导游
- 不要使用emoji或动作描写
- 如果资料中没有相关信息，请如实告知，不要编造


【景区资料】
{context_text}

【游客问题】
{query}

【回答】"""

    return prompt