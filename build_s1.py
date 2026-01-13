import requests
import csv
import datetime
from io import StringIO

# ============================================================
# 설정: Google Sheet ID (공개 시트로 설정 필요)
# ============================================================
SHEET_ID = "1dArVEO9Dkizz5FMxbbiRDv0K_n9ZfJu0JXlKI8Z89pI"

# 탭별 CSV URL
EMP_DATA_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=emp_data"
SCHEDULE_DATA_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=schedule_data"

def get_current_week_dates():
    """현재 주의 일~토 날짜 반환 (KST 기준)"""
    # UTC 시간을 KST로 변환 (GitHub Actions에서 실행될 때 시간대 문제 해결)
    utc_now = datetime.datetime.utcnow()
    kst_now = utc_now + datetime.timedelta(hours=9)
    today = kst_now.date()

    # 일요일 찾기 (weekday: 월=0, 일=6)
    # (weekday() + 1) % 7 을 계산하면 일=0, 월=1, ..., 토=6
    days_since_sunday = (today.weekday() + 1) % 7
    sunday = today - datetime.timedelta(days=days_since_sunday)

    week_dates = []
    for i in range(7):  # 일~토
        d = sunday + datetime.timedelta(days=i)
        week_dates.append(d)

    return week_dates

def fetch_csv_data(url):
    """Google Sheet에서 CSV 데이터 가져오기"""
    try:
        response = requests.get(url)
        response.encoding = 'utf-8'
        reader = csv.reader(StringIO(response.text))
        rows = list(reader)
        return rows
    except Exception as e:
        print(f"데이터 가져오기 실패: {e}")
        return []

def parse_employees(rows):
    """직원 데이터 파싱"""
    employees = []
    if len(rows) < 2:
        return employees

    # 첫 행은 헤더, 두 번째 행부터 데이터
    for row in rows[1:]:
        if len(row) >= 2:
            employees.append({
                "email": row[0].strip(),
                "name": row[1].strip(),
                "note": row[2].strip() if len(row) > 2 else ""
            })
    return employees

def parse_schedules(rows):
    """일정 데이터 파싱"""
    schedules = []
    if len(rows) < 2:
        return schedules

    # 첫 행은 헤더, 두 번째 행부터 데이터
    for row in rows[1:]:
        if len(row) >= 6:
            try:
                schedules.append({
                    "id": row[0].strip(),
                    "name": row[1].strip(),
                    "email": row[2].strip(),
                    "type": row[3].strip(),  # 연차, 출장, 외근 등
                    "start_date": row[4].strip(),
                    "end_date": row[5].strip(),
                    "reason": row[6].strip() if len(row) > 6 else "",
                    "location": row[7].strip() if len(row) > 7 else "",
                    "status": row[8].strip() if len(row) > 8 else ""
                })
            except:
                continue
    return schedules

def get_schedules_for_date(schedules, name, target_date):
    """특정 직원의 특정 날짜 모든 일정 찾기 (오전/오후 구분)"""
    target_str = target_date.strftime("%Y-%m-%d")
    morning = None
    afternoon = None

    for s in schedules:
        if s["name"] == name and s["start_date"] <= target_str <= s["end_date"]:
            schedule_type = s["type"]

            if "오전" in schedule_type:
                morning = s
            elif "오후" in schedule_type:
                afternoon = s
            else:
                # 오전/오후 구분 없는 일정 (연차, 출장 등)
                morning = s

    return morning, afternoon

def get_status_class(schedule_type):
    """일정 유형에 따른 CSS 클래스 반환"""
    if not schedule_type:
        return "office", "내근"

    t = schedule_type.lower()
    if "연차" in schedule_type or "반차" in schedule_type or "휴가" in schedule_type:
        return "vacation", "" + schedule_type
    elif "출장" in schedule_type:
        return "trip", "출장"
    elif "외근" in schedule_type or "미팅" in schedule_type:
        return "outside", "" + schedule_type
    elif "내근" in schedule_type:
        return "interior", "" + schedule_type
    else:
        return "office", "내근"

