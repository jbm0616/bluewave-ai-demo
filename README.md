# BlueWave Downside Web v3

## 이 버전의 목적
신규계약을 체결했지만 미래 운임·연료가격을 모르는 상황에서:
1. 신규계약 전/후 Downside 비교
2. 경영진 최소 공헌이익 Risk Limit 설정
3. Historical Path 기반 최소 필요 경제적 보호수준 계산
4. 보호 우선순위 설명

## Streamlit 배포
기존 GitHub 저장소에서 아래 파일을 교체/추가하세요.
- app.py
- calc_engine.py
- scenario_data.json
- requirements.txt

그 뒤 Commit하면 Streamlit Community Cloud가 자동 재배포됩니다.

## 경영진 입력
- 분석기간: 3 / 6 / 12개월
- 최소 공헌이익 유지율
- 위험허용수준: P20 / P10 / P5

## 주의
'최소 필요 경제적 보호수준'은 실제 FFA hedge ratio가 아닙니다.
실제 FFA 데이터와 basis risk를 연결한 뒤 계약수량·월물로 변환합니다.
