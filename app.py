import os
import streamlit as st
import pandas as pd
from datetime import datetime
import main  # 👈 우리가 고친 주가 수집 엔진(main.py)을 웹에 연결!!

st.set_page_config(page_title="PB 주도 섹터 분석 대시보드", layout="wide")
st.title("📈 시장 주도 섹터 아카이빙 대시보드")

BASE_DIR = "stock"
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

# ⚙️ 모바일/PC 공용 상단 컨트롤 패널
st.markdown("### ⚙️ 컨트롤 패널")

# 수집된 날짜 폴더 목록 자동 갱신
available_dates = sorted([f for f in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, f))], reverse=True)

# 1. 사용자가 날짜를 마음대로 입력하거나 선택할 수 있는 창
input_date = st.text_input("📅 분석하고 싶은 날짜 입력 (형식: YYYY-MM-DD)", value="2026-06-03")

# 2. 실시간 데이터 수집 가동 버튼
if st.button("🚀 입력한 날짜의 데이터 실시간 수집/분역하기"):
    try:
        # 입력된 날짜 유효성 검사
        datetime.strptime(input_date, "%Y-%m-%d")
        with st.spinner(f"🔄 {input_date} 시점의 KOSPI/NASDAQ 데이터를 격하게 수집 중입니다... 약 30초 소요"):
            main.실행하기(input_date) # 👈 main.py의 무적 폰트 엔진 가동!!
        st.success(f"✨ {input_date} 자산 분석 및 차트 갱신 완료!")
        st.rerun() # 화면 즉시 새로고침
    except ValueError:
        st.error("❌ 날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식으로 입력해주세요 (예: 2026-06-15)")

st.markdown("---")

# 3. 과거 기록 조회용 셀렉트 박스
selected_date = st.selectbox("📂 이미 수집된 과거 분석 일자 선택 조회", available_dates if available_dates else ["데이터 없음"])

# 4. 차트 및 표 시각화 출력부
if selected_date and selected_date != "데이터 없음":
    st.header(f"📊 {selected_date} 기준 시장 분석 결과")
    date_folder = os.path.join(BASE_DIR, selected_date)
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🇰🇷 KOSPI 수익률 상위 10 추이")
        kospi_img_path = os.path.join(date_folder, f"kospi_top10_returns_{selected_date}.png")
        if os.path.exists(kospi_img_path):
            st.image(kospi_img_path, use_container_width=True)
            
    with col2:
        st.subheader("🇺🇸 NASDAQ 수익률 상위 10 추이")
        nasdaq_img_path = os.path.join(date_folder, f"nasdaq_top10_returns_{selected_date}.png")
        if os.path.exists(nasdaq_img_path):
            st.image(nasdaq_img_path, use_container_width=True)

    st.markdown("---")
    st.subheader("📋 최종 수익률 요약 테이블")
    summary_csv_path = os.path.join(date_folder, f"market_summary_{selected_date}.csv")
    if os.path.exists(summary_csv_path):
        df_summary = pd.read_csv(summary_csv_path)
        st.dataframe(df_summary, use_container_width=True)