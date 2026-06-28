from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class RecyclingRule(Base):
    __tablename__ = "recycling_rules"
    __table_args__ = (UniqueConstraint("item_name", "city", name="uq_rule_item_city"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    material: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    disposal_steps: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str] = mapped_column(String(80), default="通用", nullable=False)
    source_name: Mapped[str] = mapped_column(String(120), default="示範資料", nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    keywords: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class ScanRecord(Base):
    __tablename__ = "scan_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    input_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    guessed_item: Mapped[str] = mapped_column(String(120), default="未知物品", nullable=False)
    suggested_category: Mapped[str] = mapped_column(String(80), default="需要人工確認", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    device_type: Mapped[str] = mapped_column(String(80), default="browser camera", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class ScanFeedback(Base):
    __tablename__ = "scan_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scan_id: Mapped[int] = mapped_column(ForeignKey("scan_records.id"), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    corrected_item: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    corrected_category: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    user_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
