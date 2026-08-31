# DKPI Data Readiness Monitoring Platform

**Version:** 1.1

**Status:** Draft

**Owner:** Jermyn Liu

---

# 1. Background

DKPI (Data KPI) data is produced across multiple business channels and markets.

Currently, data readiness is monitored manually through ad-hoc checking and validations, which introduces operational overhead and increases the risk of delayed data detection.

The goal of this project is to build a centralized monitoring dashboard that automatically tracks DKPI data readiness and provides visibility into data readiness status across channels, markets, and KPIs.

---

# 2. Objective

Build a monitoring platform that:

- Supports multiple data sources
- Uses Excel as the initial MVP data source
- Supports future migration to Databricks
- Monitors DKPI data readiness
- Calculates expected data ready dates
- Detects missing or delayed data
- Provides visual dashboards for monitoring
- Supports market-specific readiness rules
- Supports business-day based calculations

---

# 3. Project Scope

## Phase 1 (MVP1)

MVP1 supports only:

### Channel

- Agency

### Market

- CN

### Frequency

- Monthly

### Features

- Monthly KPI Data Monitoring
- KPI Readiness Calculation
- KPI Data Validation
- Missing Data Detection
- Dashboard Visualization
- Historical Tracking

---
### MVP1 Data Source Strategy

Due to current Databricks access restrictions, the MVP1 version shall use Excel files as the primary data source.

Excel files will simulate the structure and content of the corresponding Databricks source tables.

Actual MVP1 KPI source files shall be stored under `data/source/`. Standard and reference data used by validation rules shall be stored under `data/reference/`. Configuration files, including `kpi_config.xlsx`, `kpi_validation_rule_config.xlsx`, `calendar_config.xlsx`, and `source_table_mapping.xlsx`, shall remain under `configs/`.

The standard-value reference file is `data/reference/kpi_standard_values.xlsx`. It is used by `DEVIATION_FROM_STANDARD_WITHIN_PERCENT` and is looked up by `market + kpi_id + frequency + period`. The file shall contain `channel`, `market`, `kpi_id`, `kpi_name`, `frequency`, `period`, `standard_value`, `effective_from`, `effective_to`, and `remark`.

For the MVP1 Agency source file `Agency_data_checking_UC.csv`, the normalized source fields are `ACCOUNT_ID` for `kpi_id`, `ACCOUNT` for `kpi_name`, `PERIOD` for the monitoring period, and `VALUE` for the KPI value. AG0016 monthly validation uses the row where `ACCOUNT_ID = AG0016` and `PERIOD` equals the requested monthly period.

For markets where the source data contains sub-channel records, such as Singapore MAG/MFA or Indonesia sub-channels, the default validation grain is market-level aggregation. The system validates `channel + market + kpi_id + frequency + period` by summing KPI values across sub-channels. Source fields such as `DISTRIBUTION_CHANNEL` and `CHANNEL_CODE` do not change the default validation key and are not displayed in the MVP dashboard.

Only KPIs with a matching validation-rule binding in `kpi_validation_rule_config.xlsx` shall be validated. The binding match is the exact `channel + market + kpi_id + frequency` combination; matching `kpi_id` values from another market or channel shall not qualify a KPI for validation. KPI inventory rows without a matching validation-rule binding shall be skipped.

Validation results shall use the fixed file `data/results/kpi_validation_results.csv`. Each rule result shall include the validation execution date and timestamp. Results from different execution dates shall be retained as validation history. For the same `execution_date + channel + market + kpi_id + frequency + period` key, a later execution shall overwrite the complete earlier rule and summary result batch for that day. For example, three executions on `2026-08-28` retain only the last `2026-08-28` batch; a later execution on `2026-08-31` is appended and both dates remain persisted.