def generate_cell_html(morning_schedule, afternoon_schedule=None, day_idx=None):
    """테이블 셀 HTML 생성 (오전/오후 구분)"""
    # 둘 다 없는 경우
    if morning_schedule is None and afternoon_schedule is None:
        if day_idx in (5, 6):
            return ''
        return '<span class="office">내근</span>'

    # 오전과 오후 모두 있는 경우
    if morning_schedule is not None and afternoon_schedule is not None:
        css_class_m, label_m = get_status_class(morning_schedule["type"])
        css_class_a, label_a = get_status_class(afternoon_schedule["type"])
        reason_m = morning_schedule.get("reason", "")
        reason_a = afternoon_schedule.get("reason", "")

        html = f'''<span class="section morning">
                            <span class="status {css_class_m}">{label_m}</span>'''
        if reason_m:
            html += f'\n                            <span class="desc">{reason_m}</span>'
        html += f'''
                        </span>
                        <span class="section afternoon">
                            <span class="status {css_class_a}">{label_a}</span>'''
        if reason_a:
            html += f'\n                            <span class="desc">{reason_a}</span>'
        html += '''
                        </span>'''
        return html

    # 오전만 있는 경우
    if morning_schedule is not None:
        css_class, label = get_status_class(morning_schedule["type"])
        reason = morning_schedule.get("reason", "")

        # 오전/오후 구분 여부 확인
        if "오전" in morning_schedule["type"]:
            # "오전내근", "오전외근", "오전반차" 등 - 상단에 표시
            html = f'''<div class="morning-content">
                            <span class="status {css_class}">{label}</span>'''
            if reason:
                html += f'\n                            <span class="desc">{reason}</span>'
            html += '\n                        </div>'
            return html
        elif css_class == "office":
            # 일반 "내근" (오전/오후 구분 없음) - 전체 표시
            return '<span class="office">내근</span>'
        else:
            # 오전/오후 구분 없는 일정 (연차, 출장 등) - 전체 표시
            html = f'<span class="status {css_class}">{label}</span>'
            if reason:
                html += f'\n                        <span class="desc">{reason}</span>'
            return html

    # 오후만 있는 경우
    if afternoon_schedule is not None:
        css_class, label = get_status_class(afternoon_schedule["type"])
        reason = afternoon_schedule.get("reason", "")

        html = f'''<div class="afternoon-content">
                            <span class="status {css_class}">{label}</span>'''
        if reason:
            html += f'\n                            <span class="desc">{reason}</span>'
        html += '\n                        </div>'
        return html

    return ''

