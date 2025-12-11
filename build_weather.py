import requests
import datetime
import os

# 1. 설정: 전국의 주요 10개 지역 (위도/경도)
LOCATIONS = [
    {"name": "서울", "lat": 37.5665, "lon": 126.9780},
    {"name": "부산", "lat": 35.1796, "lon": 129.0756},
    {"name": "인천", "lat": 37.4563, "lon": 126.7052},
    {"name": "대구", "lat": 35.8714, "lon": 128.6014},
    {"name": "대전", "lat": 36.3504, "lon": 127.3845},
    {"name": "광주", "lat": 35.1595, "lon": 126.8526},
    {"name": "울산", "lat": 35.5384, "lon": 129.3114},
    {"name": "세종", "lat": 36.4800, "lon": 127.2890},
    {"name": "강릉", "lat": 37.7519, "lon": 128.8760},
    {"name": "제주", "lat": 33.4996, "lon": 126.5312},
]

def get_weather_icon(code):
    """WMO 날씨 코드를 이모지로 변환"""
    if code == 0: return "☀️"
    if code <= 3: return "⛅"
    if code <= 48: return "🌫️"
    if code <= 67: return "🌧️"
    if code <= 77: return "☃️"
    return "☔"

def create_html():
    cards_html = ""
    
    print(">>> 날씨 데이터 수집 시작")
    
    for loc in LOCATIONS:
        # Open-Meteo 무료 API 호출 (API Key 불필요)
        url = f"https://api.open-meteo.com/v1/forecast?latitude={loc['lat']}&longitude={loc['lon']}&daily=weathercode,temperature_2m_max,temperature_2m_min&timezone=auto"
        
        try:
            res = requests.get(url).json()
            daily = res['daily']
            
            # 오늘 날씨 데이터 추출
            icon = get_weather_icon(daily['weathercode'][0])
            max_temp = round(daily['temperature_2m_max'][0])
            min_temp = round(daily['temperature_2m_min'][0])
            
            # 카드 HTML 생성
            cards_html += f"""
            <div class="card">
                <div class="loc-name">{loc['name']}</div>
                <div class="icon">{icon}</div>
                <div class="temps">
                    <span class="max">{max_temp}°</span> / <span class="min">{min_temp}°</span>
                </div>
            </div>
            """
            print(f"{loc['name']} 완료")
            
        except Exception as e:
            print(f"{loc['name']} 에러: {e}")

    # 현재 시간 (업데이트 표시용)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    # 전체 HTML 조립 (TV용 CSS 포함)
    full_html = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="refresh" content="3600"> 
        <title>전국 날씨 대시보드</title>
        <style>
            body {{
                background-color: #121212; 
                color: white; 
                font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;
                margin: 0; padding: 40px;
                height: 100vh; box-sizing: border-box;
                display: flex; flex-direction: column;
            }}
            header {{ 
                text-align: center; margin-bottom: 30px; 
                font-size: 2.5rem; font-weight: bold; color: #ffd700; 
            }}
            .grid {{
                display: grid; 
                grid-template-columns: repeat(5, 1fr); /* 가로 5개씩 2줄 */
                gap: 20px; 
                flex-grow: 1;
            }}
            .card {{
                background: #1e1e1e; 
                border-radius: 20px; 
                display: flex; flex-direction: column; 
                justify-content: center; align-items: center;
                box-shadow: 0 4px 10px rgba(0,0,0,0.5);
            }}
            .loc-name {{ font-size: 1.8rem; margin-bottom: 10px; color: #aaaaaa; }}
            .icon {{ font-size: 5rem; margin: 10px 0; }}
            .temps {{ font-size: 2rem; font-weight: bold; }}
            .max {{ color: #ff6b6b; }} .min {{ color: #4facfe; }}
            footer {{ 
                text-align: right; color: #555; margin-top: 20px; font-size: 1rem; 
            }}
        </style>
    </head>
    <body>
        <header>KR Weather Dashboard</header>
        <div class="grid">
            {cards_html}
        </div>
        <footer>Last Update: {now_str}</footer>
    </body>
    </html>
    """

    # 파일 저장
    with open("daily_weather.html", "w", encoding="utf-8") as f:
        f.write(full_html)
    print(">>> daily_weather.html 생성 완료")

if __name__ == "__main__":
    create_html()
