# BlueWave AI 해운 리스크 의사결정 시스템 — Streamlit MVP

엑셀 `AI활용기획_MVP통합본(1).xlsx`의 계산 논리를 Python으로 옮긴 웹 데모입니다.
웹앱은 엑셀 수식 결과를 읽는 방식이 아니라 `data_model.json` 원자료를 읽고 `calc_engine.py`에서 직접 재계산합니다.

## 배포 (로컬 Python 설치 불필요)
1. GitHub에서 새 repository를 만듭니다.
2. 이 폴더의 `app.py`, `calc_engine.py`, `data_model.json`, `requirements.txt`를 업로드합니다.
3. Streamlit Community Cloud에서 GitHub를 연결합니다.
4. Main file path를 `app.py`로 지정하고 Deploy합니다.

## 기본 결과 (현재 모델)
- 최소유동성 Floor: $10.5m
- 외부조달 모형가정: $4.0m
- 무보호 최저/연말현금: 약 $7.03m
- 30% 보호: 약 $9.13m, Floor 미달 1개월
- 50% 보호: 약 $10.53m, Floor 충족
- 70% 보호: 약 $11.93m, Floor 충족
- 100% 보호: 약 $14.03m, Floor 충족
- Stress에서 Floor 충족에 필요한 최소 경제적 보호수준: 약 49.6%

## 현재 MVP 범위
- 월별 운임/연료 Exposure
- 실제 공개 과거시장 데이터의 10/90 분위수 Stress
- Minimum Liquidity Floor 기반 Need
- 보호수준별 현금흐름 비교
- 보호 후 유동성 버퍼
- 규칙 기반 AI 설명 데모

## 후속 고도화
- EEX/Baltic 실제 FFA 가격 및 계약단위
- 실제 Hedge Ratio / 계약수량
- Basis Risk / Hedge Effectiveness
- Initial & Variation Margin
- 거래수수료·스프레드·금융비용
- 실제 VLSFO/Marine Fuel 파생상품
- LLM 기반 계약서/경영목표 자연어 해석 및 전략 설명

## 검증
`test_engine.py`를 실행하면 엑셀의 주요 결과와 Python 계산값이 일치하는지 확인합니다.
