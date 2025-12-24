# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

SAPPT Research 웹사이트 - 한국 농업식물보호 연구기관을 위한 정적 웹사이트 + 동적 대시보드 플랫폼. 
GitHub Pages를 통해 www.sappt.co.kr 에서 호스팅됨.

## 빌드 명령어

```bash
# Python 의존성 설치
pip install -r requirements.txt

# 날씨 대시보드 생성 (daily_weather.html 출력)
python build_weather.py
```

## 자동화

GitHub Actions 워크플로우 (`.github/workflows/daily_weather.yml`)가 매시간 날씨 데이터를 업데이트:
- Open-Meteo API에서 한국 9개 도시의 실시간 날씨 데이터 가져옴
- SVG 한국 지도와 예보가 포함된 `daily_weather.html` 생성
- "WeatherBot"으로 자동 커밋

## 아키텍처

### 페이지 유형
- **기업 페이지** (`index.html`, `s1.html`) - 정적 회사 정보
- **날씨 대시보드** (`daily_weather.html`, `w1.html-w3.html`) - 생성된 날씨 시각화
- **키오스크 디스플레이** (`kiosk.html`) - 자동 회전 iframe 캐러셀 (20초 간격)
- **이미지 갤러리** (`image01.html`) - Picsum API를 통한 랜덤 이미지 회전

### 주요 파일
- `build_weather.py` - Open-Meteo API 데이터를 가져와 날씨 HTML을 생성하는 Python 스크립트
- `assets/json/sapptSicknessDic.json` - 식물 병해충 백과사전 데이터 (100개 이상 항목)
- `assets/css/styles.css` - 반응형 브레이크포인트가 포함된 메인 스타일시트 (1000px, 700px, 600px)

### 외부 의존성
- `assets/js/`에 Toast UI Chart (6.3MB) 및 Calendar (1.5MB) 라이브러리
- 데이터 테이블용 jqGrid 5.5.1
- 위치 표시용 다음/카카오 지도 API
- 날씨 데이터용 Open-Meteo API (API 키 불필요)

### 데이터 흐름
1. `build_weather.py`가 서울, 춘천, 강릉, 대전, 대구, 전주, 광주, 부산, 제주의 날씨 API 데이터 가져옴
2. 내장된 JSON과 SVG 지도가 포함된 완전한 HTML 생성
3. GitHub Actions가 매시간 업데이트된 `daily_weather.html` 커밋
4. GitHub Pages를 통해 정적 파일 제공

## 개발 참고사항

- 페이지들은 CSS/JS가 내장된 자체 완결형 구조
- UTF-8 인코딩 및 한국어 폰트(맑은 고딕, Pretendard)로 한국어 지원
- 전반적으로 모바일 반응형 디자인
- Google Analytics 추적 활성화 (UA-135186223-1)
