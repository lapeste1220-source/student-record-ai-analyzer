import streamlit as st
import pdfplumber
import json
from openai import OpenAI
import streamlit.components.v1 as components

from utils import (
    parse_student_record,
    extract_books,
    generate_html_report,
    admin_zip_download
)
from analysis import run_gpt_analysis, summarize_book


# ==============================
# 기본 설정
# ==============================
st.set_page_config(page_title="AI 생기부 분석 시스템", layout="wide")


# ==============================
# 관리자 인증
# ==============================
st.sidebar.header("접속 인증")

password = st.sidebar.text_input("접속 암호", type="password")

if password != st.secrets["ADMIN_PASSWORD"]:
    st.sidebar.warning("올바른 암호를 입력해야 시스템이 실행됩니다.")
    st.stop()

client = OpenAI(api_key=st.secrets["OPENAI_KEY"])


# ==============================
# 학과 패턴 DB 로드
# ==============================
@st.cache_data
def load_admit_profiles():
    with open("config/admit_profiles.json", "r", encoding="utf-8") as f:
        return json.load(f)

admit_profiles = load_admit_profiles()


# ==============================
# 패턴 점수 계산
# ==============================
def calculate_pattern_match(student_text, major):

    profile = admit_profiles.get(major, None)
    if not profile:
        return None

    def score_keywords(keywords):
        return sum(kw in student_text for kw in keywords) / max(len(keywords), 1)

    result = {
        "핵심역량": score_keywords(profile.get("핵심역량", [])),
        "세특 패턴": score_keywords(profile.get("세특패턴", [])),
        "탐구 패턴": score_keywords(profile.get("탐구·프로젝트 패턴", [])),
        "독서 패턴": score_keywords(profile.get("독서 패턴", [])),
        "비교과 패턴": score_keywords(profile.get("비교과 패턴", [])),
    }

    result["총합 점수"] = (
        result["핵심역량"] * 0.30 +
        result["세특 패턴"] * 0.30 +
        result["탐구 패턴"] * 0.20 +
        result["독서 패턴"] * 0.10 +
        result["비교과 패턴"] * 0.10
    )

    return result


# ==============================
# 로그인
# ==============================
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.title("AI 기반 생기부 분석 시스템")

    name = st.text_input("이름")
    school = st.text_input("학교명")
    year = st.number_input("학년도", value=2025)

    if st.button("로그인"):
        st.session_state.user = {"name": name, "school": school, "year": year}

    st.stop()

st.sidebar.success(f"{st.session_state.user['name']}님 로그인됨")


# ==============================
# 관리자 ZIP
# ==============================
st.sidebar.subheader("관리자 메뉴")
if st.sidebar.checkbox("ZIP 다운로드"):
    st.title("관리자 다운로드")
    if st.button("전체 ZIP 생성"):
        path = admin_zip_download()
        with open(path, "rb") as f:
            st.download_button("ZIP 다운로드", f, file_name="all_reports.zip")
    st.stop()


# ==============================
# PDF 업로드
# ==============================
st.header("1. 생활기록부 PDF 업로드")

uploaded_pdf = st.file_uploader("PDF 업로드", type=["pdf"])

if uploaded_pdf:
    with pdfplumber.open(uploaded_pdf) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    st.session_state.raw = text
    st.success("PDF 텍스트 추출 완료!")


# ==============================
# 학과 선택
# ==============================
st.header("2. 희망 학과 선택")

all_majors = list(admit_profiles.keys())
target_major = st.selectbox("희망 학과", all_majors)


# ==============================
# 분석 실행
# ==============================
if st.button("분석 시작"):

    if "raw" not in st.session_state:
        st.error("PDF를 먼저 업로드하세요.")
        st.stop()

    st.session_state.pattern_result = calculate_pattern_match(
        st.session_state.raw,
        target_major
    )

    with st.spinner("AI 분석 중..."):

        sections = parse_student_record(st.session_state.raw)
        books = extract_books(st.session_state.raw)

        gpt_result = run_gpt_analysis(
            client=client,
            sections=sections,
            target_univ=None,
            target_major=target_major,
            target_values=None
        )

        book_results = []
        for b in books:
            summary = summarize_book(client, b)
            book_results.append({
                "title": b["title"],
                "author": b["author"],
                "summary": summary,
            })

        st.session_state.analysis = gpt_result
        st.session_state.books = book_results


# ==============================
# 분석 결과 출력
# ==============================
if "analysis" in st.session_state:

    st.header("3. 분석 결과")

    st.subheader("🎯 학과 패턴 매칭 점수")
    st.write(st.session_state.pattern_result)

    st.subheader("📝 종합 분석 결과")
    st.write(st.session_state.analysis)

    st.subheader("📚 독서활동 분석")
    for b in st.session_state.books:
        st.markdown(f"### 📘 {b['title']} — {b['author']}")
        st.write("\n".join(b["summary"].get("summary_text", [])))
        st.write("\n".join(b["summary"].get("major_links", [])))
        st.write("\n".join(b["summary"].get("projects", [])))
        st.markdown("---")

    html_bytes = generate_html_report(
        st.session_state.user,
        st.session_state.analysis,
        st.session_state.books
    )

    st.download_button(
        "📥 HTML 리포트 다운로드",
        html_bytes,
        file_name="analysis_report.html",
        mime="text/html"
    )
