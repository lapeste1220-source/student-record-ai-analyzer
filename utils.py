import re
import os
import io
import zipfile
from xhtml2pdf import pisa
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
    생기부 독서활동 영역에서
    [도서명, 저자, 독서중심내용] 자동 추출
    """

    # 패턴 예: (1학기) 1984(조지오웰) ... 독서 중심 내용
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
# 3) PDF 생성 (독서활동 표로 구성)
# ==============================
def generate_pdf(user, analysis, books):
    import pandas as pd
    from xhtml2pdf import pisa

    # ==========================
    # 1) 독서활동 표 생성
    # ==========================
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

    table_html = df.to_html(index=False, escape=False)

    # ==========================
    # 2) HTML 템플릿 (고급 디자인 적용)
    # ==========================
    html = f"""
    <html>
    <head>
        <meta charset="UTF-8" />
        <style>
            @page {{
                size: A4;
                margin: 25mm;
            }}

            body {{
                font-family: 'Noto Sans KR';
                line-height: 1.6;
            }}

            h1 {{
                text-align: center;
                font-size: 26px;
                margin-bottom: 30px;
            }}

            h2 {{
                color: #16499A;
                border-bottom: 2px solid #16499A;
                padding-bottom: 4px;
            }}

            .box {{
                border: 1px solid #ccc;
                padding: 10px;
                margin-bottom: 15px;
                border-radius: 6px;
            }}

            .strength {{
                color: #0B6EDE;
                font-weight: bold;
            }}

            .weakness {{
                color: #C62828;
                font-weight: bold;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
            }}

            th, td {{
                border: 1px solid #777;
                padding: 8px;
                font-size: 12px;
            }}

            th {{
                background-color: #f0f0f0;
            }}

        </style>
    </head>

    <body>

    <h1>AI 기반 학생부 분석 리포트</h1>

    <h2>학생 정보</h2>
    <div class="box">
        <p><strong>이름:</strong> {user['name']}</p>
        <p><strong>학교:</strong> {user['school']}</p>
        <p><strong>지원 학년도:</strong> {user['year']}</p>
    </div>

    <h2>한 줄 요약</h2>
    <div class="box">{analysis['summary']}</div>

    <h2>강점</h2>
    <div class="box strength">{analysis['strengths']}</div>

    <h2>약점</h2>
    <div class="box weakness">{analysis['weaknesses']}</div>

    <h2>3학년 전략 제안</h2>
    <div class="box">
        <pre>{analysis['improvement_plan']}</pre>
    </div>

    <h2>독서활동 분석</h2>
    {table_html}

    </body>
    </html>
    """

    pdf_bytes = io.BytesIO()
    pisa.CreatePDF(io.StringIO(html), dest=pdf_bytes)

    return pdf_bytes.getvalue()



# ==============================
# 4) 관리자 ZIP 다운로드
# ==============================
def admin_zip_download():
    zip_path = "all_reports.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        for f in os.listdir("reports"):
            z.write(f"reports/{f}")
    return zip_path