Each KPI shall also have one separate `KPI_SUMMARY` result row. The final result is `PASSED` only when all enabled rules pass; otherwise it is `FAILED` when a rule fails, `PREVIOUS_PERIOD_MISSING` when the previous-period input required by a comparison rule is unavailable, `STANDARD_VALUE_MISSING` when the configured standard input is unavailable, or `VALIDATION_INCOMPLETE` when the result cannot be completed for another configured prerequisite reason. Rule detail rows shall not repeat the KPI final result.

The result file shall also include ready-timing fields: `expected_ready_date`, `data_ready_time`, `ready_status`, and `ready_delay_days`. For source rows with `CREATE_DATE` populated and `UPDATE_DATE` empty, `CREATE_DATE` is the data ready time. If both are populated and `UPDATE_DATE > CREATE_DATE`, `UPDATE_DATE` is the data ready time. If both are empty, the validation execution timestamp is used as the data ready time. If the current execution date is before `target availability`, the KPI result is `NOT_DUE` and data validation rules are not executed.

For a target availability rule using `BD`, the expected ready date shall advance only across configured business days for the KPI market. Weekends and configured market holidays shall be skipped. SG target availability values such as `M+3BD` shall therefore use the SG rows in `calendar_config.xlsx`; the calendar input may use `Y/N` or boolean values for `is_business_day`, which the configuration layer shall normalize. If a market has no usable calendar rows, `BD` shall fall back to calendar-day arithmetic and the result shall remain executable.

When a source file contains a market field such as `BU_CODE`, validation shall be limited to the markets present in that uploaded source. This prevents incomplete configuration for an unrelated market from affecting the selected market's validation run.

If a selected, rule-configured KPI has no `target availability` value in `kpi_config.xlsx`, the run shall fail with the specific market, KPI, and channel so that incomplete KPI metadata can be corrected.

The result file shall include `aggregation_level` and `aggregation_detail`. MVP1 distribution validation persists `aggregation_level = Agency` and `aggregation_detail = ALL`; `Agency` is the canonical stored value, not a dashboard-only display label. Result writing shall normalize all legacy `MARKET` variants, including different letter cases or surrounding spaces, to `Agency`; no persisted result may retain `MARKET`. Sub-channel contribution is not displayed in the MVP dashboard.

When data is ready on or before the expected ready date, `ready_status` is `READY_ON_TIME`. When data is ready after the expected ready date, `ready_status` is `READY_DELAYED` and `ready_delay_days` is calculated using the same unit as the target availability rule: `BD` uses business-day delay and `CD` uses calendar-day delay. When no source record is available after the target date, `ready_status` is `DELAYED` and delay days are calculated from the expected ready date to the execution date.

Once Databricks access becomes available, the system should support migration to Databricks through configuration changes only.

No business logic changes should be required during the migration.

## MVP1 Implementation Scope

To reduce implementation risk and validate the architecture, the first MVP implementation will focus on a limited scope.

Channel:

- Agency

Market:

- CN

Frequency:

- Monthly

KPI:

- Selected representative KPIs

Data Source:

- Excel Files

The purpose of MVP1 is to validate the complete monthly monitoring workflow for Agency and CN before scaling to additional markets, KPIs and channels. Daily monitoring is outside MVP1.

## Future Phases

Additional channels:

- Risk
- Banca

Additional features:

- Email Notifications
- Alerting
- User Access Control
- Scheduled Monitoring Jobs
- Audit History

---

# 4. Business Structure

## Channels

The platform supports three business channels:

- Risk
- Banca
- Agency

### Current Scope

Only Agency is included in MVP1.

---

## Markets

Agency contains multiple markets.

Initial markets include:

- CN
- JP
- HK
- SG
- PH
- ID
- MM
- MY
- KH
- VN

Each market may have:

- Different data readiness rules
- Different business calendars
- Different source tables
- Different KPI inventories

## KPI Volume

Some markets may contain a large number of KPIs.

Example:

Agency CN

- 109+ KPIs

The architecture should be scalable enough to support:

- Multiple Channels
- Multiple Markets
- Thousands of KPI readiness checks

---

