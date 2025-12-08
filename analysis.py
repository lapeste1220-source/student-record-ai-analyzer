def run_gpt_analysis(client, sections, target_univ, target_major, target_values):

    prompt = f"""
    아래는 학생의 생활기록부 주요 항목입니다:

    {sections}

    목표 대학: {target_univ}
    목표 학과: {target_major}
    대학/학과 인재상: {target_values}

    아래 형식으로 분석하시오:

    1) 학생부 한 줄 요약
    2) 강점 3~5개
    3) 약점 3~5개
    4) 1·2학년 내용과 연결하여 3학년의 구체적인 보완 활동 제안:
       - 프로젝트
       - 보고서 주제
       - 독서 제안
       - 학급/학년 프로젝트
       - 리더십·협력 활동
    5) 마인드맵 구조(JSON)
    """

    response = client.chat.completions.create(
        model="gpt-5",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message["content"]


def summarize_book(client, book):

    prompt = f"""
    도서명: {book['title']}
    저자: {book['author']}

    다음을 작성하시오:
    1) 책의 핵심 내용 요약(검색 기반 가능)
    2) 해당 책이 학생부 전공적합성에 주는 의미
    3) 연계 가능한 프로젝트 또는 보고서 주제 2가지
    """

    response = client.chat.completions.create(
        model="gpt-5",
        messages=[{"role": "user", "content": prompt}]
    )

    summary = response.choices[0].message["content"]

    return {
        "title": book["title"],
        "author": book["author"],
        "summary": summary
    }
