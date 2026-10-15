# System Architecture

## 1. Architecture Overview

The system simulates industrial pump telemetry, processes incoming messages, stores validated readings, detects abnormal conditions, and serves operational insights through a web dashboard.

## 2. Technology Stack

- Telemetry simulation: Python
- Messaging: MQTT with Eclipse Mosquitto
- Ingestion and processing: Python
- Database: PostgreSQL
- Backend API: FastAPI
- Live communication: WebSockets
- Frontend: React, TypeScript, and Vite
- Data analysis: SQL, Pandas, NumPy
- Historical reporting: Power BI Desktop
- Testing: pytest and API/performance tests
- Version control: Git and GitHub

## 3. Data Flow

1. A Python simulator generates timestamped sensor readings.
2. The simulator publishes messages to Mosquitto using MQTT.
3. A Python ingestion worker subscribes to the telemetry topic.
4. The worker validates readings and handles duplicate event IDs.
5. Valid readings are stored in PostgreSQL.
6. Rule-based checks evaluate readings and generate alert events.
7. FastAPI exposes asset, telemetry, alert, and maintenance endpoints.
8. WebSockets deliver incremental updates to connected dashboard clients.
9. React displays current equipment status and historical trends.
10. Power BI connects to curated database tables or views for historical reporting.

## 4. Reliability Considerations

- Use bounded database queries and connection pooling.
- Record event timestamps and server receipt timestamps separately.
- Handle MQTT reconnects and malformed messages.
- Prevent duplicate event processing.
- Resynchronize the dashboard after reconnection.
- Log ingestion errors and alert-processing failures.
- Keep credentials outside source control.

## 5. Security and Safety

The initial prototype will run locally.

The MQTT broker will remain local-only during development. No public broker exposure is required.

The prototype will issue alerts and maintenance recommendations only. It will not automatically control or shut down physical equipment.

## 6. Performance Strategy

- Use WebSockets for incremental updates.
- Avoid fetching full telemetry history for every dashboard update.
- Index frequently queried database fields.
- Limit historical query ranges and chart data points.
- Measure API latency, ingestion delay, and dashboard rendering performance.

## 7. Integration Boundaries

The prototype uses PostgreSQL and simulated sensor data.

Integration with actual PLCs, industrial gateways, IBM Db2, Oracle, or company infrastructure is outside the initial scope and requires confirmed technical requirements.