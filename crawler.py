from __future__ import annotations

import argparse
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from database import SessionLocal, init_db, upsert_rule


DEFAULT_URL = "https://recycle.moenv.gov.tw/"
DEFAULT_SOURCE_NAME = "環境部資源回收公開資訊"
KEYWORDS = ["回收", "資源", "分類", "容器", "塑膠", "紙", "鋁", "玻璃", "電池", "廚餘"]


def fetch_dynamic_html(url: str) -> str:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(locale="zh-TW")
        page.goto(url, wait_until="networkidle", timeout=60_000)
        page.wait_for_timeout(800)
        html = page.content()
        browser.close()
        return html


def infer_category(text: str) -> str:
    if any(term in text for term in ["寶特瓶", "PET", "塑膠", "PP", "PVC"]):
        return "資源回收 / 塑膠類"
    if any(term in text for term in ["紙容器", "紙餐盒", "紙杯", "紙盒"]):
        return "資源回收 / 紙容器"
    if any(term in text for term in ["鋁箔", "鐵罐", "鋁罐", "金屬"]):
        return "資源回收 / 金屬類"
    if any(term in text for term in ["玻璃", "玻璃瓶"]):
        return "資源回收 / 玻璃類"
    if "電池" in text:
        return "資源回收 / 乾電池"
    if "廚餘" in text:
        return "廚餘"
    return "回收資訊"


def infer_material(text: str) -> str:
    for material in ["PET", "PP", "PVC", "紙容器", "鋁箔", "金屬", "玻璃", "電池", "廚餘"]:
        if material in text:
            return material
    if "塑膠" in text:
        return "塑膠"
    if "紙" in text:
        return "紙類"
    return "未標示"


def extract_keywords(text: str) -> str:
    return ",".join(keyword for keyword in KEYWORDS if keyword in text)


def extract_rules(html: str, base_url: str, source_name: str, limit: int) -> list[dict[str, object]]:
    soup = BeautifulSoup(html, "html.parser")
    records: list[dict[str, object]] = []
    seen: set[str] = set()

    for anchor in soup.select("a[href]"):
        title = " ".join(anchor.get_text(" ", strip=True).split())
        href = anchor.get("href", "")
        if len(title) < 4:
            continue
        if any(skip in title for skip in ["回首頁", "網站導覽", "English", "登入", "搜尋"]):
            continue

        context = anchor.find_parent(["li", "tr", "article", "div"]) or anchor
        context_text = " ".join(context.get_text(" ", strip=True).split())
        combined = f"{title} {context_text}"
        keywords = extract_keywords(combined)
        if not keywords and len(records) >= 4:
            continue

        source_url = urljoin(base_url, href)
        key = f"{title}|{source_url}"
        if key in seen:
            continue
        seen.add(key)

        records.append(
            {
                "item_name": title[:120],
                "category": infer_category(combined),
                "material": infer_material(combined),
                "disposal_steps": context_text[:360] or "請依地方環保局公告進行分類與回收。",
                "city": "通用",
                "source_name": source_name,
                "source_url": source_url,
                "keywords": keywords or "回收",
            }
        )
        if len(records) >= limit:
            break

    return records


def save_rules(records: list[dict[str, object]]) -> tuple[int, int]:
    init_db(seed=False)
    created = 0
    updated = 0
    with SessionLocal() as session:
        for record in records:
            if upsert_rule(session, record):
                created += 1
            else:
                updated += 1
        session.commit()
    return created, updated


def main() -> None:
    parser = argparse.ArgumentParser(description="Crawl recycling information into the project database.")
    parser.add_argument("--url", default=DEFAULT_URL, help="Target dynamic page URL.")
    parser.add_argument("--source-name", default=DEFAULT_SOURCE_NAME, help="Source name saved in DB.")
    parser.add_argument("--limit", type=int, default=12, help="Maximum records to save.")
    parser.add_argument("--dry-run", action="store_true", help="Print parsed records without saving.")
    args = parser.parse_args()

    html = fetch_dynamic_html(args.url)
    records = extract_rules(html, args.url, args.source_name, args.limit)

    if args.dry_run:
        for record in records:
            print(f"- {record['item_name']} / {record['category']} / {record['source_url']}")
        return

    created, updated = save_rules(records)
    print(f"Crawler finished. Created {created}, updated {updated}.")


if __name__ == "__main__":
    main()
