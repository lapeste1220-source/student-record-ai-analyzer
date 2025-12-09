import streamlit as st
import os
import json
from io import BytesIO

from openai import OpenAI
from pypdf import PdfReader
from fpdf import FPDF
import csv  # 학번/이름 선택을 위한 CSV 사용


# =========================
# 설정값
# =========================

APP_TITLE = "함창고 학생부 분석 시스템"
ACCESS_PASSWORD = "hamchang2025"  # 1차 보안 비밀번호
USAGE_LOG_FILE = "usage_log.json"
MAX_USES_PER_NAME = 2
KOREAN_FONT_FILE = "NanumGothic.ttf"  # 같은 폴더에 폰트 파일 넣어두기
STUDENTS_FILE = "students.csv"  # 학번/이름 목록 CSV

# 토큰 제한 (응답 길이만 제한 – 입력 길이는 전체 사용)
MAX_COMPLETION_TOKENS = 2000  # GPT가 생성하는 최대 토큰 수


# =========================
# 유틸 함수: 사용 횟수 관리
# =========================

def load_usage_log():
    """이름별 사용 횟수 기록을 JSON으로 관리."""
    if not os.path.exists(USAGE_LOG_FILE):
        return {}
    try:
        with open(USAGE_LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_usage_log(log):
    try:
        with open(USAGE_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"사용 이력 저장 중 오류: {e}")


def can_use_analysis(student_key: str) -> bool:
    """이름/학번을 합친 key 기준으로 최대 MAX_USES_PER_NAME회까지 허용."""
    if not student_key:
        return False
    log = load_usage_log()
    current = log.get(student_key, 0)
    return current < MAX_USES_PER_NAME


def increase_usage(student_key: str):
    if not student_key:
        return
    log = load_usage_log()
    current = log.get(student_key, 0)
    log[student_key] = current + 1
    save_usage_log(log)


def get_usage_count(student_key: str) -> int:
    log = load_usage_log()
    return log.get(student_key, 0)


# =========================
# 유틸 함수: 학생 목록 로드
# =========================

def load_students():
    """
    students.csv에서 학번/이름 목록을 불러온다.
    CSV 형식 예시:
    학번,이름
    10101,김가은
    10102,박호준
    """
    students = []
    if not os.path.exists(STUDENTS_FILE):
        return students
    try:
        with open(STUDENTS_FILE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                students.append({
                    "id": row.get("학번", "").strip(),
                    "name": row.get("이름", "").strip(),
                })
    except Exception as e:
        st.error(f"학생 목록을 불러오는 중 오류: {e}")
    return students


# =========================
# 유틸 함수: PDF 텍스트 추출
# =========================

def extract_text_from_pdf(uploaded_file) -> str:
    """
    텍스트 기반 PDF에서 텍스트를 추출.
    - Streamlit UploadedFile을 BytesIO로 감싸서 사용
    - 모든 페이지(1쪽~마지막쪽) 사용
    """
    try:
        # UploadedFile → BytesIO
        uploaded_file.seek(0)
        data = uploaded_file.read()
        buffer = BytesIO(data)

        reader = PdfReader(buffer)
        num_pages = len(reader.pages)

        if num_pages == 0:
            st.error("PDF에 페이지가 없습니다.")
            return ""

        st.caption(f"PDF는 총 {num_pages}쪽이며, 1쪽부터 {num_pages}쪽까지 모두 사용합니다.")

        text = ""
        for i in range(num_pages):
            page = reader.pages[i]
            page_text = page.extract_text() or ""
            text += page_text + "\n"

        return text.strip()

    except Exception as e:
        st.error(f"PDF 텍스트를 읽는 중 오류가 발생했습니다: {e}")
        return ""


# =========================
# 유틸 함수: OpenAI 클라이언트 생성
# =========================

def get_openai_client(api_key: str):
    try:
        client = OpenAI(api_key=api_key)
        return client
    except Exception as e:
        st.error(f"OpenAI 클라이언트 생성 오류: {e}")
        return None


# =========================
# GPT 분석 프롬프트
# =========================

def build_analysis_prompt(student_name, track, major, pdf_text):
    """
    학생부 PDF 텍스트를 기반으로 JSON 형식의 분석 요청 프롬프트 생성.
    """
    prompt = f"""
너는 대한민국 고등학교 담임교사이자 진로진학부 교사의 입장에서,
아래 학생의 학교생활기록부 내용을 학생부 종합전형 관점에서 분석하는 역할을 맡고 있다.

학생 기본 정보:
- 이름: {student_name}
- 희망계열 및 학과: {track} / {major}

아래는 이 학생의 고등학교 학교생활기록부 전체 텍스트이다.

이 텍스트에서 다음 항목들을 최대한 충실하게 찾아 분석하라.

1. 창의적체험활동
2. 교과학습발달상황
3. 행동특성 및 종합의견
4. 독서활동

위 항목들을 기반으로,
학생부 종합전형에 활용할 수 있도록 다음 내용을 JSON 형식으로만 출력하라.

JSON 형식 (중괄호 포함 전체를 JSON으로만 출력, 다른 설명 문장은 절대 넣지 말 것):

{{
  "basic_info": {{
    "name": "{student_name}",
    "track": "{track}",
    "major": "{major}"
  }},
  "sections": {{
    "creative_activities": "창의적체험활동 관련 핵심 내용 요약 (문단 형태, 5~10문장)",
    "academic_performance": "교과학습발달상황 관련 핵심 내용 요약 (문단 형태, 5~10문장)",
    "behavior": "행동특성 및 종합의견 핵심 내용 요약 (문단 형태, 3~6문장)",
    "reading": {{
      "raw_list": [
        {{
          "title": "도서명 1",
          "author": "저자(알 수 없으면 빈 문자열)",
          "related_subject": "관련 교과/진로 (추론 가능하면)",
          "comment": "이 학생에게서 보이는 독서 특징 혹은 해당 도서의 역할"
        }}
      ],
      "overall_comment": "독서 활동 전반에 대한 평가와 특징 (3~6문장)"
    }}
  }},
  "analysis": {{
    "summary": "학생 전체 학교생활의 특징과 종합 평가 (5~8문장)",
    "strengths": [
      "학생의 강점 1",
      "학생의 강점 2",
      "학생의 강점 3"
    ],
    "weaknesses": [
      "학생의 보완 필요 영역 1",
      "학생의 보완 필요 영역 2"
    ],
    "keywords": [
      "핵심 키워드 1",
      "핵심 키워드 2",
      "핵심 키워드 3",
      "핵심 키워드 4",
      "핵심 키워드 5"
    ]
  }},
  "suggested_activities": {{
    "strengths": [
      {{
        "id": "S1",
        "title": "강점을 더 강화할 수 있는 활동 이름",
        "description": "구체적인 활동 내용 (어떤 식으로 진행하면 좋은지)",
        "reason": "이 활동이 해당 학생에게 적절한 이유",
        "expected_record_impact": "학생부에 어느 영역에 어떤 표현으로 반영될 수 있을지 개략 설명"
      }}
    ],
    "weaknesses": [
      {{
        "id": "W1",
        "title": "약점을 보완할 수 있는 활동 이름",
        "description": "구체적인 활동 내용",
        "reason": "이 활동이 해당 학생에게 적절한 이유",
        "expected_record_impact": "학생부에 기대되는 변화 방향"
      }}
    ]
  }},
  "reading_enrichment": {{
    "core_summaries": [
      {{
        "title": "기존 독서 도서명 예시",
        "summary": "해당 도서의 핵심 내용 요약 및 학생 진로와의 연결 (3~5문장)"
      }}
    ],
    "related_books": [
      {{
        "title": "연계 추천 도서 1",
        "reason": "왜 이 책을 읽으면 도움이 되는지 (3~4문장)"
      }},
      {{
        "title": "연계 추천 도서 2",
        "reason": "연계성 및 기대 효과"
      }}
    ]
  }}
}}

주의사항:
- 반드시 위 JSON 구조를 그대로 사용하되, 내용은 구체적으로 채워라.
- JSON 바깥에 다른 문장을 절대 쓰지 말 것.
- null 대신 빈 문자열 ""을 사용해라.
- 텍스트에서 해당 정보를 찾기 어려우면, 추론 가능한 범위 내에서 작성하되, 과도하게 지어내지 말고 "추론"임을 간접적으로 드러내라.

아래는 학교생활기록부 전체 텍스트이다:

------------------학생부 텍스트 시작------------------
{pdf_text}
------------------학생부 텍스트 끝------------------
"""
    return prompt


def call_gpt_analysis(client, prompt: str):
    """학생부 분석 API 호출 (JSON 응답 기대)."""
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",  # 선생님 계정에서 사용 가능한 모델명으로 조정 가능
            messages=[
                {
                    "role": "system",
                    "content": "너는 대한민국 고등학교 담임교사이자 진로진학부 교사이다."
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            # 새 모델에서는 max_tokens 대신 max_completion_tokens 사용
            max_completion_tokens=MAX_COMPLETION_TOKENS,
        )
        content = response.choices[0].message.content
        data = json.loads(content)
        return data
    except json.JSONDecodeError:
        st.error("GPT 응답을 JSON으로 해석하는 데 실패했습니다. 프롬프트를 조금 줄여보거나 다시 시도해 주세요.")
        return None
    except Exception as e:
        st.error(f"학생부 분석 중 오류가 발생했습니다: {e}")
        return None


def build_plan_prompt(student_name, track, major, analysis_data, selected_activities):
    """
    선택한 추천 활동을 바탕으로 실시 계획 + 학생부 예시 문구 요청 프롬프트.
    """
    strengths = analysis_data.get("analysis", {}).get("strengths", [])
    weaknesses = analysis_data.get("analysis", {}).get("weaknesses", [])
    keywords = analysis_data.get("analysis", {}).get("keywords", [])

    prompt = f"""
너는 대한민국 고등학교 담임교사이자 진로진학부 교사이다.

다음 학생의 기본 정보와 학생부 분석 결과, 그리고 학생이 실제로 수행하기로 선택한 활동 목록이 주어진다.
이 정보를 바탕으로 각 활동에 대해
1) 구체적인 실시 계획
2) 학생부에 기록될 수 있는 예시 문구
를 작성하라.

[학생 정보]
- 이름: {student_name}
- 희망계열 및 학과: {track} / {major}

[학생부 분석 요약]
- 강점: {strengths}
- 약점: {weaknesses}
- 핵심 키워드: {keywords}

[학생이 선택한 활동 목록]
각 항목은 (id, title, description, reason, expected_record_impact)로 이루어져 있다.

{json.dumps(selected_activities, ensure_ascii=False, indent=2)}

출력 형식은 마크다운 형태로 다음 구조를 따라라:

# 활동별 실시 계획 및 학생부 예시 문구

## 1. 활동 제목 예시
- 활동 ID: S1 또는 W1과 같은 형태
- 활동 개요: (1~2문장)

### (1) 실시 계획
- 기간: 몇 학년 몇 학기, 대략 기간
- 횟수/형식: 예) 주 1회, 방과후, 동아리형, 프로젝트형 등
- 구체적 활동 내용: 학생이 무엇을 하고, 어떤 결과물을 내는지
- 협력 대상: 교사, 친구, 외부 기관 등 (있다면)

### (2) 학생부 예시 문구
- 창의적체험활동 예시 문장 (2~3문장)
- 교과세특 혹은 행동특성 및 종합의견에 들어갈 수 있는 예시 문장 (2~3문장)

위와 같은 형식을 선택한 모든 활동에 대해 반복하여 작성하라.
"""
    return prompt


def call_gpt_plan(client, prompt: str):
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": "너는 대한민국 고등학교 담임교사이자 진로진학부 교사이다."
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
        )
        content = response.choices[0].message.content
        return content
    except Exception as e:
        st.error(f"실시 계획/예시 문구 생성 중 오류가 발생했습니다: {e}")
        return None


# =========================
# PDF 생성 함수 (fpdf2 사용)
# =========================

def generate_pdf_from_text(title: str, text: str) -> bytes:
    """
    전체 결과(분석 + 계획)를 하나의 텍스트로 받아 PDF로 변환.
    한글 출력을 위해 TTF 폰트 필요.
    """
    pdf = FPDF()
    pdf.add_page()

    try:
        pdf.add_font("KOREAN", "", KOREAN_FONT_FILE, uni=True)
        pdf.set_font("KOREAN", size=12)
    except Exception:
        st.warning(f"한글 폰트 로딩에 실패했습니다. 폰트 파일({KOREAN_FONT_FILE})을 확인해 주세요. 기본 폰트로 출력합니다.")
        pdf.set_font("Arial", size=12)

    # 제목
    pdf.set_font_size(16)
    pdf.multi_cell(0, 10, title)
    pdf.ln(4)
    pdf.set_font_size(12)

    # 본문
    for line in text.split("\n"):
        pdf.multi_cell(0, 7, line)
    # bytes로 반환
    pdf_bytes = pdf.output(dest="S").encode("latin1")
    return pdf_bytes


# =========================
# Streamlit 앱
# =========================

def main():
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    st.title(APP_TITLE)
    st.caption("함창고 학생부 분석 & 활동 계획 보조 시스템 (내부용)")

    # 세션 상태 초기화
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "analysis_data" not in st.session_state:
        st.session_state.analysis_data = None
    if "plan_markdown" not in st.session_state:
        st.session_state.plan_markdown = None

    # 1차 비밀번호 접근 제어
    if not st.session_state.authenticated:
        st.subheader("접속 비밀번호 입력")
        pw = st.text_input("접속 비밀번호를 입력하세요.", type="password")
        if st.button("입장"):
            if pw == ACCESS_PASSWORD:
                st.session_state.authenticated = True
                st.success("접속에 성공했습니다.")
            else:
                st.error("비밀번호가 올바르지 않습니다.")
        st.stop()

    # 메인 UI
    st.info(
        """
        ⚠️ 이 시스템은 교사용 내부 도구입니다.
        - 접속 비밀번호: hamchang2025 (학생에게 공유 금지)
        - 분석 및 활동 제안은 OpenAI GPT API를 사용합니다.
        - 교사 API 키 사용은 **추가 비밀번호 입력** 후 활성화됩니다.
        - 이름별 분석 실행 횟수 제한: 최대 2회
        """
    )

    # 기초 정보 입력
    st.subheader("1. 기초 정보 입력")

    students = load_students()

    col1, col2, col3 = st.columns(3)

    # 학번/이름 선택
    with col1:
        if not students:
            st.error("students.csv 파일에서 학생 목록을 불러오지 못했습니다. 학번,이름 형식으로 CSV를 만들어 주세요.")
            student_name = ""
            student_id = ""
        else:
            options = [f"{s['id']} {s['name']}" for s in students]
            selected_label = st.selectbox("본인 학번/이름 선택", ["선택하세요"] + options)

            if selected_label == "선택하세요":
                student_name = ""
                student_id = ""
            else:
                idx = options.index(selected_label)
                student = students[idx]
                student_name = student["name"]
                student_id = student["id"]

    with col2:
        track = st.text_input("희망 계열 (예: 공학계열, 인문사회계열 등)")
    with col3:
        major = st.text_input("희망 학과 (예: 기계공학과, 국어교육과 등)")

    # PDF 업로드
    st.subheader("2. 학교생활기록부 PDF 업로드")
    uploaded_pdf = st.file_uploader("학교생활기록부 PDF 파일을 업로드하세요.", type=["pdf"])

    if uploaded_pdf is not None:
        st.success("PDF 업로드 완료")

    # API 사용 설정
    st.subheader("3. GPT API 사용 설정")

    api_mode = st.radio(
        "API 사용 방식 선택",
        ["교사 API 사용 (추천)", "개인 API 키 직접 입력"],
        horizontal=True,
    )

    openai_api_key = None

    if api_mode == "교사 API 사용 (추천)":
        st.markdown(
            """
            - 교사용 OpenAI API 키는 서버 환경 변수 또는 Streamlit 비밀(secrets)에 저장되어 있어야 합니다.  
            - 예: `OPENAI_API_KEY` 환경 변수 또는 `st.secrets["OPENAI_API_KEY"]`
            """
        )
        teacher_pw = st.text_input(
            "교사용 분석 기능 활성화를 위한 추가 비밀번호", type="password"
        )
        if teacher_pw:
            TEACHER_PASSWORD = os.environ.get("TEACHER_PASSWORD", "teacher2025")
            if "TEACHER_PASSWORD" in st.secrets:
                TEACHER_PASSWORD = st.secrets["TEACHER_PASSWORD"]

            if teacher_pw == TEACHER_PASSWORD:
                st.success("교사 모드 활성화 완료. 서버에 저장된 API 키를 사용합니다.")
                if "OPENAI_API_KEY" in st.secrets:
                    openai_api_key = st.secrets["OPENAI_API_KEY"]
                else:
                    openai_api_key = os.environ.get("OPENAI_API_KEY")
            else:
                st.error("교사용 비밀번호가 올바르지 않습니다.")
    else:
        st.markdown(
            """
            - 학생/교사가 직접 보유한 OpenAI API 키를 입력해 사용할 수 있습니다.  
            - 키는 이 세션에서만 사용되며, 서버에 따로 저장하지 않습니다.
            """
        )
        openai_api_key = st.text_input("개인 OpenAI API 키를 입력하세요.", type="password")

    if openai_api_key is None:
        st.warning("⚠️ 아직 유효한 API 키가 설정되지 않았습니다.")

    # 학생부 분석 실행
    st.subheader("4. 학생부 분석 실행")

    # 학번+이름을 합친 key로 사용 횟수 관리
    usage_key = f"{student_id}_{student_name}" if 'student_id' in locals() and student_id and student_name else ""

    if student_name:
        used_count = get_usage_count(usage_key)
        st.caption(f"현재 '{student_name}({student_id})' 기준 분석 실행 횟수: {used_count} / {MAX_USES_PER_NAME}")

    analyze_clicked = st.button("학생부 분석 실행")

    if analyze_clicked:
        if not student_name:
            st.error("학생 성명/학번을 선택해 주세요.")
        elif not uploaded_pdf:
            st.error("학교생활기록부 PDF 파일을 업로드해 주세요.")
        elif not openai_api_key:
            st.error("유효한 OpenAI API 키가 설정되어 있지 않습니다.")
        elif not can_use_analysis(usage_key):
            st.error(f"'{student_name}({student_id})' 기준으로는 이미 {MAX_USES_PER_NAME}회 분석을 사용했습니다.")
        else:
            # 1) PDF 텍스트 추출 (모든 페이지 사용)
            with st.spinner("PDF에서 텍스트를 추출하는 중입니다..."):
                pdf_text = extract_text_from_pdf(uploaded_pdf)
                if not pdf_text:
                    st.error(
                        "PDF에서 추출할 수 있는 텍스트가 없습니다. "
                        "이미지(스캔) 형태의 학생부일 수 있습니다.\n"
                        "글자 선택이 가능한 텍스트 기반 PDF로 다시 업로드해 주세요."
                    )
                    st.stop()
                original_len = len(pdf_text)
                st.caption(f"추출된 텍스트 길이: 약 {original_len}자")

            # 2) GPT 분석
            client = get_openai_client(openai_api_key)
            if client is None:
                st.stop()
            with st.spinner("GPT로 학생부를 분석하는 중입니다..."):
                prompt = build_analysis_prompt(student_name, track, major, pdf_text)
                analysis_data = call_gpt_analysis(client, prompt)

            if analysis_data:
                st.session_state.analysis_data = analysis_data
                increase_usage(usage_key)
                st.success("학생부 분석이 완료되었습니다.")

    # 분석 결과 표시
    if st.session_state.analysis_data:
        analysis_data = st.session_state.analysis_data
        st.subheader("5. 분석 결과")

        tabs = st.tabs(["종합 요약", "세부 영역 분석", "독서 활동", "추천 활동"])

        # 탭 1: 종합 요약
        with tabs[0]:
            st.markdown("### 학생 종합 요약")
            summary = analysis_data.get("analysis", {}).get("summary", "")
            st.write(summary)

            st.markdown("### 강점")
            for s in analysis_data.get("analysis", {}).get("strengths", []):
                st.markdown(f"- {s}")

            st.markdown("### 보완 필요 영역")
            for w in analysis_data.get("analysis", {}).get("weaknesses", []):
                st.markdown(f"- {w}")

            st.markdown("### 학생부 핵심 키워드")
            keywords = analysis_data.get("analysis", {}).get("keywords", [])
            if keywords:
                st.write(", ".join(keywords))

        # 탭 2: 세부 영역
        with tabs[1]:
            st.markdown("### 창의적체험활동")
            st.write(analysis_data.get("sections", {}).get("creative_activities", ""))

            st.markdown("### 교과학습발달상황")
            st.write(analysis_data.get("sections", {}).get("academic_performance", ""))

            st.markdown("### 행동특성 및 종합의견")
            st.write(analysis_data.get("sections", {}).get("behavior", ""))

        # 탭 3: 독서 활동
        with tabs[2]:
            st.markdown("### 독서 활동 정리")
            reading = analysis_data.get("sections", {}).get("reading", {})
            raw_list = reading.get("raw_list", [])
            if raw_list:
                for idx, book in enumerate(raw_list, start=1):
                    st.markdown(
                        f"**{idx}. {book.get('title','')}**  "
                        f"(저자: {book.get('author','')}, 관련: {book.get('related_subject','')})"
                    )
                    if book.get("comment"):
                        st.caption(book.get("comment"))
            else:
                st.write("독서 활동 정보가 충분하지 않거나 추출되지 않았습니다.")

            st.markdown("### 독서 활동 전반 평가")
            st.write(reading.get("overall_comment", ""))

            st.markdown("### 연계 추천 도서")
            re_en = analysis_data.get("reading_enrichment", {})
            for rb in re_en.get("related_books", []):
                st.markdown(f"- **{rb.get('title','')}**: {rb.get('reason','')}")

        # 탭 4: 추천 활동 선택
        with tabs[3]:
            st.markdown("### 추천 활동 중 원하는 것 선택")

            suggested = analysis_data.get("suggested_activities", {})
            strength_acts = suggested.get("strengths", [])
            weakness_acts = suggested.get("weaknesses", [])

            selected_activities = []

            st.markdown("#### 강점을 더 강화하는 활동")
            if strength_acts:
                for i, act in enumerate(strength_acts):
                    key = f"strength_act_{i}"
                    checked = st.checkbox(
                        f"[{act.get('id','')}] {act.get('title','')}",
                        key=key
                    )
                    with st.expander("상세 보기", expanded=False):
                        st.markdown(f"- 설명: {act.get('description','')}")
                        st.markdown(f"- 추천 이유: {act.get('reason','')}")
                        st.markdown(f"- 학생부 반영 방향: {act.get('expected_record_impact','')}")
                    if checked:
                        selected_activities.append(act)
            else:
                st.write("강점을 강화하는 추천 활동이 없습니다.")

            st.markdown("#### 약점을 보완하는 활동")
            if weakness_acts:
                for i, act in enumerate(weakness_acts):
                    key = f"weakness_act_{i}"
                    checked = st.checkbox(
                        f"[{act.get('id','')}] {act.get('title','')}",
                        key=key
                    )
                    with st.expander("상세 보기", expanded=False):
                        st.markdown(f"- 설명: {act.get('description','')}")
                        st.markdown(f"- 추천 이유: {act.get('reason','')}")
                        st.markdown(f"- 학생부 반영 방향: {act.get('expected_record_impact','')}")
                    if checked:
                        selected_activities.append(act)
            else:
                st.write("약점을 보완하는 추천 활동이 없습니다.")

            st.markdown("---")
            generate_plan_clicked = st.button("선택한 활동으로 실시 계획 및 학생부 예시 문구 생성")

            if generate_plan_clicked:
                if not selected_activities:
                    st.error("최소 1개 이상의 활동을 선택해 주세요.")
                elif not openai_api_key:
                    st.error("유효한 OpenAI API 키가 설정되어 있지 않습니다.")
                else:
                    client = get_openai_client(openai_api_key)
                    if client is None:
                        st.stop()
                    with st.spinner("선택한 활동을 기반으로 실시 계획과 학생부 예시 문구를 생성하는 중입니다..."):
                        plan_prompt = build_plan_prompt(
                            student_name, track, major, analysis_data, selected_activities
                        )
                        plan_markdown = call_gpt_plan(client, plan_prompt)
                    if plan_markdown:
                        st.session_state.plan_markdown = plan_markdown
                        st.success("실시 계획 및 예시 문구 생성 완료!")

    # 실시 계획 / 예시 문구 결과 표시 & PDF 생성
    if st.session_state.plan_markdown or st.session_state.analysis_data:
        st.subheader("6. 최종 결과 및 PDF 다운로드")

        analysis_text_block = ""
        if st.session_state.analysis_data:
            a = st.session_state.analysis_data
            analysis_text_block += f"[학생 정보]\n이름: {a.get('basic_info', {}).get('name','')}\n"
            analysis_text_block += f"희망 계열/학과: {a.get('basic_info', {}).get('track','')} / {a.get('basic_info', {}).get('major','')}\n\n"
            analysis_text_block += "[종합 요약]\n"
            analysis_text_block += a.get("analysis", {}).get("summary", "") + "\n\n"
            analysis_text_block += "[강점]\n"
            for s in a.get("analysis", {}).get("strengths", []):
                analysis_text_block += f"- {s}\n"
            analysis_text_block += "\n[보완 필요 영역]\n"
            for w in a.get("analysis", {}).get("weaknesses", []):
                analysis_text_block += f"- {w}\n"
            analysis_text_block += "\n[핵심 키워드]\n"
            analysis_text_block += ", ".join(a.get("analysis", {}).get("keywords", [])) + "\n\n"

        plan_text_block = ""
        if st.session_state.plan_markdown:
            st.markdown("### 실시 계획 및 학생부 예시 문구 (미리보기)")
            st.markdown(st.session_state.plan_markdown)
            plan_text_block = st.session_state.plan_markdown

        full_text_for_pdf = analysis_text_block + "\n\n" + plan_text_block

        if full_text_for_pdf.strip():
            file_name = f"{student_name}_학생부분석.pdf" if 'student_name' in locals() and student_name else "학생부분석.pdf"
            pdf_bytes = generate_pdf_from_text(
                f"{student_name} 학생부 분석 및 활동 계획" if 'student_name' in locals() and student_name else "학생부 분석 및 활동 계획",
                full_text_for_pdf,
            )

            st.download_button(
                label="결과 PDF 다운로드",
                data=pdf_bytes,
                file_name=file_name,
                mime="application/pdf",
            )
        else:
            st.info("분석 결과 또는 실시 계획이 있을 때 PDF로 다운로드할 수 있습니다.")


if __name__ == "__main__":
    main()
