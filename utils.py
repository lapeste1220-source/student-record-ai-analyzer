from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
import io


def generate_pdf(user, analysis, books):
    buffer = io.BytesIO()

    # PDF 문서 설정
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm
    )

    styles = getSampleStyleSheet()

    # 고급 스타일 정의
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Title'],
        fontSize=26,
        leading=30,
        alignment=1,
        textColor=colors.HexColor("#16499A"),
        spaceAfter=20,
    )

    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor("#16499A"),
        spaceAfter=10,
        spaceBefore=15
    )

    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['BodyText'],
        fontSize=12,
        leading=16,
        spaceAfter=10,
    )

    elements = []

    # ===============================
    # 1. 표지
    # ===============================
    elements.append(Paragraph("학생부 맞춤형 분석 리포트", title_style))
    elements.append(Spacer(1, 20))

    cover_info = f"""
    <b>이름:</b> {user['name']}<br/>
    <b>학교:</b> {user['school']}<br/>
    <b>지원 학년도:</b> {user['year']}<br/>
    """
    elements.append(Paragraph(cover_info, body_style))
    elements.append(Spacer(1, 40))

    elements.append(Paragraph(
        "본 리포트는 AI 기반 분석 도구를 활용하여 학생부 주요 강점, 약점, 전공 적합성 등을 종합적으로 평가한 문서입니다.",
        body_style
    ))

    elements.append(Spacer(1, 30))

    elements.append(Paragraph("-----------------------------------------------", body_style))
    elements.append(Spacer(1, 20))

    # ===============================
    # 2. 종합 분석 요약
    # ===============================
    elements.append(Paragraph("📘 종합 분석 요약", subtitle_style))

    summary_text = f"""
    <b>• 한 줄 요약:</b> {analysis['summary']}<br/><br/>

    <b>• 강점:</b><br/>
    {'<br/>'.join('- ' + s for s in analysis['strengths'])}<br/><br/>

    <b>• 약점:</b><br/>
    {'<br/>'.join('- ' + w for w in analysis['weaknesses'])}<br/><br/>

    <b>• 3학년 보완 전략:</b><br/>
    - 프로젝트: {', '.join(analysis['suggestions']['projects'])}<br/>
    - 보고서 주제: {', '.join(analysis['suggestions']['reports'])}<br/>
    - 추천 독서: {', '.join(analysis['suggestions']['books'])}<br/>
    - 학급/학년 활동: {analysis['suggestions']['class_activity']}<br/>
    - 리더십/협력: {analysis['suggestions']['leadership']}<br/>
    """

    elements.append(Paragraph(summary_text, body_style))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("-----------------------------------------------", body_style))

    # ===============================
    # 3. 독서활동 테이블
    # ===============================
    elements.append(Paragraph("📚 독서활동 분석", subtitle_style))

    table_data = [["도서명", "저자", "핵심 요약", "전공 연계", "프로젝트 제안"]]

    for b in books:
        table_data.append([
            b["title"],
            b["author"],
            "<br/>".join(b["summary"]["summary_text"]),
            "<br/>".join(b["summary"]["major_links"]),
            "<br/>".join(b["summary"]["projects"]),
        ])

    table = Table(table_data, colWidths=[40*mm, 30*mm, 60*mm, 40*mm, 40*mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#16499A")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("ALIGN", (0,0), (-1,-1), "LEFT"),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("GRID", (0,0), (-1,-1), 0.5, colors.gray),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 20))

    elements.append(Paragraph(
        "<i>본 문서는 학생부 기반 맞춤형 분석 알고리즘 및 GPT 모델을 활용하여 생성되었습니다.</i>",
        body_style
    ))

    # ===============================
    # PDF 생성
    # ===============================
    doc.build(elements)

    pdf_value = buffer.getvalue()
    buffer.close()

    return pdf_value
