"""
将 backend/data/data.csv 中的游客消费数据导入到 SQLite `visitor_consumption` 表。

用法（在 backend/ 目录下运行）::

    conda activate DGA
    python scripts/ingest_consumption.py

脚本会：
  1. 读取 `backend/data/data.csv`
  2. 按需要重建 `visitor_consumption` 表（带确认提示，加 --force 跳过）
  3. 解析 `2025/8/13` 格式的日期为 ISO 日期对象
  4. 批量写入数据库
"""
import csv
import sys
from datetime import date
from pathlib import Path

# 允许从 backend/ 或仓库根目录执行
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.database import engine, SessionLocal, init_db  # noqa: E402
from app.models import VisitorConsumption  # noqa: E402

CSV_PATH = ROOT / "data" / "data.csv"


def _parse_date(raw: str) -> date:
    """解析 `2025/8/13` 或 `2025/08/13` 格式的日期为 date 对象。"""
    parts = raw.split("/")
    if len(parts) != 3:
        raise ValueError(f"无法解析的日期格式: {raw!r}")
    year, month, day = (int(p) for p in parts)
    return date(year, month, day)


def _parse_float(raw: str) -> float:
    """空串或非法值统一返回 0.0，避免 CSV 缺失字段导致导入失败。"""
    if raw is None or raw.strip() == "":
        return 0.0
    return float(raw)


def _parse_int(raw: str) -> int:
    if raw is None or raw.strip() == "":
        return 0
    return int(float(raw))


def load_rows(csv_path: Path) -> list[dict]:
    """读取 CSV 并转为可直接导入的字段字典列表。"""
    rows: list[dict] = []
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "tourist_id": row["tourist_id"].strip(),
                "user_nickname": row["user_nickname"].strip(),
                "age": _parse_int(row["age"]),
                "gender": row["gender"].strip(),
                "attraction_name": row["attraction_name"].strip(),
                "attraction_type": row["attraction_type"].strip(),
                "visit_date": _parse_date(row["visit_date"]),
                "stay_duration": _parse_float(row["stay_duration"]),
                "ticket_cost": _parse_float(row["ticket_cost"]),
                "food_cost": _parse_float(row["food_cost"]),
                "shopping_cost": _parse_float(row["shopping_cost"]),
                "transport_cost": _parse_float(row["transport_cost"]),
                "entertainment_cost": _parse_float(row["entertainment_cost"]),
                "total_cost": _parse_float(row["total_cost"]),
                "group_size": _parse_int(row["group_size"]),
                "satisfaction": _parse_int(row["satisfaction"]),
            })
    return rows


def main() -> int:
    if not CSV_PATH.exists():
        print(f"[错误] 找不到数据文件: {CSV_PATH}")
        return 1

    # 初始化数据库（确保表已创建）
    init_db()

    rows = load_rows(CSV_PATH)
    print(f"[信息] 已解析 {len(rows)} 条消费记录")

    # 询问是否清空旧数据
    force = "--force" in sys.argv
    if not force:
        with engine.connect() as conn:
            from sqlalchemy import text
            existing = conn.execute(text("SELECT COUNT(*) FROM visitor_consumption")).scalar() or 0
        if existing > 0:
            print(f"[警告] 表中已有 {existing} 条记录。")
            answer = input("是否清空后重新导入? [y/N]: ").strip().lower()
            if answer != "y":
                print("[信息] 已取消，未做任何改动。")
                return 0

    # 清空旧数据
    with engine.connect() as conn:
        from sqlalchemy import text
        conn.execute(text("DELETE FROM visitor_consumption"))
        conn.commit()

    # 批量写入
    db = SessionLocal()
    try:
        for r in rows:
            db.add(VisitorConsumption(**r))
        db.commit()
        print(f"[成功] 已导入 {len(rows)} 条记录到 visitor_consumption 表")
    finally:
        db.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())