from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from dkpi_monitoring.providers.base import DataProvider


class ExcelProvider(DataProvider):
    def __init__(self, base_path: Path):
        self.base_path = base_path

    def get_table_data(
        self,
        source_table: str,
        date_from: date,
        date_to: date,
        filters: dict[str, Any] | None = None,
    ) -> pd.DataFrame:
        file_path = self.base_path / f"{source_table}.xlsx"
        df = pd.read_excel(file_path)
        if filters:
            date_column = filters.get("date_column")
            if date_column and date_column in df.columns:
                df = df[pd.to_datetime(df[date_column], errors="coerce").between(date_from, date_to)]
        return df

    def get_config_table(
        self,
        config_name: str,
        filters: dict[str, Any] | None = None,
    ) -> pd.DataFrame:
        file_path = self.base_path / f"{config_name}.xlsx"
        df = pd.read_excel(file_path)
        return df

    def get_calendar_data(
        self,
        market: str,
        date_from: date,
        date_to: date,
    ) -> pd.DataFrame:
        file_path = self.base_path / f"calendar_{market}.xlsx"
        df = pd.read_excel(file_path)
        return df
