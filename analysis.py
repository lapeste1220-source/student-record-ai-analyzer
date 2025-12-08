import json
from openai import OpenAI


# =====================================================
# 1) 종합 GPT 분석 (학생부 분석 전체)
# =====================================================
def run_gpt_analysis(client, sections, target_univ, target_major, target_values):

    prompt = f"""
다음은 학생부 주요 항목입니다:

{json.dumps(sections, ensure_ascii=False, indent=2)}

희망 학과: {target_major}

학생부 분석을 아래 형식의 **JSON**으로 정확히 출력하세요.

{
  "summary": "한 줄 요약",
  "strengths": ["강점1", "강점2", "강점3"],
  "weaknesses": ["약점1", "약점2", "약점3"],
  "recommendations": {
      "projects": ["프로젝트 제안 1", "프로젝트 제안 2"],
      "reports": ["보고서 주제 1", "보고서 주제 2"],
      "books": ["추천도서1", "추천도서2"],
      "leadership": ["리더십 활동 제안"]
  },
  "mindmap": {
      "summary": "요약",
      "strengths": ["강점1", "강점2"],
      "weaknesses": ["약점1", "약점2"],
      "activities": {
          "projects": ["프로젝트1"],
          "reading": ["독서1"],
          "extracurricular": ["비교과1"]
      }
  }
}

위 JSON 구조 이외의 설명, 문장은 절대로 넣지 마세요.
"""

    response = client.chat.completions.create(
        model="gpt-5",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    raw = response.choices[0].message["content"].strip()

    # JSON 파싱 시도
    try:
        data = json.loads(raw)
        return data
    except:
        # 파싱 실패하면 최소한의 구조로 반환 (앱 크래시 방지)
        return {
            "summary": "정보 분석 중 오류 발생",
            "strengths": [],
            "weaknesses": [],
            "recommendations": {},
            "mindmap": {}
        }



# =====================================================
# 2) 책 Summary 분석
# =====================================================
def summarize_book(client, book):

    prompt = f"""
도서명: {book['title']}
저자: {book['author']}
학생 독서 기록: {book['student_note']}

아래 형식의 **JSON**으로 정확하게 출력하세요:

{
  "summary_text": ["핵심 요약1", "핵심 요약2", "핵심 요약3"],
  "major_links": ["전공 연계1", "전공 연계2", "전공 연계3"],
  "projects": ["프로젝트 제안1", "프로젝트 제안2"]
}

위 JSON 형식을 반드시 지키고, 설명 문장은 절대로 추가하지 마세요.
"""

    response = client.chat.completions.create(
        model="gpt-5",
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.choices[0].message["content"].strip()

    # JSON 파싱
    try:
        data = json.loads(raw)
        return data
    except:
        # 실패 시 최소 구조 제공
        return {
            "summary_text": ["요약 생성 실패"],
            "major_links": [],
            "projects": []
        }
