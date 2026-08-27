from __future__ import annotations

import streamlit as st

from dkpi_monitoring.dashboard.data import DashboardDataProvider


def run_dashboard(data_provider: DashboardDataProvider) -> None:
    raise NotImplementedError
