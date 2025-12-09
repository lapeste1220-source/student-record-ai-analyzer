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

# ⚠ 길이/토큰 제한 (속도 문제 해결용)
MAX_PDF_CHARS = 8000          # PDF에서 앞부분 8,000자만 사용
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
