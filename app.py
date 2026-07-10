import os
import streamlit as st
import pandas as pd
from datetime import date, datetime
import main  # 👈 우리가 고친 주가 수집 엔진(main.py)을 웹에 연결!!

st.set_page_config(page_title="PB 주도 섹터 분석 대시보드", layout="wide")
st.title("📈 시장 주도 섹터 아카이빙 대시보드")

BASE_DIR = "stock"
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

@st.cache_data
def load_summary_csv(csv_path):
    return pd.read_csv(csv_path)

# ⚙️ 모바일/PC 공용 상단 컨트롤 패널
st.markdown("### ⚙️ 컨트롤 패널")

# 수집된 날짜 폴더 목록 자동 갱신
available_dates = sorted([f for f in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, f))], reverse=True)

# 1. 사용자가 날짜를 선택할 수 있는 달력 위젯 (직접 타이핑 시 발생하는 형식 오류 원천 차단)
input_date_obj = st.date_input("📅 분석하고 싶은 날짜 선택", value=date(2026, 6, 3))
input_date = input_date_obj.strftime("%Y-%m-%d")

# 2. 실시간 데이터 수집 가동 버튼
if st.button("🚀 입력한 날짜의 데이터 실시간 수집/분석하기"):
    try:
        with st.spinner(f"🔄 {input_date} 시점의 KOSPI/NASDAQ 데이터를 수집 중입니다..."):
            main.실행하기(input_date) # 👈 main.py의 무적 폰트 엔진 가동!!
        st.success(f"✨ {input_date} 자산 분석 및 차트 갱신 완료!")
        st.rerun() # 화면 즉시 새로고침
    except Exception as e:
        st.error(f"❌ 데이터 수집 중 오류가 발생했습니다: {e}")

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
        else:
            st.info("⚠️ 이 날짜의 KOSPI 차트가 아직 생성되지 않았습니다. 상단에서 다시 수집해주세요.")

    with col2:
        st.subheader("🇺🇸 NASDAQ 수익률 상위 10 추이")
        nasdaq_img_path = os.path.join(date_folder, f"nasdaq_top10_returns_{selected_date}.png")
        if os.path.exists(nasdaq_img_path):
            st.image(nasdaq_img_path, use_container_width=True)
        else:
            st.info("⚠️ 이 날짜의 NASDAQ 차트가 아직 생성되지 않았습니다. 상단에서 다시 수집해주세요.")

    st.markdown("---")
    st.subheader("📋 최종 수익률 요약 테이블")
    summary_csv_path = os.path.join(date_folder, f"market_summary_{selected_date}.csv")
    if os.path.exists(summary_csv_path):
        df_summary = load_summary_csv(summary_csv_path)
        st.dataframe(df_summary, use_container_width=True)
    else:
        st.info("⚠️ 이 날짜의 요약 테이블이 아직 생성되지 않았습니다. 상단에서 다시 수집해주세요.")
