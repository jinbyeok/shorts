## 환경 변수 설정

루트 경로(`c:\workspace\shorts`)에 `.env` 파일을 생성하고 아래와 같이 설정하세요:

```
OPENAI_API_KEY=your_openai_api_key_here
```

예시 파일은 `.env.example`을 참고하세요.



## Nate 뉴스 키워드 크롤링 + 로컬 DB 저장

원하는 키워드와 시간을 지정해 Nate 뉴스를 크롤링하고 SQLite DB에 저장할 수 있습니다.

### 1) 즉시 1회 크롤링

```bash
python main.py --keyword "아이폰" --crawl-once --top-n 10
```

### 2) 매일 지정 시각에 자동 크롤링

```bash
python main.py --keyword "아이폰" --time 09:30 --top-n 10
```

- `--time` 형식: `HH:MM` (24시간제)
- 기본 DB 파일: `nate_news.db`
- DB 파일을 바꾸려면 `--db-path`를 사용하세요.

```bash
python main.py --keyword "반도체" --time 18:00 --db-path ./data/news.db
```

저장 테이블(`nate_news`) 주요 컬럼:
- `keyword`: 검색 키워드
- `title`: 기사 제목
- `link`: 기사 URL (중복 방지)
- `content`: 기사 본문
- `crawled_at`: 수집 시각


## 저장된 기사로 30초 영상 만들기 (Google AI)

DB에 저장된 기사 1건을 선택해 **자막 + 기사 읽는 보이스**가 포함된 최대 30초 영상을 만들 수 있습니다.

### 1) 저장된 기사 목록 조회

```bash
python main.py --list-articles --top-n 10
```

### 2) 기사 ID로 영상 생성

```bash
python main.py --make-video --article-id 3 --video-output ./news_3.mp4
```

선택 옵션:

```bash
python main.py --make-video --article-id 3 --voice-name Kore --video-output ./news_3.mp4
```

필요 환경 변수:
- `GOOGLE_API_KEY` (Google GenAI 호출용)

기본 동작:
- 기사 본문을 Google AI로 30초 내 내레이션 스크립트로 요약
- Google AI TTS 음성을 생성
- 제목/자막/보이스를 합성해 세로형(1080x1920) 쇼츠 영상으로 저장
