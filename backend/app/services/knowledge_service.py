import os
import shutil
from fastapi import UploadFile
from sqlalchemy.orm import Session
from markitdown import MarkItDown
from app.models import KnowledgeDoc
import torch
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# 自动定位项目路径，并规范化知识库存储目录
CURRENT_DIR = os.path.abspath(__file__)
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR)))

DATA_DIR = os.path.join(BACKEND_DIR, "data", "knowledge_docs")
MODEL_PATH = os.path.join(BACKEND_DIR, "models", "bge-small-zh-v1.5")
VECTOR_STORE_DIR = os.path.join(BACKEND_DIR, "vector_store", "lingshan")

os.makedirs(DATA_DIR, exist_ok=True)

# 懒加载 embedding 模型，避免模块导入时立即初始化（与 RAG 服务的 embedding 模型隔离）
_embeddings = None


def _get_embeddings() -> HuggingFaceEmbeddings:
    global _embeddings
    if _embeddings is None:
        print("[Knowledge] 正在初始化 BGE Embedding 模型...")
        DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
        _embeddings = HuggingFaceEmbeddings(
            model_name=MODEL_PATH,
            model_kwargs={'device': DEVICE},
            encode_kwargs={"normalize_embeddings": True},
        )
        print(f"[Knowledge] Embedding 模型初始化成功，使用设备: {DEVICE}")
    return _embeddings

async def save_uploaded_file(db: Session, file: UploadFile, title: str, user_id: int) -> KnowledgeDoc:
    """
    接收上传的文件，保存到本地，并在数据库建档。
    """
    # 1. 提取后缀并拼出路径
    file_extension = file.filename.split(".")[-1]
    safe_filename = f"{title}_{user_id}.{file_extension}"
    file_path = os.path.join(DATA_DIR, safe_filename)

    # 2. 流式写入硬盘
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 3. 数据库记录建档 (默认状态为 uploaded)
    file_size = os.path.getsize(file_path)
    new_doc = KnowledgeDoc(
        title=title,
        file_type=file_extension,
        file_size=file_size,
        file_path=file_path,
        user_id=user_id,
        status="uploaded"
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    return new_doc


def process_document(db: Session, doc_id: int):
    """
    Step 2：解析 -> 切块 -> 向量化入库
    """
    # 1. 从数据库找出这条记录
    doc = db.query(KnowledgeDoc).filter(KnowledgeDoc.id == doc_id).first()
    if not doc:
        raise ValueError(f"找不到 ID 为 {doc_id} 的文档")

    # 先把状态改为处理中，防止重复点击
    doc.status = "processing"
    db.commit()

    try:
        # MarkItDown 解析
        print(f"正在解析文档: {doc.file_path}")
        md = MarkItDown()
        result = md.convert(doc.file_path)
        raw_text = result.text_content

        # LangChain 文本切块

        print("正在进行文本切块...")
        
        # 1. 结构感知切分：利用 MarkItDown 生成的 # 标题进行切割
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]
        markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
        md_header_splits = markdown_splitter.split_text(raw_text)

        # 2. 长度兜底切分：防止某个标题下的段落太长
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,     # 每块大约 500 字
            chunk_overlap=50    # 上下块重叠 50 字，防止一句话被分成两半
        )
        splits = text_splitter.split_documents(md_header_splits)
        
        # 3. 元数据
        for split in splits:
            split.metadata["doc_id"] = str(doc_id)
            split.metadata["title"] = doc.title

        print(f"切块完成，共产生 {len(splits)} 个文本块。")


        print("正在将知识存入 Chroma 向量数据库")
        # 连接并实例化 Chroma 数据库
        vectorstore = Chroma(
            collection_name="lingshan_knowledge", 
            embedding_function=_get_embeddings(),
            persist_directory=VECTOR_STORE_DIR
        )
        
        # 入库
        vectorstore.add_documents(documents=splits)
        
        # 更新数据库真实状态
        doc.chunk_count = len(splits)
        doc.status = "ready" 
        print("知识库处理成功，文件状态已更新为 ready。")

    except Exception as e:
        print(f" 处理失败: {e}")
        doc.status = "failed"

    finally:
        # 无论成功失败，都必须保存最终状态
        db.commit()


def sync_pre_ingested_docs(db: Session):
    """
    启动时扫描 Chroma guide_parents 集合中的预摄入文档，
    为尚未在 SQL 数据库中建档的文档自动创建 KnowledgeDoc 记录，
    使前端知识库列表可以展示这些文档。
    """
    from app.models import KnowledgeDoc

    try:
        embeddings = _get_embeddings()
        parent_store = Chroma(
            collection_name="guide_parents",
            persist_directory=VECTOR_STORE_DIR,
            embedding_function=embeddings,
        )

        results = parent_store.get()
        if not results or not results.get("metadatas"):
            return

        # 提取所有唯一的 source 文件名
        seen_sources = set()
        for metadata in results["metadatas"]:
            source = metadata.get("source", "")
            if source:
                seen_sources.add(source)

        if not seen_sources:
            return

        # 统计每个 source 对应的子文档数量
        child_store = Chroma(
            collection_name="guide_children",
            persist_directory=VECTOR_STORE_DIR,
            embedding_function=embeddings,
        )
        child_results = child_store.get()
        source_chunk_counts = {}
        if child_results and child_results.get("metadatas"):
            for meta in child_results["metadatas"]:
                src = meta.get("source", "")
                if src:
                    source_chunk_counts[src] = source_chunk_counts.get(src, 0) + 1

        created_count = 0
        for source in seen_sources:
            existing = db.query(KnowledgeDoc).filter(
                KnowledgeDoc.title == source
            ).first()
            if existing:
                continue

            chunk_count = source_chunk_counts.get(source, 0)
            new_doc = KnowledgeDoc(
                title=source,
                file_type="docx",
                file_size=0,
                file_path="",
                user_id=1,
                status="ready",
                chunk_count=chunk_count,
            )
            db.add(new_doc)
            created_count += 1

        db.commit()
        print(f"[Startup] 预摄入文档同步完成，新增 {created_count} 条记录，共 {len(seen_sources)} 个文档")

    except Exception as e:
        print(f"[Startup] 预摄入文档同步失败: {e}")
        db.rollback()