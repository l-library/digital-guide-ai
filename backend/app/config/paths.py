"""
统一路径配置模块。

所有数据目录、模型路径、向量存储路径的唯一来源。
所有路径基于本文件所在位置（backend/app/config/）向上推算到 backend/ 根目录，
不受进程工作目录（CWD）影响。无论从哪个目录启动服务，路径始终正确。
"""
import os

# backend/ 项目根目录
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 一级数据目录
DATA_DIR = os.path.join(_PROJECT_ROOT, "data")
MODELS_DIR = os.path.join(_PROJECT_ROOT, "models")
VECTOR_STORE_DIR = os.path.join(_PROJECT_ROOT, "vector_store")

# 二级数据目录
TEMP_AUDIO_DIR = os.path.join(DATA_DIR, "temp_audios")
KNOWLEDGE_DOCS_DIR = os.path.join(DATA_DIR, "knowledge_docs")
DB_PATH = os.path.join(DATA_DIR, "app.db")

# 模型子目录
BGE_MODEL_DIR = os.path.join(MODELS_DIR, "bge-small-zh-v1.5")

# 向量存储集合
LINGSHAN_STORE_DIR = os.path.join(VECTOR_STORE_DIR, "lingshan")
ENTERPRISE_KB_DIR = os.path.join(VECTOR_STORE_DIR, "enterprise_kb")

# 配置文件
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
ROUTE_TEMPLATES_PATH = os.path.join(CONFIG_DIR, "path.txt")

# 确保关键运行时目录存在
os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)
os.makedirs(KNOWLEDGE_DOCS_DIR, exist_ok=True)
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
