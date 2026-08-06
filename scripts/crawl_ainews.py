"""
AI뉴스 자동 크롤러 — Google News RSS 기반 (누적 축적 방식)
실행: python scripts/crawl_ainews.py
결과: data/ainews.json  (신규 뉴스를 기존 데이터에 누적 추가, 최대 MAX_TOTAL건 보관)
"""

MAX_TOTAL = 500   # 최대 누적 보관 건수 (초과 시 오래된 것부터 제거)

import feedparser
import json
import datetime
import re
import os
import time

# ── RSS 피드 목록 ──────────────────────────────────────────────────────
FEEDS = [
    "https://news.google.com/rss/search?q=인공지능+생성AI+LLM&hl=ko&gl=KR&ceid=KR:ko",
    "https://news.google.com/rss/search?q=ChatGPT+Claude+Gemini+AI모델&hl=ko&gl=KR&ceid=KR:ko",
    "https://news.google.com/rss/search?q=AI+반도체+엔비디아+HBM&hl=ko&gl=KR&ceid=KR:ko",
    "https://news.google.com/rss/search?q=AI+정책+규제+AI기본법&hl=ko&gl=KR&ceid=KR:ko",
    "https://news.google.com/rss/search?q=네이버+카카오+LG+KT+AI+인공지능&hl=ko&gl=KR&ceid=KR:ko",
    "https://news.google.com/rss/search?q=OpenAI+Anthropic+Google+DeepMind+AI&hl=ko&gl=KR&ceid=KR:ko",
]

# ── AI 관련성 키워드 ───────────────────────────────────────────────────
AI_KEYWORDS = [
    "인공지능", "AI", "LLM", "ChatGPT", "GPT", "Claude", "Gemini",
    "생성AI", "언어모델", "NVIDIA", "GPU", "딥러닝", "머신러닝",
    "OpenAI", "Anthropic", "DeepMind", "Copilot", "HyperCLOVA",
    "로봇", "자율주행", "AI칩", "온디바이스", "엑사원", "카나나",
    "HBM", "NPU", "AI반도체", "파운데이션모델",
]

# ── 카테고리 분류 규칙 ────────────────────────────────────────────────
CAT_RULES = [
    ("생성AI", [
        "ChatGPT", "GPT-", "Claude", "Gemini", "LLM", "생성AI", "거대언어모델",
        "언어모델", "Llama", "Copilot", "HyperCLOVA", "클로바", "카나나",
        "엑사원", "o1", "o3", "Sora", "멀티모달", "파운데이션", "챗봇",
        "OpenAI", "Anthropic",
    ]),
    ("정책/규제", [
        "AI법", "AI기본법", "규제", "정책", "법률", "거버넌스", "행정",
        "부처", "법안", "입법", "의회", "EU AI", "행정명령", "과기부",
        "행안부", "금융위", "안전기준", "가이드라인", "윤리",
    ]),
    ("기업동향", [
        "엔비디아", "NVIDIA", "삼성전자", "SK하이닉스", "애플", "마이크로소프트",
        "MS", "구글", "메타", "아마존", "투자", "매출", "출시", "인수합병",
        "주가", "시가총액", "HBM", "NPU", "데이터센터", "클라우드",
    ]),
    ("연구/기술", [
        "연구", "논문", "알고리즘", "학습", "기술", "발표", "성능",
        "반도체", "칩", "GPU", "양자", "로봇", "자율주행", "AlphaFold",
        "벤치마크", "오픈소스", "파라미터",
    ]),
    ("국내AI", [
        "네이버", "카카오", "LG AI", "LG전자", "KT AI", "SK텔레콤", "SKT",
        "삼성SDS", "현대차", "한국", "국내", "서울대", "KAIST", "정부24",
        "과학기술", "정보통신",
    ]),
]


def is_ai_related(text: str) -> bool:
    text_l = text.lower()
    return any(kw.lower() in text_l for kw in AI_KEYWORDS)


