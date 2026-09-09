# DKPI Data Readiness Monitoring - Implementation Task Plan

## 1. Scope and Planning Rules

- Source documents: `docs/01_PRD.md`, `docs/02_ARCHITECTURE.md`
- Task granularity: each task is designed to be completed in less than 1 working day.
- Dependency notation:
	- `FS` = Finish-to-Start dependency (default)
	- `SS` = Start-to-Start dependency (can run in parallel once predecessor starts)
- Priority scale:
	- `P0` = critical for MVP1 path
	- `P1` = important for MVP1 quality and completeness
	- `P2` = post-MVP1 extension preparation
- MVP1 scope baseline:
	- Channel: Agency
	- Market: CN
	- Frequency: Monthly
	- KPI: selected representative KPIs
	- Source: Excel

## 2. Task Backlog

| Task ID | Task Name | Est. Effort | Priority | MVP1 | Dependencies | Acceptance Criteria |
|----------|----------|----------|----------|----------|----------|----------|
| T001 | Define Python environment and dependencies | 0.25 day | P0 | Yes | None | Virtual environment setup documented; required packages for pandas, streamlit, pydantic, openpyxl installed; project runs without missing import errors. |
| T002 | Finalize domain model classes | 0.5 day | P0 | Yes | T001 (FS) | Domain models require both `kpi_id` and `kpi_name` for KPI, validation-rule, and monitoring-result records; KPI models include target availability; model validation works for sample payloads. |
| T003 | Implement configuration loader entrypoint | 0.5 day | P0 | Yes | T002 (FS) | Config loader resolves configured source type and returns typed config entities; loader handles invalid source selection with clear error. |
| T004 | Build Excel configuration reader | 0.5 day | P0 | Yes | T003 (FS) | `kpi_config.xlsx`, `kpi_validation_rule_config.xlsx`, `calendar_config.xlsx`, and `source_table_mapping.xlsx` can be read into normalized dataframes; malformed sheet structure returns validation error. `data/reference/kpi_standard_values.xlsx` is available as the standard-value reference template. |
| T005 | Implement source table mapping resolution | 0.5 day | P0 | Yes | T004 (FS) | KPI `source_table + market` resolves to exactly one mapping row; the row supplies `provider_type` and physical Excel object name; missing or duplicate mappings are detected and reported. |
| T006 | Implement configuration validation rules | 0.75 day | P0 | Yes | T004 (FS), T005 (FS), T012A (FS) | Validation catches missing target availability, missing KPI IDs/names, mismatched KPI IDs/names, invalid calendar code references, duplicate active KPI keys, invalid validation-rule parameters, and malformed validation rule types; validation report is machine-readable. |
| T007 | Implement business calendar data loading | 0.5 day | P0 | Yes | T004 (FS) | Configured CN and MY calendar entries load with complete date coverage for the test period; MY covers the inclusive range `2026-07-01` to `2028-07-01` with weekend/public-holiday `Y/N` flags and holiday metadata; duplicates and missing dates are detected, while absent market calendars are represented as unconfigured. |
| T008 | Implement business calendar service core functions | 0.75 day | P0 | Yes | T007 (FS) | Configured markets use `is_business_day`, `add_business_days`, and holiday/weekend rules; markets without calendar entries use calendar-day fallback for `BD`; `add_calendar_days` is verified. |
| T009 | Implement target-availability parser | 0.5 day | P0 | Yes | T002 (FS), T008 (FS) | Parser supports configured target-availability forms including `M+nBD`, `M+nCD`, `D+nBD`, `D+nCD`, `T+CDn`, and normalized `T+nCD`; invalid formats are rejected with explicit error. |
| T010 | Implement expected ready date calculator | 0.5 day | P0 | Yes | T009 (FS), T008 (FS) | Expected ready date computation uses KPI `target_availability`; configured-market `BD`, unconfigured-market `BD` fallback, `CD`, and `T` data-period-end anchors pass tests. |
| T010B | Connect configured calendars to validation execution | 0.5 day | P0 | Yes | T010 (FS), T013 (FS) | Excel calendar rows normalize `Y/N` and boolean flags, SG `M+NBD` skips weekends/holidays during dashboard validation, and markets without usable calendar rows use documented calendar-day fallback. |
| T010C | Scope validation to configured markets | 0.25 day | P0 | Yes | T010B (FS), T013 (FS) | Dashboard execution uses the configured market set for the selected channel-frequency workspace instead of limiting execution to uploaded EDL `BU_CODE` markets. Source `BU_CODE` values are used only to match records for each configured market, so configured markets absent from the source are surfaced as missing when due. |
| T010D | Enforce configured KPI validation scope | 0.25 day | P0 | Yes | T012A (FS), T012B (FS) | Dashboard execution joins KPI inventory to validation rules by exact `channel + market + kpi_id + frequency`; KPIs without a matching validation-rule binding are skipped, and same-ID KPIs from another market or channel are not selected. Missing target availability fails with the specific market/KPI/channel. |
| T010A | Implement data ready time derivation | 0.5 day | P0 | Yes | T010 (FS) | Data ready time is derived from `CREATE_DATE` and `UPDATE_DATE`; when both are empty, validation execution timestamp is used. |
| T011 | Define readiness condition evaluator primitives | 0.5 day | P0 | Yes | T002 (FS) | Evaluator supports configured record/value readiness conditions; each condition returns pass/fail plus reason. |
| T012 | Implement composite readiness evaluator (`all_of`, `any_of`) | 0.5 day | P0 | Yes | T011 (FS) | Nested condition evaluation works; `all_of` returns first failed reason; `any_of` returns aggregated failure when all fail. |
| T012A | Define KPI validation rule model and repository | 0.5 day | P0 | Yes | T002 (FS), T004 (FS) | `kpi_validation_rule_config.xlsx` loads typed rule bindings for all five initial rule types; generic `rule_id` values are reusable across KPIs and markets, every binding carries both `kpi_id` and `kpi_name`, and thresholds may vary by binding. |
| T012B | Validate KPI validation rule configuration | 0.5 day | P0 | Yes | T012A (FS), T005 (FS) | Validation rejects missing required parameters, unsupported rule types, duplicate rule bindings, invalid thresholds, invalid KPI/source references, and missing standard-value references; generic rule IDs may repeat across KPI/market bindings, and KPIs without `VALUE_NOT_NULL` remain valid. Standard values are resolved from `data/reference/kpi_standard_values.xlsx` by market, KPI, frequency, and period. |
| T012C | Generate monthly EDL validation rules from KPI inventory | 0.5 day | P0 | Yes | T004 (FS), T005 (FS), T012A (FS), T012E (SS) | Dashboard action generates `RULE_RECORD_EXISTS`, `RULE_VALUE_NOT_NULL`, `RULE_VALUE_GREATER_THAN_ZERO`, `RULE_EDL_VS_ANAPLAN`, and `RULE_EDL_VS_PBI` for all rows with `kpi_id` populated, `monthly = Y`, and `derivation logic = EDL`; generation is idempotent and upserts the complete five-rule set, including rule orders 101/102 and comparison sources `ANAPLAN`/`PBI`. |
| T012D | Implement market-level KPI aggregation | 0.5 day | P0 | Yes | T012A (FS), T013 (FS) | Validation filters by market, KPI, period, and monthly mode, then sums `VALUE` across sub-channels; generated output records persist `aggregation_level = Agency` and `aggregation_detail = ALL`; result writes normalize all legacy `MARKET` case/whitespace variants to `Agency`. |
| T012E | Implement EDL downstream consistency rules | 1 day | P0 | Yes | T012A (FS), T012D (FS), T013 (FS) | `EDL_MATCH_ANAPLAN` at order 101 and `EDL_MATCH_PBI` at order 102 compare EDL with downstream values using mapping-backed KPI names. Downstream KPI names match mapping rows using case- and repeated-whitespace-insensitive text keys; six-row-header Anaplan exports support both `unit + KPI + month + value` and `unit + month + KPI + value` layouts, while `Jul 26`, `1 Aug 26`, and PBI timestamps such as `7/1/2026` normalize to the correct period keys. Downstream country names normalize to configured market codes. CN and markets without configured sub-channel comparison use Agency-level values; SG compares `SG-MAG`/`SG-MFA` independently, and ID compares `ID-GA`/`ID-BRANCH` independently. Values match within $10^{-5}$ or fail; when EDL is incorrect, a completed Override tracker value passes only if both Anaplan and PBI match it for every mismatching unit, with the override stated in `reason`. Missing mapped values also use `FAILED` with the detail in `reason`. |
| T013 | Implement Excel data provider table read | 0.5 day | P0 | Yes | T001 (FS), T005 (FS) | Provider reads the physical Excel object under `data/source/` resolved from KPI `source_table + market` mapping and date range; returns normalized dataframe with expected columns and dtypes. |
| T014 | Implement provider error mapping and retry handling | 0.5 day | P1 | Yes | T013 (FS) | Provider raises standardized error categories for config, schema, and transient failures; retry behavior defined for transient errors. |
| T015 | Implement provider factory selection | 0.25 day | P0 | Yes | T013 (FS) | Factory creates provider from configuration; unsupported provider type fails fast with clear message. |
| T016 | Implement result repository write path (MVP memory/file) | 0.5 day | P0 | Yes | T002 (FS) | Monitoring results persist with execution metadata; an MVP1 rerun overwrites the prior result set for the same monitoring slice and date; existing result CSV reads tolerate malformed historical rows by skipping unreadable rows and treat empty files as empty history. |
| T017 | Implement latest result retrieval query | 0.5 day | P1 | Yes | T016 (FS) | Latest query returns the stored MVP1 result per KPI slice and monitoring date; filters (channel, market, frequency, status) function correctly. |
| T018 | Implement result history retrieval query | 0.5 day | P1 | Yes | T016 (FS) | History query returns ordered MVP1 results across a date range; rerun versions are not retained in MVP1. |
| T019 | Build monitoring orchestration skeleton | 0.5 day | P0 | Yes | T006 (FS), T015 (FS), T016 (FS) | Orchestrator accepts run parameters (`channel`, `market`, `frequency`, `monitoring_date`) and executes configuration-to-result pipeline steps without KPI-specific branching. |
| T020 | Implement per-KPI execution loop | 0.75 day | P0 | Yes | T019 (FS), T010 (FS), T012 (FS), T013 (FS), T022 (FS) | For each active KPI, system computes expected date, evaluates readiness, derives actual date and status, and creates output record matching monitoring result schema. |
| T021 | Add execution metadata and versioning strategy | 0.5 day | P1 | Yes | T020 (FS), T016 (FS) | Execution ID and execution timestamp are generated and documented; MVP1 reruns overwrite the prior result set for the same monitoring slice and date. |
| T022 | Implement monitoring status derivation rules | 0.5 day | P0 | Yes | T010 (FS), T012 (FS) | `READY_EARLY`, `NOT_DUE`, `READY_ON_TIME`, `READY_DELAYED`, and `MISSING` semantics are implemented exactly as architecture definitions and verified via unit tests; past-due KPIs with no source record use `MISSING`; not-yet-due KPIs with source data use `READY_EARLY` and run the full configured validation rule set, while not-yet-due KPIs without source records use `NOT_DUE` and skip remaining validation after `RULE_RECORD_EXISTS`; legacy `DELAYED` ready-status values are normalized to `MISSING`. |
| T023 | Seed MVP1 sample configuration data | 0.5 day | P0 | Yes | T006 (FS), T007 (FS) | Agency-CN-Monthly KPI inventory with target availability, configured CN calendar, validation rules, `data/reference/kpi_standard_values.xlsx`, and `source_table_mapping.xlsx` rows resolving each active KPI to its physical Excel file are available and pass validation. |
| T024 | Prepare MVP1 sample Excel source data | 0.5 day | P0 | Yes | T013 (SS), T023 (SS) | Sample source files are stored under `data/source/`, include ready, late, and missing cases, and conform to normalized contract expectations. |
| T024A | Stage Monthly/Daily split project structure | 0.25 day | P0 | Yes | T023 (FS), T024 (FS) | Frequency-specific folders exist: `configs/monthly/`, `configs/daily/`, `configs/shared/`, `data/source/monthly/`, `data/source/daily/`, `data/results/monthly/`, and `data/results/daily/`. Monthly KPI config and validation-rule config are active from `configs/monthly/`; shared `agency_kpi_mapping.xlsx`, `calendar_config.xlsx`, and `source_table_mapping.xlsx` are available from `configs/shared/`; legacy top-level config remains fallback during transition. |
| T025 | Build Streamlit dashboard skeleton and navigation | 0.5 day | P1 | Yes | T030B (FS), T012C (FS) | Dashboard loads successfully by local URL and provides Agency and Banca Monthly/Daily workspaces plus a Risk Monthly workspace. Each workspace provides a `Data files` section that is expanded before a result exists and collapses automatically after validation completes. Monthly workspaces include EDL/Anaplan/PBI/Override tracker/standard file upload controls with Monthly defaults for omitted EDL, Anaplan, PBI, and standard files; Override tracker remains explicit upload only. Daily workspaces render the same five-file upload structure with Daily-specific labels, start empty, do not reuse Monthly uploads or Monthly default source files, and require only Daily EDL before execution. Daily Anaplan and PBI are optional comparison inputs; omitted files make the corresponding comparison rules fail with a diagnostic reason. The workspace also provides frequency-appropriate period selection, KPI summary, rule-detail sections, and frequency-aware rule generation with Manulife-inspired green enterprise styling. |
| T025B | Generate Daily EDL validation rules | 0.25 day | P1 | Yes | T024A (FS), T012E (FS) | Daily configuration maintenance button is labeled `Generate EDL daily validation rules` when the Daily workspace is selected. Clicking it reads `configs/daily/kpi_config.xlsx` and upserts `RECORD_EXISTS`, `VALUE_NOT_NULL`, `VALUE_GREATER_THAN_ZERO`, `EDL_MATCH_ANAPLAN`, and `EDL_MATCH_PBI` into `configs/daily/kpi_validation_rule_config.xlsx` for every populated Daily EDL KPI, using rule orders 1, 2, 3, 101, and 102 with comparison sources `ANAPLAN` and `PBI`. |
| T025C | Implement Daily validation execution | 0.5 day | P1 | Yes | T024A (FS), T025 (FS), T025B (FS) | Daily validation uses `configs/daily/` KPI and validation-rule workbooks, shared calendar data, and independent persistence under `data/results/daily/kpi_validation_results.csv`. Daily rules follow the Monthly validation pattern. Daily runs accept a single start date or an inclusive start/end date range with `end >= start` enforced. Daily Anaplan `1 Aug 26` labels normalize to exact daily period keys, and Daily PBI accepts `Line Items` as the KPI-name column with exact daily timestamps. Daily Expected KPI scope is driven by configured Daily KPIs and target availability, not uploaded EDL `BU_CODE` markets; metrics operate at KPI-day grain, so every expected KPI is counted once per included expected date. Due configured markets missing from EDL, such as CN or JP, are reported as `MISSING`. SG and HK Daily KPIs are expected only on configured working days; non-working selected dates exclude those market KPI-days from Expected and all validation metrics, while working-day target availability is evaluated with business-day arithmetic. |
| T025D | Add Daily validation calendar | 0.25 day | P1 | Yes | T025C (FS) | Daily dashboard renders calendar grids before Validation Rule Details using Daily `KPI_SUMMARY` history filtered by an inclusive Start/End date range when no KPI Summary row is selected. Green means all executed Daily KPI validations passed; red means at least one KPI is `MISSING`; yellow means no Missing KPI but at least one validation failed; gray means only `NOT_DUE` results or no execution. Missing has priority over failed. Each calendar cell displays the day and outcome summary. A range that crosses months renders one calendar grid per included month. Calendar aggregation uses the same Start/End date, Market, MVP, KPI Name, and metric drill-down KPI-day scope as KPI Summary. Selecting a Summary row hides the calendar; clearing selection restores it. |
| T025A | Scope dashboard execution by channel and frequency | 0.5 day | P1 | Yes | T025 (FS), T012A (FS) | Selected Channel/Frequency filters KPI inventory and validation rules before market filtering. Monthly reads KPI inventory and validation rules from `configs/monthly/`; Daily reads them from `configs/daily/`; both use shared and legacy config fallback. Monthly defaults to the prior month-end, Daily defaults to the current date, and an unconfigured workspace shows an empty state without executing another channel's rules. |
| T026 | Implement dashboard KPI status summary view | 0.5 day | P1 | Yes | T025 (FS), T022 (FS), T030B (FS) | Summary table displays only the latest `KPI_SUMMARY` result per `channel + market + kpi_id + frequency + period`, including ready status, delay days, validation status, and reason; it places `status = FAILED` rows first for both Monthly and Daily validation using stable ordering, hides `kpi_id`, aggregation fields, execution metadata, and cross-system comparison diagnostics, and displays `data_ready_time` as `YYYY-MM-DD`. A compact title band and user-friendly Market/Period/MVP1-MVP2/KPI Name filters apply to the metric cards and summary data. |
| T026A | Implement expected KPI readiness metrics | 0.5 day | P1 | Yes | T010D (FS), T026 (FS), T030B (FS) | Two metric rows show Expected, Ready, Missing, Not Due, Delayed, Validation Passed, and Validation Failed. Cards emphasize numeric values and show an active selection state. Expected KPI count is limited to active, EDL, non-null KPI IDs with an exact rule binding; all metric categories use the documented summary and `RULE_RECORD_EXISTS` status definitions. Ready KPI includes any Expected KPI with a passed `RULE_RECORD_EXISTS`, including `READY_EARLY` source data before target availability. Not Due KPI includes only `ready_status = NOT_DUE` KPIs whose `RULE_RECORD_EXISTS` did not pass. `READY_EARLY` KPIs run the full configured validation rule set and are counted in Validation Passed or Validation Failed by summary status; `NOT_DUE` KPIs without source records remain excluded from pass/fail. The validation row uses content width only. Clicking a metric filters KPI Summary and the Daily validation calendar to that metric's KPI key set, clears stale Summary selection, and creates a unique KPI Summary scroll request after rerender so repeated selections always navigate there. Daily keys include period so the scope remains at KPI-day grain. |
| T026B | Improve dashboard filter ergonomics | 0.25 day | P1 | Yes | T026 (FS), T026A (FS) | Market and MVP use `All` single selectors, Period uses a resettable selector that defaults to the currently selected validation period, KPI Name provides a searchable multi-select dropdown with empty selection meaning all KPIs, Reset filters explicitly restores widget default values, resets Period to the current validation period, clears metric drill-down, Market KPI Overview row selection, KPI Summary row selection, and drill-down market state, and Streamlit session state retains completed channel-frequency results while users refine filters. When both Monthly and Daily have results, switching frequency preserves each workspace's sidebar period inputs, filters, metric drill-down, table selection state, and last viewed Results/KPI Summary/Validation Rule Details section. Returning to Daily uses its saved validation date range as the sidebar default so results are not cleared by a recreated date widget. Daily sidebar start/end date changes invalidate the prior completed Daily result workspace so Results cannot retain stale dates from an older run. |
| T026C | Add Market KPI Overview | 0.5 day | P1 | Yes | T026A (FS), T026B (FS) | A dashboard-only table between metric cards and KPI Summary groups the filtered Expected KPI set by Market and displays Channel, Frequency, Period, and the seven KPI counts. The table keeps this full schema even when the current scope has no rows, so Missing, Delayed, and Validation Failed highlighting never fails on absent columns. Non-zero Missing, Delayed, and Validation Failed counts are highlighted. Selecting one market row stores a pending Market from the dataframe event and reruns; the next render applies Market before its selectbox is instantiated, suppresses the resulting programmatic Market filter change from clearing selection, filters KPI Summary and Daily calendar to that market, and uses the KPI Summary element anchor to scroll there while the overview remains rendered at the pre-drill-down scope. Clearing the selected row with one deselection restores the user's prior Market filter and clears Summary selection, and manual Market selection exits the drill-down. No overview records are persisted. |
| T027 | Implement dashboard rule detail view | 0.5 day | P1 | Yes | T025 (FS), T030B (FS), T012E (FS) | Selecting one KPI Summary dataframe row displays only matching `RULE` rows from the same `channel + market + kpi_id + frequency + period + execution_timestamp` and navigates to the detail section. Clearing the Summary selection clears details and shows a selection prompt. Details are read-only, lead with market, and include rule type, status, actual value, previous value, standard value, threshold, baseline/comparison source, comparison level, compared values, difference, and reason. `kpi_id` and `rule_id` are hidden only in the UI and remain persisted. Sub-channel contribution is not rendered in the MVP dashboard. `PASSED` and `FAILED` status cells use accessible green/yellow highlighting consistent with KPI Summary. Percentage-based `actual_value` values display one decimal place with a `%` suffix. The redundant selected-KPI status panel is not rendered. |
| T028 | Add unit tests for calendar and rule engine | 0.75 day | P0 | Yes | T010 (FS), T012 (FS) | Test suite covers configured-market business-day calculations, unconfigured-market calendar-day fallback, rule parsing, expected dates, and readiness condition pass/fail variants. |
| T028A | Add unit tests for KPI validation rules | 0.75 day | P0 | Yes | T012B (FS) | Tests cover record existence, nullable KPI exceptions, non-null values, values greater than zero, previous-period percentage thresholds, standard-value percentage thresholds, diagnostic failures, missing comparison inputs, AG0016 monthly row selection by `ACCOUNT_ID` and `PERIOD`, monthly Anaplan `Aug 26` column-order detection, daily Anaplan period parsing, and SG business-day target availability across weekends. |
| T029 | Add unit tests for provider normalization | 0.5 day | P1 | Yes | T013 (FS), T014 (FS) | Tests verify normalized columns, data types, null handling, and error mapping behavior for Excel provider. |
| T030 | Add integration test for end-to-end monthly run | 0.75 day | P0 | Yes | T020 (FS), T023 (FS), T024 (FS), T016 (FS), T028 (FS), T037 (FS) | One run from config load to result persistence succeeds and produces expected statuses for not-due, ready, late, and missing sample KPIs. AG0016 `PERIOD=2026-07-31` validation uses the reference standard value and generates output under `data/results/`. |
| T030A | Implement fixed validation result output | 0.5 day | P0 | Yes | T028A (FS), T010A (FS), T010D (FS), T012E (FS) | Results are written to fixed file `data/results/kpi_validation_results.csv`; only rule-configured KPIs are persisted; rule rows include execution date, timestamp, expected ready date, data ready time, ready status, delay days, aggregation fields, and EDL/Anaplan/PBI baseline, comparison, and difference fields; all stored `aggregation_level` values use `Agency`, with legacy `MARKET` values migrated during writes; different execution dates are appended as history. |
| T030B | Implement KPI validation summary result | 0.5 day | P0 | Yes | T030A (FS) | Each execution batch has one `KPI_SUMMARY` row per KPI; `status` represents rule result on `RULE` rows and KPI final result on `KPI_SUMMARY` rows; rule rows do not repeat the final result. Dashboard display selects the latest summary batch. |
| T031 | Add regression test for rerun overwrite behavior | 0.5 day | P1 | Yes | T021 (FS), T030B (FS) | Re-execution overwrites the earlier complete rule and summary batch only when `execution_date + channel + market + kpi_id + frequency + period` matches. Results from different execution dates remain persisted as history, while the dashboard displays the latest execution timestamp. |
| T032 | Add architecture conformance checklist | 0.25 day | P1 | Yes | T030 (FS) | Checklist verifies contracts from architecture doc are represented in code interfaces and model schemas; no unresolved ambiguity items remain. |
| T033 | Add operational logging for orchestration steps | 0.5 day | P1 | Yes | T020 (FS) | Logs include execution ID, KPI key, provider operation, rule evaluation outcome, and persistence status. |
| T034 | Create Databricks provider interface stub | 0.5 day | P2 | No | T015 (FS) | Databricks provider class compiles against provider contract with method stubs and TODO markers; no business logic changes needed. |
| T035 | Create config switch playbook (Excel to Databricks) | 0.25 day | P2 | No | T034 (FS), T032 (FS) | Documentation defines only configuration changes required for provider migration and validates unchanged engine/rule code path. |
| T036 | Confirm MVP scope (MVP1) sign-off | 0.25 day | P0 | Yes | None | Written sign-off confirms MVP1 delivery scope is Agency-CN-Monthly only and daily monitoring is deferred beyond MVP1. |
| T037 | Implement schema drift validation (pre-run) | 0.5 day | P0 | Yes | T006 (FS), T013 (FS) | Before each monitoring run, schema drift checks validate config and source columns/types; violations fail fast with actionable error messages. |
| T038 | Execute business UAT and sign-off | 0.5 day | P0 | Yes | T026 (FS), T027 (FS), T030 (FS) | UAT checklist is executed with business users, defects triaged, and formal MVP1 acceptance decision documented. |
| T039 | Create operational runbook (MVP1) | 0.5 day | P1 | Yes | T033 (FS), T038 (FS) | Runbook documents setup, execution command, monitoring flow, common failures, and recovery actions; walkthrough completed with handover audience. |

