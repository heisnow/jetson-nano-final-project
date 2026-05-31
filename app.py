from __future__ import annotations

import os
from collections import Counter, defaultdict

import click
from flask import Flask, jsonify, render_template, request
from sqlalchemy import desc, func, or_, select

from database import SessionLocal, get_database_url, init_db, seed_demo_data
from models import JetsonEvent, SafetyArticle


PROJECT = {
    "name": "工安新聞與安全帽風險資料分析平台",
    "subtitle": "把分散的工安資訊整理成可查詢、可分析、可提醒的安全儀表板",
    "team_members": ["林偲駒", "邱冠凱", "黃舒禾", "方守東"],
    "summary": (
        "本專題以工安新聞、職災案例與安全帽相關資料為核心，透過動態網頁爬蟲蒐集資料，"
        "存入 Render PostgreSQL，並使用 Flask 將資料整理成列表與分析圖表。"
        "Jetson Orin Nano + 攝像頭保留為加分擴充模組，攝像頭型號尚未確定時，"
        "系統先以不綁硬體型號的資料介面設計，未來可接 USB 或 CSI 攝像頭。"
    ),
    "motivation": (
        "工地的安全往往不是缺少規定，而是缺少即時被看見的風險。"
        "我們希望做一個讓安全管理更接近日常的工具：先從公開資料理解事故樣態，"
        "再讓 AI 裝置在現場成為提醒者。"
    ),
    "data_sources": [
        "勞動部職業安全衛生署新聞公告與公開資訊",
        "工安、職災、安全帽相關公開新聞網頁",
        "Jetson Orin Nano 原型偵測事件資料",
    ],
    "stack": ["Flask", "Render PostgreSQL", "Playwright crawler", "SQLAlchemy", "Render"],
}


RISK_KEYWORDS = ["安全帽", "高處", "墜落", "夾捲", "感電", "營造", "機械", "高溫", "移工", "教育訓練"]


def create_app() -> Flask:
    app = Flask(__name__)
    init_db(seed=True)

    @app.route("/")
    def index():
        with SessionLocal() as session:
            article_count = session.scalar(select(func.count()).select_from(SafetyArticle)) or 0
            event_count = session.scalar(select(func.count()).select_from(JetsonEvent)) or 0
            latest_articles = session.scalars(
                select(SafetyArticle)
                .order_by(desc(SafetyArticle.published_at), desc(SafetyArticle.created_at))
                .limit(5)
            ).all()
            latest_events = session.scalars(
                select(JetsonEvent).order_by(desc(JetsonEvent.captured_at)).limit(3)
            ).all()

        return render_template(
            "index.html",
            project=PROJECT,
            article_count=article_count,
            event_count=event_count,
            latest_articles=latest_articles,
            latest_events=latest_events,
        )

    @app.route("/articles")
    def articles():
        keyword = request.args.get("q", "").strip()
        category = request.args.get("category", "").strip()

        with SessionLocal() as session:
            category_rows = session.execute(
                select(SafetyArticle.category, func.count())
                .group_by(SafetyArticle.category)
                .order_by(SafetyArticle.category)
            ).all()

            stmt = select(SafetyArticle)
            if keyword:
                like = f"%{keyword}%"
                stmt = stmt.where(
                    or_(
                        SafetyArticle.title.ilike(like),
                        SafetyArticle.summary.ilike(like),
                        SafetyArticle.keywords.ilike(like),
                    )
                )
            if category:
                stmt = stmt.where(SafetyArticle.category == category)

            rows = session.scalars(
                stmt.order_by(desc(SafetyArticle.published_at), desc(SafetyArticle.created_at))
            ).all()

        return render_template(
            "articles.html",
            project=PROJECT,
            articles=rows,
            keyword=keyword,
            selected_category=category,
            categories=[row[0] for row in category_rows],
        )

    @app.route("/analysis")
    def analysis():
        with SessionLocal() as session:
            rows = session.scalars(select(SafetyArticle)).all()

        category_counts = Counter(row.category for row in rows)
        source_counts = Counter(row.source_name for row in rows)
        keyword_counts = Counter()
        monthly_counts: dict[str, int] = defaultdict(int)

        for row in rows:
            content = f"{row.title} {row.summary} {row.keywords}"
            for keyword in RISK_KEYWORDS:
                if keyword in content:
                    keyword_counts[keyword] += 1
            if row.published_at:
                monthly_counts[row.published_at.strftime("%Y-%m")] += 1
            else:
                monthly_counts["未標日期"] += 1

        max_category = max(category_counts.values(), default=1)
        max_keyword = max(keyword_counts.values(), default=1)
        max_monthly = max(monthly_counts.values(), default=1)

        return render_template(
            "analysis.html",
            project=PROJECT,
            category_counts=category_counts.most_common(),
            source_counts=source_counts.most_common(5),
            keyword_counts=keyword_counts.most_common(),
            monthly_counts=sorted(monthly_counts.items()),
            max_category=max_category,
            max_keyword=max_keyword,
            max_monthly=max_monthly,
        )

    @app.route("/jetson")
    def jetson():
        with SessionLocal() as session:
            events = session.scalars(
                select(JetsonEvent).order_by(desc(JetsonEvent.captured_at)).limit(20)
            ).all()
        return render_template("jetson.html", project=PROJECT, events=events)

    @app.route("/plan")
    def plan():
        return render_template("plan.html", project=PROJECT)

    @app.route("/health")
    def health():
        database_kind = "postgresql" if get_database_url().startswith("postgresql") else "sqlite"
        return jsonify({"status": "ok", "database": database_kind})

    @app.cli.command("init-db")
    def init_db_command():
        init_db(seed=False)
        click.echo("Database tables are ready.")

    @app.cli.command("seed-demo")
    def seed_demo_command():
        seed_demo_data()
        click.echo("Demo data inserted.")

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
