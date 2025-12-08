import re
import os
import io
import zipfile
import pandas as pd


# ==============================
# 1) 생기부 섹션 자동 분리 엔진
# ==============================
def parse_student_record(text):

    patterns = {
        "자율활동": r"자율활동([\s\S]*?)동아리활동",
        "창체동아리": r"동아리활동([\s\S]*?)진로활동",
        "진로활동": r"진로활동([\s\S]*?)창의적 체험활동상황",
        "교과학습발달상황": r"교과학습발달상황([\s\S]*?)세부능력 및 특기사항",
        "교과별 세부능력 특기사항": r"세부능력 및 특기사항([\s\S]*?)독서활동",
        "독서활동": r"독서활동([\s\S]*?)행동특성 및 종합의견",
        "행동특성및종합의견": r"행동특성 및 종합의견([\s\S]*)"
    }

    result = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        result[key] = match.group(1).strip() if match else "(해당 항목 없음)"

    return result


# ==============================
# 2) 독서활동 자동 추출 엔진
# ==============================
def extract_books(text):
    """
    생기부 독서활동 영역에서 도서명, 저자, 학생 기록을 추출
    예: (1학기) 1984(조지오웰) ... 내용
    """

    pattern = r"\)\s*(.+?)\((.+?)\)\s*(.+?)(?=\n|$)"

    books = []
    for match in re.findall(pattern, text):
        title = match[0].strip()
        author = match[1].strip()
        content = match[2].strip()

        books.append({
            "title": title,
            "author": author,
            "student_note": content
        })

    return books


# ==============================
# 3) HTML 리포트 생성 (PDF 대체)
# ==============================
def generate_html_report(user, analysis, books):

    # --------------------------
    # 독서활동 표 생성
    # --------------------------
    df = pd.DataFrame([
        {
            "도서명": b["title"],
            "저자": b["author"],
            "요약": " / ".join(b["summary"]["summary_text"]),
            "전공 연계": " / ".join(b["summary"]["major_links"]),
            "프로젝트 제안": " / ".join(b["summary"]["projects"])
        }
        for b in books
    ])

    book_table_html = df.to_html(index=False, escape=False)

    # --------------------------
    # HTML 형태로 생성
    # --------------------------
    html_content = f"""
    <html>
    <head>
        <meta charset="UTF-8" />
        <style>
            body {{
                font-family: Arial, sans-serif;
                padding: 20px;
                line-height: 1.6;
            }}
            h1, h2 {{
                color: #16499A;
            }}
            .section {{
                margin-top: 30px;
                margin-bottom: 30px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
            }}
            table, th, td {{
                border: 1px solid #ccc;
                padding: 8px;
                text-align: left;
            }}
            th {{
                background-color: #f2f2f2;
            }}
        </style>
    </head>

    <body>
        <h1>AI 기반 학생부 분석 보고서</h1>

        <div class="section">
            <h2>학생 정보</h2>
            <p><strong>이름:</strong> {user['name']}</p>
            <p><strong>학교:</strong> {user['school']}</p>
            <p><strong>지원 학년도:</strong> {user['year']}</p>
        </div>

        <div class="section">
            <h2>종합 분석 결과</h2>
            <pre>{analysis}</pre>
        </div>

        <div class="section">
            <h2>독서활동 분석</h2>
            {book_table_html}
        </div>
    </body>
    </html>
    """

    return html_content.encode("utf-8")


# ==============================
# 4) 관리자 ZIP 다운로드
# ==============================
def admin_zip_download():
    zip_path = "all_reports.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        if os.path.exists("reports"):
            for f in os.listdir("reports"):
                z.write(f"reports/{f}")
    return zip_path
