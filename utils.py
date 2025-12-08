import re
import os
import io
import zipfile
import pandas as pd


# ==============================
# 1) 학생부 자동 분리 엔진
# ==============================
def parse_student_record(text):

    patterns = {
        "자율활동": r"자율활동([\s\S]*?)동아리활동",
        "창체동아리": r"동아리활동([\s\S]*?)진로활동",
        "진로활동": r"진로활동([\s\S]*?)창의적 체험활동상황|[\s\S]*?교과학습발달상황",
        "교과학습발달상황": r"교과학습발달상황([\s\S]*?)세부능력 및 특기사항",
        "세부능력특기사항": r"세부능력 및 특기사항([\s\S]*?)독서활동",
        "독서활동": r"독서활동([\s\S]*?)행동특성 및 종합의견",
        "행동특성 및 종합의견": r"행동특성 및 종합의견([\s\S]*)"
    }

    result = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            extracted = match.group(1).strip()
            if len(extracted) < 2:
                extracted = "(해당 항목 없음)"
        else:
            extracted = "(해당 항목 없음)"
        result[key] = extracted

    return result


# ==============================
# 2) 독서활동 자동 추출 엔진
# ==============================
def extract_books(text):
    """
    실제 생기부 PDF의 다양한 패턴을 수용하도록 범용 정규식 설계
    예시:
      도서명(저자) 내용...
      도서명 (저자) 내용...
    """

    pattern = r"([^\n(]+?)\s*\(([^)]+)\)\s*([^\n]+)"
    matches = re.findall(pattern, text)

    books = []
    for title, author, note in matches:
        books.append({
            "title": title.strip(),
            "author": author.strip(),
            "student_note": note.strip()
        })

    return books


# ==============================
# 3) HTML 리포트 생성
# ==============================
def generate_html_report(user, analysis, books):
    
    # 분석이 dict인 경우 문자열로 변환
    analysis_text = ""
    if isinstance(analysis, dict):
        for k, v in analysis.items():
            analysis_text += f"{k}: {v}\n"
    else:
        analysis_text = str(analysis)

    # 독서 테이블 생성
    if books:
        df = pd.DataFrame([
            {
                "도서명": b.get("title", ""),
                "저자": b.get("author", ""),
                "요약": " / ".join(b["summary"].get("summary_text", [])),
                "전공 연계": " / ".join(b["summary"].get("major_links", [])),
                "프로젝트 제안": " / ".join(b["summary"].get("projects", [])),
            }
            for b in books
        ])
        book_table_html = df.to_html(index=False, escape=False)
    else:
        book_table_html = "<p>독서 기록 없음</p>"

    # HTML
    html = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: Arial, sans-serif;
                padding: 20px;
            }}
            h1, h2 {{
                color: #16499A;
            }}
        </style>
    </head>
    <body>
        <h1>AI 생기부 분석 리포트</h1>

        <h2>학생 정보</h2>
        <p><b>이름:</b> {user.get('name')}</p>
        <p><b>학교:</b> {user.get('school')}</p>
        <p><b>학년도:</b> {user.get('year')}</p>

        <h2>종합 분석 결과</h2>
        <pre>{analysis_text}</pre>

        <h2>독서활동 분석</h2>
        {book_table_html}
    </body>
    </html>
    """

    return html.encode("utf-8")


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
