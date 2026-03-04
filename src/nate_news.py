import re
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Iterable
from urllib.parse import quote_plus
import requests
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " +
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0 Safari/537.36"
}

ARTICLE_DB_PATH = "nate_news.db"


def init_news_db(db_path: str = ARTICLE_DB_PATH):
    """기사 저장을 위한 로컬 SQLite DB를 초기화합니다."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS nate_news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL,
                title TEXT NOT NULL,
                link TEXT NOT NULL UNIQUE,
                content TEXT,
                crawled_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_nate_news_keyword_crawled_at
            ON nate_news(keyword, crawled_at)
            """
        )


def save_news_to_db(news_list: Iterable[dict], keyword: str, db_path: str = ARTICLE_DB_PATH):
    """크롤링한 기사 목록을 SQLite DB에 저장합니다."""
    crawled_at = datetime.now().isoformat(timespec="seconds")
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            """
            INSERT OR IGNORE INTO nate_news (keyword, title, link, content, crawled_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    keyword,
                    article["title"],
                    article["link"],
                    article.get("content"),
                    crawled_at,
                )
                for article in news_list
            ],
        )


def get_saved_article_by_id(article_id: int, db_path: str = ARTICLE_DB_PATH):
    """DB에 저장된 기사를 ID로 조회합니다."""
    init_news_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT id, keyword, title, link, content, crawled_at
            FROM nate_news
            WHERE id = ?
            """,
            (article_id,),
        ).fetchone()

    return dict(row) if row else None


def list_saved_articles(limit: int = 20, db_path: str = ARTICLE_DB_PATH):
    """최근 저장된 기사 목록을 조회합니다."""
    init_news_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, keyword, title, link, crawled_at
            FROM nate_news
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]


def _extract_article_links(soup: BeautifulSoup):
    selectors = [
        "a.lt1",
        "a.tit",
        "div.mduSubjectList a",
        "ul.search_news_list a",
        "a[href*='/view/']",
    ]

    seen = set()
    extracted = []
    for selector in selectors:
        for link_tag in soup.select(selector):
            href = link_tag.get("href", "").strip()
            if not href:
                continue

            if href.startswith("//"):
                href = "https:" + href
            elif href.startswith("/"):
                href = "https://news.nate.com" + href

            if not href.startswith("http"):
                continue
            if "news.nate.com/view" not in href:
                continue

            title = link_tag.get_text(" ", strip=True)
            if not title:
                continue

            normalized_link = re.sub(r"[?&]mid=n\d+", "", href)
            if normalized_link in seen:
                continue
            seen.add(normalized_link)
            extracted.append({"title": title, "link": normalized_link})
    return extracted


def crawl_nate_news_by_keyword(keyword: str, top_n: int = 10):
    """Nate 뉴스 검색 결과에서 키워드 관련 기사 top_n개를 수집합니다."""
    encoded = quote_plus(keyword)
    url = f"https://news.nate.com/search?searchType=1&q={encoded}"
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    candidates = _extract_article_links(soup)

    news_list = []
    for article in candidates[:top_n]:
        content = get_nate_article_content(article["link"])
        news_list.append(
            {
                "title": article["title"],
                "link": article["link"],
                "content": content,
            }
        )
    return news_list


def _next_run_datetime(time_str: str):
    hour, minute = map(int, time_str.split(":"))
    now = datetime.now()
    run_at = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if run_at <= now:
        run_at += timedelta(days=1)
    return run_at


def schedule_keyword_crawl(
    keyword: str,
    time_str: str,
    top_n: int = 10,
    db_path: str = ARTICLE_DB_PATH,
):
    """매일 특정 시각에 키워드 기반 Nate 뉴스를 크롤링하고 DB에 저장합니다."""
    init_news_db(db_path)
    print(f"[scheduler] 키워드='{keyword}', 실행시각='{time_str}', DB='{db_path}'")

    while True:
        run_at = _next_run_datetime(time_str)
        wait_seconds = int((run_at - datetime.now()).total_seconds())
        print(f"[scheduler] 다음 실행: {run_at.isoformat(sep=' ', timespec='minutes')}")
        time.sleep(max(wait_seconds, 0))

        try:
            crawled_news = crawl_nate_news_by_keyword(keyword=keyword, top_n=top_n)
            save_news_to_db(crawled_news, keyword=keyword, db_path=db_path)
            print(f"[scheduler] 저장 완료: {len(crawled_news)}건")
        except Exception as exc:  # noqa: BLE001 - 스케줄러는 계속 실행되어야 함
            print(f"[scheduler] 크롤링 실패: {exc}")

def get_nate_top_news(date: str = "20250923", top_n: int = 10, timeout=10):
    base_url = f"https://news.nate.com/rank/interest?sc=ent&p=day&date={date}"
    response = requests.get(base_url, headers=headers)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # 2. 모든 <script> 태그와 <style> 태그를 찾아서 제거
    for unwanted_tag in soup.find_all(['script', 'style']):
        unwanted_tag.decompose() # 태그와 그 안의 내용을 문서에서 완전히 제거

    # 3. 기사 리스트 가져오기
    news_links = soup.select("div.mduSubjectList > div.mlt01 a")  # 최신 Nate 구조
    news_list = []

    # 4. 기사 title, link 설정
    for a in news_links[:top_n]:
        title = a.get_text(strip=True)
        link = a["href"]
        if not link.startswith("http"):
            link = "https:" + link
        
        content = get_nate_article_content(link)
        news_list.append({"title": title, "link": link, "content": content})
    return news_list

def get_nate_article_content(article_url: str):
    response = requests.get(article_url, headers=headers, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    # 본문 내용 가져오기
    # article_content = soup.select_one("div.article")  # Nate 본문 영역
    article_content = (
        soup.select_one("div.article")
        or soup.select_one("div#realArtcContents")
        or soup.select_one("div#articleContent")
    )
    return article_content.get_text("\n", strip=True) if article_content else None


# if __name__ == "__main__":
#     nate_news = get_nate_top_news("20250923", top_n=10)
#     print(f"nate_news: {nate_news}")
#     for idx, news in enumerate(nate_news, start=1):
#         content = get_nate_article_content(news['link'])
#         print("본문:", content[:200], "...\n")  # 본문 일부만 출력
