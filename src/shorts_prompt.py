import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# OpenAI API 클라이언트 초기화
# 루트(.env)에서 환경변수 로드
project_root_env = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=project_root_env)

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("환경변수 OPENAI_API_KEY가 설정되어 있지 않습니다. 루트 .env를 확인하세요.")

client = OpenAI(api_key=api_key)

def create_youtube_shorts_script(article_content: str) -> str:
    """
    뉴스 기사 본문을 유튜브 쇼츠용 스크립트로 요약
    """
    prompt = f"""
다음 뉴스 기사 내용을 바탕으로 유튜브 쇼츠용 스크립트를 작성해 주세요.

[기사 내용]
{article_content}

[조건]
- 많은 사람들이 공감하고 내용을 이해할 수 있도록 작성할 것
- 문장은 간결할 것
- 전체 스크립트를 읽었을 때 30초 이내여야 함
- 반드시 한국어 존댓말로 작성할 것
- ‘시작 → 본문 → 결론’ 구조를 가진 스크립트로 만들 것
- 결론에는 "구독", "좋아요", "댓글" 등의 행위를 강요하지 말 것
- 유튜브 쇼츠에 맞게 흥미를 끌 수 있도록 작성할 것
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",  # 혹은 gpt-4o / gpt-5 등 원하는 모델
        messages=[
            {"role": "system", "content": "너는 유튜브 쇼츠 전문 스크립트 작가이다."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=500
    )

    script = response.choices[0].message.content.strip()
    return script


# if __name__ == "__main__":
#     # 예시: 기사 본문 일부
#     article_text = """
# 최근 엔터테인먼트 업계에서 숏폼 콘텐츠가 급성장하고 있습니다.
# 짧은 영상으로 소비자들의 관심을 끌고, 새로운 수익 모델이 확대되고 있다는 분석입니다.
# """
#     shorts_script = create_youtube_shorts_script(article_text)
#     print("유튜브 쇼츠 스크립트:")
#     print(shorts_script)