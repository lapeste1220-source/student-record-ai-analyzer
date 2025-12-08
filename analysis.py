import json


# =====================================================
# 1) GPT 기반 학생부 종합 분석
# =====================================================
def run_gpt_analysis(client, sections, target_univ, target_major, target_values):

    prompt = f"""
    너는 학생부 종합전형 전문 컨설턴트다.

    아래는 학생의 생활기록부 주요 항목이다:

    {json.dumps(sections, ensure_ascii=False, indent=2)}

    목표 대학: {target_univ}
    목표 학과: {target_major}
    대학/학과 인재상: {target_values}

    아래 형식으로 출력하라(중요: 반드시 JSON 구조로 출력):

    {{
      "summary": "학생부 한 줄 요약",
      "strengths": ["강점1", "강점2", "강점3"],
      "weaknesses": ["약점1", "약점2", "약점3"],
      "suggestions": {{
          "projects": ["프로젝트1", "프로젝트2"],
          "reports": ["보고서 주제1", "보고서 주제2"],
          "books": ["추천 도서1", "추천 도서2"],
          "class_activity": "학급 또는 학년 프로젝트 제안",
          "leadership": "리더십/협력 활동 제안"
      }},
      "mindmap": {{
         "summary": "핵심요약",
         "strengths": ["강점A","강점B"],
         "weaknesses": ["약점A","약점B"],
         "activities": {{
            "탐구활동":["활동1","활동2"],
            "프로젝트":["활동3","활동4"]
         }}
      }}
    }}
    """

    response = client.chat.completions.create(
        model="gpt-5",
        messages=[{"role": "user", "content": prompt}]
    )

    content = response.choices[0].message["content"]

    try:
        return json.loads(content)   # JSON 파싱 시도
    except:
        # 실패 시 GPT 출력 중 JSON 부분만 추출
        json_start = content.find("{")
        json_end = content.rfind("}")
        cleaned = content[json_start:json_end+1]
        return json.loads(cleaned)


# =====================================================
# 2) GPT 기반 독서 분석 (심화 모드)
# =====================================================
def summarize_book(client, book):

    prompt = f"""
    너는 학생부 독서 영역 전문분석가다.

    도서명: {book['title']}
    저자: {book['author']}
    학생이 적은 독서기록 내용: {book['student_note']}

    아래 형식(JSON)으로 출력하라:

    {{
      "summary_text": ["요약1", "요약2", "..."],
      "major_links": ["전공 연계1", "전공 연계2", "전공 연계3"],
      "projects": ["프로젝트 제안1", "프로젝트 제안2"]
    }}
    """

    response = client.chat.completions.create(
        model="gpt-5",
        messages=[{"role": "user", "content": prompt}]
    )

    content = response.choices[0].message["content"]

    try:
        return json.loads(content)
    except:
        json_start = content.find("{")
        json_end = content.rfind("}")
        cleaned = content[json_start:json_end+1]
        return json.loads(cleaned)
