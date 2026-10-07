import json, math
from pathlib import Path

MONTHS = [f"{i}월" for i in range(1, 13)]

def percentile_inc(values, p):
    vals = sorted(float(x) for x in values)
    if not vals:
        raise ValueError("empty values")
    if len(vals) == 1:
        return vals[0]
    k = (len(vals) - 1) * p
    lo = math.floor(k)
    hi = math.ceil(k)
    if lo == hi:
        return vals[lo]
    return vals[lo] * (hi - k) + vals[hi] * (k - lo)

def load_model(path=None):
    if path is None:
        path = Path(__file__).resolve().parent / "data_model.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def historical_stress(model):
    h = model["market_history"]
    keys = ["PNW_Japan", "USG_Japan", "KOBC_TC", "Brent"]
    rets = {k: [] for k in keys}
    for i in range(1, len(h)):
        for k in keys:
            prev = float(h[i-1][k])
            cur = float(h[i][k])
            rets[k].append(cur / prev - 1.0)
    p_lo = float(model["assumptions"]["downside_percentile"])
    p_hi = float(model["assumptions"]["upside_percentile"])
    return {
        "A_down": min(percentile_inc(rets["KOBC_TC"], p_lo), 0.0),
        "C1_down": min(percentile_inc(rets["PNW_Japan"], p_lo), 0.0),
        "C2_down": min(percentile_inc(rets["USG_Japan"], p_lo), 0.0),
        "D_up": max(percentile_inc(rets["KOBC_TC"], p_hi), 0.0),
        "Fuel_up": max(percentile_inc(rets["Brent"], p_hi), 0.0),
    }

def monthly_market_shocks(model, stress=None):
    if stress is None:
        stress = historical_stress(model)
    b = model["baseline_market"]
    commission = float(b["commission"])
    rows = []
    for e in model["exposures"]:
        a = float(e["A_P5TC_days"]) * float(b["P5TC"]) * stress["A_down"] * (1-commission)
        c1 = float(e["C1_PNW_t"]) * float(b["PNW_Japan"]) * stress["C1_down"] * (1-commission)
        c2 = float(e["C2_USG_t"]) * float(b["USG_Japan"]) * stress["C2_down"] * (1-commission)
        d = float(e["D_TCin_days"]) * float(b["TCin_proxy"]) * stress["D_up"]
        fuel = -float(e["fuel_t"]) * float(b["VLSFO_base"]) * stress["Fuel_up"]
        total = a + c1 + c2 + d + fuel
        rows.append({
            "month": e["month"], "A": a, "C1": c1, "C2": c2,
            "D": d, "Fuel": fuel, "total": total
        })
    return rows

def cashflow(model, protection=0.0, floor=None, external_financing=None, stress=None):
    f = model["finance"]
    if floor is None:
        floor = float(f["liquidity_floor"])
    if external_financing is None:
        external_financing = float(f["external_financing"])
    protection = max(0.0, min(1.0, float(protection)))
    shocks = monthly_market_shocks(model, stress)
    ocf_month = float(f["operating_cashflow_2025"]) / 12.0
    debt_q = float(f["debt_principal_2026"]) / 4.0
    capex_h = float(f["newbuilding_capex_2026"]) / 2.0
    fin_h = float(external_financing) / 2.0
    debt_months = set(model["assumptions"]["debt_payment_months"])
    capex_months = set(model["assumptions"]["capex_payment_months"])
    fin_months = set(model["assumptions"]["financing_inflow_months"])
    begin = float(f["starting_cash"])
    rows = []
    for i in range(1, 13):
        market = float(shocks[i-1]["total"])
        protected = -market * protection
        net_market = market + protected
        debt = debt_q if i in debt_months else 0.0
        capex = capex_h if i in capex_months else 0.0
        financing = fin_h if i in fin_months else 0.0
        end = begin + ocf_month + net_market + financing - debt - capex
        rows.append({
            "month": MONTHS[i-1], "begin_cash": begin, "baseline_ocf": ocf_month,
            "market_shock": market, "protection_effect": protected, "net_market": net_market,
            "external_financing": financing, "debt_principal": debt, "capex": capex,
            "end_cash": end, "floor": float(floor), "buffer": end-float(floor),
            "meets_floor": end >= float(floor)
        })
        begin = end
    return rows

def strategy_summary(model, levels=(0,.30,.50,.70,1.0), floor=None, external_financing=None):
    shock_total = sum(x["total"] for x in monthly_market_shocks(model))
    out = []
    labels = {0:"무보호", .30:"부분보호 30%", .50:"균형보호 50%", .70:"안정성보호 70%", 1.0:"시장위험 100% 보호"}
    for p in levels:
        rows = cashflow(model, p, floor=floor, external_financing=external_financing)
        out.append({
            "label": labels.get(p, f"{p:.0%} 보호"),
            "protection": p,
            "min_cash": min(r["end_cash"] for r in rows),
            "miss_months": sum(1 for r in rows if not r["meets_floor"]),
            "end_cash": rows[-1]["end_cash"],
            "protected_loss": -shock_total * p,
            "min_buffer": min(r["buffer"] for r in rows),
        })
    return out

def required_protection(model, floor=None, external_financing=None):
    base = cashflow(model, 1.0, floor=floor, external_financing=external_financing)
    nohedge = cashflow(model, 0.0, floor=floor, external_financing=external_financing)
    req = 0.0
    binding_month = None
    for b, n in zip(base, nohedge):
        market_loss = b["end_cash"] - n["end_cash"]
        if n["end_cash"] >= n["floor"]:
            p = 0.0
        elif market_loss <= 0:
            p = float('inf')
        else:
            p = (n["floor"] - n["end_cash"]) / market_loss
        if p > req:
            req = p
            binding_month = n["month"]
    return {"required": req, "binding_month": binding_month, "feasible": req <= 1.0}

def explain(model, protection, floor=None, external_financing=None):
    rows = cashflow(model, protection, floor=floor, external_financing=external_financing)
    req = required_protection(model, floor=floor, external_financing=external_financing)
    min_cash = min(r["end_cash"] for r in rows)
    min_buffer = min(r["buffer"] for r in rows)
    misses = sum(1 for r in rows if not r["meets_floor"])
    p = float(protection)
    if misses:
        verdict = f"현재 보호수준 {p:.0%}에서는 최소유동성 Floor를 {misses}개월 충족하지 못합니다."
    else:
        verdict = f"현재 보호수준 {p:.0%}에서는 모든 월에 최소유동성 Floor를 충족합니다."
    if req["feasible"]:
        need = f"이 Stress에서 Floor를 지키기 위한 최소 경제적 보호수준은 약 {req['required']:.1%}이며, 가장 제약적인 시점은 {req['binding_month']}입니다."
    else:
        need = "시장위험을 100% 보호해도 Floor를 충족하지 못하므로 구조적 유동성 보완이 먼저 필요합니다."
    return {
        "verdict": verdict,
        "need": need,
        "liquidity": f"선택 전략의 최저 월말현금은 ${min_cash/1_000_000:,.2f}m, 최저 Floor 대비 여유는 ${min_buffer/1_000_000:,.2f}m입니다.",
        "caveat": "현재 MVP의 보호수준은 실제 FFA 계약비율이 아닙니다. 실제 FFA 가격·계약단위·Basis Risk·Initial/Variation Margin·거래비용을 연결한 뒤 Hedge Ratio와 실행 Capacity를 산출하도록 고도화합니다."
    }
