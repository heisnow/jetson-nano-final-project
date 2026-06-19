from __future__ import annotations

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from models import Base, RecyclingRule, ScanFeedback, ScanRecord


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
    {
        "item_name": "玻璃瓶",
        "category": "資源回收 / 玻璃類",
        "material": "玻璃",
        "disposal_steps": "倒空內容物，簡單沖洗，避免破裂割傷，依地方規定投入玻璃容器回收。",
        "city": "通用",
        "source_name": "示範資料：生活回收規則",
        "source_url": "demo://glass-bottle",
        "keywords": "玻璃瓶,玻璃罐,酒瓶,醬料瓶",
    },
    {
        "item_name": "塑膠袋",
        "category": "依地方規定回收",
        "material": "PE 或塑膠薄膜",
        "disposal_steps": "乾淨塑膠袋可集中回收；若沾滿油污、湯汁或食物殘渣，通常應作一般垃圾處理。",
        "city": "通用",
        "source_name": "示範資料：生活回收規則",
        "source_url": "demo://plastic-bag",
        "keywords": "塑膠袋,PE,塑膠薄膜,購物袋",
    },
    {
        "item_name": "保麗龍餐盒",
        "category": "依地方規定回收",
        "material": "PS 保麗龍",
        "disposal_steps": "乾淨保麗龍可依地方規定回收；若沾油或食物殘渣，需先清潔，無法清潔時作一般垃圾。",
        "city": "通用",
        "source_name": "示範資料：生活回收規則",
        "source_url": "demo://styrofoam-box",
        "keywords": "保麗龍,PS,保麗龍餐盒,泡棉",
    },
    {
        "item_name": "廚餘",
        "category": "廚餘",
        "material": "食物殘渣",
        "disposal_steps": "瀝乾水分後投入廚餘桶；骨頭、貝殼、衛生紙等不可混入，依地方規定分類生熟廚餘。",
        "city": "通用",
        "source_name": "示範資料：生活回收規則",
        "source_url": "demo://food-waste",
        "keywords": "廚餘,食物殘渣,剩菜,果皮",
    },
    {
        "item_name": "衛生紙",
        "category": "一般垃圾",
        "material": "污染紙類",
        "disposal_steps": "使用過的衛生紙、紙巾多屬一般垃圾，不建議投入紙類回收。",
        "city": "通用",
        "source_name": "示範資料：生活回收規則",
        "source_url": "demo://tissue",
        "keywords": "衛生紙,紙巾,污染紙類,一般垃圾",
    },
]


def init_db(seed: bool = True) -> None:
    Base.metadata.create_all(engine)
    if seed:
        seed_demo_data()


def seed_demo_data() -> None:
    with SessionLocal() as session:
        for item in DEMO_RULES:
            upsert_rule(session, item)
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


def save_scan_feedback(
    scan_id: int,
    is_correct: bool,
    corrected_item: str = "",
    corrected_category: str = "",
    user_note: str = "",
) -> ScanFeedback:
    with SessionLocal() as session:
        record = session.get(ScanRecord, scan_id)
        if record is None:
            raise ValueError("Scan record not found.")

        feedback = ScanFeedback(
            scan_id=scan_id,
            is_correct=is_correct,
            corrected_item=corrected_item,
            corrected_category=corrected_category,
            user_note=user_note,
        )
        session.add(feedback)
        session.commit()
        session.refresh(feedback)
        return feedback
