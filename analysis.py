def run_gpt_analysis(client, sections, target_univ, target_major, target_values):

    prompt = f"""
    아래는 학생의 생활기록부 주요 항목입니다:

    {sections}

    목표 대학: {target_univ}
    목표 학과: {target_major}
    대학/학과 인재상: {target_values}

    아래 형식으로 분석하시오(학생부 어투 유지):

    1) 학생부 한 줄 요약
    2) 강점 3~5개
    3) 약점 3~5개
    4) 1·2학년 내용과 연결하여 3학년 구체적 보완 전략:
       - 프로젝트 2개
       - 보고서 주제 2개
       - 독서 제안 2권
       - 학급/학년 프로젝트 제안
       - 리더십·협력 활동 제안
    5) 마인드맵 구조(JSON)
    """

    response = client.chat.completions.create(
        model="gpt-5",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message["content"]




def summarize_book(client, book):
    """
    심화 모드 분석:
    - 책 요약 10줄
    - 학생이 적은 독서내용 활용
    - 전공연계 3개
    - 프로젝트 제안 2개
    """

    prompt = f"""
    도서명: {book['title']}
    저자: {book['author']}
    학생 독서기록 내용: {book['student_note']}

    다음 기준에 따라 분석하시오(학생부 어투):

    1) 책 핵심 요약(약 10줄)
    2) 전공 관련 역량 또는 학업역량과의 연계 3개
    3) 보고서 또는 프로젝트 제안 2개
    """

    response = client.chat.completions.create(
        model="gpt-5",
        messages=[{"role": "user", "content": prompt}]
    )

    text = response.choices[0].message["content"].strip()

    return {
        "summary_text": text.split("\n")[0:10],
        "major_links": text.split("\n")[10:13],
        "projects": text.split("\n")[13:15],
    }
