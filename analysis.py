def run_gpt_analysis(client, sections, target_major):
    prompt = f"""
    너는 대한민국 입시 전문가이자 학생부 분석 전문 컨설턴트이다.

    아래 학생의 생기부 내용을 읽고,
    희망 학과: {target_major}
    에 맞춘 종합 분석을 4가지로 나누어 작성하라.

    1) 전공 적합성 종합 평가
    2) 학생의 강점 및 역량 분석
    3) 비교과·세특에서 드러나는 전공 관련 패턴 분석
    4) 추천 가능한 심화 탐구 또는 프로젝트 제안
    5) 생기부 전체 특징 기반 마인드맵(JSON 형식)

    ---------------------
    [생기부 내용]
    {sections}
    ---------------------
    """

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    text = res.choices[0].message.content

    return {
        "overall": text,
        "strengths": text,
        "patterns": text,
        "projects": text,
        "mindmap": "{}"
    }


def summarize_book(client, book):
    prompt = f"""
    아래 도서에 대해 생기부 독서활동 관점에서 분석하라.

    도서명: {book['title']}
    저자: {book['author']}
    학생 메모: {book['student_note']}

    출력 형식:
    1) 핵심 요약 bullet 5개
    2) 전공 연계 포인트 5개
    3) 실천 가능한 프로젝트 3개
    """

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    content = res.choices[0].message.content.split("\n")

    return {
        "summary_text": content[:5],
        "major_links": content[5:10],
        "projects": content[10:13]
    }