# 5. Data Readiness Concept

The platform measures whether KPIs are delivered on time according to predefined business rules.

## Example 1

Expected Ready Date:

2026-08-05

Actual Ready Date:

2026-08-04

Result:

- READY

---

## Example 2

Expected Ready Date:

2026-08-05

Actual Ready Date:

2026-08-07

Result:

- LATE

---

## Example 3

Expected Ready Date:

2026-08-05

Actual Ready Date:

Not Available

Result:

- MISSING

## 5.2 Status Taxonomy

The monitoring result status shall use exactly these values:

- `NOT_DUE`: the expected ready date has not been reached; readiness is not judged as late or missing.
- `READY`: the readiness conditions are satisfied and the actual ready date is on or before the expected ready date.
- `LATE`: the readiness conditions are satisfied and the actual ready date is after the expected ready date.
- `MISSING`: the expected ready date has been reached or passed and the readiness conditions are not satisfied, or a required date cannot be derived.

Ready timing is represented in validation output using `READY_ON_TIME`, `READY_DELAYED`, `DELAYED`, and `NOT_DUE`.

## 5.1 KPI Ready Determination

The platform shall determine KPI readiness based on configurable business rules.

A KPI may be considered Ready when:

- Expected records exist
- Record count is greater than zero
- Required KPI value is available
- Source data passes basic validation checks

Readiness determination logic may vary by KPI and shall be configurable.

Examples:

KPI A:

- Record Exists = Ready

KPI B:

- Record Exists
- Record Count > 0

KPI C:

- Record Exists
- KPI Value Not Null

The readiness determination method should be maintained through configuration rather than application code.

## 5.3 KPI Data Validation Rules

The `kpi_validation_rule_config.xlsx` file defines data checks for each KPI. The KPI `target availability` field defines when data is expected to be ready, while validation rules determine whether the available KPI data satisfies the configured checks.

The initial validation rule types are:

1. `RECORD_EXISTS`: at least one source record exists for the KPI and monitoring period.
2. `VALUE_NOT_NULL`: the configured KPI value is not null. KPIs that legitimately allow null values shall not have this rule configured.
3. `VALUE_GREATER_THAN_ZERO`: the configured KPI value is greater than zero.
4. `CHANGE_VS_PREVIOUS_PERIOD_WITHIN_PERCENT`: the absolute percentage change from the previous period does not exceed `threshold_percent`.
5. `DEVIATION_FROM_STANDARD_WITHIN_PERCENT`: the absolute percentage deviation from `standard_value` does not exceed `threshold_percent`.

Each row represents one validation-rule binding for one KPI. `rule_id` is a reusable generic rule identifier and does not contain `kpi_id`; multiple rows for the same KPI are evaluated in ascending `rule_order`, and all enabled rules must pass. The configuration shall include `channel`, `market`, `kpi_id`, `kpi_name`, `frequency`, `source_table`, `rule_id`, `rule_type`, `rule_order`, `value_column`, `threshold_percent`, `enabled`, `effective_from`, `effective_to`, and `remark`. Parameters not applicable to a rule type remain empty.

The same `rule_id` may be reused by different KPIs and markets. Thresholds and standard values are properties of the KPI rule binding, so comparison rules may use different values for different KPI and market combinations.

Every KPI must have both `kpi_id` and `kpi_name`. `kpi_id` is the stable identifier used for configuration relationships and joins; `kpi_name` is the human-readable KPI name used for display. The same `kpi_id` and `kpi_name` must be carried consistently into ready-date rules and validation rules.

Validation rules are configuration metadata only. New rule types may be added by introducing a new `rule_type` and its defined parameters without changing the KPI inventory structure.

Baseline validation rules may be generated from KPI inventory metadata. The generation process shall select KPI rows where `kpi_id` is populated, `monthly = Y`, and `derivation logic = EDL`; it shall upsert `RULE_RECORD_EXISTS`, `RULE_VALUE_NOT_NULL`, and `RULE_VALUE_GREATER_THAN_ZERO` without creating duplicates. Manually configured comparison rules shall be preserved.

