
import os
import time
import uuid
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb
from dotenv import load_dotenv

from alert_config import ALERT_CONFIG


ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

DB_CONFIG = {
    "host": os.getenv("PGHOST", "localhost"),
    "port": int(os.getenv("PGPORT", "5432")),
    "dbname": os.getenv("PGDATABASE", "industrial_pump_analytics"),
    "user": os.getenv("PGUSER", "postgres"),
    "password": os.getenv("PGPASSWORD"),
}

POLL_SECONDS = 2


def get_connection():
    if not DB_CONFIG["password"]:
        raise ValueError("Set PGPASSWORD in the root .env file")
    return psycopg.connect(**DB_CONFIG)


def ensure_lifecycle_columns(cur):
    cur.execute("""
        ALTER TABLE alert_events
        ADD COLUMN IF NOT EXISTS condition_recovered
        BOOLEAN NOT NULL DEFAULT FALSE
    """)
    cur.execute("""
        ALTER TABLE alert_events
        ADD COLUMN IF NOT EXISTS recovery_detected_at
        TIMESTAMPTZ NULL
    """)


def ensure_notification_outbox(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS alert_notification_outbox (
            event_id UUID PRIMARY KEY,
            alert_id UUID NOT NULL,
            event_type TEXT NOT NULL,
            payload JSONB NOT NULL,
            delivery_status TEXT NOT NULL DEFAULT 'PENDING'
                CHECK (delivery_status IN (
                    'PENDING', 'PROCESSING', 'DELIVERED', 'FAILED'
                )),
            attempts INTEGER NOT NULL DEFAULT 0,
            next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            delivered_at TIMESTAMPTZ,
            last_error TEXT,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (alert_id, event_type)
        )
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_alert_outbox_pending
        ON alert_notification_outbox (next_attempt_at, created_at)
        WHERE delivery_status IN ('PENDING', 'FAILED')
    """)


def enqueue_critical_notification(
    cur, alert_id, asset_id, rule_code, event_type
):
    event_id = uuid.uuid4()

    if event_type == "critical_alert_escalated":
        message = (
            f"{rule_code} escalated to CRITICAL for pump {asset_id}"
        )
    else:
        message = (
            f"{rule_code} triggered a CRITICAL alert for pump {asset_id}"
        )

    payload = {
        "event_id": str(event_id),
        "event_type": event_type,
        "alert_id": str(alert_id),
        "asset_id": str(asset_id),
        "rule_code": rule_code,
        "severity": "CRITICAL",
        "message": message,
        "simulated": True,
    }

    cur.execute("""
        INSERT INTO alert_notification_outbox (
            event_id, alert_id, event_type, payload
        )
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (alert_id, event_type) DO NOTHING
    """, (
        event_id,
        alert_id,
        event_type,
        Jsonb(payload),
    ))

    if cur.rowcount:
        print(
            f"NOTIFICATION QUEUED | {asset_id} | "
            f"{rule_code} | {event_type}",
            flush=True,
        )


def fetch_recent_readings(cur, last_reading_id):
    cur.execute("""
        SELECT
            reading_id,
            asset_id,
            recorded_at,
            temperature_c,
            vibration_mm_s,
            pressure_bar,
            flow_rate_m3_h
        FROM telemetry
        WHERE reading_id > %s
        ORDER BY reading_id
        LIMIT 1000
    """, (last_reading_id,))
    return cur.fetchall()


def get_active_alert(cur, asset_id, rule_code):
    cur.execute("""
        SELECT
            alert_id,
            severity,
            status,
            condition_recovered
        FROM alert_events
        WHERE asset_id = %s
          AND rule_code = %s
          AND status IN ('OPEN', 'ACKNOWLEDGED')
        ORDER BY opened_at DESC
        LIMIT 1
    """, (asset_id, rule_code))
    return cur.fetchone()


def create_or_escalate_alert(
    cur, asset_id, rule_code, severity, incident_key
):
    active = get_active_alert(cur, asset_id, rule_code)

    if active:
        alert_id, old_severity, status, recovered = active

        if severity == "CRITICAL" and old_severity != "CRITICAL":
            cur.execute("""
                UPDATE alert_events
                SET severity = 'CRITICAL'
                WHERE alert_id = %s
                RETURNING alert_id
            """, (alert_id,))

            updated = cur.fetchone()

            if updated:
                enqueue_critical_notification(
                    cur,
                    updated[0],
                    asset_id,
                    rule_code,
                    "critical_alert_escalated",
                )
                print(
                    f"ALERT ESCALATED | {asset_id} | "
                    f"{rule_code} | CRITICAL",
                    flush=True,
                )
        return

    new_alert_id = uuid.uuid4()

    cur.execute("""
        INSERT INTO alert_events (
            alert_id,
            asset_id,
            rule_code,
            incident_key,
            severity,
            status,
            opened_at,
            condition_recovered,
            recovery_detected_at
        )
        VALUES (%s, %s, %s, %s, %s, 'OPEN', NOW(), FALSE, NULL)
        ON CONFLICT DO NOTHING
        RETURNING alert_id
    """, (
        new_alert_id,
        asset_id,
        rule_code,
        incident_key,
        severity,
    ))

    created = cur.fetchone()

    if not created:
        return

    alert_id = created[0]

    print(
        f"ALERT CREATED | {asset_id} | "
        f"{rule_code} | {severity}",
        flush=True,
    )

    if severity == "CRITICAL":
        enqueue_critical_notification(
            cur,
            alert_id,
            asset_id,
            rule_code,
            "critical_alert_created",
        )


def mark_recovery(cur, asset_id, rule_code):
    """Mark recovery without automatically resolving the alert."""
    cur.execute("""
        UPDATE alert_events
        SET condition_recovered = TRUE,
            recovery_detected_at = COALESCE(
                recovery_detected_at, NOW()
            )
        WHERE asset_id = %s
          AND rule_code = %s
          AND status IN ('OPEN', 'ACKNOWLEDGED')
          AND condition_recovered = FALSE
        RETURNING alert_id
    """, (asset_id, rule_code))

    if cur.fetchone():
        print(
            f"RECOVERY DETECTED | {asset_id} | {rule_code} "
            "| awaiting operator resolution",
            flush=True,
        )


def clear_recovery_if_fault_returns(cur, asset_id, rule_code):
    """Revoke recovery when the condition leaves its recovery range."""
    cur.execute("""
        UPDATE alert_events
        SET condition_recovered = FALSE,
            recovery_detected_at = NULL
        WHERE asset_id = %s
          AND rule_code = %s
          AND status IN ('OPEN', 'ACKNOWLEDGED')
          AND condition_recovered = TRUE
        RETURNING alert_id
    """, (asset_id, rule_code))

    if cur.fetchone():
        print(
            f"RECOVERY REVOKED | {asset_id} | {rule_code} "
            "| recovery condition no longer holds",
            flush=True,
        )


def process_rule(
    cur, counters, asset_id, rule_code, value, recorded_at
):
    config = ALERT_CONFIG[rule_code]

    if value is None:
        return

    active = get_active_alert(cur, asset_id, rule_code)

    if rule_code in ("HIGH_TEMPERATURE", "HIGH_VIBRATION"):
        triggered = value > config["warning"]
        recovered = value <= config["recovery"]
        severity = (
            "CRITICAL"
            if value > config["critical"]
            else "WARNING"
        )

    elif rule_code == "LOW_FLOW":
        triggered = value < config["minimum"]
        recovered = value >= config["recovery"]
        severity = "WARNING"

    elif rule_code == "PRESSURE_ANOMALY":
        triggered = (
            value < config["minimum"]
            or value > config["maximum"]
        )
        recovered = (
            config["recovery_minimum"]
            <= value
            <= config["recovery_maximum"]
        )
        severity = "WARNING"

    else:
        return

    key = (asset_id, rule_code)

    if active:
        if recovered:
            mark_recovery(cur, asset_id, rule_code)
            counters[key] = 0

        else:
            clear_recovery_if_fault_returns(
                cur, asset_id, rule_code
            )
            counters[key] = 0

            if (
                rule_code in (
                    "HIGH_TEMPERATURE",
                    "HIGH_VIBRATION",
                )
                and value > config["critical"]
            ):
                create_or_escalate_alert(
                    cur,
                    asset_id,
                    rule_code,
                    "CRITICAL",
                    f"{asset_id}:{rule_code}:"
                    f"{recorded_at.isoformat()}",
                )

        # Resolution remains an operator action in the API.
        return

    if triggered:
        counters[key] = counters.get(key, 0) + 1
    else:
        counters[key] = 0

    if counters[key] >= config["persistence"]:
        create_or_escalate_alert(
            cur,
            asset_id,
            rule_code,
            severity,
            f"{asset_id}:{rule_code}:"
            f"{recorded_at.isoformat()}",
        )
        counters[key] = 0


def check_stale_telemetry(cur):
    freshness = ALERT_CONFIG["STALE_TELEMETRY"][
        "freshness_seconds"
    ]

    cur.execute("""
        SELECT a.asset_id
        FROM assets a
        LEFT JOIN (
            SELECT
                asset_id,
                MAX(received_at) AS last_received
            FROM telemetry
            GROUP BY asset_id
        ) t ON t.asset_id = a.asset_id
        WHERE a.status = 'RUNNING'
          AND (
              t.last_received IS NULL
              OR t.last_received
                 < NOW() - (%s * INTERVAL '1 second')
          )
    """, (freshness,))

    stale_assets = {row[0] for row in cur.fetchall()}

    cur.execute("""
        SELECT asset_id
        FROM assets
        WHERE status = 'RUNNING'
    """)
    running_assets = {row[0] for row in cur.fetchall()}

    for asset_id in running_assets:
        if asset_id in stale_assets:
            clear_recovery_if_fault_returns(
                cur, asset_id, "STALE_TELEMETRY"
            )
            create_or_escalate_alert(
                cur,
                asset_id,
                "STALE_TELEMETRY",
                "WARNING",
                f"{asset_id}:STALE_TELEMETRY:{uuid.uuid4()}",
            )
        else:
            mark_recovery(cur, asset_id, "STALE_TELEMETRY")


def main():
    print(
        "Starting Industrial Pump Alert Engine...",
        flush=True,
    )

    counters = {}

    with get_connection() as conn:
        with conn.cursor() as cur:
            ensure_lifecycle_columns(cur)
            ensure_notification_outbox(cur)

            cur.execute(
                "SELECT COALESCE(MAX(reading_id), 0) FROM telemetry"
            )
            last_reading_id = cur.fetchone()[0]

        conn.commit()

    print(
        f"Resuming after reading_id={last_reading_id}",
        flush=True,
    )

    while True:
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    readings = fetch_recent_readings(
                        cur, last_reading_id
                    )

                    for row in readings:
                        (
                            reading_id,
                            asset_id,
                            recorded_at,
                            temperature,
                            vibration,
                            pressure,
                            flow,
                        ) = row

                        checks = [
                            ("HIGH_TEMPERATURE", temperature),
                            ("HIGH_VIBRATION", vibration),
                            ("LOW_FLOW", flow),
                            ("PRESSURE_ANOMALY", pressure),
                        ]

                        for rule_code, value in checks:
                            process_rule(
                                cur,
                                counters,
                                asset_id,
                                rule_code,
                                value,
                                recorded_at,
                            )

                        last_reading_id = reading_id

                    # Check freshness even when no new reading arrived.
                    check_stale_telemetry(cur)

                conn.commit()

        except (
            psycopg.Error,
            ValueError,
            KeyError,
            TypeError,
        ) as exc:
            print(
                f"Alert engine error: {exc}",
                flush=True,
            )

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
