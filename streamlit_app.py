import streamlit as st
import pdfplumber
import json
from openai import OpenAI

from utils import (
    parse_student_record,
    extract_books,
    generate_html_report
)
from analysis import run_gpt_analysis, summarize_book


# ---------------------
# 기본 설정
# ---------------------
st.set_page_config(page_title="함창고 학생 분석 시스템", layout="wide")

client = OpenAI(api_key=st.secrets["OPENAI_KEY"])


# ---------------------
# 로그인 (이름만 입력)
# ---------------------
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.title("함창고 학생 분석 시스템")

    name = st.text_input("학생 이름을 입력하세요")

    if st.button("시작"):
        if len(name.strip()) == 0:
            st.warning("이름을 입력해야 합니다.")
            st.stop()
        st.session_state.user = {"name": name}

    st.stop()

st.sidebar.success(f"{st.session_state.user['name']} 학생 접속 중")


# ---------------------
# PDF 업로드
# ---------------------
st.header("1. 생활기록부 PDF 업로드")
uploaded_pdf = st.file_uploader("PDF 업로드", type=["pdf"])

if uploaded_pdf:
    with pdfplumber.open(uploaded_pdf) as pdf:
        text = "\n".join([page.extract_text() or "" for page in pdf.pages])

    st.session_state.raw = text
    st.success("PDF 업로드 완료!")


# ---------------------
# 학과 리스트
# ---------------------
majors = [
    "컴퓨터·소프트웨어", "인공지능", "생명·바이오", "화학·신소재", "기계·항공",
    "전기전자", "에너지", "수학·통계", "물리", "지구·환경",
    "경제", "경영", "교육", "심리",
    "정치외교", "행정", "사회학", "미디어·광고",
    "역사", "철학",
    "의대", "약대", "치대", "한의대", "간호",
    "과학특성화(UST·UNIST·GIST·DGIST)"
]


# ---------------------
# 희망 학과 선택
# ---------------------
if "raw" in st.session_state:
    st.header("2. 희망 학과 선택")

    target_major = st.selectbox("희망 학과", majors)

    if st.button("분석 시작"):
        with st.spinner("AI 분석 중입니다..."):

            # 생기부 자동 분리
            sections = parse_student_record(st.session_state.raw)

            # 독서 자동 추출
            books = extract_books(st.session_state.raw)

            # 종합 GPT 분석
            ai_result = run_gpt_analysis(
                client,
                sections=sections,
                target_major=target_major
            )

            # 책 분석
            book_results = []
            for b in books:
                summary = summarize_book(client, b)
                book_results.append({
                    "title": b["title"],
                    "author": b["author"],
                    "summary": summary
                })

            st.session_state.analysis = ai_result
            st.session_state.books = book_results
            st.session_state.major = target_major


# ---------------------
# 분석 결과 출력
# ---------------------
if "analysis" in st.session_state:

    st.header("3. 분석 결과")

    st.subheader("🎯 전공 적합성 종합 분석")
    st.write(st.session_state.analysis["overall"])

    st.subheader("📌 핵심 역량 분석")
    st.write(st.session_state.analysis["strengths"])

    st.subheader("📘 비교과·세특 패턴 분석")
    st.write(st.session_state.analysis["patterns"])

    st.subheader("🧠 추천 심화 탐구·프로젝트")
    st.write(st.session_state.analysis["projects"])

    # 독서 분석
    st.subheader("📚 독서 기반 전공 연계 분석")
    for b in st.session_state.books:
        st.markdown(f"### 📘 {b['title']} — {b['author']}")
        st.write("\n".join(b["summary"]["summary_text"]))
        st.write("**전공 연계:**")
        st.write("\n".join(b["summary"]["major_links"]))
        st.write("**추천 프로젝트:**")
        st.write("\n".join(b["summary"]["projects"]))
        st.markdown("---")

    # 마인드맵(JSON)
    st.subheader("🧩 마인드맵(JSON)")
    st.json(json.loads(st.session_state.analysis["mindmap"]))

    # HTML 다운로드
    st.subheader("📥 HTML 보고서 다운로드")
    html_bytes = generate_html_report(
        st.session_state.user,
        st.session_state.analysis,
        st.session_state.books
    )

    st.download_button(
        "보고서 다운로드 (HTML)",
        html_bytes,
        file_name="student_analysis_report.html",
        mime="text/html"
    )
