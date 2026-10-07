from calc_engine import load_model, historical_stress, strategy_summary, required_protection

m=load_model()
s=historical_stress(m)
expected_stress={"A_down":-0.20013718747279946,"C1_down":-0.07184873949579829,"C2_down":-0.0749940797575069,"D_up":0.227413403380056,"Fuel_up":0.07766586339677373}
for k,v in expected_stress.items():
    assert abs(s[k]-v)<1e-10,(k,s[k],v)
expected={0.0:7027068.2160705365,0.3:9126861.451249376,0.5:10526723.608035268,0.7:11926585.76482116,1.0:14026379.0}
for row in strategy_summary(m):
    assert abs(row["end_cash"]-expected[row["protection"]])<1e-6,(row,expected[row["protection"]])
r=required_protection(m)
assert abs(r["required"]-0.4961819657877421)<1e-10,r
assert r["binding_month"]=="12월",r
print("PASS: Python engine matches workbook key outputs")
