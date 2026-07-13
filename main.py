import datetime
import os

import FinanceDataReader as fdr
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
import yfinance as yf
from tqdm import tqdm

# ==========================================
# 🔥 [경환님 전용 무적의 폰트 엔진] 온/오프라인 한글 완벽 대응
# ==========================================
def 세팅_한글_폰트():
    font_name = "NanumGothic"
    # 스트림릿 리눅스 서버 환경일 때 (맑은 고딕이 없을 때)
    if not os.path.exists(r"C:\Windows\Fonts\malgun.ttf"):
        print("🌐 웹 서버 환경 감지: 나눔고딕 폰트 엔진 설치 시작...")
        import urllib.request
        # 네이버 나눔고딕 오픈소스 폰트를 서버에 직접 다운로드
        font_url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
        local_font_path = "NanumGothic.ttf"
        if not os.path.exists(local_font_path):
            urllib.request.urlretrieve(font_url, local_font_path)
        
        fm.fontManager.addfont(local_font_path)
        font_name = fm.FontProperties(fname=local_font_path).get_name()
    else:
        # 경환님 개인 PC 환경일 때
        font_name = "Malgun Gothic"
        
    plt.rcParams["font.family"] = font_name
    plt.rcParams["axes.unicode_minus"] = False
    print(f"✅ 한글 폰트 '{font_name}' 무적 엔진 적용 완료!")

# 폰트 세팅 가동
세팅_한글_폰트()

# ==========================================
# [1단계] 데이터 수집 함수 정의
# ==========================================
def _fetch_kospi_listing_from_github_cache(max_days_back=10):
    # fdr.StockListing("KOSPI")는 내부적으로 KRX 리소스번들 API를 먼저 호출해
    # 최신 거래일자를 알아낸 뒤, GitHub에 미리 저장된 CSV를 읽는다.
    # 그 KRX API가 불안정할 때를 대비해, 최근 영업일을 직접 훑어 같은 CSV를
    # 바로 읽어오는 우회 경로.
    last_error = None
    today = datetime.datetime.now()
    for offset in range(max_days_back):
        day = today - datetime.timedelta(days=offset)
        if day.weekday() >= 5:  # 토, 일 제외
            continue
        date_str = day.strftime("%Y-%m-%d")
        csv_url = f"https://raw.githubusercontent.com/FinanceData/fdr_krx_data_cache/refs/heads/master/data/listing/krx/{date_str}.csv"
        try:
            df = pd.read_csv(csv_url, index_col=0, dtype={"Code": str, "Dept": str, "ChangeCode": str, "MarketId": str})
            return df.reset_index(drop=True)
        except Exception as e:
            last_error = e
    raise RuntimeError(f"KOSPI 종목 리스트를 가져오지 못했습니다: {last_error}")

@st.cache_data(ttl=3600, show_spinner=False)
def get_top_100_tickers(market_type):
    if market_type == "KOSPI":
        try:
            df_stock = fdr.StockListing(market_type)
        except Exception:
            df_stock = _fetch_kospi_listing_from_github_cache()
            df_stock = df_stock[df_stock["MarketId"] == "STK"].reset_index(drop=True)
        df_top100 = df_stock.sort_values(by="Marcap", ascending=False).head(100)
        return df_top100[["Code", "Name"]].values.tolist()
    elif market_type == "NASDAQ":
        df_stock = fdr.StockListing(market_type)
        df_top100 = df_stock.head(100)
        return df_top100[["Symbol", "Name"]].values.tolist()

@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_single_close(code, start_date):
    try:
        df_price = fdr.DataReader(code, start=start_date)
        return df_price["Close"] if not df_price.empty else None
    except Exception:
        return None

def fetch_closure_prices(ticker_list, start_date):
    series_map = {}
    for code, name in tqdm(ticker_list, desc="주가 데이터 다운로드 중"):
        close_series = _fetch_single_close(code, start_date)
        if close_series is not None:
            series_map[f"{name}({code})"] = close_series
    return pd.DataFrame(series_map)

# ==========================================
# [2단계] 섹터/산업 분류 함수 정의
# ==========================================
@st.cache_data(ttl=3600, show_spinner=False)
def _get_krx_desc():
    try:
        return fdr.StockListing("KRX-DESC")
    except Exception:
        return None

@st.cache_data(ttl=86400, show_spinner=False)
def _fetch_nasdaq_industry(ticker):
    try:
        return yf.Ticker(ticker).info.get("industry", "미분류")
    except Exception:
        return "미분류"

def build_kospi_sector_csv(price_csv, date_folder):
    sector_path = os.path.join(date_folder, "kospi_100_sectors.csv")
    df_k = pd.read_csv(price_csv, index_col=0)
    krx_desc = _get_krx_desc()
    k_list = []
    for col in df_k.columns:
        industry = "미분류"
        if krx_desc is not None:
            code = col.split("(")[-1].replace(")", "")
            match = krx_desc[krx_desc["Code"] == code]
            industry = match["Industry"].values[0] if not match.empty else "미분류"
        k_list.append({"종목명": col, "Industry": industry})
    pd.DataFrame(k_list).to_csv(sector_path, encoding="utf-8-sig", index=False)
    return sector_path

