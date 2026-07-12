"""
数据库连接和会话管理（SQLAlchemy + SQLite）
"""
import logging
from sqlalchemy import create_engine, text
from app.config.paths import DB_PATH

logger = logging.getLogger(__name__)
from sqlalchemy.orm import sessionmaker, declarative_base

# 数据库文件路径：backend/data/app.db
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite 多线程支持
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def _add_column_if_missing(engine, table_name, column_name, column_def):
    """检测列是否存在，不存在则 ALTER TABLE ADD COLUMN（SQLite 兼容）"""
    with engine.connect() as conn:
        result = conn.execute(text(f"PRAGMA table_info({table_name})"))
        columns = [row[1] for row in result]
        if column_name not in columns:
            conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_def}"))
            conn.commit()
            logger.info(f"[migration] 已添加列: {table_name}.{column_name}")


def init_db():
    """创建所有表，并检测添加缺失的列（首次运行时调用）"""
    import app.models  # 确保 Base.metadata 注册了所有模型表
    Base.metadata.create_all(bind=engine)

    # SQLite 迁移：为已有 users 表补充新增字段
    _add_column_if_missing(engine, "users", "is_active", "is_active BOOLEAN DEFAULT 1")
    _add_column_if_missing(engine, "users", "token_version", "token_version INTEGER DEFAULT 0")
    _add_column_if_missing(engine, "users", "interests", "interests TEXT DEFAULT '[]'")
    _add_column_if_missing(engine, "users", "last_interest_update", "last_interest_update DATETIME")

    # 推荐日志保留 90 天，定期清理
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM recommend_logs WHERE created_at < date('now', '-90 days')"))
        conn.commit()


def get_db():
    """FastAPI 依赖注入：获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
