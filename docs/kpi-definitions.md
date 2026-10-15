# KPI Definitions

## 1. Equipment Availability

**Formula**

Availability (%) = Operating Time / Scheduled Time × 100

**Requirements:** Scheduled time and confirmed operating/stopped states must be available. Missing state data must not be assumed to mean the pump was operating.

## 2. Downtime

**Formula**

Total Downtime = Sum of confirmed stopped intervals during the reporting period.

Overlapping downtime intervals must not be counted twice.

## 3. Mean Time Between Failures (MTBF)

**Formula**

MTBF = Total Operating Time / Number of qualifying failures

**Requirements:** Requires confirmed failure events and operating-time data. Sensor anomalies alone are not confirmed failures.

## 4. Mean Time To Repair (MTTR)

**Formula**

MTTR = Total Repair Duration / Number of completed qualifying repairs

**Requirements:** Requires reliable failure and repair timestamps. The treatment of waiting time must be documented.

## 5. Active Alerts

**Formula**

Count of distinct alerts whose status is OPEN or ACKNOWLEDGED at the reporting time.

Repeated sensor readings belonging to one incident must not create repeated alert counts.

## 6. Alert Acknowledgement Time

**Formula**

Acknowledgement Time = acknowledged_at - opened_at

Calculate only for acknowledged alerts.

## 7. Alert Resolution Time

**Formula**

Resolution Time = resolved_at - opened_at

Calculate only for resolved alerts.

## 8. Energy Consumption

For interval energy readings:

Total Energy = Sum of valid interval kWh readings.

For cumulative meter readings:

Energy Consumed = Latest Valid Meter Reading - Earliest Valid Meter Reading

Do not sum cumulative meter readings.

## 9. Flow Performance

Compare measured flow rate against the equipment's documented operating target.

Flow Performance (%) = Measured Flow Rate / Target Flow Rate × 100

This KPI requires a valid target for the asset and an appropriate operating state.

## 10. Data Freshness

Data Age = Current Time - Latest Valid Reading Timestamp

The dashboard must distinguish fresh readings from stale or disconnected equipment.

## KPI Reporting Rules

- Always state the reporting period and applicable equipment filters.
- Exclude invalid readings from calculations and report data-quality issues separately.
- Do not infer confirmed failures from threshold alerts alone.
- Document units and source fields for every KPI.
