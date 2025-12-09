import streamlit as st
import pdfplumber
from openai import OpenAI
import json

from utils import (
    parse_student_record,
    extract_books,
    generate_html_report,
)
from analysis import run_gpt_analysis, summarize_book


# -------------------------------------------------------
# 기본 설정
# -------------------------------------------------------
st.set_page_config(page_title="함창고 학생 분석 시스템", layout="wide")


# -------------------------------------------------------
# 보안용 암호 입력
# -------------------------------------------------------
st.sidebar.header("접속 인증")

password = st.sidebar.text_input("접속 암호", type="password")

if "ADMIN_PASSWORD" not in st.secrets:
    st.error("관리자 비밀번호(ADMIN_PASSWORD)가 Streamlit Secrets에 설정되지 않았습니다.")
    st.stop()

if password != st.secrets["ADMIN_PASSWORD"]:
    st.sidebar.warning("올바른 암호를 입력해야 시스템이 실행됩니다.")
    st.stop()

client = OpenAI(api_key=st.secrets["OPENAI_KEY"])


# -------------------------------------------------------
# 학과 목록 (고정 20개 정식 버전)
# -------------------------------------------------------
MAJOR_LIST = [
    "컴퓨터·소프트웨어",
    "데이터사이언스",
    "AI·인공지능",
    "전기전자공학",
    "기계공학",
    "화학·화학공학",
    "생명과학·생명공학",
    "재료·신소재공학",
    "환경·에너지",
    "건축학",
    "산업공학",
    "수학",
    "물리학",
    "화학",
    "경영학",
    "경제학",
    "사회·행정학",
    "정치외교학",
    "언론·미디어",
    "교육학",
    "심리학",
    "디자인학",
    "의학",
    "치의학",
    "약학",
    "한의학",
    "교대",
    "과학특성화",
]


# -------------------------------------------------------
# 로그인 처리
# -------------------------------------------------------
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.title("함창고 학생 분석 시스템")

    name = st.text_input("성명", placeholder="예: 홍길동")

    if st.button("로그인") and name.strip() != "":
        st.session_state.user = {"name": name.strip()}
        st.experimental_rerun()

    st.stop()

st.sidebar.success(f"{st.session_state.user['name']}님 로그인됨")


# -------------------------------------------------------
# PDF 업로드
# -------------------------------------------------------
st.header("1. 생활기록부 PDF 업로드")

uploaded_pdf = st.file_uploader("PDF 업로드", type=["pdf"])

if uploaded_pdf:
    with pdfplumber.open(uploaded_pdf) as pdf:
        text = "\n".join([page.extract_text() or "" for page in pdf.pages])

    st.session_state.raw = text
    st.success("PDF 텍스트 추출 완료!")


# -------------------------------------------------------
# 희망 학과 선택
# -------------------------------------------------------
st.header("2. 희망 학과 선택")

if uploaded_pdf:
    target_major = st.selectbox("희망 학과", MAJOR_LIST, index=0)
else:
    st.info("PDF를 먼저 업로드하세요.")
    st.stop()


# -------------------------------------------------------
# 분석 시작
# -------------------------------------------------------
if st.button("분석 시작"):

    if "raw" not in st.session_state:
        st.error("먼저 PDF를 업로드하세요.")
        st.stop()

    with st.spinner("AI 분석 중입니다..."):

        sections = parse_student_record(st.session_state.raw)
        books = extract_books(st.session_state.raw)

        gpt_result = run_gpt_analysis(
            client=client,
            sections=sections,
            target_major=target_major,
        )

        book_results = []
        for b in books:
            summary = summarize_book(client, b)
            book_results.append({
                "title": b["title"],
                "author": b["author"],
                "summary": summary
            })

        st.session_state.analysis = gpt_result
        st.session_state.books = book_results


# -------------------------------------------------------
# 결과 출력
# -------------------------------------------------------
if "analysis" in st.session_state:
    st.header("3. 분석 결과")

    st.subheader("📝 종합 분석 결과")
    st.write(st.session_state.analysis)

    st.subheader("📚 독서활동 분석")
    for b in st.session_state.books:
        st.markdown(f"### 📘 {b['title']} — {b['author']}")
        st.write("\n".join(b["summary"]["summary_text"]))
        st.write("**전공 연계:**")
        st.write("\n".join(b["summary"]["major_links"]))
        st.write("**프로젝트 제안:**")
        st.write("\n".join(b["summary"]["projects"]))
        st.markdown("---")

    st.subheader("📥 HTML 리포트 다운로드")
    html_bytes = generate_html_report(
        st.session_state.user,
        st.session_state.analysis,
        st.session_state.books
    )

    st.download_button(
        "HTML 리포트 다운로드",
        html_bytes,
        file_name="analysis_report.html",
        mime="text/html"
    )
