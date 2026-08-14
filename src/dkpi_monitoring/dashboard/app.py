from __future__ import annotations

import streamlit as st

from dkpi_monitoring.dashboard.data import DashboardDataProvider


def run_dashboard(data_provider: DashboardDataProvider) -> None:
    st.title("DKPI Data Readiness Monitoring")
    st.sidebar.header("Filters")

    overview = data_provider.get_overview_metrics()
    st.metric("Readiness", f"{overview.readiness_pct:.1f}%")
    st.write(overview)

    st.header("KPI Status")
    kpi_metrics = data_provider.get_kpi_metrics(None, None, None)
    st.dataframe([kpi.__dict__ for kpi in kpi_metrics])
