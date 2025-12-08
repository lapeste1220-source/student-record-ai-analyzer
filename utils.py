import re
import os
import io
import zipfile
from xhtml2pdf import pisa

# 생기부 섹션 별 분리
def parse_student_record(text):

    patterns = {
        "교과학습발달상황": r"교과학습발달상황([\s\S]*?)교과별 세부능력",
        "교과별 세부능력 특기사항": r"교과별 세부능력 특기사항([\s\S]*?)자율활동",
        "자율활동": r"자율활동([\s\S]*?)동아리활동",
        "창체동아리": r"동아리활동([\s\S]*?)진로활동",
        "진로활동": r"진로활동([\s\S]*?)개인별",
        "개인별특기사항": r"개인별 특기사항([\s\S]*?)행동특성",
        "행동특성및종합의견": r"행동특성 및 종합의견([\s\S]*)"
    }

    result = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        result[key] = match.group(1).strip() if match else "(해당 항목 없음)"

    return result


# 독서 목록 자동 추출
def extract_books(text):
    book_pattern = r"도서명[:：]?\s*(.+?)\s*저자[:：]?\s*(.+?)\n"
    books = re.findall(book_pattern, text)
    return [{"title": b[0], "author": b[1]} for b in books]


# PDF 생성
def generate_pdf(user, analysis, books):

    html = f"""
    <h1>AI 생기부 분석 리포트</h1>
    <h3>{user['name']} · {user['school']} ({user['year']})</h3>

    <h2>한 줄 요약</h2>
    <p>{analysis['summary']}</p>

    <h2>강점</h2>
    <p>{analysis['strengths']}</p>

    <h2>약점</h2>
    <p>{analysis['weaknesses']}</p>

    <h2>3학년 전략 제안</h2>
    <pre>{analysis['improvement_plan']}</pre>

    <h2>독서 분석</h2>
    """

    for b in books:
        html += f"<h3>{b['title']} — {b['author']}</h3>"
        html += f"<p>{b['summary']}</p>"

    pdf_bytes = io.BytesIO()
    pisa.CreatePDF(io.StringIO(html), dest=pdf_bytes)
    return pdf_bytes.getvalue()


# 관리자 ZIP 다운로드
def admin_zip_download():
    zip_path = "all_reports.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        for f in os.listdir("reports"):
            z.write(f"reports/{f}")
    return zip_path
