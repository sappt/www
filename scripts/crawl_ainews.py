"""
농업·작물보호 뉴스 자동 크롤러 — Google News RSS 기반 (누적 축적 방식)

실행:  python scripts/crawl_ainews.py
산출:  assets/json/ainews.json       누적 기사 목록 (최대 MAX_TOTAL건)
       assets/json/ainews_meta.json  수집 기준 — 검색어·추출 어휘·추천검색어·통계
                                     (news.html 의 '수집 기준' 패널이 이 파일을 읽는다)

의존성 없음 — 표준 라이브러리만 사용합니다.
(feedparser 는 이 서버의 시스템 파이썬에 설치되어 있지 않아, 로컬 크론과
 GitHub Actions 양쪽에서 동일하게 돌도록 urllib + ElementTree 로 구현했습니다.)

수집 대상은 농약 등록·시험, 잔류허용기준(PLS), 병해충 발생, 작물보호 산업 동향입니다.
지자체 방제 홍보 기사는 스코어링으로 걸러냅니다.
"""

import datetime
import email.utils
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

# ══════════════════════════════════════════════════════════════════════
#  설정
# ══════════════════════════════════════════════════════════════════════

MAX_TOTAL = 500       # 누적 보관 상한 (초과 시 오래된 기사부터 제거)
RECENT_DAYS = 180     # 이보다 오래된 기사는 수집하지 않음
MIN_SCORE = 1         # 이 점수 미만이면 hidden 처리 (삭제하지 않고 보관)
PER_FEED_LIMIT = 100  # 피드당 최대 처리 건수 (구글은 피드당 50~75건을 돌려준다)
REQUEST_GAP = 1.5     # 피드 간 요청 간격(초)
RETRY = 3             # 피드별 재시도 횟수

UA = "Mozilla/5.0 (compatible; SapptNewsBot/1.0; +https://www.sappt.co.kr/)"

# ── 카테고리별 검색어 ──────────────────────────────────────────────────
# 카테고리는 카드 필터 버튼과 1:1 대응합니다. 순서가 곧 버튼 순서입니다.
FEEDS = [
    ("농약·작물보호", [
        "농약 병해충 방제",
        "작물보호제 등록 농약",
    ]),
    ("정책·제도", [
        "농약 잔류허용기준 PLS 식약처",
        "농촌진흥청 농약 고시 개정",
    ]),
    ("병해충 발생", [
        "병해충 발생 예찰 조사 결과",
        "과수화상병 돌발해충 발생",
        "농작물 병해충 발생 전망",
    ]),
    ("시험·연구", [
        "농약 직권등록 시험",
        "농업과학원 작물보호 연구",
        "약효 약해 시험 농약 등록",
    ]),
    ("산업·기업", [
        "팜한농 경농 동방아그로 농협케미컬",
        "친환경농자재 생물농약",
        "작물보호제 시장 신제품",
    ]),
]

# ── 관련성 키워드: 하나도 없으면 수집 대상이 아님 ──────────────────────
DOMAIN_KEYWORDS = [
    "농약", "병해충", "방제", "작물보호", "농작물", "살균제", "살충제", "제초제",
    "잔류", "PLS", "MRL", "예찰", "약해", "약효", "농진청", "농촌진흥청",
    "농자재", "농업", "재배", "병해", "해충", "농산물", "농가", "농협",
]

# ── 신뢰 매체: 가점 대상 (농업 전문지 + 통신사) ────────────────────────
TRUSTED_SOURCES = {
    "영농자재신문", "농민신문", "한국농어민신문", "농수축산신문", "농업인신문",
    "한국농정신문", "한국영농신문", "농촌여성신문", "농기자재신문", "농축유통신문",
    "연합뉴스", "뉴시스", "뉴스1", "식약일보", "kenews.co.kr", "아그리뉴스",
    "농업정보신문", "한국농업신문", "농어민신문",
}

