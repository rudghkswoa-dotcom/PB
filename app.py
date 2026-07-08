import os
import streamlit as st
import pandas as pd
import matplotlib.colors as mcolors
from datetime import datetime
import main  # 👈 우리가 고친 주가 수집 엔진(main.py)을 웹에 연결!!

st.set_page_config(page_title="PB 주도 섹터 분석 대시보드", page_icon="📈", layout="wide")

BASE_DIR = "stock"
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

RETURN_COLS = ["KOSPI_최종수익률(%)", "NASDAQ_최종수익률(%)"]
# 국내 증시 관례에 맞춰 상승=빨강, 하락=파랑, 중립=회색인 diverging 컬러맵
RETURN_CMAP = mcolors.LinearSegmentedColormap.from_list(
    "kr_returns", ["#2a78d6", "#f0efec", "#e34948"]
)

@st.cache_data
def load_summary_csv(csv_path):
    df = pd.read_csv(csv_path, index_col=0)
    df.index.name = "종목명"
    return df

def style_summary(df):
    present_cols = [c for c in RETURN_COLS if c in df.columns]
    max_abs = df[present_cols].abs().max().max()
    max_abs = max_abs if pd.notna(max_abs) and max_abs > 0 else 1
    return (
        df.style
        .background_gradient(cmap=RETURN_CMAP, vmin=-max_abs, vmax=max_abs, subset=present_cols)
        .format("{:+.2f}%", subset=present_cols)
    )

# ⚙️ 컨트롤 패널 (사이드바)
with st.sidebar:
    st.markdown("## ⚙️ 컨트롤 패널")

    available_dates = sorted(
        [f for f in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, f))],
        reverse=True,
    )

    input_date = st.text_input("📅 분석하고 싶은 날짜 입력 (YYYY-MM-DD)", value="2026-06-03")

    if st.button("🚀 실시간 수집/분석하기", use_container_width=True):
        try:
            datetime.strptime(input_date, "%Y-%m-%d")
            with st.spinner(f"🔄 {input_date} 시점의 KOSPI/NASDAQ 데이터를 수집 중입니다..."):
                main.실행하기(input_date) # 👈 main.py의 무적 폰트 엔진 가동!!
            st.success(f"✨ {input_date} 자산 분석 및 차트 갱신 완료!")
            st.rerun() # 화면 즉시 새로고침
        except ValueError:
            st.error("❌ 날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식으로 입력해주세요 (예: 2026-06-15)")
        except Exception as e:
            st.error(f"❌ 데이터 수집 중 오류가 발생했습니다: {e}")

    st.markdown("---")
    selected_date = st.selectbox(
        "📂 과거 분석 일자 조회", available_dates if available_dates else ["데이터 없음"]
    )

# 📊 메인 화면
st.title("📈 시장 주도 섹터 아카이빙 대시보드")

if not selected_date or selected_date == "데이터 없음":
    st.info("👈 왼쪽 사이드바에서 날짜를 입력해 데이터를 수집하거나, 과거 분석 일자를 선택해주세요.")
else:
    st.caption(f"기준일: {selected_date}")
    date_folder = os.path.join(BASE_DIR, selected_date)
    summary_csv_path = os.path.join(date_folder, f"market_summary_{selected_date}.csv")

    df_summary = load_summary_csv(summary_csv_path) if os.path.exists(summary_csv_path) else None

    if df_summary is not None:
        metric_col1, metric_col2 = st.columns(2)
        for metric_col, label, market_col in (
            (metric_col1, "🇰🇷 KOSPI 수익률 1위", "KOSPI_최종수익률(%)"),
            (metric_col2, "🇺🇸 NASDAQ 수익률 1위", "NASDAQ_최종수익률(%)"),
        ):
            series = df_summary[market_col].dropna() if market_col in df_summary.columns else pd.Series(dtype=float)
            if not series.empty:
                metric_col.metric(label, series.idxmax(), f"{series.max():+.2f}%")

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

    st.subheader("📋 최종 수익률 요약 테이블")
    if df_summary is not None:
        st.dataframe(style_summary(df_summary), use_container_width=True)
