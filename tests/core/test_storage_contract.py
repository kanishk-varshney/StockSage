import pandas as pd

from src.core.config.data_contracts import DATA_DIR
from src.core.market.stock_data import StockData
from src.core.market.storage import CSVStorage


def test_data_dir_is_absolute_path():
    assert DATA_DIR.is_absolute()


def test_storage_writes_price_contract_files(tmp_path):
    stock_data = StockData(symbol="TEST")
    stock_data.company_info = {"longName": "Test Co"}
    stock_data.prices.daily = pd.DataFrame({"Close": [100.0, 101.0]})

    saved = CSVStorage(base_dir=tmp_path).save(stock_data)
    saved_paths = {p.split("/")[-1] for p in saved}

    assert "company_info.csv" in saved_paths
    assert "daily.csv" in saved_paths
    assert "historical_prices.csv" in saved_paths
