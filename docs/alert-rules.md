# Alert Rules

## Important Notice

The initial thresholds below are illustrative simulation settings only. They are not validated industrial operating limits or safety settings.

Real deployment requires equipment-specific limits approved by qualified personnel.

## 1. High Temperature

- Rule code: HIGH_TEMPERATURE
- Trigger: Temperature exceeds the configured simulation threshold.
- Persistence: Condition must remain true for three consecutive valid readings.
- Severity: WARNING or CRITICAL, depending on the configured threshold.
- Clear condition: Temperature falls below the configured recovery threshold.
- Recovery: Use hysteresis to avoid repeated open/close events near a threshold.

## 2. High Vibration

- Rule code: HIGH_VIBRATION
- Trigger: Vibration exceeds the configured simulation threshold for three consecutive valid readings.
- Severity: WARNING or CRITICAL according to the simulation configuration.
- Response: Create an alert and flag the asset for inspection.

## 3. Low Flow

- Rule code: LOW_FLOW
- Trigger: Flow remains below the configured minimum while the pump is expected to be operating.
- Persistence: Three consecutive valid readings.
- Response: Generate an alert and request investigation.

## 4. Abnormal Pressure

- Rule code: PRESSURE_ANOMALY
- Trigger: Pressure is outside the configured simulation range for three consecutive valid readings.
- Response: Record the event and flag the asset for inspection.

## 5. Stale Telemetry

- Rule code: STALE_TELEMETRY
- Trigger: No valid reading is received within the configured freshness interval while monitoring is expected.
- Response: Mark telemetry as stale and notify the operator.

## 6. Alert Lifecycle

- OPEN: An incident has been detected.
- ACKNOWLEDGED: A responsible user has acknowledged the incident.
- RESOLVED: The incident has been investigated and closed.

## 7. Duplicate Suppression

- One continuous incident should create one alert, not one alert per sensor reading.
- Repeated notifications must respect a configurable cooldown.
- A new alert can be created after the prior incident is resolved and the condition later recurs.

## 8. Safety Boundary

This prototype generates informational alerts and maintenance recommendations only. It must not issue automatic machine shutdown or control commands.
