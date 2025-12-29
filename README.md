# SAPPT Research 웹사이트

샤프트리서치(SAPPT Research) 공식 웹사이트 - 지속가능한 농업과 식물보호기술 연구소

**Live Site:** [www.sappt.co.kr](https://www.sappt.co.kr)

---

## 프로젝트 개요

GitHub Pages를 통해 호스팅되는 정적 웹사이트 + 동적 대시보드 플랫폼입니다.
실시간 날씨 데이터와 일정 정보를 자동으로 업데이트합니다.

---

## 프로젝트 구조

```
www/
├── .github/workflows/      # GitHub Actions 워크플로우
│   ├── daily_weather.yml   # 메인 날씨 업데이트 (9개 도시)
│   ├── w1_weather.yml      # 중부 5개 도시 날씨
│   ├── w2_weather.yml      # 남부 5개 도시 날씨
│   ├── w3_weather.yml      # 전국 10개 도시 날씨
│   └── schedule_update.yml # 주간 일정 업데이트
│
├── assets/                 # 정적 자원
│   ├── css/               # 스타일시트
│   ├── js/                # JavaScript 라이브러리
│   ├── json/              # 데이터 파일 (병해충 사전 등)
│   └── img/               # 이미지
│
├── build_weather.py        # 메인 날씨 HTML 생성 (9개 도시)
├── build_w1.py             # 중부 5개 도시 날씨 생성
├── build_w2.py             # 남부 5개 도시 날씨 생성
├── build_w3.py             # 전국 10개 도시 날씨 생성
├── build_schedule.py       # Google Sheets → 주간 일정 생성
│
├── index.html              # 메인 페이지 (회사 소개)
├── daily_weather.html      # 날씨 대시보드 (자동 생성)
├── w1.html                 # 중부권 날씨 (자동 생성)
├── w2.html                 # 남부권 날씨 (자동 생성)
├── w3.html                 # 전국 날씨 + 전광판 스크롤 (자동 생성)
├── s1.html                 # 주간 일정표 (자동 생성)
├── kiosk.html              # 키오스크 모드 (페이지 자동 순환)
├── image01.html            # 이미지 갤러리 (Picsum API)
├── cal.html                # 캘린더/폼 페이지
└── requirements.txt        # Python 의존성
```

---

## 페이지 설명

### 정적 페이지
| 파일 | 설명 |
|------|------|
| `index.html` | 회사 메인 페이지 |
| `404.html` | 404 에러 페이지 |
| `cal.html` | 출장/연차 작성 폼 |

### 날씨 대시보드 (자동 생성)
| 파일 | 도시 | 특징 |
|------|------|------|
| `daily_weather.html` | 9개 도시 | SVG 한국 지도 + 예보 |
| `w1.html` | 중부 5개 (서울, 춘천, 강릉, 대전, 전주) | 최저/최고 온도 |
| `w2.html` | 남부 5개 (대구, 광주, 부산, 제주, 여수) | 최저/최고 온도 |
| `w3.html` | 전국 10개 | 전광판 스크롤 효과 (30초) |

### 특수 페이지
| 파일 | 설명 |
|------|------|
| `kiosk.html` | 키오스크 디스플레이 (20초 간격 자동 순환) |
| `image01.html` | Picsum API 랜덤 이미지 갤러리 |
| `s1.html` | Google Sheets 연동 주간 일정표 |

---

## 자동화 (GitHub Actions)

### 날씨 업데이트
- **실행 주기:** 매시간 정각
- **데이터 소스:** [Open-Meteo API](https://open-meteo.com/) (무료, API 키 불필요)
- **커밋 사용자:** WeatherBot

| 워크플로우 | 생성 파일 | 대상 도시 |
|------------|-----------|-----------|
| `daily_weather.yml` | `daily_weather.html` | 9개 도시 |
| `w1_weather.yml` | `w1.html` | 중부 5개 |
| `w2_weather.yml` | `w2.html` | 남부 5개 |
| `w3_weather.yml` | `w3.html` | 전국 10개 |

### 일정 업데이트
- **워크플로우:** `schedule_update.yml`
- **생성 파일:** `s1.html`
- **데이터 소스:** Google Sheets (공개 시트)
- **실행 주기:** 매시간

---

## 로컬 개발

### 요구사항
- Python 3.9+
- requests 라이브러리

### 설치 및 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# 날씨 HTML 생성
python build_weather.py    # daily_weather.html
python build_w1.py         # w1.html
python build_w2.py         # w2.html
python build_w3.py         # w3.html

# 일정 HTML 생성
python build_schedule.py   # s1.html
```

---

## 기술 스택

### Frontend
- HTML5 / CSS3
- Vanilla JavaScript
- SVG (한국 지도)
- 반응형 디자인 (브레이크포인트: 1000px, 700px, 600px)

### 외부 라이브러리
- Toast UI Chart (차트)
- Toast UI Calendar (캘린더)
- jqGrid 5.5.1 (데이터 테이블)
- 다음/카카오 지도 API

### Backend / 자동화
- Python 3.9
- GitHub Actions
- Open-Meteo API (날씨)
- Google Sheets API (일정)

---

## 주요 기능

### w3.html 날씨 대시보드
- 전국 10개 도시 실시간 날씨
- 7일간 주간 예보
- 최저/최고 온도 표시 (파란색/빨간색)
- 전광판 스크롤 효과 (30초 순환)
- 홀수/짝수 행 stripe 효과
- 마우스 호버 시 스크롤 일시정지
- 제주도 별도 인셋 박스

### kiosk.html 키오스크 모드
- iframe 기반 페이지 자동 순환
- 20초 간격 전환
- 순환 페이지: w3.html → s1.html → image01.html
- 캐시 무시 (타임스탬프 쿼리)

---

## SEO & 분석

- Google Analytics (UA-135186223-1)
- Open Graph 메타 태그
- Twitter Card
- sitemap.xml
- robots.txt

---

## 라이선스

Copyright (c) 샤프트리서치 (SAPPT Research)
