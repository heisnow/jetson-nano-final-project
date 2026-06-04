from __future__ import annotations

import os
from collections import Counter

import click
from flask import Flask, jsonify, render_template, request
from sqlalchemy import desc, func, or_, select

from database import SessionLocal, get_database_url, init_db, save_scan_record, seed_demo_data
from models import RecyclingRule, ScanRecord


PROJECT = {
    "name": "EcoLens 生活回收與標籤辨識助手",
    "short_name": "EcoLens",
    "subtitle": "打開手機或電腦鏡頭，讓回收分類像拍照一樣簡單",
    "team_members": ["林偲駒", "邱冠凱", "黃舒禾", "方守東"],
    "summary": (
        "EcoLens 是一個貼近日常生活的 Flask 專題。使用者打開網頁即可啟用裝置鏡頭，"
        "手機可使用前後鏡頭，電腦可使用前鏡頭，將包裝、瓶罐、紙盒或標籤對準鏡頭。"
        "目前版本先以使用者輸入的標籤文字與回收規則資料庫進行分析，未來可串接 OCR "
        "與圖像模型，自動讀取畫面文字並判斷物品類型。"
    ),
    "motivation": (
        "每天都有人站在垃圾桶前猶豫：這個杯子能不能回收？鋁箔包算紙類嗎？"
        "外送餐盒太油還能丟回收嗎？EcoLens 希望把環保知識變成人人打開網頁就能使用的小工具。"
    ),
    "data_sources": [
        "地方環保局垃圾分類與資源回收公開資訊",
        "環境部資源回收相關公告與宣導資料",
        "使用者鏡頭掃描後確認的回收紀錄",
    ],
    "stack": ["Flask", "Browser Camera", "PostgreSQL", "Crawler", "Render"],
}


def create_app() -> Flask:
    app = Flask(__name__)
    init_db(seed=True)

    @app.route("/")
    def index():
        with SessionLocal() as session:
            rule_count = session.scalar(select(func.count()).select_from(RecyclingRule)) or 0
            scan_count = session.scalar(select(func.count()).select_from(ScanRecord)) or 0
            latest_rules = session.scalars(
                select(RecyclingRule).order_by(desc(RecyclingRule.created_at)).limit(4)
            ).all()
            latest_scans = session.scalars(
                select(ScanRecord).order_by(desc(ScanRecord.created_at)).limit(5)
            ).all()

        return render_template(
            "index.html",
            project=PROJECT,
            rule_count=rule_count,
            scan_count=scan_count,
            latest_rules=latest_rules,
            latest_scans=latest_scans,
        )

    @app.route("/scan")
    def scan():
        with SessionLocal() as session:
            rules = session.scalars(select(RecyclingRule).order_by(RecyclingRule.item_name)).all()
        return render_template("scan.html", project=PROJECT, rules=rules)

    @app.post("/api/analyze")
    def analyze_api():
        payload = request.get_json(silent=True) or {}
        text = str(payload.get("text", "")).strip()
        device_type = str(payload.get("device_type", "browser camera")).strip() or "browser camera"
        result = analyze_text(text)
        record = save_scan_record(
            input_text=text,
            guessed_item=result["item_name"],
            suggested_category=result["category"],
            confidence=result["confidence"],
            notes=result["disposal_steps"],
            device_type=device_type,
        )
        result["record_id"] = record.id
        return jsonify(result)

    @app.route("/rules")
    def rules():
        keyword = request.args.get("q", "").strip()
        category = request.args.get("category", "").strip()

        with SessionLocal() as session:
            category_rows = session.execute(
                select(RecyclingRule.category, func.count())
                .group_by(RecyclingRule.category)
                .order_by(RecyclingRule.category)
            ).all()

            stmt = select(RecyclingRule)
            if keyword:
                like = f"%{keyword}%"
                stmt = stmt.where(
                    or_(
                        RecyclingRule.item_name.ilike(like),
                        RecyclingRule.material.ilike(like),
                        RecyclingRule.keywords.ilike(like),
                        RecyclingRule.disposal_steps.ilike(like),
                    )
                )
            if category:
                stmt = stmt.where(RecyclingRule.category == category)

            rows = session.scalars(stmt.order_by(RecyclingRule.item_name)).all()

        return render_template(
            "rules.html",
            project=PROJECT,
            rules=rows,
            keyword=keyword,
            selected_category=category,
            categories=[row[0] for row in category_rows],
        )

    @app.route("/analysis")
    def analysis():
        with SessionLocal() as session:
            rules_data = session.scalars(select(RecyclingRule)).all()
            scans = session.scalars(select(ScanRecord).order_by(desc(ScanRecord.created_at))).all()

        category_counts = Counter(rule.category for rule in rules_data)
        material_counts = Counter(rule.material or "未標示" for rule in rules_data)
        scanned_items = Counter(scan.guessed_item for scan in scans)
        low_confidence_count = sum(1 for scan in scans if scan.confidence < 0.5)
        max_category = max(category_counts.values(), default=1)
        max_scanned = max(scanned_items.values(), default=1)

        return render_template(
            "analysis.html",
            project=PROJECT,
            category_counts=category_counts.most_common(),
            material_counts=material_counts.most_common(6),
            scanned_items=scanned_items.most_common(8),
            low_confidence_count=low_confidence_count,
            scan_count=len(scans),
            max_category=max_category,
            max_scanned=max_scanned,
        )

    @app.route("/plan")
    def plan():
        return render_template("plan.html", project=PROJECT)

    @app.route("/health")
    def health():
        database_kind = "postgresql" if get_database_url().startswith("postgresql") else "sqlite"
        return jsonify({"status": "ok", "database": database_kind, "project": PROJECT["short_name"]})

    @app.cli.command("init-db")
    def init_db_command():
        init_db(seed=False)
        click.echo("Database tables are ready.")

    @app.cli.command("seed-demo")
    def seed_demo_command():
        seed_demo_data()
        click.echo("Demo recycling rules inserted.")

    return app


def analyze_text(text: str) -> dict[str, object]:
    normalized = text.lower().replace(" ", "")
    with SessionLocal() as session:
        rules = session.scalars(select(RecyclingRule).order_by(RecyclingRule.item_name)).all()

    best_rule: RecyclingRule | None = None
    best_score = 0
    for rule in rules:
        terms = [rule.item_name, rule.material, *rule.keywords.split(",")]
        score = 0
        for term in terms:
            cleaned = term.strip().lower().replace(" ", "")
            if cleaned and cleaned in normalized:
                score += max(2, len(cleaned))
        if score > best_score:
            best_rule = rule
            best_score = score

    if best_rule:
        confidence = min(0.95, 0.42 + best_score / 28)
        return {
            "item_name": best_rule.item_name,
            "category": best_rule.category,
            "material": best_rule.material,
            "disposal_steps": best_rule.disposal_steps,
            "confidence": round(confidence, 2),
            "source_name": best_rule.source_name,
            "source_url": best_rule.source_url,
            "message": "已根據標籤文字與回收規則找到最接近的分類。",
        }

    return {
        "item_name": "未知物品",
        "category": "需要人工確認",
        "material": "無法判斷",
        "disposal_steps": "請補充包裝上的材質標示，例如 PET、PP、紙容器、鋁箔包，或查詢地方環保局規則。",
        "confidence": 0.18,
        "source_name": "",
        "source_url": "",
        "message": "目前資訊不足，系統無法自動判斷。",
    }


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
