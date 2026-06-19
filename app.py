from __future__ import annotations

import os
import csv
import io
import warnings
from collections import Counter
from urllib.parse import urlparse

import click
import requests
from requests.exceptions import SSLError
from urllib3.exceptions import InsecureRequestWarning
from bs4 import BeautifulSoup
from flask import Flask, jsonify, render_template, request
from sqlalchemy import desc, func, or_, select

from database import (
    SessionLocal,
    get_database_url,
    init_db,
    save_scan_feedback,
    save_scan_record,
    seed_demo_data,
)
from models import RecyclingRule, ScanFeedback, ScanRecord


PROJECT = {
    "name": "EcoLens 生活回收與標籤辨識助手",
    "short_name": "EcoLens",
    "subtitle": "打開手機或電腦鏡頭，讓回收分類像拍照一樣簡單",
    "team_members": ["林偲駒", "邱冠凱", "黃舒禾", "方守東"],
    "summary": (
        "EcoLens 是一個貼近日常生活的 Flask 專題。使用者打開網頁即可啟用裝置鏡頭，"
        "手機可使用前後鏡頭，電腦可使用前鏡頭，將包裝、瓶罐、紙盒或標籤對準鏡頭。"
        "目前版本結合影像特徵分析、OCR、使用者輸入線索、回收規則資料庫與網路搜尋摘要，"
        "先大致判斷垃圾分類；未來可串接圖像模型提高自動辨識能力。"
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
            categories = session.scalars(
                select(RecyclingRule.category).distinct().order_by(RecyclingRule.category)
            ).all()
        return render_template("scan.html", project=PROJECT, rules=rules, categories=categories)

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

    @app.post("/api/web-lookup")
    def web_lookup_api():
        payload = request.get_json(silent=True) or {}
        text = str(payload.get("text", "")).strip()
        device_type = str(payload.get("device_type", "web lookup")).strip() or "web lookup"
        if not text:
            return jsonify({"status": "error", "message": "請先提供照片 OCR 或物品線索。"}), 400

        result = analyze_with_web_lookup(text)
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

    @app.post("/api/visual-lookup")
    def visual_lookup_api():
        payload = request.get_json(silent=True) or {}
        text = str(payload.get("text", "")).strip()
        device_type = str(payload.get("device_type", "visual feature lookup")).strip()
        features = payload.get("features") or {}
        if not isinstance(features, dict):
            return jsonify({"status": "error", "message": "影像特徵格式錯誤，請重新拍照。"}), 400

        result = analyze_visual_features(features, text)
        record = save_scan_record(
            input_text=result["visual_lookup_text"],
            guessed_item=result["item_name"],
            suggested_category=result["category"],
            confidence=result["confidence"],
            notes=result["disposal_steps"],
            device_type=device_type or "visual feature lookup",
        )
        result["record_id"] = record.id
        return jsonify(result)

    @app.post("/api/feedback")
    def feedback_api():
        payload = request.get_json(silent=True) or {}
        scan_id = int(payload.get("record_id") or 0)
        is_correct = bool(payload.get("is_correct"))
        corrected_item = str(payload.get("corrected_item", "")).strip()
        corrected_category = str(payload.get("corrected_category", "")).strip()
        user_note = str(payload.get("user_note", "")).strip()

        try:
            feedback = save_scan_feedback(
                scan_id=scan_id,
                is_correct=is_correct,
                corrected_item=corrected_item,
                corrected_category=corrected_category,
                user_note=user_note,
            )
        except ValueError:
            return jsonify({"status": "error", "message": "找不到這筆掃描紀錄。"}), 404

        return jsonify(
            {
                "status": "ok",
                "feedback_id": feedback.id,
                "message": "已收到回饋，這些資料會用來改善分類規則與後續模型。",
            }
        )

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
            feedback_rows = session.scalars(select(ScanFeedback)).all()

        category_counts = Counter(rule.category for rule in rules_data)
        material_counts = Counter(rule.material or "未標示" for rule in rules_data)
        scanned_items = Counter(scan.guessed_item for scan in scans)
        corrected_categories = Counter(
            feedback.corrected_category for feedback in feedback_rows if feedback.corrected_category
        )
        low_confidence_count = sum(1 for scan in scans if scan.confidence < 0.5)
        incorrect_count = sum(1 for feedback in feedback_rows if not feedback.is_correct)
        feedback_count = len(feedback_rows)
        max_category = max(category_counts.values(), default=1)
        max_scanned = max(scanned_items.values(), default=1)
        max_corrected = max(corrected_categories.values(), default=1)

        return render_template(
            "analysis.html",
            project=PROJECT,
            category_counts=category_counts.most_common(),
            material_counts=material_counts.most_common(6),
            scanned_items=scanned_items.most_common(8),
            corrected_categories=corrected_categories.most_common(8),
            low_confidence_count=low_confidence_count,
            feedback_count=feedback_count,
            incorrect_count=incorrect_count,
            scan_count=len(scans),
            max_category=max_category,
            max_scanned=max_scanned,
            max_corrected=max_corrected,
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


CATEGORY_HINTS = [
    {
        "category": "資源回收 / 塑膠類",
        "item": "塑膠容器",
        "material": "PET / PP / PVC 或其他塑膠",
        "terms": ["寶特瓶", "pet", "pp", "pvc", "塑膠瓶", "飲料瓶", "塑膠容器", "plastic bottle", "plastic cup"],
        "steps": "若是乾淨塑膠容器，請倒空內容物、簡單沖洗、壓扁後投入塑膠類回收。",
    },
    {
        "category": "資源回收 / 塑膠杯",
        "item": "手搖飲塑膠杯",
        "material": "PP 或 PET 塑膠",
        "terms": ["手搖飲", "塑膠杯", "飲料杯", "杯膜", "吸管"],
        "steps": "倒掉剩餘飲料，杯膜與吸管分開，杯身沖洗後依地方規定投入塑膠類回收。",
    },
    {
        "category": "資源回收 / 紙容器",
        "item": "紙容器",
        "material": "紙、淋膜紙或複合紙材",
        "terms": ["紙容器", "紙餐盒", "紙杯", "紙盒", "牛奶盒", "鋁箔包", "利樂包", "paper carton", "carton"],
        "steps": "清空內容物，若可清潔請簡單沖洗或擦乾；油污嚴重時需依地方規定改作一般垃圾。",
    },
    {
        "category": "資源回收 / 廢紙類",
        "item": "紙箱",
        "material": "瓦楞紙板",
        "terms": ["紙箱", "瓦楞紙", "紙板", "棕色紙箱", "包裹箱", "外箱", "cardboard", "carton box", "brown box"],
        "steps": "移除膠帶、塑膠包材與非紙類填充物，保持乾燥並壓平後投入廢紙類回收；若受潮、沾油或沾滿食物殘渣，通常不適合回收。",
    },
    {
        "category": "資源回收 / 金屬類",
        "item": "鐵鋁罐",
        "material": "鐵、鋁或其他金屬",
        "terms": ["鐵罐", "鋁罐", "易開罐", "金屬罐", "鐵鋁罐", "aluminum can", "tin can"],
        "steps": "倒空內容物，簡單沖洗，壓扁後投入金屬容器回收。",
    },
    {
        "category": "資源回收 / 玻璃類",
        "item": "玻璃瓶",
        "material": "玻璃",
        "terms": ["玻璃瓶", "玻璃罐", "酒瓶", "醬料瓶", "glass bottle", "glass jar"],
        "steps": "倒空內容物並簡單沖洗，避免破裂割傷，依地方規定投入玻璃容器回收。",
    },
    {
        "category": "資源回收 / 乾電池",
        "item": "電池",
        "material": "金屬與化學材料",
        "terms": ["電池", "乾電池", "鈕扣電池", "battery", "battery recycle"],
        "steps": "不可丟一般垃圾，請投入超商、量販店、學校或清潔隊提供的電池回收點。",
    },
    {
        "category": "依地方規定回收",
        "item": "塑膠袋或保麗龍",
        "material": "塑膠薄膜或 PS 保麗龍",
        "terms": ["塑膠袋", "購物袋", "保麗龍", "保麗龍餐盒", "ps", "styrofoam"],
        "steps": "乾淨時可能可依地方規定回收；若沾滿油污、湯汁或食物殘渣，通常需作一般垃圾。",
    },
    {
        "category": "廚餘",
        "item": "廚餘",
        "material": "食物殘渣",
        "terms": ["廚餘", "剩菜", "果皮", "菜葉", "食物殘渣", "food waste"],
        "steps": "瀝乾水分後投入廚餘桶；骨頭、貝殼、衛生紙等不可混入，請依地方規定分類。",
    },
    {
        "category": "一般垃圾",
        "item": "衛生紙 / 紙巾",
        "material": "短纖維或受污染紙類",
        "terms": ["衛生紙", "紙巾", "面紙", "餐巾紙", "擦手紙", "廚房紙巾", "濕紙巾", "紙尿布", "toilet paper", "tissue"],
        "steps": "衛生紙、面紙、紙巾、擦手紙與濕紙巾通常不屬於廢紙回收；使用過或受污染時請作一般垃圾。若外包裝標示可丟馬桶的衛生紙，才可少量投入馬桶。",
    },
    {
        "category": "一般垃圾",
        "item": "一般垃圾",
        "material": "不可回收或污染物",
        "terms": ["口罩", "油污嚴重", "髒污", "污染紙", "不可回收", "吸油面紙", "複寫紙", "感熱紙"],
        "steps": "若物品沾滿油污、食物殘渣或屬衛生用品，通常不適合回收，請作一般垃圾處理。",
    },
]

TAIPEI_RECYCLING_ROWS: list[dict[str, str]] | None = None


def analyze_visual_features(features: dict[str, object], user_text: str = "") -> dict[str, object]:
    visual_profile = build_visual_profile(features)
    visual_terms = " ".join(visual_profile["terms"])
    lookup_text = " ".join(part for part in [user_text, visual_terms] if part).strip()
    if not lookup_text:
        lookup_text = "無明顯影像特徵"

    result = analyze_with_web_lookup(lookup_text)
    if visual_profile["confidence_boost"] and result["item_name"] != "未知物品":
        result["confidence"] = round(min(0.94, result["confidence"] + visual_profile["confidence_boost"]), 2)

    result["message"] = (
        f"已先解析照片特徵：{visual_profile['summary']}。"
        "系統再用這些特徵詞查詢公開分類資料與網路摘要，推測最接近的垃圾分類。"
    )
    result["visual_features"] = visual_profile["ratios"]
    result["visual_terms"] = visual_profile["terms"]
    result["visual_summary"] = visual_profile["summary"]
    result["visual_lookup_text"] = lookup_text
    return result


def build_visual_profile(features: dict[str, object]) -> dict[str, object]:
    ratios = {
        "cardboard_ratio": clamp_ratio(features.get("cardboard_ratio")),
        "white_ratio": clamp_ratio(features.get("white_ratio")),
        "gray_ratio": clamp_ratio(features.get("gray_ratio")),
        "highlight_ratio": clamp_ratio(features.get("highlight_ratio")),
        "dark_ratio": clamp_ratio(features.get("dark_ratio")),
        "green_ratio": clamp_ratio(features.get("green_ratio")),
        "blue_ratio": clamp_ratio(features.get("blue_ratio")),
        "red_orange_ratio": clamp_ratio(features.get("red_orange_ratio")),
        "transparent_like_ratio": clamp_ratio(features.get("transparent_like_ratio")),
        "metal_like_ratio": clamp_ratio(features.get("metal_like_ratio")),
        "wrinkle_ratio": clamp_ratio(features.get("wrinkle_ratio")),
        "edge_density": clamp_ratio(features.get("edge_density")),
    }

    candidates: list[tuple[float, str, list[str], str]] = []
    cardboard_score = ratios["cardboard_ratio"] * 1.8 + ratios["edge_density"] * 0.35
    if ratios["cardboard_ratio"] >= 0.10 and ratios["dark_ratio"] < 0.58:
        candidates.append(
            (
                cardboard_score,
                "紙箱 / 瓦楞紙板",
                ["棕色紙箱", "紙箱", "紙板", "瓦楞紙", "cardboard box"],
                "棕色紙板比例偏高，且畫面有紙箱邊緣或折線感",
            )
        )

    metal_score = ratios["metal_like_ratio"] * 1.5 + ratios["highlight_ratio"] * 0.5
    if ratios["metal_like_ratio"] >= 0.18 or (ratios["gray_ratio"] >= 0.24 and ratios["highlight_ratio"] >= 0.08):
        candidates.append(
            (
                metal_score,
                "鐵鋁罐 / 金屬容器",
                ["鐵鋁罐", "金屬罐", "鋁罐", "鐵罐", "aluminum can"],
                "灰白低飽和區塊與亮部反光較多，可能是金屬容器",
            )
        )

    tissue_score = ratios["wrinkle_ratio"] * 2.1 + ratios["white_ratio"] * 0.9 + ratios["edge_density"] * 0.45
    looks_like_soft_paper = (
        ratios["white_ratio"] >= 0.18
        and ratios["wrinkle_ratio"] >= 0.055
        and ratios["cardboard_ratio"] < 0.13
        and ratios["metal_like_ratio"] < 0.38
        and ratios["transparent_like_ratio"] < 0.45
    )
    if looks_like_soft_paper:
        candidates.append(
            (
                tissue_score,
                "衛生紙 / 紙巾",
                ["衛生紙", "紙巾", "面紙", "餐巾紙", "擦手紙", "一般垃圾"],
                "白色柔軟紙面與皺褶陰影明顯，可能是衛生紙、面紙或紙巾",
            )
        )

    white_score = ratios["white_ratio"] * 1.15 + ratios["transparent_like_ratio"] * 0.35
    if ratios["white_ratio"] >= 0.24 and ratios["cardboard_ratio"] < 0.12 and ratios["wrinkle_ratio"] < 0.11:
        candidates.append(
            (
                white_score,
                "白色紙容器 / 保麗龍餐盒",
                ["白色餐盒", "紙餐盒", "紙容器", "保麗龍餐盒", "styrofoam"],
                "白色或淺色區塊明顯，可能是紙餐盒、紙容器或保麗龍包材",
            )
        )

    plastic_score = ratios["transparent_like_ratio"] * 1.2 + ratios["blue_ratio"] * 0.5
    if ratios["transparent_like_ratio"] >= 0.28 or ratios["blue_ratio"] >= 0.18:
        candidates.append(
            (
                plastic_score,
                "塑膠瓶 / 塑膠容器",
                ["透明塑膠瓶", "寶特瓶", "塑膠容器", "PET", "plastic bottle"],
                "透明感、淺色反光或藍色包裝比例較高，可能是塑膠瓶罐",
            )
        )

    glass_score = ratios["green_ratio"] * 1.2 + ratios["highlight_ratio"] * 0.35
    if ratios["green_ratio"] >= 0.13 and ratios["highlight_ratio"] >= 0.04:
        candidates.append(
            (
                glass_score,
                "玻璃瓶 / 玻璃罐",
                ["玻璃瓶", "玻璃罐", "綠色玻璃瓶", "glass bottle"],
                "綠色透明感與反光同時出現，可能是玻璃瓶罐",
            )
        )

    candidates.sort(key=lambda item: item[0], reverse=True)
    if not candidates:
        strongest = max(ratios, key=ratios.get)
        readable = strongest.replace("_ratio", "").replace("_", " ")
        return {
            "terms": [],
            "summary": f"沒有足夠明顯的材質特徵；最明顯訊號是 {readable} 約 {ratios[strongest]:.0%}",
            "confidence_boost": 0.0,
            "ratios": ratios,
        }

    top_score, label, terms, reason = candidates[0]
    extra_terms: list[str] = []
    for _, _, candidate_terms, _ in candidates[1:3]:
        extra_terms.extend(candidate_terms[:2])

    summary = f"{reason}；初步候選為 {label}"
    confidence_boost = min(0.12, max(0.03, top_score / 10))
    return {
        "terms": [*terms, *extra_terms],
        "summary": summary,
        "confidence_boost": round(confidence_boost, 2),
        "ratios": ratios,
    }


def clamp_ratio(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return min(1.0, max(0.0, number))


def analyze_with_web_lookup(text: str) -> dict[str, object]:
    local_result = analyze_text(text)
    dataset_results = search_taipei_recycling_dataset(text)
    web_results = dataset_results + search_recycling_web(text)
    web_corpus = " ".join(
        [text, *[f"{item['title']} {item['snippet']}" for item in web_results]]
    )
    web_result = infer_from_dataset_result(dataset_results[0]) if dataset_results else infer_from_text_corpus(web_corpus)

    if web_result["confidence"] > local_result["confidence"] or local_result["item_name"] == "未知物品":
        result = web_result
        result["message"] = "已結合公開資料或網路搜尋摘要推測垃圾大類，請再依地方規定確認。"
    else:
        result = local_result
        result["message"] = "本地規則已有較明確結果，並已附上公開資料或網路查詢摘要供確認。"

    result["web_results"] = web_results
    result["lookup_query"] = build_lookup_query(text)
    result["source_name"] = result.get("source_name", "網路搜尋摘要")
    result["source_url"] = result.get("source_url", "")
    return result


def search_taipei_recycling_dataset(text: str) -> list[dict[str, str]]:
    rows = load_taipei_recycling_rows()
    if not rows:
        return []
    query_terms = build_query_terms(text)
    matches: list[tuple[int, dict[str, str]]] = []
    for row in rows:
        title = row.get("子類別", "")
        major = row.get("大類別", "")
        description = row.get("說明", "")
        pickup_time = row.get("回收時間", "")
        corpus = normalize_lookup_text(f"{title} {major} {description} {pickup_time}")
        score = sum(max(1, len(term)) for term in query_terms if term and term in corpus)
        if score > 0:
            matches.append(
                (
                    score,
                    {
                        "title": title or major or "臺北市回收分類資料",
                        "snippet": f"{major} / {description} / 回收時間：{pickup_time}",
                        "url": "https://data.taipei/dataset/detail?id=74643872-ee76-4727-bd02-d73b536eaad7",
                        "domain": "data.taipei",
                        "major_category": major,
                        "sub_category": title,
                        "pickup_time": pickup_time,
                        "score": str(score),
                    },
                )
            )

    matches.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in matches[:5]]


def load_taipei_recycling_rows() -> list[dict[str, str]]:
    global TAIPEI_RECYCLING_ROWS
    if TAIPEI_RECYCLING_ROWS is not None:
        return TAIPEI_RECYCLING_ROWS

    url = "https://data.taipei/api/frontstage/tpeod/dataset/resource.download"
    params = {"rid": "a4693269-1a96-4914-9c4d-cd7cfb3f3bce"}
    try:
        response = requests.get(url, params=params, timeout=8)
        response.raise_for_status()
    except SSLError:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", InsecureRequestWarning)
                response = requests.get(url, params=params, timeout=8, verify=False)
                response.raise_for_status()
        except requests.RequestException:
            TAIPEI_RECYCLING_ROWS = []
            return TAIPEI_RECYCLING_ROWS
    except requests.RequestException:
        TAIPEI_RECYCLING_ROWS = []
        return TAIPEI_RECYCLING_ROWS

    csv_text = response.content.decode("big5", errors="replace")
    TAIPEI_RECYCLING_ROWS = list(csv.DictReader(io.StringIO(csv_text)))
    return TAIPEI_RECYCLING_ROWS


def build_query_terms(text: str) -> list[str]:
    normalized = normalize_lookup_text(text)
    terms = {normalized}
    for hint in CATEGORY_HINTS:
        for term in hint["terms"]:
            cleaned = normalize_lookup_text(str(term))
            if cleaned and cleaned in normalized:
                terms.add(cleaned)
    for size in (4, 3, 2):
        for index in range(max(0, len(normalized) - size + 1)):
            fragment = normalized[index : index + size]
            if fragment and not fragment.isascii():
                terms.add(fragment)
    return sorted(terms, key=len, reverse=True)[:24]


def normalize_lookup_text(text: str) -> str:
    return text.lower().replace(" ", "").replace("\n", "").replace("\r", "")


def infer_from_dataset_result(result: dict[str, str]) -> dict[str, object]:
    major = result.get("major_category", "")
    sub_category = result.get("sub_category", "") or result.get("title", "回收物")
    snippet = result.get("snippet", "")
    combined = f"{major} {sub_category} {snippet}"
    if "不可回收" in combined:
        category = "一般垃圾"
    elif "立體類" in major:
        category = "臺北市回收 / 立體類"
    elif "平面類" in major:
        category = "臺北市回收 / 平面類"
    elif "其他類" in major:
        category = "臺北市回收 / 其他類"
    else:
        category = infer_from_text_corpus(combined)["category"]

    return {
        "item_name": sub_category,
        "category": category,
        "material": major or "公開資料分類",
        "disposal_steps": snippet,
        "confidence": round(min(0.9, 0.62 + int(result.get("score", "1")) / 40), 2),
        "source_name": "臺北市資源回收分類方式",
        "source_url": result.get("url", ""),
    }


def build_lookup_query(text: str) -> str:
    return f"{text} 垃圾分類 回收 怎麼丟"


def search_recycling_web(text: str) -> list[dict[str, str]]:
    query = build_lookup_query(text)
    try:
        response = requests.get(
            "https://duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "Mozilla/5.0 EcoLens classroom project"},
            timeout=8,
        )
        response.raise_for_status()
    except requests.RequestException:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    results: list[dict[str, str]] = []
    for node in soup.select(".result"):
        title_node = node.select_one(".result__a")
        snippet_node = node.select_one(".result__snippet")
        if not title_node:
            continue
        title = " ".join(title_node.get_text(" ", strip=True).split())
        snippet = " ".join((snippet_node.get_text(" ", strip=True) if snippet_node else "").split())
        url = title_node.get("href", "")
        if not title or "圖片" in title:
            continue
        results.append(
            {
                "title": title[:140],
                "snippet": snippet[:260],
                "url": url,
                "domain": urlparse(url).netloc,
            }
        )
        if len(results) >= 5:
            break
    return results


def infer_from_text_corpus(text: str) -> dict[str, object]:
    normalized = text.lower().replace(" ", "")
    best_hint: dict[str, object] | None = None
    best_score = 0
    for hint in CATEGORY_HINTS:
        score = 0
        for term in hint["terms"]:
            cleaned = str(term).lower().replace(" ", "")
            if cleaned and cleaned in normalized:
                score += max(2, len(cleaned))
        if score > best_score:
            best_score = score
            best_hint = hint

    if best_hint is None:
        return {
            "item_name": "未知物品",
            "category": "需要人工確認",
            "material": "無法判斷",
            "disposal_steps": "網路搜尋沒有找到足夠線索，請補充物品名稱、材質標示或使用者修正分類。",
            "confidence": 0.2,
            "source_name": "網路搜尋摘要",
            "source_url": "",
        }

    confidence = min(0.88, 0.36 + best_score / 30)
    return {
        "item_name": best_hint["item"],
        "category": best_hint["category"],
        "material": best_hint["material"],
        "disposal_steps": best_hint["steps"],
        "confidence": round(confidence, 2),
        "source_name": "網路搜尋摘要",
        "source_url": "",
    }


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
