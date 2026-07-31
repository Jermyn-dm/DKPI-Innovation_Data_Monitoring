# DKPI Data Readiness Monitoring Platform

**Version:** 1.0

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

- Connects to Databricks
- Monitors DKPI data readiness
- Calculates expected data ready dates
- Detects missing or delayed data
- Provides visual dashboards for monitoring
- Supports market-specific readiness rules
- Supports business-day based calculations

---

# 3. Project Scope

## Phase 1 (MVP11)

Only support:

### Channel

- Agency

### Features

- Daily KPI Data Monitoring
- Monthly KPI Data Monitoring
- KPI Readiness Calculation
- Missing Data Detection
- Dashboard Visualization
- Historical Tracking

---

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

---

# 5. Data Readiness Concept

The platform measures whether KPIs are delivered on time according to predefined business rules.

## Example 1

Expected Ready Date:

2026-08-05

Actual Ready Date:

2026-08-04

Result:

- Ready
- On Time

---

## Example 2

Expected Ready Date:

2026-08-05

Actual Ready Date:

2026-08-07

Result:

- Ready
- Late

---

## Example 3

Expected Ready Date:

2026-08-05

Actual Ready Date:

Not Available

Result:

- Missing

---

# 6. Functional Requirements

## FR-001 Databricks Connection

The platform shall support connection to Databricks SQL Warehouse.

Capabilities:

- Execute SQL queries
- Retrieve source data
- Handle connection failures
- Retry on transient errors
- Generate application logs

---

## FR-002 Configuration Management

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

## FR-003 Daily Monitoring

Applicable to:

- Agency
- Banca (Future)

The platform shall:

- Calculate expected daily ready dates
- Determine data availability
- Identify missing records
- Determine readiness status

Output:

- Ready
- Late
- Missing

---

## FR-004 Monthly Monitoring

Applicable to:

- Agency
- Risk (Future)
- Banca (Future)

The platform shall:

- Calculate expected monthly ready dates
- Determine actual ready dates
- Determine readiness status

Output:

- Ready
- Late
- Missing

---

## FR-005 KPI Readiness Calculation

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

## FR-006 Dashboard

The platform shall provide dashboard views including:

### Overview

Display:

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
- Daily Trend
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

Agency KPI data is sourced from three primary tables.

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

# 9. KPI Readiness Rules

Each market may have different KPI readiness rules.

Example:

| Market | KPI | Frequency | Ready Rule |
|----------|----------|----------|----------|
| CN | Premium | Monthly | M+3BD |
| JP | Premium | Monthly | M+2BD |
| HK | APE | Monthly | M+5BD |

The platform must support rule configuration without requiring code changes.

---

# 10. Configuration Driven Design

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

# 11. Data Model

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

# 12. Non-Functional Requirements

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

# 13. Technology Stack

## Language

- Python

## Data Source

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

# 14. Success Criteria

The MVP1 is considered successful if:

- Agency channel is fully supported
- At least one market is implemented end-to-end
- Daily monitoring works correctly
- Monthly monitoring works correctly
- Business day calculations work correctly
- Dashboard displays readiness status correctly
- Unit tests pass
- GitHub Copilot Agent is used throughout the development lifecycle

---

# 15. Future Enhancements

Potential future enhancements:

- Risk Channel Support
- Banca Channel Support
- Automated Notifications
- Alert Configuration
- User Management
- Databricks Job Monitoring
- Historical Trend Analytics
- AI-powered Readiness Analysis


# 16. Assumptions & Open Questions

## Assumptions

The following assumptions are made for the MVP phase:

- KPI source data is available in Databricks.
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