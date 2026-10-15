# Industrial Pump Health Analytics

## 1. Project Overview

This project is an independently developed industrial analytics prototype inspired by industrial IoT, pump monitoring, and predictive maintenance use cases.

The prototype uses simulated telemetry data to monitor pump conditions, identify abnormal readings, generate alerts, and analyze historical equipment performance.

## 2. Business Problem

Industrial pump problems such as overheating, abnormal vibration, pressure changes, and insufficient flow can affect operational reliability.

The proposed system aims to help operators identify potential issues earlier and give maintenance teams useful information for investigation.

## 3. Project Objectives

- Simulate telemetry from multiple industrial pumps.
- Receive sensor messages through MQTT.
- Validate and store readings in PostgreSQL.
- Calculate equipment health and operational KPIs.
- Detect threshold violations and selected abnormal patterns.
- Generate and track maintenance alerts.
- Display near-real-time updates in a React dashboard.
- Analyze historical performance using SQL, Python, and Power BI.
- Measure dashboard responsiveness and data pipeline latency.

## 4. Intended Users

- Plant operators
- Maintenance engineers
- Operations managers

## 5. Initial Scope

The first version will use locally simulated telemetry and will run on a Windows development machine.

No physical PLC integration, real industrial deployment, or automatic machine shutdown is included.

## 6. Success Criteria

- Sensor messages can be published and received through MQTT.
- Valid readings are stored without unintended duplicate records.
- Dashboard metrics match validated database calculations.
- Abnormal test scenarios generate the expected alerts.
- The dashboard updates without full-page reloads.
- Performance results are measured and documented.
- Another developer can follow the setup instructions to reproduce the prototype.

## 7. Limitations

The initial data is simulated and does not establish real-world failure prediction accuracy or industrial safety compliance.

All operational thresholds and model results must be validated before any real deployment.