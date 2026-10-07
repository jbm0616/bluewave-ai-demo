
import pandas as pd
import streamlit as st

from calc_engine import load_data, choose_scenario, metrics, protected_downside, priority_rows

st.set_page_config(
    page_title="BlueWave 신규계약 Downside 진단",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.block-container {padding-top:1.5rem; padding-bottom:2.5rem;}
.hero {font-size:2rem; font-weight:760; line-height:1.25; margin:.1rem 0 .35rem 0;}
.kicker {font-size:.82rem; color:#64748b; letter-spacing:.04em; text-transform:uppercase;}
.card {border:1px solid #e5e7eb;border-radius:14px;padding:16px;background:#fff;}
.small {font-size:.86rem;color:#64748b;}
</style>
""", unsafe_allow_html=True)

data = load_data()

# -------- 경영진 입력 --------
st.sidebar.header("경영진 입력")
period = st.sidebar.radio("분석기간", [3,6,12], index=1, format_func=lambda x:f"{x}개월", horizontal=True)
target_pct = st.sidebar.slider(
    "최소 공헌이익 유지율",
    min_value=80, max_value=100, value=95, step=1,
    help="분석시점 현재가격 기준 공헌이익(100%) 중 최소한 지키고 싶은 수준입니다."
)
risk = st.sidebar.selectbox(
    "위험허용수준",
    ["보통(P20)","보수적(P10)","매우 보수적(P5)"],
    index=1
)
st.sidebar.caption(
    "P20/P10/P5는 미래 확률예측이 아니라, 과거 동일 길이의 실제 공동시장경로 중 "
    "어느 정도 불리한 구간을 대표 Downside로 볼 것인지에 대한 선택입니다."
)

row = choose_scenario(data, period, risk)
m = metrics(row, target_pct/100)

# -------- Hero --------
st.markdown('<div class="kicker">Historical-path downside diagnosis · MVP</div>', unsafe_allow_html=True)
st.markdown('<div class="hero">🚢 BlueWave 신규계약 Downside 진단</div>', unsafe_allow_html=True)
st.write(
    "미래 운임을 예측하지 않고, 신규 계약이 회사 전체 시장위험을 얼마나 늘리는지 분석합니다. "
    "경영진이 기간·최소 공헌이익·위험허용수준을 정하면 이를 지키기 위해 필요한 경제적 보호수준과 우선 보호대상을 제시합니다."
)

c1,c2,c3,c4 = st.columns(4)
c1.metric("기준 공헌이익 (100%)", f"${row['new_base']/1e6:,.2f}m")
c2.metric("Downside 공헌이익", f"${row['new_down']/1e6:,.2f}m")
c3.metric("공헌이익 유지율", f"{m['new_retention']:.1%}")
req_text = f"{m['required_protection']:.1%}" if m["feasible"] else ">100%"
c4.metric("최소 필요 경제적 보호수준", req_text)

st.caption(
    "※ 기준 공헌이익(100%)은 분석시점 현재가격을 적용한 Base Case입니다. "
    "공헌이익 유지율은 Downside 공헌이익 ÷ 기준 공헌이익입니다. "
    "최소 필요 경제적 보호수준은 실제 FFA 계약비율을 뜻하지 않습니다."
)

if m["shortage"] <= 0:
    st.success(f"선택한 {risk} 경로에서도 최소 공헌이익 유지율 {target_pct}%를 이미 충족합니다. 추가 보호가 필수는 아닙니다.")
elif m["feasible"]:
    st.warning(
        f"{risk} 대표경로에서 목표 공헌이익까지 약 ${m['shortage']/1e6:,.2f}m 부족합니다. "
        f"시장위험의 약 {m['required_protection']:.1%}를 경제적으로 상쇄하면 목표 수준에 도달합니다."
    )
else:
    st.error("시장위험을 100% 경제적으로 상쇄해도 현재 입력한 목표 수준을 달성하기 어렵습니다.")

# -------- Tabs --------
t1,t2,t3,t4 = st.tabs(["신규계약 전·후", "Need 진단", "보호 우선순위", "MVP 범위"])

with t1:
    st.subheader("신규계약이 회사 전체 Downside를 얼마나 바꾸는가")
    comp = pd.DataFrame([
        {"구분":"기존 포트폴리오","기준 공헌이익":row["old_base"],"Downside 공헌이익":row["old_down"],
         "Downside 손실폭":m["old_downside_loss"],"공헌이익 유지율":m["old_retention"]},
        {"구분":"신규계약 추가 후","기준 공헌이익":row["new_base"],"Downside 공헌이익":row["new_down"],
         "Downside 손실폭":m["new_downside_loss"],"공헌이익 유지율":m["new_retention"]},
    ])
    st.dataframe(
        comp.style.format({
            "기준 공헌이익":"${:,.0f}",
            "Downside 공헌이익":"${:,.0f}",
            "Downside 손실폭":"${:,.0f}",
            "공헌이익 유지율":"{:.1%}"
        }),
        use_container_width=True, hide_index=True
    )

    a,b,c = st.columns(3)
    a.metric("신규계약 추가 Downside", f"${m['incremental_downside']/1e6:,.2f}m")
    b.metric("전체 Downside 중 신규계약 기여", f"{m['new_contract_risk_share']:.1%}")
    c.metric("대표 Historical Path", row["path"])
    st.info(
        "신규계약은 기준 공헌이익도 늘릴 수 있지만, 불리한 시장경로에서 하방손실폭을 더 크게 만들 수 있습니다. "
        "BlueWave는 계약의 수익 증가와 Downside 증가를 분리해 보여줍니다."
    )

with t2:
    st.subheader("경영목표를 지키기 위해 최소 얼마를 보호해야 하는가")
    target = row["new_base"] * target_pct/100
    need_df = pd.DataFrame([
        {"항목":"기준 공헌이익 (100%)","값":row["new_base"]},
        {"항목":f"{risk} Downside 공헌이익","값":row["new_down"]},
        {"항목":f"경영진 최소 목표 ({target_pct}%)","값":target},
        {"항목":"목표 대비 부족액","값":m["shortage"]},
    ])
    st.dataframe(need_df.style.format({"값":"${:,.0f}"}), use_container_width=True, hide_index=True)

    levels = [0,.30,.50,.70,1.0]
    rows=[]
    for p in levels:
        v=protected_downside(row,p)
        rows.append({
            "경제적 보호수준":p,
            "보호 후 Downside 공헌이익":v,
            "공헌이익 유지율":v/row["new_base"],
            "목표 충족":v>=target
        })
    sdf=pd.DataFrame(rows)
    st.dataframe(
        sdf.style.format({
            "경제적 보호수준":"{:.0%}",
            "보호 후 Downside 공헌이익":"${:,.0f}",
            "공헌이익 유지율":"{:.1%}"
        }),
        use_container_width=True, hide_index=True
    )
    st.caption(
        f"현재 선택조건에서 계산되는 연속형 최소 필요 보호수준은 약 {m['required_protection']:.1%}입니다. "
        "30/50/70/100%는 이해를 위한 비교안입니다."
    )

with t3:
    st.subheader("어떤 시장위험부터 보호를 검토해야 하는가")
    p = pd.DataFrame(priority_rows(row))
    show = p[["위험요인","영향","우선순위","판단","설명"]].copy()
    show["우선순위"] = show["우선순위"].apply(lambda x:"-" if pd.isna(x) else int(x))
    st.dataframe(
        show.style.format({"영향":"${:,.0f}"}),
        use_container_width=True, hide_index=True
    )

    losses = p[p["영향"]<0].sort_values("보호검토손실",ascending=False)
    if len(losses):
        top=losses.iloc[0]
        st.success(f"현재 선택한 Historical Path에서는 **{top['위험요인']}**가 가장 큰 공헌이익 훼손요인으로 나타납니다.")
    positives = p[p["영향"]>=0]
    if len(positives):
        names=", ".join(positives["위험요인"].tolist())
        st.info(f"{names}는 같은 시장경로에서 손실을 일부 상쇄하는 자연상계/우호요인으로 작용합니다.")

with t4:
    st.subheader("현재 MVP가 하는 것과 하지 않는 것")
    st.markdown("""
**현재 MVP**
- 신규계약 추가 전·후의 Downside 비교
- 3·6·12개월 실제 과거 공동시장경로를 활용한 변동성 반영
- 경영진 Risk Limit과 Downside 공헌이익 비교
- 최소 필요 **경제적 보호수준** 산출
- 위험요인별 손실기여도와 보호 우선순위 제안

**후속 고도화**
- 실제 FFA Forward Curve 및 월물 연결
- Spot–FFA Basis Risk와 Hedge Ratio
- 계약수량·월물·진입시점 제안
- 실제 VLSFO/Marine Fuel 파생상품 데이터
- 거래비용·증거금·금융비용·결제시차
""")
    st.info(
        "현재 모델은 미래 가격을 맞히는 예측모형이 아닙니다. 분석시점 현재가격을 기준으로, "
        "과거에 실제로 함께 움직였던 시장경로를 미래 불확실성의 Stress 시나리오로 재사용합니다."
    )

st.divider()
st.caption(
    f"MVP 기준시점: {data['meta']['market_base']} · 신규계약: {data['meta']['new_contract']} · "
    "실제 FFA 실행비율/월물/수량은 후속 고도화"
)
