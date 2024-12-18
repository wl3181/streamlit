import yfinance as yf
import pandas as pd
from pandas.tseries.offsets import BDay  # 工作日偏移
from datetime import datetime
import streamlit as st


def fetch_stock_data(ticker, start_date, end_date, holding_period):
    adjusted_start_date = pd.to_datetime(start_date) - BDay(35)
    adjusted_end_date = pd.to_datetime(end_date) + BDay(holding_period + 10)
    today = pd.Timestamp(datetime.today())
    print(
        f"Adjusted Start Date (including 30 trading days back): {adjusted_start_date.date()}"
    )
    print(
        f"Adjusted End Date (including 20 trading days back): {adjusted_end_date.date()}"
    )
    data = yf.download(
        ticker, start=adjusted_start_date.date(), end=adjusted_end_date.date()
    )

    data = data[["Adj Close", "Volume"]]
    data.columns = [col[0] for col in data.columns]
    trading_days = data.index.sort_values()
    start_date = pd.Timestamp(start_date)
    end_date = pd.Timestamp(end_date)
    start_idx = trading_days.searchsorted(start_date, side="left")
    end_idx = trading_days.searchsorted(end_date, side="right") - 1

    adjusted_start_idx = max(0, start_idx - 20)
    adjusted_end_idx = min(len(trading_days) - 1, end_idx + holding_period)

    adjusted_start_date = trading_days[adjusted_start_idx]
    adjusted_end_date = trading_days[adjusted_end_idx]

    if trading_days[end_idx] < start_date or trading_days[start_idx] > end_date:
        return pd.DataFrame()

    if adjusted_end_date > today:
        print("Adjusted end date exceeds today's date. Returning empty DataFrame.")
        return pd.DataFrame()  # 返回一个空的 DataFrame

    final_data = data.loc[adjusted_start_date:adjusted_end_date]
    return final_data


def identify_breakout_days(
    df, volume_threshold, price_change_threshold, holding_period=10
):
    df["20DayAvgVolume"] = df["Volume"].shift(1).rolling(20).mean()
    df = df.dropna(subset=["20DayAvgVolume"])
    df["Return"] = (df["Adj Close"].shift(-holding_period) - df["Adj Close"]) / df[
        "Adj Close"
    ]
    df = df.dropna(subset=["Return"])
    df["VolumeBreakout"] = df["Volume"] > df["20DayAvgVolume"] * (
        volume_threshold / 100
    )
    df["PriceChange"] = df["Adj Close"].pct_change()
    df["PriceBreakout"] = df["PriceChange"] > (price_change_threshold / 100)
    df["Breakout"] = df["VolumeBreakout"] & df["PriceBreakout"]
    return df[df["Breakout"]]


def main(
    ticker=None,
    start_date=None,
    end_date=None,
    volume_threshold=200,
    price_change_threshold=1,
    holding_period=10,
):
    stock_data = fetch_stock_data(
        ticker, start_date, end_date, holding_period=holding_period
    )
    if len(stock_data) > 0:
        breakout_days = identify_breakout_days(
            stock_data,
            volume_threshold,
            price_change_threshold,
            holding_period=holding_period,
        )
    else:
        breakout_days = pd.DataFrame()
    print(breakout_days)
    # save to csv


if __name__ == "__main__":
    # from alpha_vantage.timeseries import TimeSeries

    # ticker = "AAPL"
    # start_date = "2024-01-01"
    # end_date = "2024-10-31"
    # volume_threshold = 200  # 成交量阈值，200% 表示当天成交量是平均值的两倍
    # price_change_threshold = 2  # 价格上涨阈值，2% 表示上涨2%

    # main(
    #     ticker=ticker,
    #     start_date=start_date,
    #     end_date=end_date,
    #     volume_threshold=volume_threshold,
    #     price_change_threshold=price_change_threshold,
    #     holding_period=10,
    # )

    st.title("Stock Breakout Analysis(Allison Yang)")
    st.sidebar.header("Input Parameters")

    ticker = st.sidebar.text_input("Stock Ticker", "AAPL")
    start_date = st.sidebar.date_input("Start Date", pd.Timestamp("2024-01-01"))
    end_date = st.sidebar.date_input("End Date", pd.Timestamp("2024-11-01"))
    volume_threshold = st.sidebar.slider("Volume Threshold (%)", 100, 500, 200)
    price_change_threshold = st.sidebar.slider("Price Change Threshold (%)", 1, 10, 2)
    holding_period = st.sidebar.slider("Holding Period (days)", 1, 30, 10)

    if st.sidebar.button("Generate Report"):
        st.write(f"Fetching data for {ticker} from {start_date} to {end_date}...")
        stock_data = fetch_stock_data(ticker, start_date, end_date, holding_period)

        if stock_data.empty:
            st.error("No stock data found. Please check the ticker or date range.")
        else:
            breakout_days = identify_breakout_days(
                stock_data, volume_threshold, price_change_threshold, holding_period
            )

            if breakout_days.empty:
                st.warning("No breakout days found.")
            else:
                st.success("Breakout analysis completed!")
                st.write("Breakout days preview:")
                st.dataframe(breakout_days.head())

                csv = breakout_days.to_csv(index=True).encode("utf-8")
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"{ticker}_breakout_days.csv",
                    mime="text/csv",
                )
