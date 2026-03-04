import argparse

from src.nate_news import (
    crawl_nate_news_by_keyword,
    get_nate_top_news,
    get_saved_article_by_id,
    init_news_db,
    list_saved_articles,
    save_news_to_db,
    schedule_keyword_crawl,
)
from src.news_video import create_news_video_from_article


def parse_args():
    parser = argparse.ArgumentParser(description="Nate 뉴스 크롤링/숏츠 생성 도구")
    parser.add_argument("--keyword", help="크롤링할 검색어")
    parser.add_argument("--time", dest="schedule_time", help="매일 실행 시각(HH:MM, 24시간)")
    parser.add_argument("--top-n", type=int, default=10, help="수집 기사 개수")
    parser.add_argument("--db-path", default="nate_news.db", help="SQLite DB 파일 경로")
    parser.add_argument(
        "--crawl-once",
        action="store_true",
        help="스케줄 대신 즉시 1회 크롤링 후 DB 저장",
    )
    parser.add_argument(
        "--list-articles",
        action="store_true",
        help="DB에 저장된 최근 기사 목록 조회",
    )
    parser.add_argument("--article-id", type=int, help="영상으로 만들 기사 ID")
    parser.add_argument(
        "--make-video",
        action="store_true",
        help="DB 기사 1건을 30초 내 영상(자막+보이스)으로 생성",
    )
    parser.add_argument(
        "--video-output",
        default="news_shorts.mp4",
        help="생성할 영상 파일 경로",
    )
    parser.add_argument(
        "--voice-name",
        default="Kore",
        help="Google AI TTS voice name (예: Kore)",
    )
    return parser.parse_args()

def main():
    args = parse_args()

    if args.keyword and args.crawl_once:
        init_news_db(args.db_path)
        crawled_news = crawl_nate_news_by_keyword(args.keyword, top_n=args.top_n)
        save_news_to_db(crawled_news, keyword=args.keyword, db_path=args.db_path)
        print(f"총 {len(crawled_news)}건의 기사를 저장했습니다.")
        return

    if args.keyword and args.schedule_time:
        schedule_keyword_crawl(
            keyword=args.keyword,
            time_str=args.schedule_time,
            top_n=args.top_n,
            db_path=args.db_path,
        )
        return

    if args.list_articles:
        articles = list_saved_articles(limit=args.top_n, db_path=args.db_path)
        if not articles:
            print("저장된 기사가 없습니다.")
            return
        for article in articles:
            print(
                f"[{article['id']}] ({article['crawled_at']}) "
                f"{article['title']} / keyword={article['keyword']}"
            )
        return

    if args.make_video:
        if not args.article_id:
            raise ValueError("--make-video 사용 시 --article-id를 함께 입력하세요.")
        article = get_saved_article_by_id(args.article_id, db_path=args.db_path)
        if not article:
            raise ValueError(f"ID {args.article_id} 기사 데이터를 찾지 못했습니다.")
        if not article.get("content"):
            raise ValueError("기사 본문(content)이 비어 있어 영상을 만들 수 없습니다.")

        output_path, script = create_news_video_from_article(
            article_title=article["title"],
            article_content=article["content"],
            output_path=args.video_output,
            max_seconds=30,
            voice_name=args.voice_name,
        )
        print(f"영상 생성 완료: {output_path}")
        print("생성된 스크립트:")
        print(script)
        return

    from src.shorts_prompt import create_youtube_shorts_script
    from src.veo3 import make_shorts_video

    nate_news = get_nate_top_news("20250923", top_n=10)
    print(f"nate_news: {nate_news}")

    first_news_content = nate_news[0]['content']
    shorts_script = create_youtube_shorts_script(first_news_content)
    print(f"script: {shorts_script}")

    make_shorts_video(shorts_script, output_path="youtube_shorts.mp4")


if __name__ == "__main__":
    main()
