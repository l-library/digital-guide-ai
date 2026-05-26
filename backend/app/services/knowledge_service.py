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

# 本地 Embedding 模型路径和 Chroma 数据库路径
MODEL_PATH = os.path.join(BACKEND_DIR, "models", "bge-small-zh-v1.5")
VECTOR_STORE_DIR = os.path.join(BACKEND_DIR, "vector_store", "lingshan")

os.makedirs(DATA_DIR, exist_ok=True)
# 确保专门存知识库文档的文件夹存在

# 在这里定义全局变量，让它在模块加载时就初始化好
print("[Global] 正在初始化全局 BGE Embedding 模型...")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
embeddings = HuggingFaceEmbeddings(
    model_name=MODEL_PATH,
    model_kwargs={'device': DEVICE}
)
print(f"[Global] 全局 Embedding 模型初始化成功，使用设备: {DEVICE}")

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
            embedding_function=embeddings,
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