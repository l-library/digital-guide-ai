import logging
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from app.config.paths import LINGSHAN_STORE_DIR, BGE_MODEL_DIR

logger = logging.getLogger(__name__)

VECTOR_STORE_PATH = LINGSHAN_STORE_DIR
model_path = BGE_MODEL_DIR

# 1. 意图识别
# 根据问题关键词判断应该在哪个category里检索
# 不识别时返回None，表示全库检索


def detect_intent(query: str) -> str | None:
    if any(kw in query for kw in ["路线", "怎么玩", "行程", "游览顺序", "几小时"]):
        return "游览路线"
    if any(
        kw in query
        for kw in [
            "门票",
            "价格",
            "多少钱",
            "几点",
            "开放时间",
            "表演时间",
            "住宿",
            "餐饮",
            "交通",
            "贴士",
        ]
    ):
        return "实用信息"
    if any(
        kw in query
        for kw in ["介绍", "是什么", "在哪", "特色", "文化", "历史", "建筑", "怎么样"]
    ):
        return "景点介绍"
    return None  # 兜底：不加过滤，全库检索


# 2. 初始化vectorstore连接
# 用函数包装，避免模块加载时就初始化（占内存，且可能路径还没就绪）

_embeddings = None
_child_store = None
_parent_store = None
_knowledge_store = None  # 用户上传文档集合


def _get_stores():
    global _embeddings, _child_store, _parent_store, _knowledge_store
    if _child_store is not None:
        return _child_store, _parent_store, _knowledge_store

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
    _knowledge_store = Chroma(
        persist_directory=VECTOR_STORE_PATH,
        embedding_function=_embeddings,
        collection_name="lingshan_knowledge",
    )
    return _child_store, _parent_store, _knowledge_store


# 3. 核心检索函数


def retrieve_context(query: str, k: int = 3) -> list[str]:
    """
    输入用户问题，返回相关的父节完整内容列表。
    同时检索预摄入文档（guide_children/guide_parents）和用户上传文档（lingshan_knowledge）。
    这个列表直接拼接后送给LLM。
    """
    child_store, parent_store, knowledge_store = _get_stores()
    context_list: list[str] = []

    # ===== 管道1：guide_children → guide_parents（预摄入景区资料）=====
    intent = detect_intent(query)
    search_filter = {"category": intent} if intent else None

    child_results = child_store.similarity_search(
        query,
        k=k,
        filter=search_filter,
    )

    if not child_results:
        child_results = child_store.similarity_search(query, k=k)

    seen_parents: set[str] = set()
    for doc in child_results:
        pid = doc.metadata.get("parent_id")
        if not pid or pid in seen_parents:
            continue
        seen_parents.add(pid)

        result = parent_store.get(where={"parent_id": pid})
        if result and result["documents"]:
            context_list.append(result["documents"][0])

    # ===== 管道2：lingshan_knowledge（用户上传的文档）=====
    try:
        knowledge_results = knowledge_store.similarity_search(query, k=k)
        for doc in knowledge_results:
            content = doc.page_content
            if content not in context_list:
                context_list.append(content)
    except Exception as e:
        logger.error(f"lingshan_knowledge 检索失败: {e}")

    return context_list


def build_prompt(query: str, context_list: list[str]) -> str:
    """
    把检索到的上下文和用户问题拼成完整prompt。
    提示词从 config/prompts.yaml 加载。
    """
    from app.config.prompt_loader import get_rag_guide_prompt

    context_text = "\n\n---\n\n".join(context_list)
    return get_rag_guide_prompt(context_text=context_text, query=query)