---

# 6. Functional Requirements

## FR-001 Data Source Access

The platform shall support retrieving KPI data from configurable data sources.

Supported Data Sources:

### MVP1

- Excel Files

### Target State

- Databricks SQL Warehouse

### Future

- CSV Files
- API Sources

The active data source shall be configurable and switchable without changing monitoring logic.


---
## FR-002 Databricks Connection

The platform shall support connection to Databricks SQL Warehouse when access becomes available.

Capabilities:

- Execute SQL queries
- Retrieve source data
- Handle connection failures
- Retry on transient errors
- Generate application logs



## FR-003 Configuration Management

The platform shall support configuration-driven monitoring.

Each monitoring configuration contains:

- Channel
- Market
- KPI
- Frequency
- Source Table
- Target Availability
- Business Calendar
- KPI Validation Rules

Example:

| Channel | Market | KPI | Frequency | Rule |
|----------|----------|----------|----------|----------|
| Agency | CN | Premium | Monthly | M+3BD |

---

## FR-004 Daily Monitoring

Future scope after MVP1:

- Agency
- Banca

The platform shall:

- Calculate expected daily ready dates
- Determine data availability
- Identify missing records
- Determine readiness status

Output:

- `NOT_DUE`, `READY`, `LATE`, `MISSING`

---

## FR-005 Monthly Monitoring

Applicable to:

- Agency
- Risk (Future)
- Banca (Future)

The platform shall:

- Calculate expected monthly ready dates
- Determine actual ready dates
- Determine readiness status

Output:

- `NOT_DUE`, `READY`, `LATE`, `MISSING`

---

## FR-006 KPI Readiness Calculation

The platform shall support configurable readiness rules.

Examples:

### M+3BD

Month End + 3 Business Days

### M+5BD

Month End + 5 Business Days

### M+2CD

Month End + 2 Calendar Days

### M+5CD

Month End + 5 Calendar Days

### D+1BD

Data Date + 1 Business Day

### D+2CD

Data Date + 2 Calendar Days

For data-period-end availability, `T+CD2` means two calendar days after the data period end. The parser also accepts the equivalent normalized form `T+2CD`.

Where:

- BD = Business Day
- CD = Calendar Day

For a `BD` rule, the system shall first look up the configured business calendar for the monitoring market in `calendar_config.xlsx`. If a calendar is configured for that market, weekends and configured non-business days shall be excluded from the calculation. If no calendar is configured for the market, the `BD` offset shall fall back to calendar-day calculation. `CD` rules always use calendar-day calculation.

---

## FR-007 Dashboard

The platform shall provide dashboard views including:

MVP1 shall provide a Streamlit web page accessible by local URL. The page shall allow users to upload a KPI source file and a standard-value reference file. If no files are uploaded, the page shall use the default files under `data/source/` and `data/reference/`.

The dashboard visual style shall follow a Manulife-inspired enterprise design direction: green brand accent, clean white content surfaces, restrained typography, clear status colors, and dense operational tables suitable for repeated monitoring work. The page subtitle shall be `Distribution KPI Validation Dashboard`. The title band shall be compact and preserve vertical space for filters, KPI metrics, and validation tables. The selected-KPI status panel is not displayed because its information is available in the KPI Summary and Validation Rule Details tables.

The dashboard shall provide channel workspaces with the following frequency matrix: `Agency` supports `Monthly` and `Daily`; `Banca` supports `Monthly` and `Daily`; `Risk` supports `Monthly` only. The selected channel and frequency shall scope KPI inventory and validation-rule selection. A workspace without matching configured KPIs shall show an empty-state message and shall not execute another channel's rules.

