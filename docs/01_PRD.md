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
- Missing Data Detection
- Dashboard Visualization
- Historical Tracking

---
### MVP1 Data Source Strategy

Due to current Databricks access restrictions, the MVP1 version shall use Excel files as the primary data source.

Excel files will simulate the structure and content of the corresponding Databricks source tables.

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
- Ready Rule
- Business Calendar

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

Where:

- BD = Business Day
- CD = Calendar Day

---

## FR-007 Dashboard

The platform shall provide dashboard views including:

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

---

# 8. Data Sources

Agency KPI data is logically sourced from three primary source tables.

During MVP1 implementation, source data may be provided through Excel files that replicate the contents of the source tables.

When Databricks access becomes available, the platform shall retrieve the same data directly from Databricks without requiring business logic changes.

## Source Tables

- Table_A
- Table_B
- Table_C

Actual physical table names will be confirmed later.

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

# 10. KPI Readiness Rules

Each market may have different KPI readiness rules.

Example:

| Market | KPI | Frequency | Ready Rule |
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
- Ready Rule
- Business Calendar

The monitoring engine shall dynamically load configurations and apply readiness calculations based on configuration data.

Example:

| Channel | Market | KPI | Frequency | Ready Rule |
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
- KPI Name
- Frequency
- Source Table
- Date Column
- Value Column
- Market Column
- Active Flag

---

## Ready Rule Configuration

Stores KPI readiness rules.

Fields:

- Channel
- Market
- KPI Name
- Ready Rule
- Business Calendar
- Effective From
- Effective To

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
- ready_rule_config.xlsx
- calendar_config.xlsx

### Target State

Configuration data shall be stored in Databricks configuration tables.

Examples:

- dim_kpi_config
- dim_ready_rule
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
- Daily monitoring works correctly
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