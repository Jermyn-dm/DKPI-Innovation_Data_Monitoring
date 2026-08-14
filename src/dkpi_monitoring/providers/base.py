from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Any

import pandas as pd


class DataProvider(ABC):
    @abstractmethod
    def get_table_data(
        self,
        source_table: str,
        date_from: date,
        date_to: date,
        filters: dict[str, Any] | None = None,
    ) -> pd.DataFrame:
        raise NotImplementedError

    @abstractmethod
    def get_config_table(
        self,
        config_name: str,
        filters: dict[str, Any] | None = None,
    ) -> pd.DataFrame:
        raise NotImplementedError

    @abstractmethod
    def get_calendar_data(
        self,
        market: str,
        date_from: date,
        date_to: date,
    ) -> pd.DataFrame:
        raise NotImplementedError
