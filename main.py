import streamlit as st
import pdfplumber
from openai import OpenAI

from utils import parse_student_record, extract_books, generate_pdf, admin_zip_download
from analysis import run_gpt_analysis, summarize_book

st.set_page_config(page_title="AI 생기부 분석 시스템", layout="wide")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


# -------------------------
# 로그인
# -------------------------
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.title("AI 기반 생기부 분석 시스템")

    name = st.text_input("이름")
    school = st.text_input("학교명")
    year = st.number_input("지원 학년도", value=2025, step=1)

    if st.button("로그인"):
        st.session_state.user = {
            "name": name,
            "school": school,
            "year": year,
        }
    st.stop()

st.sidebar.success(f"{st.session_state.user['name']}님 로그인됨")


# -------------------------
# 관리자 페이지
# -------------------------
st.sidebar.subheader("관리자")
if st.sidebar.checkbox("관리자 페이지 열기"):
    st.title("관리자 페이지")

    if st.button("전체 ZIP 다운로드"):
        zip_path = admin_zip_download()
        with open(zip_path, "rb") as z:
            st.download_button("ZIP 다운로드", z, file_name="all_reports.zip")

    st.stop()


# -------------------------
# 생기부 업로드
# -------------------------
st.header("1. 생활기록부 업로드")
uploaded_pdf = st.file_uploader("PDF 업로드", type=["pdf"])

if uploaded_pdf:
    with pdfplumber.open(uploaded_pdf) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() + "\n"

    st.session_state.raw = text
    st.success("PDF 텍스트 추출 완료!")


# -------------------------
# 분석 조건 입력
# -------------------------
st.header("2. 희망 대학·학과 입력")

target_univ = st.text_input("희망 대학")
target_major = st.text_input("희망 학과")
target_values = st.text_area("대학 인재상 또는 전형 평가 요소")


if st.button("분석 시작"):
    with st.spinner("AI 분석 중..."):

        sections = parse_student_record(st.session_state.raw)
        books = extract_books(st.session_state.raw)

        # GPT 종합 분석
        gpt_result = run_gpt_analysis(
            client=client,
            sections=sections,
            target_univ=target_univ,
            target_major=target_major,
            target_values=target_values
        )

        # 독서 분석 수행
        book_results = []
        for b in books:
            summary = summarize_book(client, b)
            book_results.append({"title": b["title"], "author": b["author"], "summary": summary})

        st.session_state.analysis = gpt_result
        st.session_state.books = book_results



# -------------------------
# 분석 결과 출력
# -------------------------
if "analysis" in st.session_state:
    st.header("3. 분석 결과")

    st.subheader("종합 분석 결과")
    st.write(st.session_state.analysis)

    st.subheader("📚 독서활동 분석")

    for b in st.session_state.books:
        with st.container():
            st.markdown(f"### **{b['title']} — {b['author']}**")
            st.markdown("---")
            st.write("\n".join(b["summary"]["summary_text"]))
            st.write("**전공 연계:**")
            st.write("\n".join(b["summary"]["major_links"]))
            st.write("**프로젝트 제안:**")
            st.write("\n".join(b["summary"]["projects"]))
            st.markdown("---")

    # PDF 저장
    if st.button("PDF 저장"):
        pdf_bytes = generate_pdf(
            st.session_state.user,
            st.session_state.analysis,
            st.session_state.books
        )
        st.download_button("PDF 다운로드", pdf_bytes, file_name="analysis.pdf")