## 3. MVP1 Critical Path

The minimum sequence to deliver MVP1 usable functionality is:

T036 -> T001 -> T002 -> T003 -> T004 -> T005 -> T012A -> T012B -> T012C -> T012D -> T012E -> T006 -> T007 -> T008 -> T009 -> T010 -> T010A -> T010B -> T010C -> T010D -> T011 -> T012 -> T013 -> T014 -> T015 -> T016 -> T019 -> T022 -> T020 -> T023 -> T024 -> T028 -> T028A -> T037 -> T030 -> T030A -> T030B -> T017 -> T018 -> T025 -> T025A -> T026 -> T026A -> T026B -> T026C -> T027 -> T033 -> T038 -> T039

Notes:
- Daily monitoring support remains outside MVP1; MVP1 implements only the Agency-CN-Monthly flow defined in the PRD.
- Tasks marked `MVP1 = Yes` but not on critical path are quality/completeness tasks that can run in parallel.

## 4. Suggested Execution Waves

### Wave A - Foundation (Day 1 to Day 3 equivalent effort)
- T001, T002, T003, T004, T005, T006

### Wave B - Rules and Calendar (Day 3 to Day 5 equivalent effort)
- T007, T008, T009, T010, T011, T012

### Wave C - Data and Orchestration (Day 5 to Day 7 equivalent effort)
- T013, T014, T015, T016, T019, T020, T021, T022

