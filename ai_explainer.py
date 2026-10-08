import streamlit as st
from openai import OpenAI


def _client():
    """
    Streamlit Cloud의 Secrets에서 API 키를 읽습니다.
    GitHub 코드에 API 키를 직접 넣지 마세요.
    """
    api_key = st.secrets["OPENAI_API_KEY"]
    return OpenAI(api_key=api_key)


def _pct(value):
    return f"{value:.1%}"


def _money_m(value):
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value) / 1_000_000:,.2f}m"


def explain_result(ctx):
    """
    BlueWave 계산엔진이 산출한 수치를 AI가 '해석'만 합니다.
    AI가 보호수준이나 손익 값을 다시 계산하지 않도록 프롬프트에서 명확히 제한합니다.
    """
    feasible_text = (
        "현재 계산범위에서 목표 달성이 가능한 상태"
        if ctx["feasible"]
        else "시장위험을 100% 경제적으로 상쇄해도 현재 목표 달성이 어려운 상태"
    )

    prompt = f"""
당신은 해운사의 운임·연료비 시장위험을 경영진에게 설명하는 리스크 분석 보조자입니다.

중요한 원칙:
1. 아래 숫자는 별도의 정량 계산엔진이 이미 계산한 확정 입력값입니다.
2. 숫자를 새로 계산하거나 수정하거나 추정하지 마세요.
3. 미래 운임을 예측한다고 표현하지 마세요.
4. P20/P10/P5는 미래 발생확률이 아니라 과거 동일 기간의 실제 공동시장경로 중
   어느 정도 불리한 경로를 대표 Downside로 선택했는지를 뜻합니다.
5. '경제적 보호수준'은 실제 FFA 계약비율, 계약수량 또는 실행 권고가 아닙니다.
6. 전문용어를 최소화하고 비전문 경영자가 이해할 수 있게 설명하세요.
7. 지나치게 확정적인 투자·거래 지시는 하지 마세요.

[분석 조건]
- 분석기간: {ctx["period_months"]}개월
- 위험허용수준: {ctx["risk_level"]}
- 경영진 최소 공헌이익 유지 목표: {_pct(ctx["target_retention"])}
- 대표 과거 공동시장경로: {ctx["historical_path"]}

[계산엔진 결과]
- 기존 포트폴리오 공헌이익 유지율: {_pct(ctx["old_retention"])}
- 신규계약 추가 후 공헌이익 유지율: {_pct(ctx["new_retention"])}
- 기존 Downside 손실폭: {_money_m(ctx["old_downside_loss"])}
- 신규계약 추가 후 Downside 손실폭: {_money_m(ctx["new_downside_loss"])}
- 신규계약으로 증가한 Downside: {_money_m(ctx["incremental_downside"])}
- 전체 Downside 중 신규계약 위험기여율: {_pct(ctx["new_contract_risk_share"])}
- 경영목표 대비 부족액: {_money_m(ctx["shortage"])}
- 최소 필요 경제적 보호수준: {_pct(ctx["required_protection"])}
- 가장 큰 공헌이익 훼손요인: {ctx["top_risk"]}
- 손실을 상쇄한 자연상계/우호요인: {ctx["offset_factors"]}
- 목표 달성 가능 여부: {feasible_text}

다음 형식으로 한국어 5~7문장으로 설명하세요.

첫째, 현재 위험수준을 한 문장으로 요약합니다.
둘째, 신규계약이 기존 포트폴리오와 비교해 위험을 어떻게 바꿨는지 설명합니다.
셋째, 왜 현재 최소 필요 경제적 보호수준이 산출됐는지 경영목표와 연결해 설명합니다.
넷째, 가장 중요한 손익 훼손요인과 자연상계 요인이 있다면 설명합니다.
다섯째, 경영진이 이 결과를 어떻게 해석해야 하는지 설명합니다.
마지막에는 반드시 이 보호수준이 실제 FFA 계약비율이나 거래 실행안이 아니라는 점을 짧게 밝힙니다.

제목이나 불릿 없이 자연스러운 문단 하나로 작성하세요.
"""

    client = _client()
    response = client.responses.create(
        model=st.secrets.get("OPENAI_MODEL", "gpt-5.6-luna"),
        reasoning={"effort": "low"},
        input=prompt,
    )
    return response.output_text
