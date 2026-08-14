from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from dkpi_monitoring.providers.base import DataProvider


class DatabricksProvider(DataProvider):
    def __init__(self, connection_string: str):
        self.connection_string = connection_string

    def _execute_query(self, query: str) -> pd.DataFrame:
        raise NotImplementedError

    def get_table_data(
        self,
        source_table: str,
        date_from: date,
        date_to: date,
        filters: dict[str, Any] | None = None,
    ) -> pd.DataFrame:
        query = f"SELECT * FROM {source_table} WHERE date >= '{date_from}' AND date <= '{date_to}'"
        return self._execute_query(query)

    def get_config_table(
        self,
        config_name: str,
        filters: dict[str, Any] | None = None,
    ) -> pd.DataFrame:
        query = f"SELECT * FROM {config_name}"
        return self._execute_query(query)

    def get_calendar_data(
        self,
        market: str,
        date_from: date,
        date_to: date,
    ) -> pd.DataFrame:
        query = (
            f"SELECT * FROM dim_business_calendar WHERE market = '{market}' "
            f"AND calendar_date >= '{date_from}' AND calendar_date <= '{date_to}'"
        )
        return self._execute_query(query)
