import streamlit as st
import pdfplumber

st.set_page_config(page_title="함창고 학생 분석 시스템", layout="wide")

st.title("함창고 학생 분석 시스템")

# PDF 업로드
uploaded_pdf = st.file_uploader("PDF 업로드", type=["pdf"])

if uploaded_pdf:
    st.success("PDF 업로드 완료!")

    # PDF 텍스트 추출
    try:
        with pdfplumber.open(uploaded_pdf) as pdf:
            text = "\n".join([page.extract_text() or "" for page in pdf.pages])

        st.subheader("PDF 텍스트 미리보기")
        st.text_area("추출된 텍스트", text, height=400)

    except Exception as e:
        st.error(f"PDF 처리 중 오류 발생: {e}")
