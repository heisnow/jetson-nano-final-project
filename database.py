from __future__ import annotations

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from models import Base, RecyclingRule, ScanRecord


load_dotenv()


def normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.removeprefix("postgres://")
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


def get_database_url() -> str:
    return normalize_database_url(os.environ.get("DATABASE_URL", "sqlite:///ecolens.db"))


engine = create_engine(get_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


DEMO_RULES = [
    {
        "item_name": "寶特瓶",
        "category": "資源回收 / 塑膠類",
        "material": "PET 1 號塑膠",
        "disposal_steps": "倒空內容物，簡單沖洗，瓶身壓扁，瓶蓋與瓶身可一起投入塑膠容器回收。",
        "city": "通用",
        "source_name": "示範資料：生活回收規則",
        "source_url": "demo://pet-bottle",
        "keywords": "PET,寶特瓶,塑膠瓶,飲料瓶",
    },
    {
        "item_name": "鋁箔包",
        "category": "資源回收 / 紙容器",
        "material": "紙、塑膠膜、鋁箔複合材",
        "disposal_steps": "喝完後壓扁，若有吸管與塑膠套需分開處理，依地方規定投入紙容器回收。",
        "city": "通用",
        "source_name": "示範資料：生活回收規則",
        "source_url": "demo://carton",
        "keywords": "鋁箔包,紙容器,飲料盒,牛奶盒",
    },
    {
        "item_name": "手搖飲塑膠杯",
        "category": "資源回收 / 塑膠杯",
        "material": "PP 或 PET 塑膠",
        "disposal_steps": "倒掉剩餘飲料，杯膜與吸管分開，杯身沖洗後投入塑膠類回收。",
        "city": "通用",
        "source_name": "示範資料：生活回收規則",
        "source_url": "demo://drink-cup",
        "keywords": "手搖飲,塑膠杯,PP,PET,飲料杯",
    },
    {
        "item_name": "紙餐盒",
        "category": "依污染程度判斷",
        "material": "紙類或淋膜紙",
        "disposal_steps": "若油污嚴重通常不適合回收；若乾淨且地方接受紙容器回收，可清空後回收。",
        "city": "通用",
        "source_name": "示範資料：生活回收規則",
        "source_url": "demo://paper-box",
        "keywords": "紙餐盒,便當盒,外送盒,紙容器",
    },
    {
        "item_name": "鐵鋁罐",
        "category": "資源回收 / 金屬類",
        "material": "鋁或鐵",
        "disposal_steps": "倒空內容物，簡單沖洗，壓扁後投入金屬容器回收。",
        "city": "通用",
        "source_name": "示範資料：生活回收規則",
        "source_url": "demo://can",
        "keywords": "鐵罐,鋁罐,易開罐,金屬",
    },
    {
        "item_name": "電池",
        "category": "資源回收 / 乾電池",
        "material": "金屬與化學材料",
        "disposal_steps": "不可丟一般垃圾，應集中後投入超商、量販店或清潔隊提供的電池回收點。",
        "city": "通用",
        "source_name": "示範資料：生活回收規則",
        "source_url": "demo://battery",
        "keywords": "電池,乾電池,鈕扣電池,回收點",
    },
]


def init_db(seed: bool = True) -> None:
    Base.metadata.create_all(engine)
    if seed:
        seed_demo_data()


def seed_demo_data() -> None:
    with SessionLocal() as session:
        rule_count = session.scalar(select(func.count()).select_from(RecyclingRule)) or 0
        if rule_count == 0:
            session.add_all(RecyclingRule(**item) for item in DEMO_RULES)
        session.commit()


def upsert_rule(session: Session, rule_data: dict[str, object]) -> bool:
    item_name = str(rule_data["item_name"])
    city = str(rule_data.get("city", "通用"))
    existing = session.scalar(
        select(RecyclingRule).where(
            RecyclingRule.item_name == item_name,
            RecyclingRule.city == city,
        )
    )
    if existing:
        existing.category = str(rule_data.get("category", existing.category))
        existing.material = str(rule_data.get("material", existing.material))
        existing.disposal_steps = str(rule_data.get("disposal_steps", existing.disposal_steps))
        existing.source_name = str(rule_data.get("source_name", existing.source_name))
        existing.source_url = str(rule_data.get("source_url", existing.source_url))
        existing.keywords = str(rule_data.get("keywords", existing.keywords))
        return False

    session.add(RecyclingRule(**rule_data))
    return True


def save_scan_record(
    input_text: str,
    guessed_item: str,
    suggested_category: str,
    confidence: float,
    notes: str,
    device_type: str = "browser camera",
) -> ScanRecord:
    with SessionLocal() as session:
        record = ScanRecord(
            input_text=input_text,
            guessed_item=guessed_item,
            suggested_category=suggested_category,
            confidence=confidence,
            notes=notes,
            device_type=device_type,
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return record