def generate_html(employees, schedules, week_dates):
    """HTML 파일 생성"""
    # 한국 시간 계산
    utc_now = datetime.datetime.utcnow()
    kst_now = utc_now + datetime.timedelta(hours=9)
    update_time = kst_now.strftime("%Y-%m-%d %H:%M:%S")

    # 주간 날짜 범위 문자열
    start_date = week_dates[0]
    end_date = week_dates[6]
    days_kr = ["월", "화", "수", "목", "금", "토", "일"]
    date_range = f"{start_date.strftime('%Y.%m.%d')} ({days_kr[start_date.weekday()]}) ~ {end_date.strftime('%m.%d')} ({days_kr[end_date.weekday()]})"

    # 테이블 헤더 생성 (일~토 전체 표시)
    header_cells = ""
    day_names = ["월 (Mon)", "화 (Tue)", "수 (Wed)", "목 (Thu)", "금 (Fri)", "토 (Sat)", "일 (Sun)"]
    for d in week_dates:  # 일~토 (week_dates는 이미 [일, 월, 화, 수, 목, 금, 토] 순서)
        day_idx = d.weekday()  # 월=0, 일=6
        day_name = day_names[day_idx]
        day_class = "sunday" if day_idx == 6 else "saturday" if day_idx == 5 else ""
        if day_class:
            header_cells += f'<th style="width: 14.28%" class="{day_class}">{day_name}<br><small>{d.strftime("%m/%d")}</small></th>\n                    '
        else:
            header_cells += f'<th style="width: 14.28%">{day_name}<br><small>{d.strftime("%m/%d")}</small></th>\n                    '

    # 테이블 본문 생성 (일~토 전체 표시)
    body_rows = ""
    for emp in employees:
        cells = ""
        for d in week_dates:  # 일~토
            morning_schedule, afternoon_schedule = get_schedules_for_date(schedules, emp["name"], d)
            day_idx = d.weekday()
            cell_html = generate_cell_html(morning_schedule, afternoon_schedule, day_idx)

            # 셀 클래스 결정
            day_class = "sunday" if day_idx == 6 else "saturday" if day_idx == 5 else ""

            # 오전만 있는 경우 morning-half 클래스 추가
            if morning_schedule is not None and afternoon_schedule is None and "오전" in morning_schedule["type"]:
                cell_class = f"{day_class} morning-half".strip()
            # 오후만 있는 경우 afternoon-half 클래스 추가
            elif afternoon_schedule is not None and morning_schedule is None:
                cell_class = f"{day_class} afternoon-half".strip()
            # 오전/오후 모두 있거나 오전/오후 구분 없는 경우 full-status
            elif morning_schedule is not None and afternoon_schedule is None and "오전" not in morning_schedule["type"]:
                cell_class = f"{day_class} full-status".strip()
            else:
                cell_class = day_class

            if cell_class:
                cells += f'<td class="{cell_class}">{cell_html}</td>\n                    '
            else:
                cells += f"<td>{cell_html}</td>\n                    "

        body_rows += f'''<tr>
                    <td>{emp["name"]}</td>
                    {cells}</tr>
                '''

    html_content = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="3600">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>주간 업무 현황 - 샤프트리서치</title>

    <!-- SEO 메타 태그 -->
    <meta name="description" content="샤프트리서치 주간 업무 및 출장 현황표입니다. 연구원들의 출장, 외근, 사내근무 일정을 확인할 수 있습니다.">
    <meta name="keywords" content="샤프트리서치, SAPPT, 업무현황, 출장현황, 연구소일정">
    <meta name="author" content="샤프트리서치">
    <meta name="robots" content="index, follow">
    <link rel="canonical" href="https://www.sappt.co.kr/s1.html">

    <!-- Open Graph -->
    <meta property="og:type" content="website">
    <meta property="og:title" content="주간 업무 현황 - 샤프트리서치">
    <meta property="og:description" content="샤프트리서치 주간 업무 및 출장 현황표">
    <meta property="og:url" content="https://www.sappt.co.kr/s1.html">
    <meta property="og:locale" content="ko_KR">
    <meta property="og:site_name" content="샤프트리서치">
    <style>
        /* 기본 스타일 설정 - 다크모드 */
        *, *::before, *::after {{
            box-sizing: border-box;
        }}

        html {{
            width: 100%;
            height: 100%;
        }}

        body {{
            width: 100%;
            height: 100%;
            min-height: 100vh;
            margin: 0;
            padding: 0;
            font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif;
            background-color: #1a1a1a;
            color: #e0e0e0;
            font-size: clamp(14px, 1.5vmin, 28px);
        }}

        .container {{
            width: 100%;
            height: 100vh;
            background-color: #2d2d2d;
            padding: clamp(10px, 1vmin, 30px);
            overflow: auto;
            display: flex;
            flex-direction: column;
        }}

        /* 헤더 스타일 */
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: clamp(5px, 0.8vmin, 15px);
            border-bottom: 2px solid #64b5f6;
            padding-bottom: clamp(5px, 0.8vmin, 15px);
            flex-shrink: 0;
        }}

        .header-top {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            width: 100%;
        }}

        h1 {{
            margin: 0;
            font-size: clamp(18px, 2.2vmin, 36px);
            color: #64b5f6;
        }}

        .date-range {{
            font-size: clamp(12px, 1.8vmin, 26px);
            font-weight: bold;
            color: #b0b0b0;
        }}

        /* 테이블 스타일 */
        .table-wrapper {{
            flex: 1;
            overflow: auto;
            display: flex;
            flex-direction: column;
        }}

        table {{
            width: 100%;
            height: 100%;
            border-collapse: collapse;
            flex: 1;
            display: flex;
            flex-direction: column;
        }}

        thead {{
            flex-shrink: 0;
        }}

        tbody {{
            display: flex;
            flex-direction: column;
            flex: 1;
            height: 100%;
        }}

        tbody tr {{
            flex: 1;
            display: flex;
            border-bottom: 1px solid #555555;
        }}

        tbody tr:last-child {{
            border-bottom: 1px solid #555555;
        }}

        th, td {{
            border-right: 1px solid #555555;
            padding: clamp(8px, 1vmin, 16px);
            text-align: center;
            font-size: clamp(12px, 1.5vmin, 26px);
            display: flex;
            align-items: center;
            justify-content: center;
            flex-wrap: wrap;
        }}

        th:last-child, td:last-child {{
            border-right: none;
        }}

        thead tr {{
            display: flex;
            flex-shrink: 0;
        }}

        thead th {{
            border-bottom: 1px solid #555555;
        }}

        th {{
            background-color: #3a3a3a;
            color: #c0c0c0;
            font-weight: bold;
            white-space: nowrap;
        }}

        th small {{
            font-weight: normal;
            color: #a0a0a0;
        }}

        td:first-child {{
            font-weight: bold;
            background-color: #3a3a3a;
            flex-basis: 10%;
            width: 10%;
        }}

        tbody td:nth-child(n+2) {{
            flex-basis: 14.28%;
            width: 14.28%;
        }}

        /* td를 상하 분할 레이아웃으로 설정 */
        tbody td {{
            flex-direction: column;
            position: relative;
            padding: 0;
        }}

        /* 일반 td (내근 등) - .section이 없는 경우만 */
        tbody td:not(.morning-half):not(.afternoon-half):not(.full-status):not(:has(.section)) {{
            padding: clamp(8px, 1vmin, 16px);
        }}

        /* 오전/오후 둘 다 있는 td (.section을 가진 경우) */
        tbody td:has(.section) {{
            padding: 0;
        }}

        /* 오전 상태 (상단에만 표시, 하단 공백) */
        tbody td.morning-half {{
            padding: 0 !important;
        }}

        .morning-content {{
            flex: 0 0 50%;
            width: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: clamp(4px, 0.8vmin, 10px);
        }}

        tbody td.morning-half::after {{
            content: '';
            flex: 0 0 50%;
        }}

        /* 오후 상태 (상단 공백, 하단에만 표시) */
        tbody td.afternoon-half {{
            padding: 0 !important;
        }}

        tbody td.afternoon-half::before {{
            content: '';
            flex: 0 0 50%;
        }}

        .afternoon-content {{
            flex: 0 0 50%;
            width: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: clamp(4px, 0.8vmin, 10px);
        }}

        /* 전체 상태 (100% 표시) - 기존대로 */
        tbody td.full-status {{
            padding: clamp(8px, 1vmin, 16px);
        }}

        tbody td.full-status .status {{
            margin-bottom: 4px;
        }}

        /* 오전/오후 섹션 (같은 셀에 오전과 오후가 모두 있을 때) */
        .section {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            flex: 1;
            min-height: 0;
            padding: clamp(4px, 0.8vmin, 10px);
            min-width: 0;
        }}

        /* 오전 섹션 */
        .section.morning {{
            border-bottom: 1px solid #555555;
        }}

        /* 오후 섹션이 있으면 위에 가로 구분선 추가 */
        .section.afternoon {{
            border-top: 2px solid #555555;
        }}

        /* 상태별 라벨 스타일 - 다크모드 */
        .status {{
            display: block;
            width: 100%;
            padding: clamp(4px, 0.6vmin, 10px) clamp(6px, 1vmin, 16px);
            border-radius: 4px;
            font-size: clamp(11px, 1.2vmin, 22px);
            font-weight: bold;
            margin-bottom: 3px;
        }}

        .trip {{ background-color: #5a2c2c; color: #ff8080; }}
        .outside {{ background-color: #2c4a52; color: #64b5f6; }}
        .interior {{ background-color: #3a5a3a; color: #80d080; }}
        .vacation {{ background-color: #4a3a5a; color: #b39ddb; }}
        .office {{ color: #a0a0a0; font-size: clamp(12px, 1.2vmin, 22px); }}

        .desc {{
            display: block;
            font-size: clamp(10px, 1vmin, 18px);
            color: #b0b0b0;
            margin-top: 2px;
        }}

        .position {{
            font-size: clamp(10px, 1vmin, 18px);
            color: #a0a0a0;
        }}

        /* 요일별 색상 - 다크모드 */
        .sunday {{ color: #ff6b6b; }}
        .saturday {{ color: #74c0fc; }}

        /* 범례 */
        .legend {{
            width: 100%;
            text-align: center;
            font-size: clamp(11px, 1.2vmin, 20px);
        }}
        .legend span {{ margin-left: clamp(8px, 1vmin, 16px); }}

        /* 업데이트 시간 */
        .update-time {{
            text-align: right;
            font-size: clamp(9px, 0.9vmin, 14px);
            color: #888888;
            padding-top: 10px;
        }}

        @media print {{
            body {{ background-color: #fff; padding: 0; color: #333; }}
            .container {{ box-shadow: none; max-width: 100%; background-color: #fff; }}
            .status {{ border: 1px solid #ccc; }}
        }}
    </style>
</head>
<body>

<div class="container">
    <header>
        <div class="header-top">
            <h1>주간 업무 및 출장 현황</h1>
            <div class="date-range">{date_range}</div>
        </div>
        <div class="legend">
            <span style="color:#64b5f6">■ 외근/오전외근/오후외근</span>
            <span style="color:#80d080">■ 오전내근/오후내근</span>
            <span style="color:#b39ddb">■ 휴가/연차/반차</span>
        </div>
    </header>

    <div class="table-wrapper">
        <table>
            <thead>
                <tr>
                    <th style="width: 10%">성명</th>
                    {header_cells}
                </tr>
            </thead>
            <tbody>
                {body_rows}
            </tbody>
        </table>
    </div>

    <div class="update-time">Last Update: {update_time} (KST)</div>
</div>

</body>
</html>
'''

    with open("s1.html", "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f">>> s1.html 생성 완료 (Update Time: {update_time})")

def main():
    print(">>> 주간 일정 데이터 수집 시작")

    # 1. 주간 날짜 계산
    week_dates = get_current_week_dates()
    print(f"대상 주간: {week_dates[0]} ~ {week_dates[4]}")

    # 2. Google Sheet에서 데이터 가져오기
    print(">>> 직원 데이터 가져오는 중...")
    emp_rows = fetch_csv_data(EMP_DATA_URL)
    employees = parse_employees(emp_rows)
    print(f"직원 수: {len(employees)}")

    print(">>> 일정 데이터 가져오는 중...")
    schedule_rows = fetch_csv_data(SCHEDULE_DATA_URL)
    schedules = parse_schedules(schedule_rows)
    print(f"일정 수: {len(schedules)}")

    # 3. HTML 생성
    generate_html(employees, schedules, week_dates)

if __name__ == "__main__":
    main()
