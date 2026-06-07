from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    Form,
    BackgroundTasks,
    HTTPException,
)
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import KnowledgeDoc

from app.services.knowledge_service import (
    save_uploaded_file,
    process_document,
    _get_embeddings,
    VECTOR_STORE_DIR,
)

router = APIRouter()


@router.post("/knowledge-docs")
async def upload_knowledge_doc(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    user_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """5.1 上传知识文档接口"""
    try:
        doc = await save_uploaded_file(db, file, title, user_id)
        doc.status = "processing"
        db.commit()
        background_tasks.add_task(process_document, db, doc.id)
        return doc.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")


@router.get("/knowledge-docs")
def get_knowledge_docs(
    page: int = 1, page_size: int = 20, db: Session = Depends(get_db)
):
    """5.2 获取知识文档列表接口"""
    skip = (page - 1) * page_size
    total = db.query(KnowledgeDoc).count()
    docs = (
        db.query(KnowledgeDoc)
        .order_by(KnowledgeDoc.created_at.desc())
        .offset(skip)
        .limit(page_size)
        .all()
    )

    return {
        "items": [doc.to_dict() for doc in docs],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/knowledge-docs/{doc_id}/process")
async def trigger_process_doc(
    doc_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    """5.6 触发文档向量化接口（异步非阻塞）"""
    doc = db.query(KnowledgeDoc).filter(KnowledgeDoc.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    if doc.status == "processing":
        return {
            "doc_id": doc.id,
            "status": "processing",
            "message": "该文档正在处理中，请勿重复点击",
        }

    # 先把状态改了，让前端知道已经开始干活了
    doc.status = "processing"
    db.commit()

    # 切片和向量化任务在后台异步执行
    background_tasks.add_task(process_document, db, doc_id)

    return {"doc_id": doc.id, "status": "processing"}


import os
from langchain_chroma import Chroma
from app.services.knowledge_service import VECTOR_STORE_DIR, _get_embeddings


@router.delete("/knowledge-docs/{doc_id}")
def delete_knowledge_doc(doc_id: int, db: Session = Depends(get_db)):
    """5.5 删除知识文档接口"""
    # 1. 查出文档记录
    doc = db.query(KnowledgeDoc).filter(KnowledgeDoc.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    # 2. 清理物理文件 (如果在硬盘上还存在)
    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
            print(f"物理文件已删除: {doc.file_path}")
        except Exception as e:
            print(f"物理文件删除失败，可能被占用: {e}")

    # 3. 清理 ChromaDB 向量库中的相应记忆
    if doc.status == "ready":
        embeddings = _get_embeddings()
        try:
            vectorstore = Chroma(
                collection_name="lingshan_knowledge",
                persist_directory=VECTOR_STORE_DIR,
                embedding_function=embeddings,
            )
            vectorstore.delete(where={"doc_id": str(doc_id)})
            print(f"向量库(lingshan_knowledge)中 doc_id={doc_id} 的记忆已删除")
        except Exception as e:
            print(f"向量库(lingshan_knowledge)清理失败: {e}")

        # 同时清理预摄入文档（guide_parents / guide_children 集合，按 source 匹配）
        for collection_name in ("guide_children", "guide_parents"):
            try:
                store = Chroma(
                    collection_name=collection_name,
                    persist_directory=VECTOR_STORE_DIR,
                    embedding_function=embeddings,
                )
                store.delete(where={"source": doc.title})
                print(f"向量库({collection_name})中 source='{doc.title}' 的记忆已删除")
            except Exception as e:
                print(f"向量库({collection_name})清理失败: {e}")

    # 4. 最后，清理关系型数据库记录
    db.delete(doc)
    db.commit()

    return {"message": "success"}