After execution, the dashboard shall provide a compact filter bar for `Market`, `Period`, `MVP1/MVP2`, and `KPI Name`. Market and MVP use single-value selectors with `All markets` and `All phases` defaults, and Period uses a single selector. KPI Name uses a searchable multi-select dropdown; an empty selection means all KPIs, while selected names limit results to those KPIs. A `Reset filters` action restores these defaults. Filters shall apply consistently to the metric cards, KPI Summary, and Validation Rule Details.

The latest completed validation result and source data shall remain available while users change filters in the selected channel-frequency workspace. Changing filters shall not trigger a new validation run or require source files to be uploaded again.

The page shall allow users to select the validation period for the selected frequency. Monthly validation defaults to the previous month end. For example, when the current month is August, the default monthly validation period is July 31. Daily validation defaults to the current date.

After validation runs, the page shall display KPI-level results using `record_type = KPI_SUMMARY`. Users shall be able to select a KPI and view its rule-level validation details using `record_type = RULE`.

The dashboard shall display only the latest execution for each `channel + market + kpi_id + frequency + period` key, while persisted results retain prior execution dates. The KPI selector shall identify a KPI by channel, market, KPI ID, and KPI name. Rule details shall use the same `execution_timestamp` as the selected KPI summary so they always describe the displayed validation result.

The KPI Summary table shall hide internal fields `kpi_id`, `aggregation_level`, `aggregation_detail`, `execution_date`, and `execution_timestamp`. `data_ready_time` shall be displayed as `YYYY-MM-DD`. Validation Rule Details shall display `market` as its first column and hide `kpi_id` and `rule_id` in the page only. This display rule does not change the persisted result schema or remove either field from `data/results/kpi_validation_results.csv`. In Validation Rule Details, the `actual_value` for percentage-based comparison rules shall display one decimal place followed by `%`; non-percentage values retain their numeric representation.

The dashboard shall show two KPI metric rows. The first row contains `Expected KPI`, `Ready KPI`, `Missing KPI`, `Not Due KPI`, and `Delayed KPI`. The second row contains `Validation Passed` and `Validation Failed` and uses only the required content width, without empty metric-card placeholders.

Between the KPI metric rows and KPI Summary, the dashboard shall display a `Market KPI Overview` table. Each row represents the current `market + channel + frequency + period` scope and contains `Market`, `Channel`, `Frequency`, `Period`, `Expected KPI`, `Ready KPI`, `Missing KPI`, `Not Due KPI`, `Delayed KPI`, `Validation Passed`, and `Validation Failed`. Its KPI counts use the same definitions as the metric cards. Non-zero `Missing KPI`, `Delayed KPI`, and `Validation Failed` values shall be highlighted for operational attention. Selecting an overview row shall apply that market to the Market filter and move the page to KPI Summary. Cancelling that overview selection shall remove only the overview drill-down and restore the user's preceding Market filter value. The overview is calculated in the dashboard only and is not persisted to the validation result file.

Each KPI metric is an interactive drill-down control. Metric cards shall emphasize their numeric value with bold, readable treatment, and the selected metric shall have a clear active visual state. Selecting a metric shall filter KPI Summary to the KPIs represented by that metric and move the page to KPI Summary. Selecting a single KPI Summary row shall refresh Validation Rule Details using that row's exact `channel + market + kpi_id + frequency + period + execution_timestamp` and move the page to Validation Rule Details. Cancelling the KPI Summary selection shall clear Validation Rule Details and show a prompt to select a KPI. Validation Rule Details is read-only because it is the lowest dashboard drill-down level.

KPI Summary and Validation Rule Details shall use the same status highlighting. `PASSED` shall use a light-green background with dark-green bold text. `FAILED` shall use a light-yellow background with dark readable text. The status text remains visible so color is not the sole status indicator.