def build_nasdaq_sector_csv(price_csv, date_folder):
    sector_path = os.path.join(date_folder, "nasdaq_100_sectors.csv")
    df_n = pd.read_csv(price_csv, index_col=0)
    tickers = [col.split("(")[-1].replace(")", "") for col in df_n.columns]
    industries = [_fetch_nasdaq_industry(t) for t in tqdm(tickers, desc="나스닥 산업 정보 매핑 중")]
    n_list = [{"종목명": col, "Industry": industry} for col, industry in zip(df_n.columns, industries)]
    pd.DataFrame(n_list).to_csv(sector_path, encoding="utf-8-sig", index=False)
    return sector_path

# ==========================================
# [3단계] 수익률 분석 및 시각화 함수 정의
# ==========================================
def load_industry_mapping(sector_csv):
    if not os.path.exists(sector_csv): return {}
    df_sector = pd.read_csv(sector_csv)
    return dict(zip(df_sector["종목명"], df_sector["Industry"]))

def generate_top10_chart(price_csv, sector_csv, market_name, date_folder, date_str):
    df_price = pd.read_csv(price_csv, index_col=0)
    df_return = ((df_price / df_price.iloc[0]) - 1) * 100
    industry_map = load_industry_mapping(sector_csv)

    final_returns = df_return.iloc[-1]
    top_10_tickers = final_returns.nlargest(10).index.tolist()

    plt.figure(figsize=(13, 7))
    for rank, ticker in enumerate(top_10_tickers, 1):
        industry = industry_map.get(ticker, "미분류")
        display_label = f"{ticker}({industry})"
        plt.plot(df_return.index, df_return[ticker], marker="o", markersize=4, label=display_label)

    plt.title(f"{market_name} 시총 상위 100 [{date_str} 기준] 최근 20영업일 수익률 상위 10종목 추이", fontsize=14)
    plt.xlabel("날짜")
    plt.ylabel("누적 수익률 (%)")
    plt.xticks(rotation=45)
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left", fontsize=9)
    plt.tight_layout()

    chart_filename = os.path.join(date_folder, f"{market_name.lower()}_top10_returns_{date_str}.png")
    plt.savefig(chart_filename, dpi=200)
    plt.close()
    return df_return

# ==========================================
# [실행부 엔트리포인트] 외부 입력 대응용 함수화
# ==========================================
MARKET_SECTOR_BUILDERS = {
    "KOSPI": build_kospi_sector_csv,
    "NASDAQ": build_nasdaq_sector_csv,
}

def 실행하기(지정날짜):
    # 📁 경로 규칙 자동 설정 (상대경로 매핑으로 웹/로컬 공용화)
    BASE_DIR = "stock"
    DATE_DIR = os.path.join(BASE_DIR, 지정날짜)
    if not os.path.exists(DATE_DIR):
        os.makedirs(DATE_DIR)

    today_standard = datetime.datetime.strptime(지정날짜, "%Y-%m-%d")
    start_date = (today_standard - datetime.timedelta(days=40)).strftime("%Y-%m-%d")

    returns_by_market = {}
    for market, build_sector_csv in MARKET_SECTOR_BUILDERS.items():
        try:
            tickers = get_top_100_tickers(market)
            prices_raw = fetch_closure_prices(tickers, start_date)
            prices_raw.index = pd.to_datetime(prices_raw.index)

            prices = prices_raw.loc[:today_standard].tail(20)
            prices.index = prices.index.strftime("%Y-%m-%d")

            price_csv = os.path.join(DATE_DIR, f"{market.lower()}_prices_{지정날짜}.csv")
            prices.to_csv(price_csv, encoding="utf-8-sig")

            sector_csv = build_sector_csv(price_csv, DATE_DIR)
            returns_by_market[market] = generate_top10_chart(price_csv, sector_csv, market, DATE_DIR, 지정날짜)
        except Exception as e:
            print(f"⚠️ {market} 데이터 수집 실패, 건너뜁니다: {e}")

    if not returns_by_market:
        raise RuntimeError("KOSPI/NASDAQ 데이터를 모두 가져오지 못했습니다. 잠시 후 다시 시도해주세요.")

    summary_df = pd.DataFrame({
        f"{market}_최종수익률(%)": returns.iloc[-1]
        for market, returns in returns_by_market.items()
    })
    summary_df.to_csv(os.path.join(DATE_DIR, f"market_summary_{지정날짜}.csv"), encoding="utf-8-sig")

if __name__ == "__main__":
    # 로컬에서 단독 테스트할 때용 (날짜 바꾸기 가능)
    실행하기("2026-06-03")