def categorize(text: str) -> str:
    for cat, keywords in CAT_RULES:
        if any(k.lower() in text.lower() for k in keywords):
            return cat
    return "연구/기술"


def parse_date(entry) -> str:
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            dt = datetime.datetime(*entry.published_parsed[:6])
            return dt.strftime("%Y-%m-%d")
        except Exception:
            pass
    return datetime.date.today().strftime("%Y-%m-%d")


def clean_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    for ent, rep in [("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                     ("&quot;", '"'), ("&#39;", "'"), ("&nbsp;", " ")]:
        text = text.replace(ent, rep)
    text = re.sub(r"&#\d+;", "", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_source(entry) -> str:
    """Google News RSS 에서 원래 매체명 추출"""
    if hasattr(entry, "source") and hasattr(entry.source, "title"):
        return entry.source.title
    title = entry.get("title", "")
    if " - " in title:
        return title.rsplit(" - ", 1)[-1].strip()
    return "Google뉴스"


def extract_title(entry) -> str:
    """Google News RSS 제목에서 매체명 접미사 제거"""
    title = clean_html(entry.get("title", ""))
    if " - " in title:
        title = title.rsplit(" - ", 1)[0].strip()
    return title


def crawl_all() -> list:
    seen_titles: set = set()
    items: list = []

    for feed_url in FEEDS:
        try:
            print(f"  Fetching: {feed_url[:70]}...")
            feed = feedparser.parse(feed_url)

            for entry in feed.entries[:25]:
                title = extract_title(entry)
                if not title or title in seen_titles:
                    continue

                summary = clean_html(entry.get("summary", ""))
                combined = title + " " + summary

                if not is_ai_related(combined):
                    continue

                seen_titles.add(title)
                source = extract_source(entry)
                cat = categorize(combined)
                link = entry.get("link", "")

                # 설명: summary 우선, 없으면 title 기반 자동 생성
                if len(summary) > 30:
                    desc = summary[:250] + ("..." if len(summary) > 250 else "")
                else:
                    desc = f"{title}. AI 분야의 최신 동향입니다."

                items.append({
                    "date":   parse_date(entry),
                    "cat":    cat,
                    "title":  title,
                    "source": source,
                    "desc":   desc,
                    "link":   link,
                })

            time.sleep(1.5)  # 요청 간 간격

        except Exception as e:
            print(f"  ⚠️ Error [{feed_url[:50]}]: {e}")

    # 날짜 내림차순 (이번 배치 내)
    items.sort(key=lambda x: x["date"], reverse=True)
    return items


def accumulate(new_items: list) -> list:
    """신규 뉴스를 기존 누적 데이터에 추가 (중복 제목 제외)"""
    path = "data/ainews.json"
    existing: list = []

    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                existing = json.load(f)
            print(f"  기존 누적: {len(existing)}건")
        except Exception:
            pass

    seen_titles = {item["title"] for item in existing}
    added = 0
    for item in new_items:
        if item["title"] not in seen_titles:
            existing.append(item)
            seen_titles.add(item["title"])
            added += 1

    print(f"  신규 추가: {added}건")

    # 날짜 내림차순 전체 정렬
    existing.sort(key=lambda x: x["date"], reverse=True)

    # 최대 보관 건수 초과 시 오래된 뉴스 제거
    if len(existing) > MAX_TOTAL:
        removed = len(existing) - MAX_TOTAL
        existing = existing[:MAX_TOTAL]
        print(f"  오래된 뉴스 {removed}건 정리 (최대 {MAX_TOTAL}건 유지)")

    return existing


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print(f"AI뉴스 크롤링 시작: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    new_items = crawl_all()
    print(f"\n이번 수집: {len(new_items)}건")

    os.makedirs("data", exist_ok=True)
    output_path = "data/ainews.json"

    accumulated = accumulate(new_items)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(accumulated, f, ensure_ascii=False, indent=2)
    print(f"저장 완료: {output_path} (누적 {len(accumulated)}건)")

    print(f"{'='*60}\n")