`Expected KPI` is the count of active KPI configuration rows in the selected channel and frequency where `derivation logic = EDL`, `kpi_id` is populated, and an exact `channel + market + kpi_id + frequency` validation-rule binding exists. `Ready KPI` is an Expected KPI whose `RULE_RECORD_EXISTS` result passed. `Missing KPI` is an Expected KPI with `ready_status = DELAYED` whose `RULE_RECORD_EXISTS` result did not pass. `Not Due KPI` is an Expected KPI with `ready_status = NOT_DUE`. `Delayed KPI` is an Expected KPI with `ready_status = READY_DELAYED` whose `RULE_RECORD_EXISTS` result passed. `Validation Passed` is an Expected KPI with `KPI_SUMMARY.status = PASSED`; `Validation Failed` is an Expected KPI whose executed summary status is neither `PASSED` nor `NOT_DUE`.

The page shall provide a configuration maintenance action to generate baseline validation rules for eligible KPI inventory rows and ensure the required `source_table + market` mappings exist in `source_table_mapping.xlsx`.

### Overview

MVP1 display:

- Total KPI Count
- Ready KPI Count
- Late KPI Count
- Missing KPI Count
- Overall Readiness %

---

### Channel View

Display:

- Channel
- Readiness %
- Late Count
- Missing Count

---

### Market View

Display:

- Market
- KPI Count
- Readiness %
- Latest Status

---

### KPI View

Display:

- KPI Name
- Expected Ready Date
- Actual Ready Date
- Status

### Validation Detail View

Display:

- Rule ID
- Rule Type
- Rule Status
- Actual Value
- Previous Period Value
- Standard Value
- Threshold Percent
- Diagnostic Reason

---

### Trend View

Display:

- Historical Readiness Trend
- Monthly Trend

---

# 7. Business Day Calculation

The platform shall support business-day aware calculations.

Business calendars may differ by market.

Examples:

- SG Calendar
- JP Calendar
- HK Calendar

Requirements:

- Exclude weekends
- Support public holidays
- Support market-specific calendars
- Future-proof for additional markets

The `calendar_config.xlsx` table is the source of market business-day information. A market is considered configured only when matching calendar records exist for the required calculation range. Markets without configured calendar records shall use calendar-day calculation as the fallback, including when their configured readiness rule uses `BD`.

---

# 8. Data Sources

Agency KPI data is logically sourced from three primary source tables.

During MVP1 implementation, source data may be provided through Excel files that replicate the contents of the source tables.

When Databricks access becomes available, the platform shall retrieve the same data directly from Databricks without requiring business logic changes.

## Source Tables

- Table_A
- Table_B
- Table_C

The KPI inventory in `kpi_config.xlsx` stores the logical `source_table` associated with each KPI. The `source_table_mapping.xlsx` configuration resolves that logical value, together with the KPI market, to the physical data object that must be read.

For MVP1 Excel execution, `provider_type` identifies the source provider and `physical_object_name` identifies the Excel file under `data/source/`. For example, a KPI with `source_table = agency_fact` and market `CN` is resolved through `source_table_mapping.xlsx` to `data/source/agency_fact.xlsx` before source data is checked for KPI readiness.

---

## Market Mapping

Different markets may use different source tables.

Example:

| Market | Source Table |
|----------|----------|
| CN | Table_A |
| HK | Table_A |
| JP | Table_B |
| SG | Table_B |
| ID | Table_C |
| MM | Table_C |

Final mapping will be maintained through configuration.

The mapping key is `source_table + market`. Every active KPI in `kpi_config.xlsx` must have a matching row in `source_table_mapping.xlsx`; the mapping row determines which physical file or table contains the KPI source data.

---

# 9. Data Source Abstraction

The platform shall support multiple data providers.

The monitoring engine should not depend on a specific data source implementation.

Supported data sources:

## MVP

- Excel Files

## Target State

- Databricks SQL Warehouse

## Future

- CSV Files
- API Sources

The data source should be configurable.

Business logic should remain unchanged when switching between data sources.

Example:

Current:

Excel Provider

Future:

Databricks Provider

The dashboard and monitoring engine should not require code changes during the transition.

## Migration Strategy

The MVP1 version will use Excel files due to current Databricks access restrictions.

