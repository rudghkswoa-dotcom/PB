import os
import sys
import datetime

import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

# ---------------------------------------------------------
# [치트키 안전장치] 필수 패키지 자동 설치
# ---------------------------------------------------------
try:
    import FinanceDataReader as fdr
except ModuleNotFoundError:
    os.system(f"{sys.executable} -m pip install finance-datareader")
    import FinanceDataReader as fdr

try:
    import yfinance as yf
except ModuleNotFoundError:
    os.system(f"{sys.executable} -m pip install yfinance")
    import yfinance as yf

# 한글 폰트 설정 (Windows: Malgun Gothic, Mac: AppleGothic)
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

st.set_page_config(page_title="일별 시장 주도 섹터 대시보드", layout="wide")

# 결과 파일을 저장할 기본 폴더 (필요하면 본인 경로로 수정하세요)
BASE_DIR = r"c:\Users\경환\Desktop\stock"


# ==========================================
# [1단계] 데이터 수집 함수 (캐싱 적용)
# ==========================================
@st.cache_data(show_spinner=False)
def get_top_100_tickers(market_type):
    df_stock = fdr.StockListing(market_type)
    if market_type == "KOSPI":
        df_top100 = df_stock.sort_values(by="Marcap", ascending=False).head(100)
        return tuple(map(tuple, df_top100[["Code", "Name"]].values.tolist()))
    elif market_type == "NASDAQ":
        df_top100 = df_stock.head(100)
        return tuple(map(tuple, df_top100[["Symbol", "Name"]].values.tolist()))


@st.cache_data(show_spinner=False)
def fetch_closure_prices(ticker_tuple, start_date, end_date):
    combined_df = pd.DataFrame()
    progress = st.progress(0.0, text="주가 데이터 다운로드 중...")
    total = len(ticker_tuple)
    for i, (code, name) in enumerate(ticker_tuple):
        try:
            df_price = fdr.DataReader(code, start=start_date, end=end_date)
            if not df_price.empty:
                combined_df[f"{name}({code})"] = df_price["Close"]
        except Exception:
            pass
        progress.progress((i + 1) / total, text=f"주가 데이터 다운로드 중... ({i + 1}/{total})")
    progress.empty()
    return combined_df


# ==========================================
# [2단계] 섹터/산업 분류 함수 (캐싱 적용)
# ==========================================
@st.cache_data(show_spinner=False)
def get_industry_map(price_columns, market_type):
    industry_map = {}
    if market_type == "KOSPI":
        krx_desc = fdr.StockListing("KRX-DESC")
        for col in price_columns:
            code = col.split("(")[-1].replace(")", "")
            match = krx_desc[krx_desc["Code"] == code]
            industry_map[col] = match["Industry"].values[0] if not match.empty else "미분류"
    else:
        for col in price_columns:
            ticker = col.split("(")[-1].replace(")", "")
            try:
                industry_map[col] = yf.Ticker(ticker).info.get("industry", "미분류")
            except Exception:
                industry_map[col] = "미분류"
    return industry_map


# ==========================================
# [3단계] 수익률 계산 및 시각화
# ==========================================
def compute_returns(df_price):
    return ((df_price / df_price.iloc[0]) - 1) * 100


def plot_top_n(df_return, industry_map, market_name, date_str, top_n):
    final_returns = df_return.iloc[-1]
    top_tickers = final_returns.nlargest(top_n).index.tolist()

    fig, ax = plt.subplots(figsize=(13, 7))
    for ticker in top_tickers:
        industry = industry_map.get(ticker, "미분류")
        ax.plot(
            df_return.index,
            df_return[ticker],
            marker="o",
            markersize=4,
            label=f"{ticker}({industry})",
        )

    ax.set_title(
        f"{market_name} 시총 상위 100 [{date_str} 기준] 최근 20영업일 수익률 상위 {top_n}종목 추이",
        fontsize=14,
    )
    ax.set_xlabel("날짜")
    ax.set_ylabel("누적 수익률 (%)")
    ax.tick_params(axis="x", rotation=45)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)
    fig.tight_layout()
    return fig, top_tickers


