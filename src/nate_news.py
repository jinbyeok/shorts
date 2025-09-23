import requests
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " +
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0 Safari/537.36"
}

def get_nate_top_news(date: str = "20250923", top_n: int = 10):
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
    response = requests.get(article_url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    # 본문 내용 가져오기
    article_content = soup.select_one("div.article")  # Nate 본문 영역
    return article_content.get_text("\n", strip=True) if article_content else None


# if __name__ == "__main__":
#     nate_news = get_nate_top_news("20250923", top_n=10)
#     print(f"nate_news: {nate_news}")
#     for idx, news in enumerate(nate_news, start=1):
#         content = get_nate_article_content(news['link'])
#         print("본문:", content[:200], "...\n")  # 본문 일부만 출력