Excel files shall replicate the structure and content of the corresponding Databricks tables.

The architecture shall support seamless migration from Excel Provider to Databricks Provider.

Migration should require configuration changes only.

No modifications should be required for:

- KPI Readiness Engine
- Business Day Engine
- Monitoring Logic
- Dashboard Components

# 10. KPI Target Availability Rules

Each KPI defines its expected ready-date rule in the `target availability` field of `kpi_config.xlsx`. This is the single source of truth for expected ready-date calculation.

Example:

| Market | KPI | Frequency | Target Availability |
|----------|----------|----------|----------|
| CN | Premium | Monthly | M+3BD |
| JP | Premium | Monthly | M+2BD |
| HK | APE | Monthly | M+5BD |

The platform must support rule configuration without requiring code changes.

---

# 11. Configuration Driven Design

The platform shall follow a configuration-driven design.

Business rules must not be hardcoded in application logic.

All readiness calculations shall be driven by configurable metadata.

Configuration should support:

- Channel
- Market
- KPI
- Frequency
- Source Table
- Date Column
- Target Availability
- Business Calendar

The KPI `Source Table` value is logical. Physical source lookup is performed by matching the KPI's logical `source_table` and `market` to `source_table_mapping.xlsx`. KPI data validation rules are loaded separately from `kpi_validation_rule_config.xlsx`.

The monitoring engine shall dynamically load configurations and apply readiness calculations based on configuration data.

Example:

| Channel | Market | KPI | Frequency | Target Availability |
|----------|----------|----------|----------|----------|
| Agency | CN | Premium | Monthly | M+3BD |
| Agency | JP | Premium | Monthly | M+2BD |
| Agency | HK | APE | Monthly | M+5BD |

Future configuration changes should not require application code changes.

## Architecture Principle

The platform must be configuration-driven.

Business rules, KPI mappings, source tables and readiness calculations shall be maintained through metadata configurations rather than application code.

## Additional Architecture Principle

Business logic must be completely independent from the physical data source.

The monitoring platform shall access data through a provider abstraction layer.

Supported providers:

- Excel Provider
- Databricks Provider

Future providers should be pluggable without affecting business logic.


# 12. Data Model

The platform shall maintain the following core entities.

## KPI Configuration

Stores KPI monitoring metadata.

Fields:

- Channel
- Market
- KPI ID
- KPI Name
- Monthly Flag
- Daily Flag
- Run Batch
- MVP1/MVP2
- Derivation Logic
- Integration Flag
- Target Availability
- Remark
- Source Table
- Active Flag
- Effective From
- Effective To

---

## KPI Validation Rule Configuration

Stores data validation rules for each KPI. The configuration file is `kpi_validation_rule_config.xlsx`, with one row per rule and these fields:

- Channel
- Market
- KPI ID
- KPI Name
- Frequency
- Source Table
- Rule ID
- Rule Type
- Rule Order
- Value Column
- Threshold Percent
- Standard Value
- Enabled
- Effective From
- Effective To
- Remark

The supported rule types are `RECORD_EXISTS`, `VALUE_NOT_NULL`, `VALUE_GREATER_THAN_ZERO`, `CHANGE_VS_PREVIOUS_PERIOD_WITHIN_PERCENT`, and `DEVIATION_FROM_STANDARD_WITHIN_PERCENT`. A KPI that permits NULL values does not configure `VALUE_NOT_NULL`. Generic `rule_id` values may be reused; the binding key is `market + kpi_id + frequency + rule_id + rule_order + effective_from`.

---

## Business Calendar

Stores market-specific business day definitions.

Fields:

- Market
- Calendar Date
- Is Business Day

---

## KPI Monitoring Result

Stores monitoring results.

Fields:

- Channel
- Market
- KPI ID
- KPI Name
- Expected Ready Date
- Actual Ready Date
- Status
- Execution Timestamp

## 12.1 Configuration Repository

