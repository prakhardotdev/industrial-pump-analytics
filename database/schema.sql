
BEGIN;

CREATE TABLE assets (
    asset_id TEXT PRIMARY KEY,
    asset_name TEXT NOT NULL,
    location TEXT,
    rated_power_kw NUMERIC(10,2)
        CHECK (rated_power_kw IS NULL OR rated_power_kw > 0),
    status TEXT NOT NULL DEFAULT 'UNKNOWN'
        CHECK (status IN ('RUNNING', 'STOPPED', 'MAINTENANCE', 'UNKNOWN')),
    installed_at TIMESTAMPTZ
);

CREATE TABLE telemetry (
    reading_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    asset_id TEXT NOT NULL REFERENCES assets(asset_id),
    event_id UUID NOT NULL UNIQUE,
    recorded_at TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    temperature_c DOUBLE PRECISION,
    vibration_mm_s DOUBLE PRECISION,
    pressure_bar DOUBLE PRECISION,
    flow_rate_m3_h DOUBLE PRECISION,
    motor_current_a DOUBLE PRECISION,
    energy_kwh DOUBLE PRECISION,

    CHECK (temperature_c IS NULL OR temperature_c >= -273.15),
    CHECK (vibration_mm_s IS NULL OR vibration_mm_s >= 0),
    CHECK (pressure_bar IS NULL OR pressure_bar >= 0),
    CHECK (flow_rate_m3_h IS NULL OR flow_rate_m3_h >= 0),
    CHECK (motor_current_a IS NULL OR motor_current_a >= 0),
    CHECK (energy_kwh IS NULL OR energy_kwh >= 0),

    CHECK (
        temperature_c IS NOT NULL
        OR vibration_mm_s IS NOT NULL
        OR pressure_bar IS NOT NULL
        OR flow_rate_m3_h IS NOT NULL
        OR motor_current_a IS NOT NULL
        OR energy_kwh IS NOT NULL
    )
);

CREATE INDEX idx_telemetry_asset_time
    ON telemetry (asset_id, recorded_at DESC);

CREATE INDEX idx_telemetry_received_at
    ON telemetry (received_at DESC);

CREATE TABLE alert_events (
    alert_id UUID PRIMARY KEY,
    asset_id TEXT NOT NULL REFERENCES assets(asset_id),
    rule_code TEXT NOT NULL,
    incident_key TEXT NOT NULL,
    severity TEXT NOT NULL
        CHECK (severity IN ('INFO', 'WARNING', 'CRITICAL')),
    status TEXT NOT NULL DEFAULT 'OPEN'
        CHECK (status IN ('OPEN', 'ACKNOWLEDGED', 'RESOLVED')),
    opened_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    acknowledged_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,

    CHECK (acknowledged_at IS NULL OR acknowledged_at >= opened_at),
    CHECK (resolved_at IS NULL OR resolved_at >= opened_at),
    CHECK (status <> 'ACKNOWLEDGED' OR acknowledged_at IS NOT NULL),
    CHECK (status <> 'RESOLVED' OR resolved_at IS NOT NULL)
);

CREATE UNIQUE INDEX uq_active_alert_incident
    ON alert_events (asset_id, rule_code, incident_key)
    WHERE status IN ('OPEN', 'ACKNOWLEDGED');

CREATE INDEX idx_alerts_status_time
    ON alert_events (status, opened_at DESC);

CREATE TABLE maintenance_records (
    work_order_id UUID PRIMARY KEY,
    asset_id TEXT NOT NULL REFERENCES assets(asset_id),
    alert_id UUID REFERENCES alert_events(alert_id) ON DELETE SET NULL,
    description TEXT NOT NULL,
    assigned_to TEXT,
    status TEXT NOT NULL DEFAULT 'OPEN'
        CHECK (status IN ('OPEN', 'IN_PROGRESS', 'RESOLVED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,

    CHECK (resolved_at IS NULL OR resolved_at >= created_at),
    CHECK (status <> 'RESOLVED' OR resolved_at IS NOT NULL)
);

CREATE INDEX idx_maintenance_asset_status
    ON maintenance_records (asset_id, status);

COMMIT;
