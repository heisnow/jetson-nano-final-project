from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone

from dotenv import load_dotenv
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from models import Base, JetsonEvent, SafetyArticle


load_dotenv()


def normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.removeprefix("postgres://")
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


def get_database_url() -> str:
    return normalize_database_url(os.environ.get("DATABASE_URL", "sqlite:///safety_insight.db"))


engine = create_engine(get_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


DEMO_ARTICLES = [
    {
        "title": "工地高處作業未落實防護，安全帽與安全帶成為第一道生命線",
        "summary": "案例提醒營造現場必須落實個人防護具、作業前點檢與現場主管巡查。",
        "source_name": "示範資料：工安新聞",
        "source_url": "demo://safety-news-001",
        "category": "營造安全",
        "published_at": date(2026, 5, 18),
        "keywords": "安全帽,高處作業,安全帶,營造",
    },
    {
        "title": "職安宣導聚焦移工與新進人員，降低陌生場域事故風險",
        "summary": "新進工作者常因語言、訓練與現場文化落差而暴露在較高風險中。",
        "source_name": "示範資料：職安宣導",
        "source_url": "demo://safety-news-002",
        "category": "職安宣導",
        "published_at": date(2026, 5, 12),
        "keywords": "教育訓練,移工,職安文化",
    },
    {
        "title": "工廠機械保養未停機，夾捲危害再度成為改善重點",
        "summary": "設備維修前的上鎖掛牌與斷電確認，是避免夾捲事故的重要程序。",
        "source_name": "示範資料：職災案例",
        "source_url": "demo://safety-news-003",
        "category": "機械安全",
        "published_at": date(2026, 4, 28),
        "keywords": "機械,夾捲,上鎖掛牌,停機",
    },
    {
        "title": "夏季高溫作業增加熱危害，戶外工地需安排補水與休息",
        "summary": "高溫環境會影響判斷與反應速度，間接提高工安事故發生機率。",
        "source_name": "示範資料：職業衛生",
        "source_url": "demo://safety-news-004",
        "category": "職業衛生",
        "published_at": date(2026, 4, 10),
        "keywords": "高溫,補水,戶外作業,熱危害",
    },
    {
        "title": "安全帽未確實配戴，影像辨識可協助現場即時提醒",
        "summary": "邊緣 AI 裝置可在不等待人工巡查的情況下提醒現場人員完成防護。",
        "source_name": "示範資料：AI 應用",
        "source_url": "demo://safety-news-005",
        "category": "AI 防護",
        "published_at": date(2026, 3, 24),
        "keywords": "安全帽,Jetson,YOLO,即時偵測",
    },
]


DEMO_EVENTS = [
    {
        "location": "A 區入口",
        "helmet_status": "未戴安全帽",
        "confidence": 0.91,
        "device_note": "Jetson Orin Nano 原型測試資料，不綁定特定攝像頭型號。",
        "captured_at": datetime.now(timezone.utc) - timedelta(hours=5),
    },
    {
        "location": "B 區施工平台",
        "helmet_status": "已戴安全帽",
        "confidence": 0.96,
        "device_note": "可透過 USB 或 CSI 攝像頭擷取影像，再由 OpenCV/YOLO 判斷。",
        "captured_at": datetime.now(timezone.utc) - timedelta(hours=2),
    },
]


def init_db(seed: bool = True) -> None:
    Base.metadata.create_all(engine)
    if seed:
        seed_demo_data()


def seed_demo_data() -> None:
    with SessionLocal() as session:
        article_count = session.scalar(select(func.count()).select_from(SafetyArticle)) or 0
        if article_count == 0:
            session.add_all(SafetyArticle(**item) for item in DEMO_ARTICLES)

        event_count = session.scalar(select(func.count()).select_from(JetsonEvent)) or 0
        if event_count == 0:
            session.add_all(JetsonEvent(**item) for item in DEMO_EVENTS)

        session.commit()


def upsert_article(session: Session, article_data: dict[str, object]) -> bool:
    source_url = str(article_data["source_url"])
    existing = session.scalar(
        select(SafetyArticle).where(SafetyArticle.source_url == source_url)
    )
    if existing:
        existing.title = str(article_data.get("title", existing.title))
        existing.summary = str(article_data.get("summary", existing.summary))
        existing.source_name = str(article_data.get("source_name", existing.source_name))
        existing.category = str(article_data.get("category", existing.category))
        existing.keywords = str(article_data.get("keywords", existing.keywords))
        existing.published_at = article_data.get("published_at", existing.published_at)
        return False

    session.add(SafetyArticle(**article_data))
    return True
