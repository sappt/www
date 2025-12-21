import requests
import json
import datetime

# 남부 5개 도시 설정 (대구, 광주, 부산, 제주, 여수)
LOCATIONS = [
    {"name": "대구", "lat": 35.8714, "lon": 128.6014, "top": 42, "left": 62},
    {"name": "광주", "lat": 35.1595, "lon": 126.8526, "top": 58, "left": 22},
    {"name": "부산", "lat": 35.1796, "lon": 129.0756, "top": 72, "left": 78},
    {"name": "제주", "lat": 33.4996, "lon": 126.5312, "top": 115, "left": 72},
    {"name": "여수", "lat": 34.7604, "lon": 127.6622, "top": 92, "left": 28}
]

def get_weather_type(code):
    """WMO 코드를 아이콘 타입으로 변환"""
    if code == 0: return "sunny"
    if code <= 3: return "cloudy"
    if code >= 71 and code <= 77: return "snowy"
    return "rainy"

def fetch_weather_data():
    print(">>> 남부 5개 도시 날씨 데이터 수집 시작")
    final_data = []

    for loc in LOCATIONS:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={loc['lat']}&longitude={loc['lon']}&daily=weathercode,temperature_2m_max,temperature_2m_min&timezone=auto&forecast_days=7"

        try:
            res = requests.get(url).json()
            daily = res['daily']

            today_code = daily['weathercode'][0]
            today_max = round(daily['temperature_2m_max'][0])
            today_min = round(daily['temperature_2m_min'][0])

            weekly_forecast = []
            for i in range(7):
                d_date = daily['time'][i]
                dt_obj = datetime.datetime.strptime(d_date, "%Y-%m-%d")
                fmt_date = dt_obj.strftime("%m.%d")

                w_code = daily['weathercode'][i]
                w_max = round(daily['temperature_2m_max'][i])
                w_min = round(daily['temperature_2m_min'][i])

                weekly_forecast.append({
                    "date": fmt_date,
                    "type": get_weather_type(w_code),
                    "temp_max": w_max,
                    "temp_min": w_min
                })

            city_data = {
                "name": loc['name'],
                "top": loc['top'],
                "left": loc['left'],
                "today_max": today_max,
                "today_min": today_min,
                "current_type": get_weather_type(today_code),
                "weekly": weekly_forecast
            }
            final_data.append(city_data)
            print(f"{loc['name']} 완료")

        except Exception as e:
            print(f"{loc['name']} 에러: {e}")
            final_data.append({
                "name": loc['name'], "top": loc['top'], "left": loc['left'],
                "today_max": 0, "today_min": 0, "current_type": "cloudy", "weekly": []
            })

    return final_data

