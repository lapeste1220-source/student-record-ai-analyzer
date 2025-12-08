import streamlit as st
import pdfplumber
from openai import OpenAI
import json
from pyvis.network import Network
import streamlit.components.v1 as components

from utils import (
    parse_student_record,
    extract_books,
    generate_html_report,
    admin_zip_download
)

from analysis import run_gpt_analysis, summarize_book


# -------------------------------------------------------
# Streamlit 기본 설정
# -------------------------------------------------------
st.set_page_config(page_title="AI 생기부 분석 시스템", layout="wide")


# -------------------------------------------------------
# 암호 입력 (선생님 전용 보안)
# -------------------------------------------------------
st.sidebar.header("접속 인증")
password = st.sidebar.text_input("접속 암호 입력", type="password")

if password != st.secrets["ADMIN_PASSWORD"]:
    st.sidebar.warning("올바른 암호를 입력해야 시스템이 활성화됩니다.")
    st.stop()

# 암호가 맞으면 OpenAI 클라이언트 활성화
client = OpenAI(api_key=st.secrets["OPENAI_KEY"])


# -------------------------------------------------------
# 합격 패턴 DB 로드
# -------------------------------------------------------
@st.cache_data
def load_admit_profiles():
    with open("config/admit_profiles.json", "r", encoding="utf-8") as f:
        return json.load(f)

admit_profiles = load_admit_profiles()


# -------------------------------------------------------
# 패턴 점수 계산 함수
# -------------------------------------------------------
def calculate_pattern_match(student_text, university, major):
    profile = admit_profiles.get(university, {}).get(major, {})
    if not profile:
        return None

    def score_keywords(keywords):
        return sum(kw in student_text for kw in keywords) / max(len(keywords), 1)

    result = {
        "핵심역량 점수": score_keywords(profile.get("핵심역량", [])),
        "세특 패턴 점수": score_keywords(profile.get("세특패턴", [])),
        "탐구 패턴 점수": score_keywords(profile.get("탐구·프로젝트 패턴", [])),
        "독서 패턴 점수": score_keywords(profile.get("독서 패턴", [])),
        "비교과 패턴 점수": score_keywords(profile.get("비교과 패턴", [])),
    }

    result["총합 점수"] = (
        result["핵심역량 점수"] * 0.30 +
        result["세특 패턴 점수"] * 0.30 +
        result["탐구 패턴 점수"] * 0.20 +
        result["독서 패턴 점수"] * 0.10 +
        result["비교과 패턴 점수"] * 0.10
    )

    return result


# -------------------------------------------------------
# 마인드맵 시각화 함수
# -------------------------------------------------------
def display_mindmap(mindmap_json):
    data = json.loads(mindmap_json)

    net = Network(height="600px", width="100%", bgcolor="#FFFFFF", font_color="black")
    net.add_node("학생부 핵심구조", shape="ellipse", color="#FFB347")

    keys = ["summary", "strengths", "weaknesses", "activities"]
    colors = ["#77DD77", "#AEC6CF", "#FF6961", "#FDFD96"]
    labels = ["요약", "강점", "약점", "활동"]

    for label, key, color in zip(labels, keys, colors):
        net.add_node(label, color=color)
        net.add_edge("학생부 핵심구조", label)

    # summary
    net.add_node(data["summary"], shape="box")
    net.add_edge("요약", data["summary"])

    # strengths
    for s in data["strengths"]:
        net.add_node(s, color="#ADD8E6")
        net.add_edge("강점", s)

    # weaknesses
    for w in data["weaknesses"]:
        net.add_node(w, color="#FFB6B6")
        net.add_edge("약점", w)

    # activities
    for key, items in data["activities"].items():
        net.add_node(key, color="#FFF380")
        net.add_edge("활동", key)
        for item in items:
            net.add_node(item, shape="box")
            net.add_edge(key, item)

    return net.generate_html("mindmap.html")


# -------------------------------------------------------
# 로그인 처리
# -------------------------------------------------------
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.title("AI 기반 생기부 분석 시스템")

    name = st.text_input("이름")
    school = st.text_input("학교명")
    year = st.number_input("지원 학년도", value=2025)

    if st.button("로그인"):
        st.session_state.user = {"name": name, "school": school, "year": year}

    st.stop()

st.sidebar.success(f"{st.session_state.user['name']}님 로그인됨")


# -------------------------------------------------------
# 관리자 페이지
# -------------------------------------------------------
st.sidebar.subheader("관리자 도구")
if st.sidebar.checkbox("관리자 ZIP 다운로드"):
    st.title("관리자 페이지")

    if st.button("전체 ZIP 다운로드"):
        zip_path = admin_zip_download()
        with open(zip_path, "rb") as z:
            st.download_button("ZIP 다운로드", z, file_name="all_reports.zip")

    st.stop()


# -------------------------------------------------------
# PDF 업로드
# -------------------------------------------------------
st.header("1. 생활기록부 업로드")
uploaded_pdf = st.file_uploader("PDF 파일 업로드", type=["pdf"])

if uploaded_pdf:
    with pdfplumber.open(uploaded_pdf) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    st.session_state.raw = text
    st.success("PDF 텍스트 추출 완료!")


# -------------------------------------------------------
# 희망 대학/학과 입력
# -------------------------------------------------------
st.header("2. 희망 대학·학과 입력")

target_univ = st.text_input("희망 대학")
target_major = st.text_input("희망 학과")
target_values = st.text_area("대학 인재상 또는 전형 요소")


# -------------------------------------------------------
# 분석 실행
# -------------------------------------------------------
if st.button("분석 시작"):

    st.session_state["pattern_result"] = calculate_pattern_match(
        st.session_state.raw, target_univ, target_major
    )

    with st.spinner("AI 분석 중..."):

        sections = parse_student_record(st.session_state.raw)
        books = extract_books(st.session_state.raw)

        gpt_result = run_gpt_analysis(
            client=client,
            sections=sections,
            target_univ=target_univ,
            target_major=target_major,
            target_values=target_values
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
# 분석 결과 출력
# -------------------------------------------------------
if "analysis" in st.session_state:
    st.header("3. 분석 결과")

    st.subheader("🎯 패턴 매칭 결과")
    st.write(st.session_state["pattern_result"])

    st.subheader("종합 분석 결과")
    st.write(st.session_state.analysis)

    st.subheader("📚 독서활동 분석")
    for b in st.session_state.books:
        st.markdown(f"### **{b['title']} — {b['author']}**")
        st.markdown("---")
        st.write("\n".join(b["summary"]["summary_text"]))
        st.write("**전공 연계:**")
        st.write("\n".join(b["summary"]["major_links"]))
        st.write("**프로젝트 제안:**")
        st.write("\n".join(b["summary"]["projects"]))
        st.markdown("---")

    st.subheader("🧠 마인드맵 시각화")
    html = display_mindmap(st.session_state.analysis["mindmap"])
    components.html(html, height=650, scrolling=True)

    # HTML 리포트 다운로드
    if st.button("리포트 저장 (HTML)"):
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
