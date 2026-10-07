
import json
from pathlib import Path

RISK_ORDER = ["보통(P20)", "보수적(P10)", "매우 보수적(P5)"]

def load_data(path=None):
    if path is None:
        path = Path(__file__).resolve().parent / "scenario_data.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def choose_scenario(data, period, risk):
    for row in data["scenario_rows"]:
        if int(row["period"]) == int(period) and row["risk"] == risk:
            return row
    raise KeyError((period, risk))

def metrics(row, target_rate):
    target_rate = float(target_rate)
    new_base = float(row["new_base"])
    new_down = float(row["new_down"])
    old_base = float(row["old_base"])
    old_down = float(row["old_down"])

    total_downside = max(0.0, new_base - new_down)
    target_value = new_base * target_rate
    shortage = max(0.0, target_value - new_down)

    if total_downside <= 0:
        required = 0.0
    else:
        required = shortage / total_downside

    required = max(0.0, required)
    feasible = required <= 1.0 + 1e-12

    return {
        "old_retention": old_down / old_base if old_base else None,
        "new_retention": new_down / new_base if new_base else None,
        "old_downside_loss": old_base - old_down,
        "new_downside_loss": new_base - new_down,
        "incremental_downside": (new_base - new_down) - (old_base - old_down),
        "new_contract_risk_share": ((new_base - new_down) - (old_base - old_down)) / (new_base - new_down) if (new_base-new_down) else None,
        "target_value": target_value,
        "shortage": shortage,
        "required_protection": required,
        "feasible": feasible,
    }

def protected_downside(row, protection):
    p = max(0.0, min(1.0, float(protection)))
    base = float(row["new_base"])
    down = float(row["new_down"])
    return down + p * (base - down)

def priority_rows(row):
    label_map = {
        "A":("A Index-linked TC-out","운임 하락 시 신규계약 수익 감소"),
        "C1":("C1 PNW Voyage","PNW 운임 하락 시 수익 감소"),
        "C2":("C2 USG Voyage","USG 운임 하락 시 수익 감소"),
        "D":("D future TC-in","Panamax 하락 시 조달비 절감 가능 → 자연상계"),
        "Fuel":("Fuel purchase","연료가격 상승 시 비용 증가"),
    }
    out=[]
    for key in ["A","C1","C2","D","Fuel"]:
        impact=float(row[key])
        name,desc=label_map[key]
        out.append({"key":key,"위험요인":name,"영향":impact,"보호검토손실":max(0,-impact),"설명":desc})
    neg=sorted([x for x in out if x["영향"]<0], key=lambda x:x["보호검토손실"], reverse=True)
    rank={x["key"]:i+1 for i,x in enumerate(neg)}
    for x in out:
        x["우선순위"]=rank.get(x["key"], None)
        x["판단"]="자연상계/우호요인" if x["영향"]>=0 else ("최우선 보호검토" if x["우선순위"]==1 else "보호검토")
    return out