def generate_html(weather_data):
    utc_now = datetime.datetime.utcnow()
    kst_now = utc_now + datetime.timedelta(hours=9)
    server_time_str = kst_now.strftime("%Y-%m-%d %H:%M:%S")

    json_data = json.dumps(weather_data, ensure_ascii=False)

    html_template = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="3600">
    <title>KOREA WEATHER DASHBOARD</title>
    <style>
        body {{
            background-color: #eef2f5;
            margin: 0;
            overflow: hidden;
            font-family: 'Pretendard', 'Malgun Gothic', sans-serif;
            display: flex;
            flex-direction: column;
            height: 100vh;
            position: relative;
        }}

        header {{
            background: #ffffff;
            height: 80px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0 50px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.05);
            z-index: 100;
            flex-shrink: 0;
        }}

        .title {{ font-size: 2rem; font-weight: 900; color: #2c3e50; letter-spacing: -1px; }}
        .clock-container {{ text-align: right; color: #555; }}
        #currentDate {{ font-size: 1.2rem; font-weight: bold; color: #7f8c8d; }}
        #currentTime {{ font-size: 2.5rem; font-weight: 900; color: #2c3e50; line-height: 1; }}

        .main-content {{
            flex: 1;
            display: flex;
            padding: 20px;
            gap: 20px;
            overflow: hidden;
        }}

        .left-panel {{
            width: 40%;
            flex-shrink: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            background: #fff;
            border-radius: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
            position: relative;
            overflow: hidden;
        }}

        .map-wrapper {{ position: relative; width: 100%; max-height: 100%; aspect-ratio: 420 / 280; }}
        svg.map-svg {{ width: 100%; height: 100%; overflow: visible; filter: drop-shadow(10px 10px 20px rgba(0,0,0,0.15)); }}
        .land {{ fill: #f8f9fa; stroke: #cbd5e0; stroke-width: 2; transition: fill 0.3s; }}
        .inset-box {{ fill: rgba(255, 255, 255, 0.8); stroke: #cbd5e0; stroke-width: 2; stroke-dasharray: 5, 5; }}

        .right-panel {{
            flex: 1;
            background: #fff;
            border-radius: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            padding: 20px;
            overflow: hidden;
        }}

        .panel-header {{ font-size: 1.5rem; font-weight: 800; color: #2c3e50; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid #f1f2f6; }}
        .forecast-table-container {{
            display: flex;
            justify-content: center;
            align-items: center;
            overflow-y: auto;
            overflow-x: auto;
            width: 100%;
        }}
        table {{ width: auto; border-collapse: collapse; font-size: calc(0.8rem + 0.5vw); text-align: center; }}
        th {{ position: sticky; top: 0; background: #fff; padding: calc(0.8vw + 8px) calc(0.5vw + 4px); color: #7f8c8d; font-weight: 700; border-bottom: 2px solid #eef2f5; z-index: 10; font-size: calc(0.8rem + 0.5vw); }}
        td {{ padding: calc(0.8vw + 6px) calc(0.5vw + 4px); border-bottom: 1px solid #f1f2f6; vertical-align: middle; }}
        .region-name {{ font-weight: 800; color: #2c3e50; text-align: left; padding-left: calc(0.5vw + 8px); white-space: nowrap; font-size: calc(0.9rem + 0.6vw); }}

        .forecast-cell {{ display: flex; flex-direction: column; align-items: center; justify-content: center; gap: calc(0.3vw + 2px); }}
        .mini-icon svg {{ width: calc(1.5vw + 20px); height: calc(1.5vw + 20px); }}

        .mini-temp {{ font-size: calc(0.7rem + 0.4vw); color: #555; font-weight: 600; white-space: nowrap; }}
        .t-min {{ color: #3498db; }}
        .t-max {{ color: #e74c3c; }}

        .marker {{ position: absolute; transform: translate(-50%, -50%); display: flex; flex-direction: column; align-items: center; z-index: 10; }}
        .weather-svg {{ width: 45px; height: 45px; animation: float 3s ease-in-out infinite; filter: drop-shadow(0 3px 3px rgba(0,0,0,0.15)); }}

        .info-box {{
            background: rgba(255, 255, 255, 0.95);
            border: 2px solid #dde1e6;
            padding: 4px 12px;
            border-radius: 20px;
            margin-top: -2px;
            font-size: 1.0rem;
            font-weight: 800;
            color: #333;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            white-space: nowrap;
            display: flex;
            gap: 5px;
            align-items: center;
        }}

        .marker-temps {{ font-size: 0.95rem; }}

        .server-time {{
            position: absolute;
            bottom: 20px;
            left: 20px;
            color: #95a5a6;
            font-size: 0.8rem;
            font-weight: 600;
            background: rgba(255,255,255,0.8);
            padding: 5px 10px;
            border-radius: 15px;
            z-index: 999;
            pointer-events: none;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }}

        @keyframes float {{
            0%, 100% {{ transform: translateY(0); }}
            50% {{ transform: translateY(-6px); }}
        }}

        .weather-svg {{ width: calc(2vw + 30px); height: calc(2vw + 30px); }}
        .info-box {{ font-size: calc(0.7rem + 0.4vw); padding: calc(0.3vw + 4px) calc(0.5vw + 10px); }}
        .marker-temps {{ font-size: calc(0.6rem + 0.4vw); }}
        .server-time {{ font-size: calc(0.5rem + 0.3vw); padding: calc(0.3vw + 4px) calc(0.4vw + 8px); }}

        header {{ height: calc(4vw + 50px); padding: 0 calc(2vw + 30px); }}
        .title {{ font-size: calc(1rem + 0.8vw); }}
        #currentDate {{ font-size: calc(0.7rem + 0.4vw); }}
        #currentTime {{ font-size: calc(1.2rem + 0.9vw); }}

        .main-content {{ padding: calc(0.8vw + 12px); gap: calc(0.8vw + 12px); }}
        .right-panel {{ padding: calc(0.8vw + 12px); border-radius: calc(0.8vw + 12px); }}
        .left-panel {{ border-radius: calc(0.8vw + 12px); }}
    </style>
</head>
<body>

    <header>
        <div class="title">LIVE WEATHER MONITOR</div>
        <div class="clock-container">
            <div id="currentDate"></div>
            <div id="currentTime"></div>
        </div>
    </header>

    <div class="main-content">
        <div class="left-panel">
            <div class="map-wrapper" id="mapContainer">
                <svg class="map-svg" viewBox="30 100 360 240">
                    <path class="land" d="M 130,60 L 260,30 L 270,80 L 290,100 L 295,180 L 320,230 L 335,235 L 320,250 L 310,330 L 290,360 L 250,370 L 230,390 L 190,395 L 160,380 L 130,400 L 100,380 L 90,330 L 80,300 L 60,280 L 90,260 L 50,200 L 30,180 L 20,160 L 50,150 L 60,130 L 90,120 L 80,90 L 110,80 Z" />
                    <rect class="inset-box" x="230" y="320" width="120" height="90" rx="10" />
                    <path class="land" d="M 260,365 C 260,345 320,345 320,365 C 320,385 260,385 260,365 Z" />
                </svg>
            </div>
        </div>

        <div class="right-panel">
            <div class="forecast-table-container">
                <table id="forecastTable">
                    <thead><tr id="tableHeaderRow"><th>지역</th></tr></thead>
                    <tbody id="tableBody"></tbody>
                </table>
            </div>
        </div>
    </div>

    <div class="server-time">Last Update: {server_time_str}</div>

    <script>
        const weatherData = {json_data};

        function updateClock() {{
            const now = new Date();
            const days = ['일', '월', '화', '수', '목', '금', '토'];
            const dateStr = `${{now.getFullYear()}}. ${{String(now.getMonth()+1).padStart(2, '0')}}. ${{String(now.getDate()).padStart(2, '0')}} (${{days[now.getDay()]}})`;
            const timeStr = `${{String(now.getHours()).padStart(2, '0')}}:${{String(now.getMinutes()).padStart(2, '0')}}`;
            document.getElementById('currentDate').innerText = dateStr;
            document.getElementById('currentTime').innerText = timeStr;
        }}
        setInterval(updateClock, 1000);
        updateClock();

        const getIconSvg = (type) => {{
            const icons = {{
                sunny: `<svg viewBox="0 0 64 64"><circle cx="32" cy="32" r="14" fill="#ffb900" /><g stroke="#ffb900" stroke-width="5" stroke-linecap="round"><line x1="32" y1="4" x2="32" y2="9" /><line x1="32" y1="55" x2="32" y2="60" /><line x1="4" y1="32" x2="9" y2="32" /><line x1="55" y1="32" x2="60" y2="32" /><line x1="12" y1="12" x2="16" y2="16" /><line x1="48" y1="48" x2="52" y2="52" /><line x1="12" y1="52" x2="16" y2="48" /><line x1="48" y1="16" x2="52" y2="12" /></g></svg>`,
                cloudy: `<svg viewBox="0 0 64 64"><path fill="#bdc3c7" d="M16,40 Q4,40 4,28 Q4,18 14,16 Q18,4 30,6 Q36,0 46,6 Q58,6 58,22 Q62,26 62,34 Q62,44 50,44 Z" /><path fill="#ecf0f1" d="M16,36 Q8,36 8,28 Q8,22 14,20 Q18,10 30,12 Q36,8 44,12 Q54,12 54,24 Q58,28 58,34 Q58,40 50,40 Z" /></svg>`,
                rainy: `<svg viewBox="0 0 64 64"><path fill="#bdc3c7" d="M12,32 Q4,32 4,22 Q4,12 14,10 Q18,2 30,4 Q36,0 44,4 Q54,4 54,18 Q58,22 58,28 Q58,36 50,36 Z" /><g fill="#3498db"><path d="M20,42 L16,52 L24,52 Z" /><path d="M34,42 L30,52 L38,52 Z" /><path d="M48,42 L44,52 L52,52 Z" /></g></svg>`,
                snowy: `<svg viewBox="0 0 64 64"><path fill="#bdc3c7" d="M12,32 Q4,32 4,22 Q4,12 14,10 Q18,2 30,4 Q36,0 44,4 Q54,4 54,18 Q58,22 58,28 Q58,36 50,36 Z" /><g stroke="#3498db" stroke-width="3" stroke-linecap="round"><line x1="20" y1="44" x2="20" y2="52" /><line x1="16" y1="48" x2="24" y2="48" /><line x1="34" y1="44" x2="34" y2="52" /><line x1="30" y1="48" x2="38" y2="48" /><line x1="48" y1="44" x2="48" y2="52" /><line x1="44" y1="48" x2="52" y2="48" /></g></svg>`
            }};
            return icons[type] || icons.sunny;
        }};

        function drawMapMarkers() {{
            const container = document.getElementById('mapContainer');
            weatherData.forEach(city => {{
                const el = document.createElement('div');
                el.className = 'marker';
                el.style.top = city.top + '%';
                el.style.left = city.left + '%';
                const delay = (Math.random() * 2).toFixed(2);

                el.innerHTML = `
                    <div class="weather-svg" style="animation-delay: -${{delay}}s">
                        ${{getIconSvg(city.current_type)}}
                    </div>
                    <div class="info-box">
                        <span>${{city.name}}</span>
                        <span class="marker-temps">
                            <span class="t-min">${{city.today_min}}°</span>/<span class="t-max">${{city.today_max}}°</span>
                        </span>
                    </div>
                `;
                container.appendChild(el);
            }});
        }}

        function drawForecastTable() {{
            const tableHeaderRow = document.getElementById('tableHeaderRow');
            const tableBody = document.getElementById('tableBody');

            if(weatherData.length > 0) {{
                weatherData[0].weekly.forEach(day => {{
                    const th = document.createElement('th');
                    th.innerText = day.date;
                    tableHeaderRow.appendChild(th);
                }});
            }}

            weatherData.forEach(city => {{
                const tr = document.createElement('tr');
                const tdName = document.createElement('td');
                tdName.className = 'region-name';
                tdName.innerText = city.name;
                tr.appendChild(tdName);

                city.weekly.forEach(day => {{
                    const td = document.createElement('td');
                    td.innerHTML = `
                        <div class="forecast-cell">
                            <div class="mini-icon">${{getIconSvg(day.type)}}</div>
                            <div class="mini-temp">
                                <span class="t-min">${{day.temp_min}}°</span>/<span class="t-max">${{day.temp_max}}°</span>
                            </div>
                        </div>
                    `;
                    tr.appendChild(td);
                }});
                tableBody.appendChild(tr);
            }});
        }}

        drawMapMarkers();
        drawForecastTable();
    </script>
</body>
</html>
    """

    with open("w2.html", "w", encoding="utf-8") as f:
        f.write(html_template)
    print(f">>> w2.html 생성 완료 (Update Time: {server_time_str})")

if __name__ == "__main__":
    data = fetch_weather_data()
    generate_html(data)