# ── 가점 키워드: 시험 연구소 관점에서 실질 정보가 있는 기사의 표지 ─────
SIGNAL_PATTERN = re.compile(
    r"(등록|고시|개정|신설|기준|잔류|PLS|MRL|직권등록|시험|연구|개발|승인|허가"
    r"|출시|특허|안전성|저항성|약효|약해|지침서|평가|보고서|통계|수출|원제"
    r"|신제품|품목|잠정|재평가|독성|이력|검출|부적합)"
)

# ── 감점 1: 지자체 홍보 기사 (전체의 약 15%를 차지) ───────────────────
LOCALGOV_PATTERN = re.compile(
    # "청양군, ...", "경기도, ...", "전남광주특별시, ..." — 앞자리를 넉넉히 잡는다
    r"^[가-힣]{2,7}(시|군|구|도)\s*[,·]"
    r"|[가-힣]{2,4}(시|군)\s*[가-힣]{1,3}(읍|면|동)"  # "의성군 단북면"
    r"|농업기술센터|농기센터|[가-힣]{2,3}농협"
)

# ── 감점 2: 홍보·행사성 문구 ──────────────────────────────────────────
PROMO_PATTERN = re.compile(
    r"(공동방제|당부|총력|캠페인|협의회|간담회|성료|위촉|시상|표창"
    r"|방제 실시|지도 실시|현장 점검|홍보|다짐|발대식|박차)"
)

# ── 즉시 제외: 뉴스카드에 절대 올라오면 안 되는 것 ────────────────────
BLOCK_PATTERN = re.compile(r"(부고|인사말|신임|채용공고|동정|주가|증권가|운세|날씨)")

# ── 추천검색어: 고정 어휘 (사전에서 나오지 않는 축) ───────────────────
# 실제 뉴스 제목의 어휘는 작물·병해충명보다 주제어 층위에 몰려 있다.
# (실측: 농약 27건 / 방제 17건 / 작물보호제 10건 vs 사과·탄저병 0건)
# 그래서 주제어를 별도 타입으로 두되, 어디까지나 화이트리스트로 한정한다 —
# 빈도만으로 뽑으면 '시험·발생·등록·주의' 같은 일반명사가 상위를 점령한다.
FIXED_KEYWORDS = {
    "주제": [
        "농약", "방제", "작물보호제", "병해충", "잔류농약", "제초제",
        "살충제", "살균제", "생물농약", "드론방제", "돌발해충", "예찰",
        "약제저항성", "친환경", "안전사용", "농자재",
    ],
    "기관·기업": [
        "농진청", "농촌진흥청", "작물보호협회", "식약처", "농관원", "농업과학원",
        "팜한농", "경농", "동방아그로", "농협케미컬", "성보화학", "인바이오",
    ],
    "제도": [
        "PLS", "잔류허용기준", "직권등록", "안전사용기준", "재평가", "지침서",
        "친환경농자재", "유기농업자재", "스마트농업", "차등관리제",
    ],
}

# 병해충 사전에 없는 노지 작물 (사전은 시설·과수 중심이라 벼·콩 등이 빠져 있다)
EXTRA_CROPS = [
    "벼", "콩", "옥수수", "감자", "고구마", "인삼", "참깨", "밀", "보리",
    "토마토", "파프리카", "블루베리", "복숭아", "자두", "단감", "차나무",
]

# 추천검색어 노출 조건
# 최소 매칭 기사 수는 누적량에 따라 올라간다 — 초기에는 2건, 400건 쌓이면 5건.
KW_MIN_HITS_FLOOR = 2
KW_PER_TYPE = {"주제": 6, "작물": 4, "병해충": 4, "기관·기업": 3, "제도": 3}

# ── 경로 (스크립트 위치 기준으로 해석 — 어디서 실행해도 동일) ─────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEWS_PATH = os.path.join(ROOT, "assets", "json", "ainews.json")
META_PATH = os.path.join(ROOT, "assets", "json", "ainews_meta.json")
DICT_PATH = os.path.join(ROOT, "assets", "json", "sapptSicknessDic.json")


