# Data Dictionary

## 1. Assets

| Field | Type | Description |
|---|---|---|
| asset_id | TEXT | Unique equipment identifier |
| asset_name | TEXT | Readable pump name |
| location | TEXT | Plant or area |
| rated_power_kw | NUMERIC | Rated motor power in kW |
| status | TEXT | Current operational state |
| installed_at | TIMESTAMPTZ | Installation timestamp |

## 2. Telemetry

| Field | Type | Description |
|---|---|---|
| reading_id | BIGINT | Database-generated reading ID |
| asset_id | TEXT | Reference to the asset |
| event_id | UUID | Unique telemetry event ID |
| recorded_at | TIMESTAMPTZ | Time the reading was recorded |
| received_at | TIMESTAMPTZ | Time the server received the event |
| temperature_c | DOUBLE PRECISION | Temperature in degrees Celsius |
| vibration_mm_s | DOUBLE PRECISION | Vibration velocity in mm/s |
| pressure_bar | DOUBLE PRECISION | Pressure in bar |
| flow_rate_m3_h | DOUBLE PRECISION | Flow rate in cubic metres per hour |
| motor_current_a | DOUBLE PRECISION | Motor current in amperes |
| energy_kwh | DOUBLE PRECISION | Energy value in kWh; measurement semantics must be defined |

## 3. Alert Events

| Field | Type | Description |
|---|---|---|
| alert_id | UUID | Unique alert identifier |
| asset_id | TEXT | Related equipment |
| rule_code | TEXT | Rule that generated the alert |
| severity | TEXT | Alert severity |
| status | TEXT | Open, acknowledged, or resolved |
| opened_at | TIMESTAMPTZ | Alert creation time |
| acknowledged_at | TIMESTAMPTZ | Acknowledgement time |
| resolved_at | TIMESTAMPTZ | Resolution time |

## 4. Maintenance Records

| Field | Type | Description |
|---|---|---|
| work_order_id | UUID | Unique work-order identifier |
| asset_id | TEXT | Related equipment |
| alert_id | UUID | Related alert, when applicable |
| description | TEXT | Maintenance issue or action |
| assigned_to | TEXT | Responsible person or team |
| status | TEXT | Work-order status |
| created_at | TIMESTAMPTZ | Creation timestamp |
| resolved_at | TIMESTAMPTZ | Resolution timestamp |

## 5. Data Quality Rules

- Every telemetry event must have a valid event ID and asset ID.
- Timestamps must include timezone information.
- Sensor units must be consistent.
- Missing readings must not silently be replaced with zero.
- Duplicate event IDs must not create duplicate readings.
- Invalid sensor values must be logged and handled according to validation rules.
- Simulated data must be clearly identified as simulated.
