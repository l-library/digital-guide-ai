# 一次性建表脚本，直接运行就能建
import sys
import os

# 把 backend 目录加到系统路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_dir)

from app.database import engine
from app.models import Base

def init():
    print("正在核对数据库表结构...")
    # 扫描 models.py，并在 app.db 里创建不存在的表
    Base.metadata.create_all(bind=engine)
    print("数据库表结构初始化/更新成功")

if __name__ == "__main__":
    init()
