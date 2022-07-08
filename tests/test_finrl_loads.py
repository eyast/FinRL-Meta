from typing import List

import pandas as pd
import pytest

from meta.config_tickers import DOW_30_TICKER
from meta.config_tickers import SINGLE_TICKER
from meta.data_processor import DataProcessor


@pytest.fixture(scope="session")
def start_date():
    return "2021-01-01"


@pytest.fixture(scope="session")
def end_date():
    return "2021-10-31"


@pytest.fixture(scope="session")
def time_interval():
    return "1d"


@pytest.mark.parametrize(
    "ticker_input_binance, expected_df_size_binance",
    [(["BTCUSDT"], 302), (["ETHUSDT"], 302)],
)
def test_binance_data_processor(
    time_interval: str,
    start_date: str,
    end_date: str,
    ticker_input_binance: List[str],
    expected_df_size_binance: int,
) -> None:
    """
    Tests the Binance Downloader and the returned data shape
    """
    assert isinstance(start_date, str)
    assert isinstance(end_date, str)
    data_source = "binance"
    dp = DataProcessor(data_source, start_date, end_date, time_interval)
    dp.download_data(ticker_input_binance)
    assert isinstance(dp.dataframe, pd.DataFrame)
    assert dp.dataframe.shape == (
        expected_df_size_binance,
        8,
    ) or dp.dataframe.shape == (expected_df_size_binance - 1, 8)


@pytest.mark.parametrize(
    "ticker_input, expected_df_size",
    [(SINGLE_TICKER, 210), (DOW_30_TICKER, 6300)],
)
def test_yahoo_data_processor(
    time_interval: str,
    start_date: str,
    end_date: str,
    ticker_input: List[str],
    expected_df_size: int,
) -> None:
    """
    Tests the Yahoo Downloader and the returned data shape
    """
    assert isinstance(start_date, str)
    assert isinstance(end_date, str)
    data_source = "yahoofinance"
    dp = DataProcessor(data_source, start_date, end_date, time_interval)
    dp.download_data(ticker_input)
    assert isinstance(dp.dataframe, pd.DataFrame)
    assert dp.dataframe.shape == (
        expected_df_size,
        9,
    ) or dp.dataframe.shape == (expected_df_size - 1, 9)
