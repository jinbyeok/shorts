from src.nate_news import get_nate_top_news
from src.shorts_prompt import create_youtube_shorts_script
from src.veo3 import make_shorts_video

def main():
    nate_news = get_nate_top_news("20250923", top_n=10)
    print(f"nate_news: {nate_news}")

    first_news_content = nate_news[0]['content']
    shorts_script = create_youtube_shorts_script(first_news_content)
    print(f"script: {shorts_script}")

    make_shorts_video(shorts_script, output_path="youtube_shorts.mp4")


if __name__ == "__main__":
    main()