The platform shall maintain monitoring configurations in a dedicated configuration repository.

### MVP1

Configuration files may be maintained using Excel files.

Examples:

- kpi_config.xlsx
- kpi_validation_rule_config.xlsx
- calendar_config.xlsx

### Target State

Configuration data shall be stored in Databricks configuration tables.

Examples:

- dim_kpi_config
- dim_business_calendar

The system should load configurations dynamically from the active configuration source.

Future migration from Excel to Databricks should require configuration changes only.

# 13. Non-Functional Requirements

## Performance

Dashboard response time:

- Less than 5 seconds

---

## Scalability

Support:

- 100+ KPI monitoring configurations

---

## Reliability

Readiness calculations must be:

- Accurate
- Repeatable
- Auditable

---

## Maintainability

The platform should support:

- New Markets
- New KPIs
- New Rules
- New Source Tables

Without major code changes.

---

# 14. Technology Stack

## Language

- Python

## Data Source

### MVP1

- Excel Files

### Target State

- Databricks SQL Warehouse


## Visualization

- Streamlit

## Testing

- Pytest

## Version Control

- GitHub

## AI Assistant

- GitHub Copilot Agent

## Deployment

### MVP1

- Local Execution

### Future

- Docker
- Databricks Apps
- Azure App Service

---

# 15. Success Criteria

The MVP1 is considered successful if:

- Agency channel is fully supported
- At least one market is implemented end-to-end
- Monthly monitoring works correctly
- Business day calculations work correctly
- Dashboard displays readiness status correctly
- Excel-based execution works correctly
- Excel Provider and Databricks Provider follow the same data contract
- Migration to Databricks requires configuration changes only
- Unit tests pass
- GitHub Copilot Agent is used throughout the development lifecycle

---

# 16. Future Enhancements

Potential future enhancements:

- Risk Channel Support
- Banca Channel Support
- Automated Notifications
- Alert Configuration
- User Management
- Databricks Job Monitoring
- Historical Trend Analytics
- AI-powered Readiness Analysis


# 17. Assumptions & Open Questions

## Assumptions

The following assumptions are made for the MVP phase:

- KPI source data can be provided through Excel files during MVP1.
- KPI source data will eventually be available in Databricks.
- Excel files can simulate the structure of Databricks source tables.
- Business calendars can be provided for each market.
- Markets without business-calendar configuration use calendar-day calculation for `BD` rules.
- KPI readiness rules can be maintained through configuration.
- Historical KPI data is available for validation and testing.
- Databricks SQL Warehouse is accessible from the application.

---

## Open Questions

The following items require further clarification:

### Business

- Final Agency market list
- Complete KPI inventory per market
- Ownership of KPI readiness rules

### Data

- Physical source table names
- Data refresh mechanisms
- Availability of holiday calendars

### Technology

- Production deployment strategy
- Authentication requirements
- Monitoring and alerting requirements

### Future Scope

- Risk channel rollout timeline
- Banca channel rollout timeline

# 18. Risks

## Access Risk

Databricks access is currently unavailable.

Impact:

- Direct integration cannot be validated during MVP1.

Mitigation:

- Use Excel Provider during MVP1.
- Ensure Excel structure matches Databricks table structure.
- Implement Data Source Abstraction layer.

---

## Business Rule Risk

Not all KPI readiness rules may be fully documented.

Impact:

- Incorrect readiness calculations.

Mitigation:

- Maintain readiness rules through configuration.
- Allow rule updates without code changes.

---

## Market Calendar Risk

Holiday calendars may vary by market.

Impact:

- Incorrect business day calculations.

Mitigation:

- Maintain market-specific business calendars.
- Support future calendar updates.

---

## Scalability Risk

The solution may need to support:

- 3 Channels
- 10+ Markets
- 100+ KPIs per Market

Impact:

- Performance degradation
- Complex rule maintenance

Mitigation:

- Configuration Driven Design
- Rule Engine Architecture
- Data Provider Abstraction