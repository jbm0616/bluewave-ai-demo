from pathlib import Path
import pandas as pd
import streamlit as st

from calc_engine import (
    load_model, historical_stress, monthly_market_shocks, cashflow,
    strategy_summary, required_protection, explain
)

st.set_page_config(
    page_title="BlueWave AI 해운 리스크 의사결정",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Style ----------
st.markdown("""
<style>
.block-container {padding-top: 1.6rem; padding-bottom: 2rem;}
.small-note {font-size: 0.88rem; color: #6b7280;}
.card {border:1px solid #e5e7eb; border-radius:14px; padding:18px; background:#ffffff; box-shadow:0 1px 2px rgba(0,0,0,.03);}
.good {border-left:5px solid #16a34a;}
.warn {border-left:5px solid #f59e0b;}
.bad {border-left:5px solid #dc2626;}
.kicker {font-size:.83rem; color:#64748b; text-transform:uppercase; letter-spacing:.05em;}
.hero {font-size:2.0rem; font-weight:750; line-height:1.2; margin:.2rem 0 .35rem 0;}
</style>
""", unsafe_allow_html=True)

model = load_model()
stress = historical_stress(model)

# ---------- Sidebar controls ----------
st.sidebar.header("시나리오 입력")
def m(v): return float(v)/1_000_000

def usd_m(label, default, minv=0.0, maxv=30.0, step=0.5, help=None):
    return st.sidebar.slider(label, minv, maxv, float(default), step, help=help) * 1_000_000

floor = usd_m("최소유동성 Floor ($m)", m(model["finance"]["liquidity_floor"]), 5.0, 20.0, 0.5)
external = usd_m("외부조달 가정 ($m)", m(model["finance"]["external_financing"]), 0.0, 12.0, 0.5,
                 "BlueWave 모형 가정. 6월·12월에 절반씩 유입되는 것으로 계산합니다.")
protection = st.sidebar.slider("검토 보호수준", 0, 100, 70, 5) / 100
st.sidebar.caption("보호수준은 시장충격 중 경제적으로 상쇄하려는 비율입니다. 실제 FFA 헤지비율·계약수량과는 다릅니다.")

req = required_protection(model, floor=floor, external_financing=external)
chosen = cashflow(model, protection, floor=floor, external_financing=external)
chosen_min = min(x["end_cash"] for x in chosen)
chosen_buffer = min(x["buffer"] for x in chosen)
chosen_miss = sum(1 for x in chosen if not x["meets_floor"])

# ---------- Hero ----------
st.markdown('<div class="kicker">AI-based shipping risk decision support · MVP</div>', unsafe_allow_html=True)
st.markdown('<div class="hero">🚢 BlueWave 해운 리스크 의사결정 시스템</div>', unsafe_allow_html=True)
st.write("운임·연료비 노출을 월별 현금흐름에 반영하고, 역사적 시장충격에서 최소유동성(Floor)을 지키기 위해 필요한 보호수준과 전략별 결과를 비교합니다.")

c1, c2, c3, c4 = st.columns(4)
c1.metric("무보호 Stress 예상손실", f"${-sum(x['total'] for x in monthly_market_shocks(model))/1e6:,.2f}m")
c2.metric("Floor 방어 최소 보호수준", f"{req['required']:.1%}" if req['feasible'] else ">100%")
c3.metric("선택 전략 최저현금", f"${chosen_min/1e6:,.2f}m")
c4.metric("최소유동성 버퍼", f"${chosen_buffer/1e6:,.2f}m")

st.caption("※ Floor 방어 최소 보호수준은 시장충격의 경제적 상쇄 비율이며, 실제 FFA 계약비율을 의미하지 않습니다.")

if chosen_miss == 0:
    st.success(f"선택한 {protection:.0%} 보호전략은 현재 가정에서 모든 월에 Floor를 충족합니다.")
else:
    st.warning(f"선택한 {protection:.0%} 보호전략은 Floor를 {chosen_miss}개월 충족하지 못합니다.")

st.info("실제 공시 재무상태와 공개 시장데이터에 합성 운영계약을 결합한 MVP입니다. 보호수준은 경제적 보호수준이며, 실제 FFA 헤지비율·계약수량·증거금·거래비용은 후속 고도화 단계에서 반영합니다.")

# ---------- Tabs ----------
t1, t2, t3, t4, t5 = st.tabs(["대시보드", "Exposure & Stress", "Need 진단", "전략 비교", "유동성 여력 / AI 설명"])

with t1:
    st.subheader("한눈에 보는 의사결정")
    rows = strategy_summary(model, floor=floor, external_financing=external)
    df = pd.DataFrame(rows)
    show = df[["label","protection","min_cash","miss_months","end_cash","min_buffer"]].copy()
    show.columns = ["전략","보호수준","최저 월말현금","Floor 미달개월","연말현금","최저 Floor 여유"]
    st.dataframe(show.style.format({
        "보호수준":"{:.0%}", "최저 월말현금":"${:,.0f}", "연말현금":"${:,.0f}", "최저 Floor 여유":"${:,.0f}"
    }), use_container_width=True, hide_index=True)

    chart_rows = []
    for p in [0,.3,.5,.7,1.0]:
        for r in cashflow(model,p,floor=floor,external_financing=external):
            chart_rows.append({"월":r["month"],"전략":f"{p:.0%}","월말현금":r["end_cash"]/1e6})
    cdf = pd.DataFrame(chart_rows)
    pivot = cdf.pivot(index="월", columns="전략", values="월말현금")
    st.line_chart(pivot)
    st.caption(f"현재 입력에서 최소 필요 보호수준은 약 {req['required']:.1%}이며, 제약 시점은 {req['binding_month']}입니다.")

with t2:
    st.subheader("노출 → 역사적 시장충격")
    exp = pd.DataFrame(model["exposures"])
    exp.columns = ["월","P5TC 노출(days)","PNW→Japan(t)","USG→Japan(t)","TC-in 노출(days)","연료(t)"]
    st.dataframe(exp, use_container_width=True, hide_index=True)

    a,b,c,d,e = st.columns(5)
    a.metric("Panamax 운임 하락 Proxy", f"{stress['A_down']:.1%}")
    b.metric("PNW 운임 하락", f"{stress['C1_down']:.1%}")
    c.metric("USG 운임 하락", f"{stress['C2_down']:.1%}")
    d.metric("TC-in 비용 상승", f"+{stress['D_up']:.1%}")
    e.metric("Brent 상승", f"+{stress['Fuel_up']:.1%}")

    shocks = pd.DataFrame(monthly_market_shocks(model))
    shocks["시장손실($m)"] = shocks["total"] / 1e6
    st.bar_chart(shocks.set_index("month")[["시장손실($m)"]])
    with st.expander("데이터·Proxy 정의"):
        st.write("• 운임·TC Stress는 2022-03~2025-12 공개 월별데이터의 10/90 분위수로 계산합니다.")
        st.write("• A(P5TC)는 실제 P5TC 역사시계열 대신 KOBC Panamax TC 변동률을 시장충격 Proxy로 사용합니다.")
        st.write("• 실물 연료는 VLSFO이지만, MVP에서는 $535/t 기준비용에 Brent 월간 상승률을 적용합니다.")
        st.write("• 서로 다른 노출은 무리하게 상계하지 않고 개별 충격 후 현금흐름에서 합산합니다.")

with t3:
    st.subheader("Need 진단 | 최소유동성을 지키려면 얼마나 보호해야 하는가?")
    nohedge = cashflow(model,0,floor=floor,external_financing=external)
    full = cashflow(model,1,floor=floor,external_financing=external)
    need_rows = []
    for n, b in zip(nohedge, full):
        market_loss = b["end_cash"] - n["end_cash"]
        if n["end_cash"] >= floor:
            rp = 0.0
        elif market_loss > 0:
            rp = max(0.0, (floor - n["end_cash"])/market_loss)
        else:
            rp = None
        need_rows.append({
            "월":n["month"], "무보호 현금":n["end_cash"], "100% 경제적 보호 시 현금":b["end_cash"],
            "Floor":floor, "필요 보호수준":rp
        })
    ndf = pd.DataFrame(need_rows)
    st.dataframe(ndf.style.format({
        "무보호 현금":"${:,.0f}","100% 경제적 보호 시 현금":"${:,.0f}","Floor":"${:,.0f}","필요 보호수준":lambda x: "-" if pd.isna(x) else f"{x:.1%}"
    }), use_container_width=True, hide_index=True)

    if req["feasible"]:
        st.success(f"현재 재무가정에서는 {req['binding_month']}이 제약 시점이며, Floor 방어에 필요한 최소 경제적 보호수준은 약 {req['required']:.1%}입니다.")
    else:
        st.error("시장위험을 전부 제거해도 Floor를 충족하지 못합니다. 헤지보다 구조적 유동성 보완이 먼저 필요합니다.")

with t4:
    st.subheader("전략 3안")
    ss = {x["protection"]:x for x in strategy_summary(model, floor=floor, external_financing=external)}
    cards = [(.30,"부분보호형","시장위험 일부 완화"),(.50,"최소방어형","Floor 충족을 목표"),(.70,"안정성 우선형","추가 유동성 버퍼 확보")]
    cols = st.columns(3)
    for col,(p,name,desc) in zip(cols,cards):
        x=ss[p]
        css = "good" if x["miss_months"]==0 else "bad"
        with col:
            st.markdown(f'<div class="card {css}"><b>{name}</b><br><span class="small-note">{desc}</span><hr>'
                        f'<b>{p:.0%}</b> 보호<br>최저현금 <b>${x["min_cash"]/1e6:,.2f}m</b><br>'
                        f'Floor 미달 <b>{x["miss_months"]}개월</b><br>최저 여유 <b>${x["min_buffer"]/1e6:,.2f}m</b></div>', unsafe_allow_html=True)
    st.markdown("#### 왜 100% 보호를 기본 추천하지 않는가?")
    st.write("현재 MVP는 실제 FFA 가격·헤지비용·Basis Risk·증거금·계약단위를 아직 반영하지 않았기 때문에 보호수준이 높을수록 현금흐름 결과가 기계적으로 개선됩니다. 따라서 100%는 최적안이 아니라 '최대 보호 시나리오'로만 제시하며, 실제 Hedge Ratio와 계약수량은 FFA 실데이터를 연결한 고도화 단계에서 산출합니다.")

with t5:
    st.subheader("유동성 여력 및 AI 의사결정 설명")
    st.metric("선택 전략 최소유동성 버퍼", f"${chosen_buffer/1e6:,.2f}m")
    st.write("이 값은 **증거금 한도라고 단정하지 않고**, 보호전략 적용 후 회사가 보유하는 최소 유동성 버퍼로 해석합니다.")
    if chosen_buffer < 0:
        st.warning("현재 선택 전략은 최소유동성 자체를 충족하지 못하므로, 보호수준 또는 외부조달 가정을 다시 검토해야 합니다.")
    else:
        st.success("현재 선택 전략은 최소유동성을 충족합니다. 실제 파생상품 실행 Capacity는 후속 단계에서 증거금·계약비용을 연결해 검증합니다.")

    st.markdown("#### AI 의사결정 설명")
    ex = explain(model, protection, floor=floor, external_financing=external)
    st.write(ex["verdict"])
    st.write(ex["need"])
    st.write(ex["liquidity"])
    st.caption(ex["caveat"])
    st.info("현재는 계산결과를 규칙 기반으로 자연어화한 설명 데모입니다. 선정 후 LLM을 연결해 계약서 자연어 해석, 경영목표 반영, 전략 비교 설명, Basis Risk 경고를 자동화할 수 있습니다.")

st.divider()
st.caption("MVP 구분: EuroDry 2025 재무상태 참고(실제) · BlueWave 계약 포트폴리오(합성) · 시장데이터(실제 공개자료) · Floor/외부조달/Proxy 방식(모형 가정)")
