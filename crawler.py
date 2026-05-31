from __future__ import annotations

import argparse
import re
from datetime import date
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from database import SessionLocal, init_db, upsert_article


DEFAULT_URL = "https://www.osha.gov.tw/48110/48417/48419/lpsimplelist"
DEFAULT_SOURCE_NAME = "勞動部職業安全衛生署新聞稿"
RISK_TERMS = ["安全帽", "工安", "職安", "職災", "營造", "墜落", "高處", "機械", "感電", "高溫", "防護", "教育訓練"]
NON_ARTICLE_TERMS = [
    "按Enter",
    "回首頁",
    "網站導覽",
    "English",
    "RSS",
    "意見信箱",
    "雙語辭彙",
    "首頁",
    "新聞公告",
    "顯示條件查詢",
    "第一頁",
    "下一頁",
    "最後一頁",
    "回上一頁",
]


def fetch_dynamic_html(url: str) -> str:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(locale="zh-TW")
        page.goto(url, wait_until="networkidle", timeout=60_000)
        page.wait_for_timeout(800)
        html = page.content()
        browser.close()
        return html


def parse_roc_or_ad_date(raw_text: str) -> date | None:
    match = re.search(r"(\d{3,4})[-/.年](\d{1,2})[-/.月](\d{1,2})", raw_text)
    if not match:
        return None

    year = int(match.group(1))
    month = int(match.group(2))
    day = int(match.group(3))
    if year < 1911:
        year += 1911

    try:
        return date(year, month, day)
    except ValueError:
        return None


def categorize(text: str) -> str:
    if any(term in text for term in ["安全帽", "防護具", "個人防護"]):
        return "個人防護"
    if any(term in text for term in ["墜落", "高處", "營造"]):
        return "營造安全"
    if any(term in text for term in ["機械", "夾捲", "停機"]):
        return "機械安全"
    if any(term in text for term in ["高溫", "熱危害", "健康"]):
        return "職業衛生"
    if any(term in text for term in ["教育", "訓練", "宣導"]):
        return "職安宣導"
    return "工安新聞"


def extract_keywords(text: str) -> str:
    return ",".join(term for term in RISK_TERMS if term in text)


def extract_articles(html: str, base_url: str, source_name: str, limit: int) -> list[dict[str, object]]:
    soup = BeautifulSoup(html, "html.parser")
    records: list[dict[str, object]] = []
    seen_urls: set[str] = set()
    is_osha_news_page = "osha.gov.tw/48110/48417/48419" in base_url

    for anchor in soup.select("a[href]"):
        title = " ".join(anchor.get_text(" ", strip=True).split())
        href = anchor.get("href", "")
        if len(title) < 8:
            continue
        if any(skip in title for skip in NON_ARTICLE_TERMS):
            continue

        source_url = urljoin(base_url, href)
        if source_url in seen_urls:
            continue
        if href.startswith("javascript:") or href == "#":
            continue

        context_node = anchor.find_parent(["li", "tr", "article", "div"]) or anchor
        context_text = " ".join(context_node.get_text(" ", strip=True).split())
        combined = f"{title} {context_text}"
        keywords = extract_keywords(combined)
        published_at = parse_roc_or_ad_date(context_text)

        if is_osha_news_page and "/48110/48417/48419/" not in source_url:
            continue
        if is_osha_news_page and not source_url.endswith("/post"):
            continue
        if not is_osha_news_page and "/post" not in source_url and not published_at and not keywords:
            continue

        if not keywords and len(records) >= 5:
            continue

        seen_urls.add(source_url)
        records.append(
            {
                "title": title[:255],
                "summary": context_text[:320] if context_text else title,
                "source_name": source_name,
                "source_url": source_url,
                "category": categorize(combined),
                "published_at": published_at,
                "keywords": keywords or "職安",
            }
        )
        if len(records) >= limit:
            break

    return records


def save_articles(records: list[dict[str, object]]) -> tuple[int, int]:
    init_db(seed=False)
    created = 0
    updated = 0
    with SessionLocal() as session:
        for record in records:
            if upsert_article(session, record):
                created += 1
            else:
                updated += 1
        session.commit()
    return created, updated


def main() -> None:
    parser = argparse.ArgumentParser(description="Crawl dynamic safety web pages into the project database.")
    parser.add_argument("--url", default=DEFAULT_URL, help="Target dynamic page URL.")
    parser.add_argument("--source-name", default=DEFAULT_SOURCE_NAME, help="Source name saved in DB.")
    parser.add_argument("--limit", type=int, default=12, help="Maximum records to save.")
    parser.add_argument("--dry-run", action="store_true", help="Print parsed records without saving.")
    args = parser.parse_args()

    html = fetch_dynamic_html(args.url)
    records = extract_articles(html, args.url, args.source_name, args.limit)

    if args.dry_run:
        for record in records:
            print(f"- {record['title']} / {record['category']} / {record['source_url']}")
        return

    created, updated = save_articles(records)
    print(f"Crawler finished. Created {created}, updated {updated}.")


if __name__ == "__main__":
    main()
