import os
import sys

# [치트키 안전장치] 라이브러리 자동 설치
try:
    import FinanceDataReader as fdr
    import seaborn as sns
except ModuleNotFoundError:
    os.system(f"{sys.executable} -m pip install finance-datareader seaborn")
    import FinanceDataReader as fdr
    import seaborn as sns

import datetime
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import pandas as pd
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
def get_top_100_tickers(market_type):
    df_stock = fdr.StockListing(market_type)
    if market_type == "KOSPI":
        df_top100 = df_stock.sort_values(by="Marcap", ascending=False).head(100)
        return df_top100[["Code", "Name"]].values.tolist()
    elif market_type == "NASDAQ":
        df_top100 = df_stock.head(100)
        return df_top100[["Symbol", "Name"]].values.tolist()

def fetch_closure_prices(ticker_list, start_date):
    combined_df = pd.DataFrame()
    for code, name in tqdm(ticker_list, desc="주가 데이터 다운로드 중"):
        try:
            df_price = fdr.DataReader(code, start=start_date)
            if not df_price.empty:
                combined_df[f"{name}({code})"] = df_price["Close"]
        except Exception:
            continue
    return combined_df

# ==========================================
# [2단계] 섹터/산업 분류 함수 정의
# ==========================================
def process_sectors(kospi_price_csv, nasdaq_price_csv, date_folder):
    kospi_sector_path = os.path.join(date_folder, "kospi_100_sectors.csv")
    nasdaq_sector_path = os.path.join(date_folder, "nasdaq_100_sectors.csv")

    if os.path.exists(kospi_price_csv):
        df_k = pd.read_csv(kospi_price_csv, index_col=0)
        krx_desc = fdr.StockListing("KRX-DESC")
        k_list = []
        for col in df_k.columns:
            code = col.split("(")[-1].replace(")", "")
            match = krx_desc[krx_desc["Code"] == code]
            industry = match["Industry"].values[0] if not match.empty else "미분류"
            k_list.append({"종목명": col, "Industry": industry})
        pd.DataFrame(k_list).to_csv(kospi_sector_path, encoding="utf-8-sig", index=False)

    if os.path.exists(nasdaq_price_csv):
        df_n = pd.read_csv(nasdaq_price_csv, index_col=0)
        n_list = []
        for col in tqdm(df_n.columns, desc="나스닥 산업 정보 매핑 중"):
            ticker = col.split("(")[-1].replace(")", "")
            try:
                industry = yf.Ticker(ticker).info.get("industry", '미분류')
            except Exception:
                industry = "미분류"
            n_list.append({"종목명": col, "Industry": industry})
        pd.DataFrame(n_list).to_csv(nasdaq_sector_path, encoding="utf-8-sig", index=False)

    return kospi_sector_path, nasdaq_sector_path

# ==========================================
# [3단계] 수익률 분석 및 시각화 함수 정의
# ==========================================
def load_industry_mapping(sector_csv):
    if not os.path.exists(sector_csv): return {}
    df_sector = pd.read_csv(sector_csv)
    return dict(zip(df_sector["종목명"], df_sector["Industry"]))

def generate_top10_chart(price_csv, sector_csv, market_name, date_folder, date_str):
    # 차트를 그릴 때 다시 한번 한글 폰트 강제 주입
    세팅_한글_폰트()
    
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
def 실행하기(지정날짜):
    # 📁 경로 규칙 자동 설정 (상대경로 매핑으로 웹/로컬 공용화)
    BASE_DIR = "stock"
    DATE_DIR = os.path.join(BASE_DIR, 지정날짜)
    if not os.path.exists(DATE_DIR):
        os.makedirs(DATE_DIR)

    today_standard = datetime.datetime.strptime(지정날짜, "%Y-%m-%d")
    start_date = (today_standard - datetime.timedelta(days=40)).strftime("%Y-%m-%d")

    kospi_100 = get_top_100_tickers("KOSPI")
    nasdaq_100 = get_top_100_tickers("NASDAQ")

    kospi_prices_raw = fetch_closure_prices(kospi_100, start_date)
    nasdaq_prices_raw = fetch_closure_prices(nasdaq_100, start_date)

    kospi_prices_raw.index = pd.to_datetime(kospi_prices_raw.index)
    nasdaq_prices_raw.index = pd.to_datetime(nasdaq_prices_raw.index)

    kospi_prices = kospi_prices_raw.loc[:today_standard].tail(20)
    nasdaq_prices = nasdaq_prices_raw.loc[:today_standard].tail(20)

    kospi_prices.index = kospi_prices.index.strftime("%Y-%m-%d")
    nasdaq_prices.index = nasdaq_prices.index.strftime("%Y-%m-%d")

    kospi_price_csv = os.path.join(DATE_DIR, f"kospi_prices_{지정날짜}.csv")
    nasdaq_price_csv = os.path.join(DATE_DIR, f"nasdaq_prices_{지정날짜}.csv")
    kospi_prices.to_csv(kospi_price_csv, encoding="utf-8-sig")
    nasdaq_prices.to_csv(nasdaq_price_csv, encoding="utf-8-sig")

    kospi_sector_csv, nasdaq_sector_csv = process_sectors(kospi_price_csv, nasdaq_price_csv, DATE_DIR)

    kospi_returns = generate_top10_chart(kospi_price_csv, kospi_sector_csv, "KOSPI", DATE_DIR, 지정날짜)
    nasdaq_returns = generate_top10_chart(nasdaq_price_csv, nasdaq_sector_csv, "NASDAQ", DATE_DIR, 지정날짜)

    summary_df = pd.DataFrame({
        "KOSPI_최종수익률(%)": kospi_returns.iloc[-1],
        "NASDAQ_최종수익률(%)": nasdaq_returns.iloc[-1],
    })
    summary_df.to_csv(os.path.join(DATE_DIR, f"market_summary_{지정날짜}.csv"), encoding="utf-8-sig")

if __name__ == "__main__":
    # 로컬에서 단독 테스트할 때용 (날짜 바꾸기 가능)
    실행하기("2026-06-03")