# ══════════════════════════════════════════════════════════════════════
#  수집
# ══════════════════════════════════════════════════════════════════════

def feed_url(query: str) -> str:
    return ("https://news.google.com/rss/search?q="
            + urllib.parse.quote(query) + "&hl=ko&gl=KR&ceid=KR:ko")


def fetch(url: str) -> bytes:
    """재시도 포함 HTTP GET. 모두 실패하면 예외를 올린다."""
    last = None
    for attempt in range(1, RETRY + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=25) as resp:
                return resp.read()
        except Exception as e:          # noqa: BLE001 - 네트워크 오류 전반
            last = e
            if attempt < RETRY:
                time.sleep(2 * attempt)
    raise last


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    for ent, rep in [("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                     ("&quot;", '"'), ("&#39;", "'"), ("&nbsp;", " ")]:
        text = text.replace(ent, rep)
    text = re.sub(r"&#\d+;", "", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_pubdate(raw: str):
    """RFC-2822 pubDate → date 객체. 실패하면 None (오늘 날짜로 위장하지 않는다)."""
    if not raw:
        return None
    try:
        return email.utils.parsedate_to_datetime(raw).date()
    except Exception:
        return None


def split_title(raw_title: str, source_hint: str) -> str:
    """구글 뉴스 제목 끝의 ' - 매체명' 접미사를 제거한다."""
    title = clean_text(raw_title)
    if source_hint and title.endswith(" - " + source_hint):
        return title[: -(len(source_hint) + 3)].strip()
    if " - " in title:
        return title.rsplit(" - ", 1)[0].strip()
    return title


def is_relevant(title: str) -> bool:
    return any(kw in title for kw in DOMAIN_KEYWORDS)


def score_article(title: str, source: str) -> int:
    """
    시험 연구소 관점의 관련성 점수.
    정렬에는 쓰지 않는다 — 오래된 기사가 상위로 올라오기 때문이다.
    노출/보류를 가르는 게이트로만 쓴다.
    """
    score = 0
    if source in TRUSTED_SOURCES:
        score += 3
    score += 2 * len(SIGNAL_PATTERN.findall(title))
    if LOCALGOV_PATTERN.search(title):
        score -= 3
    if PROMO_PATTERN.search(title):
        score -= 2
    return score


def crawl_all() -> list:
    cutoff = datetime.date.today() - datetime.timedelta(days=RECENT_DAYS)
    seen_titles = set()
    items = []

    for cat, queries in FEEDS:
        for query in queries:
            url = feed_url(query)
            print(f"  [{cat}] {query}")
            try:
                raw = fetch(url)
                root = ET.fromstring(raw)
            except Exception as e:      # noqa: BLE001
                print(f"    ! 실패: {e}")
                continue

            taken = 0
            for entry in root.findall("./channel/item")[:PER_FEED_LIMIT]:
                src_el = entry.find("source")
                source = clean_text(src_el.text) if src_el is not None else "Google뉴스"
                publisher = (src_el.get("url", "") if src_el is not None else "")

                title = split_title(entry.findtext("title", ""), source)
                if not title or title in seen_titles:
                    continue
                if BLOCK_PATTERN.search(title) or not is_relevant(title):
                    continue

                published = parse_pubdate(entry.findtext("pubDate", ""))
                if published is None or published < cutoff:
                    continue

                seen_titles.add(title)
                score = score_article(title, source)
                items.append({
                    "date":      published.strftime("%Y-%m-%d"),
                    "cat":       cat,
                    "title":     title,
                    "source":    source,
                    "publisher": publisher,
                    "link":      clean_text(entry.findtext("link", "")),
                    "score":     score,
                    "hidden":    score < MIN_SCORE,
                })
                taken += 1

            print(f"    → {taken}건")
            time.sleep(REQUEST_GAP)

    items.sort(key=lambda x: x["date"], reverse=True)
    return items


# ══════════════════════════════════════════════════════════════════════
#  누적
# ══════════════════════════════════════════════════════════════════════

def load_json(path, fallback):
    if not os.path.exists(path):
        return fallback
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if data else fallback
    except Exception:
        return fallback


def accumulate(new_items: list) -> list:
    existing = load_json(NEWS_PATH, [])
    print(f"  기존 누적: {len(existing)}건")

    by_title = {item["title"]: item for item in existing}
    added = 0
    for item in new_items:
        if item["title"] not in by_title:
            by_title[item["title"]] = item
            added += 1
    print(f"  신규 추가: {added}건")

    # 누적분 전체를 매번 다시 채점한다.
    # 이번 수집에 다시 잡힌 기사만 갱신하면, 규칙을 바꿔도 옛 기사는 옛 점수로 남는다
    # (구글 뉴스는 같은 기사를 매번 돌려주지 않는다).
    rescored = 0
    for item in by_title.values():
        score = score_article(item["title"], item.get("source", ""))
        if item.get("score") != score:
            rescored += 1
        item["score"] = score
        item["hidden"] = score < MIN_SCORE
    if rescored:
        print(f"  재채점 변경: {rescored}건")

    merged = sorted(by_title.values(), key=lambda x: x["date"], reverse=True)
    if len(merged) > MAX_TOTAL:
        print(f"  오래된 기사 {len(merged) - MAX_TOTAL}건 정리 (상한 {MAX_TOTAL}건)")
        merged = merged[:MAX_TOTAL]
    return merged, added


# ══════════════════════════════════════════════════════════════════════
#  추천검색어
# ══════════════════════════════════════════════════════════════════════

DISEASE_TOKENS = [
    "탄저병", "노균병", "흰가루병", "잿빛곰팡이병", "균핵병", "녹병", "무름병",
    "시들음병", "역병", "점무늬병", "줄기마름병", "뿌리썩음병", "잎마름병",
    "검은별무늬병", "세균병", "바이러스병", "화상병", "총채벌레", "진딧물",
    "응애", "나방", "노린재", "먹노린재", "흰불나방", "혹파리", "가루이", "선충",
]


def build_vocabulary() -> dict:
    """
    추천검색어 후보를 엔티티 타입별로 만든다.
    단순 빈도 집계는 '시험·발생·등록·주의' 같은 일반명사가 상위를 점령해 쓸 수 없다.
    작물·병해충 어휘는 사이트가 이미 갖고 있는 병해충 사전에서 가져온다.
    """
    vocab = {"작물": set(EXTRA_CROPS), "병해충": set(DISEASE_TOKENS)}

    rows = load_json(DICT_PATH, {})
    rows = rows.get("rows", []) if isinstance(rows, dict) else rows
    for row in rows:
        title = re.sub(r"\([^)]*\)", "", row.get("title", "")).strip()
        if not title:
            continue
        head = title.split()[0]
        if 2 <= len(head) <= 5:
            vocab["작물"].add(head)
        for token in DISEASE_TOKENS:
            if token in title:
                vocab["병해충"].add(token)

    vocab = {k: sorted(v) for k, v in vocab.items()}
    vocab.update(FIXED_KEYWORDS)
    return vocab


def build_keywords(articles: list) -> list:
    """실제 기사에 일정 건수 이상 매칭되는 후보만 남긴다 (클릭 시 0건 방지)."""
    visible = [a for a in articles if not a.get("hidden")]
    min_hits = max(KW_MIN_HITS_FLOOR, len(visible) // 80)
    vocab = build_vocabulary()
    chips = []

    for kw_type, words in vocab.items():
        hits = []
        for word in words:
            count = sum(1 for a in visible if word in a["title"])
            if count >= min_hits:
                hits.append({"word": word, "count": count, "type": kw_type})
        hits.sort(key=lambda x: -x["count"])
        chips.extend(hits[: KW_PER_TYPE.get(kw_type, 3)])

    chips.sort(key=lambda x: -x["count"])
    return chips, vocab, min_hits


def build_meta(articles: list, chips: list, vocab: dict, min_hits: int) -> dict:
    """news.html '수집 기준' 패널이 읽는 파일. 어떤 검색어로 긁고 어떤 어휘로 뽑는지 그대로 노출한다."""
    visible = [a for a in articles if not a.get("hidden")]
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))

    # 어휘별 실제 매칭 건수 — 노출되지 않은 어휘도 몇 건 걸렸는지 보여준다
    vocabulary = {}
    for kw_type, words in vocab.items():
        entries = [{"word": w,
                    "count": sum(1 for a in visible if w in a["title"])}
                   for w in words]
        entries.sort(key=lambda x: (-x["count"], x["word"]))
        vocabulary[kw_type] = entries

    return {
        "updated": now.strftime("%Y-%m-%d %H:%M KST"),
        "stats": {
            "total": len(articles),
            "visible": len(visible),
            "hidden": len(articles) - len(visible),
            "sources": len({a["source"] for a in articles}),
            "oldest": min((a["date"] for a in articles), default=""),
            "newest": max((a["date"] for a in articles), default=""),
        },
        "settings": {
            "recent_days": RECENT_DAYS,
            "min_score": MIN_SCORE,
            "max_total": MAX_TOTAL,
            "keyword_min_hits": min_hits,
        },
        "feeds": [{"cat": cat, "queries": queries} for cat, queries in FEEDS],
        "chips": chips,
        "vocabulary": vocabulary,
        "scoring": [
            {"rule": "신뢰 매체", "delta": "+3", "detail": "농업 전문지·통신사 " + str(len(TRUSTED_SOURCES)) + "종"},
            {"rule": "핵심어", "delta": "+2/개", "detail": "등록·고시·기준·잔류·시험·약효·저항성 등"},
            {"rule": "지자체 홍보", "delta": "-3", "detail": "'○○시,' '○○군 ○○면' 농업기술센터 등"},
            {"rule": "행사·홍보 문구", "delta": "-2", "detail": "공동방제·당부·총력·성료·캠페인 등"},
        ],
    }


# ══════════════════════════════════════════════════════════════════════

def main():
    started = datetime.datetime.now()
    print("=" * 62)
    print(f"농업뉴스 크롤링 시작: {started.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 62)

    new_items = crawl_all()
    print(f"\n이번 수집: {len(new_items)}건 "
          f"(노출 {sum(1 for i in new_items if not i['hidden'])} / "
          f"보류 {sum(1 for i in new_items if i['hidden'])})")

    articles, added = accumulate(new_items)
    chips, vocab, min_hits = build_keywords(articles)
    meta = build_meta(articles, chips, vocab, min_hits)

    os.makedirs(os.path.dirname(NEWS_PATH), exist_ok=True)
    with open(NEWS_PATH, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=1)
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)

    size_kb = os.path.getsize(NEWS_PATH) // 1024
    print(f"\n저장: {os.path.relpath(NEWS_PATH, ROOT)} "
          f"(누적 {len(articles)}건 / {size_kb}KB)")
    print(f"저장: {os.path.relpath(META_PATH, ROOT)} "
          f"(추천검색어 {len(chips)}개 / 어휘 "
          f"{sum(len(v) for v in meta['vocabulary'].values())}개)")
    print(f"소요 {(datetime.datetime.now() - started).seconds}초")
    print("=" * 62)

    # 수집이 통째로 실패했으면 크론이 알아챌 수 있게 종료코드를 남긴다
    if not new_items:
        print("경고: 이번 수집 결과가 0건입니다. RSS 응답을 확인하세요.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
