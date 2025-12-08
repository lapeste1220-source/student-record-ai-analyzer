def parse_student_record(text):
    """
    학생부 PDF에서 주요 항목을 자동 분리하는 정규식 엔진 (개선 버전)
    """

    patterns = {
        "자율활동": r"자율활동([\s\S]*?)동아리활동",
        "창체동아리": r"동아리활동([\s\S]*?)진로활동",
        "진로활동": r"진로활동([\s\S]*?)창의적 체험활동상황",
        "교과학습발달상황": r"교과학습발달상황([\s\S]*?)세부능력 및 특기사항",
        "교과별 세부능력 특기사항": r"세부능력 및 특기사항([\s\S]*?)독서활동",
        "독서활동": r"독서활동([\s\S]*?)행동특성 및 종합의견",
        "행동특성및종합의견": r"행동특성 및 종합의견([\s\S]*)"
    }

    result = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            extracted = match.group(1).strip()
        else:
            extracted = "(해당 항목 없음)"
        result[key] = extracted

    return result
