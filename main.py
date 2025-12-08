import json

@st.cache_data
def load_admit_profiles():
    with open("config/admit_profiles.json", "r", encoding="utf-8") as f:
        return json.load(f)

admit_profiles = load_admit_profiles()

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


    st.subheader("🧠 마인드맵 시각화")
    display_mindmap(st.session_state.analysis["mindmap"])
   
    # PDF 저장
    if st.button("PDF 저장"):
        pdf_bytes = generate_pdf(
            st.session_state.user,
            st.session_state.analysis,
            st.session_state.books
        )
        st.download_button("PDF 다운로드", pdf_bytes, file_name="analysis.pdf")
from pyvis.network import Network
import json
import streamlit.components.v1 as components


def display_mindmap(mindmap_json):
    """
    GPT가 생성한 마인드맵 JSON을 pyvis 네트워크 그래프로 렌더링
    """

    # JSON 문자열을 dict로 변환
    data = json.loads(mindmap_json)

    net = Network(height="600px", width="100%", bgcolor="#FFFFFF", font_color="black")

    net.add_node("학생부 핵심구조", shape="ellipse", color="#FFB347")

    # 1차 노드: summary, strengths, weaknesses, activities
    net.add_node("요약", color="#77DD77")
    net.add_edge("학생부 핵심구조", "요약")

    net.add_node("강점", color="#AEC6CF")
    net.add_edge("학생부 핵심구조", "강점")

    net.add_node("약점", color="#FF6961")
    net.add_edge("학생부 핵심구조", "약점")

    net.add_node("활동", color="#FDFD96")
    net.add_edge("학생부 핵심구조", "활동")

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

    # HTML 생성
    net.set_options('''
        var options = {
          "edges": {"smooth": false},
          "physics": {"enabled": true}
        }
    ''')

    html = net.generate_html("mindmap.html")
def calculate_pattern_match(student_text, university, major):
    profile = admit_profiles.get(university, {}).get(major, {})
    if not profile:
        return None

    def score_keywords(keywords):
        score = 0
        for kw in keywords:
            if kw in student_text:
                score += 1
        return score / max(len(keywords), 1)

    result = {
        "핵심역량 점수": score_keywords(profile.get("핵심역량", [])),
        "세특 패턴 점수": score_keywords(profile.get("세특패턴", [])),
        "탐구 패턴 점수": score_keywords(profile.get("탐구·프로젝트 패턴", [])),
        "독서 패턴 점수": score_keywords(profile.get("독서 패턴", [])),
        "비교과 패턴 점수": score_keywords(profile.get("비교과 패턴", [])),
    }

    # 총점 (가중치 조정 가능)
    result["총합 점수"] = (
        result["핵심역량 점수"] * 0.30 +
        result["세특 패턴 점수"] * 0.30 +
        result["탐구 패턴 점수"] * 0.20 +
        result["독서 패턴 점수"] * 0.10 +
        result["비교과 패턴 점수"] * 0.10
    )

    return result

    # Streamlit에 표시
    components.html(html, height=650, scrolling=True)
