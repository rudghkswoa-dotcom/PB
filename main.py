import os
import sys

# [치트키 안전장치] 실행 환경에 따라 라이브러리가 누락되었을 경우 자동 설치
try:
    import FinanceDataReader as fdr
    import seaborn as sns
except ModuleNotFoundError:
    print(
        "💡 필수 패키지(FinanceDataReader 또는 seaborn)가 없어 자동 설치를 시작합니다..."
    )
    os.system(f"{sys.executable} -m pip install finance-datareader seaborn")
    import FinanceDataReader as fdr
    import seaborn as sns

import datetime
import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf
from tqdm import tqdm

# 한글 폰트 설정 (Windows: Malgun Gothic, Mac: AppleGothic)
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False


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
    print("\n[2/3] 최신 산업(Industry) 분류 매핑 중...")

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
        pd.DataFrame(k_list).to_csv(
            kospi_sector_path, encoding="utf-8-sig", index=False
        )

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
        pd.DataFrame(n_list).to_csv(
            nasdaq_sector_path, encoding="utf-8-sig", index=False
        )

    return kospi_sector_path, nasdaq_sector_path


# ==========================================
# [3단계] 수익률 분석 및 시각화 함수 정의
# ==========================================
def load_industry_mapping(sector_csv):
    if not os.path.exists(sector_csv):
        return {}
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
        plt.plot(
            df_return.index,
            df_return[ticker],
            marker="o",
            markersize=4,
            label=display_label,
        )

    plt.title(
        f"{market_name} 시총 상위 100 [{date_str} 기준] 최근 20영업일 수익률 상위 10종목 추이",
        fontsize=14,
    )
    plt.xlabel("날짜")
    plt.ylabel("누적 수익률 (%)")
    plt.xticks(rotation=45)
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left", fontsize=9)
    plt.tight_layout()

    # 파일명 뒤에 날짜를 붙여 확실히 구분
    chart_filename = os.path.join(
        date_folder, f"{market_name.lower()}_top10_returns_{date_str}.png"
    )
    plt.savefig(chart_filename, dpi=200)
    plt.close()
    return df_return


# ==========================================
# [메인 실행부] 전체 파이프라인 총괄
# ==========================================
def main():
    print(f"==================================================")
    print(f"🚀 일별 시장 주도 섹터 아카이빙 파이프라인 가동")
    print(f"==================================================")

    # 1. 🎯 [PB님 설정] 분석을 원하는 기준일을 지정하세요!
    target_date_str = "2026-07-01"  # 예: "2026-06-15", "2026-07-01", "2026-07-06" 등

    # 메인 저장 폴더 (stock) 경로
    BASE_DIR = r"c:\Users\경환\Desktop\stock"

    # 날짜별 하위 폴더 경로 생성 (예: c:\Users\경환\Desktop\stock\2026-06-03)
    DATE_DIR = os.path.join(BASE_DIR, target_date_str)
    if not os.path.exists(DATE_DIR):
        os.makedirs(DATE_DIR)
        print(f"📁 해당 날짜의 기록 보존 폴더를 신규 생성했습니다: {DATE_DIR}")

    today_standard = datetime.datetime.strptime(target_date_str, "%Y-%m-%d")
    start_date = (today_standard - datetime.timedelta(days=40)).strftime(
        "%Y-%m-%d"
    )

    print(f"🎯 분석 기준일: {target_date_str}")

    # [1단계] 데이터 수집
    print("\n[1/3] 양대 시장 시총 상위 100 종목 주가 수집 중...")
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

    # 날짜 폴더 내부에 주가 파일 보관
    kospi_price_csv = os.path.join(DATE_DIR, f"kospi_prices_{target_date_str}.csv")
    nasdaq_price_csv = os.path.join(
        DATE_DIR, f"nasdaq_prices_{target_date_str}.csv"
    )
    kospi_prices.to_csv(kospi_price_csv, encoding="utf-8-sig")
    nasdaq_prices.to_csv(nasdaq_price_csv, encoding="utf-8-sig")

    # [2단계] 섹터 정보 연동 및 매핑
    kospi_sector_csv, nasdaq_sector_csv = process_sectors(
        kospi_price_csv, nasdaq_price_csv, DATE_DIR
    )

    # [3단계] 수익률 분석 및 차트 자동 생성
    print("\n[3/3] 상위 10개 종목 '종목명(Industry)' 차트 생성 중...")
    kospi_returns = generate_top10_chart(
        kospi_price_csv, kospi_sector_csv, "KOSPI", DATE_DIR, target_date_str
    )
    nasdaq_returns = generate_top10_chart(
        nasdaq_price_csv, nasdaq_sector_csv, "NASDAQ", DATE_DIR, target_date_str
    )

    # 종합 결과 요약본 엑셀도 날짜 폴더에 저장
    summary_df = pd.DataFrame(
        {
            "KOSPI_최종수익률(%)": kospi_returns.iloc[-1],
            "NASDAQ_최종수익률(%)": nasdaq_returns.iloc[-1],
        }
    )
    summary_df.to_csv(
        os.path.join(DATE_DIR, f"market_summary_{target_date_str}.csv"),
        encoding="utf-8-sig",
    )

    print("\n==================================================")
    print(f"✅ [{target_date_str}] 데이터 아카이빙 완료!")
    print(f"📂 저장 위치: {DATE_DIR}")
    print("==================================================")


if __name__ == "__main__":
    main()