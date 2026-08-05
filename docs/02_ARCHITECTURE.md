# Architecture Design

## Source of Truth
This document is aligned with `docs/01_PRD.md` and serves as the architecture blueprint for the DKPI Data Readiness Monitoring platform.

## Core Architecture
The architecture is built around a configuration-driven monitoring engine with abstracted data providers, a reusable business calendar service, and a Streamlit dashboard for visualization.

### Logical Layers
- Data Source Layer
- Configuration Layer
- Business Calendar Layer
- KPI Rule Engine
- Monitoring Engine
- Dashboard Layer

## Data Source Layer
- Provides an abstraction over data source implementations.
- Supports MVP Excel provider and future Databricks provider.
- Ensures business logic remains unchanged when provider changes.

## Configuration Layer
- Loads KPI configurations, ready rules, business calendars, and source table mappings.
- Uses configuration metadata to drive monitoring logic.
- Supports Excel files in MVP and future Databricks-backed configuration tables.

## Business Calendar Layer
- Encapsulates market-specific business day rules.
- Supports public holidays and weekends.
- Provides business-day and calendar-day calculation functions.

## KPI Rule Engine
- Parses readiness rules such as `M+3BD`, `M+5CD`, `D+1BD`.
- Calculates expected ready dates.
- Determines KPI status based on configurable readiness conditions.

## Monitoring Engine
- Orchestrates end-to-end monitoring execution.
- Reads config, retrieves source data, evaluates readiness, and persists results.
- Supports daily and monthly KPI monitoring.
- Emits monitoring result records for dashboard and historical trend calculation.

## Monitoring Result Storage Design
- Stores KPI monitoring results in a dedicated result repository.
- Persists fields: channel, market, KPI name, frequency, expected ready date, actual ready date, status, missing reason, record count, evaluation details, execution timestamp.
- Supports recent result retrieval and historical trend queries.
- Enables auditability through execution metadata and result versioning.
- Allows persistence in MVP storage (file or in-memory) and future Databricks-backed tables.

## Configuration Repository Design
- Defines a configuration repository abstraction for metadata sources.
- Supports Excel files in MVP and Databricks config tables in future.
- Maintains KPI configuration, ready-rule configuration, business calendar data, and source table mappings.
- Provides dynamic source selection so the active configuration source can change without application logic changes.
- Validates configuration completeness, active KPI filters, effective-dated rules, and market-specific mappings.
- Ensures business logic consumes normalized config objects rather than raw files or SQL rows.

## Provider Interface Contract
- Uses a provider contract that abstracts physical data source access.
- Core methods:
  - `get_table_data(source_table, date_from, date_to, filters)`
  - `get_config_table(config_name, filters)`
  - `get_calendar_data(market, date_from, date_to)`
- Requires providers to normalize data shapes so the engine receives consistent data regardless of Excel or Databricks backend.
- Supports provider selection via configuration and handles provider-specific errors, retries, and connection issues.
- Keeps provider implementations pluggable and independent of KPI readiness logic.

## KPI Rule Engine Scope
- Parses readiness rule expressions such as `M+3BD`, `M+5CD`, `D+1BD`, and similar variants.
- Calculates expected ready dates using business-date and calendar-date rules.
- Evaluates KPI readiness according to configurable conditions, including record existence, record count, and required KPI value presence.
- Supports KPI-specific readiness criteria sourced from metadata rather than hardcoded in logic.
- Produces structured readiness results with status (`Ready`, `Late`, `Missing`) and diagnostic reasons.
- Enables future extension to more complex rule forms without changing the core engine.

## Business Calendar Model
- Represents market-specific business calendars with date-level records and business-day flags.
- Handles weekends, public holidays, and market-specific non-business days.
- Supports lookup functions for `is_business_day`, `add_business_days`, `add_calendar_days`, and next/previous business day calculations.
- Uses calendar metadata from the configuration repository so calendars can be updated without code changes.
- Provides calendar ranges to support both daily and monthly readiness calculations.

## Dashboard Layer
- Streamlit-based visualization.
- Displays overview, channel, market, KPI, and trend views.
- Consumes persisted monitoring results.