# ==========================================
# [파이프라인] 시장 하나에 대해 전체 과정 실행
# ==========================================
def run_market_pipeline(market_type, market_name, target_dt, top_n, save_files, date_dir):
    tickers = get_top_100_tickers(market_type)
    start_date = (target_dt - datetime.timedelta(days=40)).strftime("%Y-%m-%d")
    end_date = target_dt.strftime("%Y-%m-%d")

    prices_raw = fetch_closure_prices(tickers, start_date, end_date)
    if prices_raw.empty:
        return None, None, None

    prices_raw.index = pd.to_datetime(prices_raw.index)
    prices = prices_raw.loc[:target_dt].tail(20)
    prices.index = prices.index.strftime("%Y-%m-%d")

    industry_map = get_industry_map(tuple(prices.columns.tolist()), market_type)
    returns = compute_returns(prices)
    fig, top_tickers = plot_top_n(returns, industry_map, market_name, end_date, top_n)

    if save_files:
        os.makedirs(date_dir, exist_ok=True)
        prices.to_csv(
            os.path.join(date_dir, f"{market_type.lower()}_prices_{end_date}.csv"),
            encoding="utf-8-sig",
        )
        fig.savefig(
            os.path.join(date_dir, f"{market_name.lower()}_top{top_n}_returns_{end_date}.png"),
            dpi=200,
        )

    return fig, returns, top_tickers


# ==========================================
# [UI] Streamlit 화면 구성
# ==========================================
st.title("📈 일별 시장 주도 섹터 대시보드")
st.caption("기준일을 바꾸면 해당 일자 기준 최근 20영업일 누적 수익률 상위 종목을 다시 계산합니다.")

with st.sidebar:
    st.header("설정")
    target_date = st.date_input("기준일 선택", value=datetime.date(2026, 6, 25))
    market_choice = st.radio("시장 선택", ["KOSPI", "NASDAQ", "둘 다"], index=2)
    top_n = st.slider("상위 몇 종목을 볼까요?", min_value=5, max_value=20, value=10)
    save_files = st.checkbox("결과 파일(CSV/PNG)을 로컬에도 저장", value=False)
    run_btn = st.button("분석 실행", type="primary", use_container_width=True)

target_date_str = target_date.strftime("%Y-%m-%d")
date_dir = os.path.join(BASE_DIR, target_date_str)

if run_btn:
    markets_to_run = []
    if market_choice in ("KOSPI", "둘 다"):
        markets_to_run.append(("KOSPI", "KOSPI"))
    if market_choice in ("NASDAQ", "둘 다"):
        markets_to_run.append(("NASDAQ", "NASDAQ"))

    tabs = st.tabs([m[1] for m in markets_to_run])
    target_dt = datetime.datetime.combine(target_date, datetime.time())

    for tab, (mtype, mname) in zip(tabs, markets_to_run):
        with tab:
            with st.spinner(f"{mname} 데이터 수집 및 계산 중..."):
                fig, returns, top_tickers = run_market_pipeline(
                    mtype, mname, target_dt, top_n, save_files, date_dir
                )

            if fig is None:
                st.error("해당 기간의 데이터를 가져오지 못했습니다. 날짜를 조정해보세요 (거래일이 아니거나 데이터가 없을 수 있습니다).")
            else:
                st.pyplot(fig)
                st.subheader(f"{mname} 상위 {top_n}종목 최종 누적 수익률")
                final = returns.iloc[-1][top_tickers].sort_values(ascending=False)
                st.dataframe(final.rename("최종 누적 수익률(%)").to_frame(), use_container_width=True)

                if save_files:
                    st.success(f"CSV/PNG 저장 완료: {date_dir}")
else:
    st.info("왼쪽 사이드바에서 기준일과 옵션을 선택한 뒤 '분석 실행' 버튼을 눌러주세요.")