### Wave D - MVP1 Data and Verification (Day 7 to Day 9 equivalent effort)
- T023, T024, T028, T029, T030, T031, T032, T033

### Wave E - Dashboard and Handover (Day 9 to Day 10 equivalent effort)
- T017, T018, T025, T026, T027

### Wave F - Post-MVP1 Readiness (Optional)
- T034, T035

### Wave G - MVP1 Governance and Handover Controls
- T036, T037, T038, T039

## 5. Deferred to V2

The following items are explicitly deferred and not required for MVP1 delivery:

- CI/CD quality gates
- Performance benchmarking
- Full idempotency and preservation of all rerun versions; MVP1 uses overwrite-on-rerun.
- Configuration approval workflow

## 6. Accepted Review Items Incorporated

The accepted review items are incorporated as follows:

- MVP Scope Confirmation: T036
- Configuration Validation: T006
- Schema Drift Validation: T037
- Provider Error Handling: T014
- Business UAT: T038
- Operational Runbook: T039

## 7. Definition of Done for MVP1

MVP1 is complete when all conditions are met:

- All `P0` tasks with `MVP1 = Yes` are completed and accepted.
- End-to-end Agency CN Monthly run produces expected `NOT_DUE`, `READY`, `LATE`, and `MISSING` outcomes using Excel source.
- Pre-run schema contract validation is active and blocks invalid configuration or source schema before execution.
- Dashboard displays latest status and history from persisted monitoring results.
- UAT is completed with documented acceptance decision.
- Operations runbook is published and reviewed.
- Contract-level architecture ambiguity is closed through implemented schemas and interface-aligned code.
- Test suite includes unit and integration coverage for rule engine, calendar, provider normalization, and orchestration pipeline.
