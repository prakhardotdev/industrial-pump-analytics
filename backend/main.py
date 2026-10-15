import os
from pathlib import Path
from uuid import UUID

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

DB_CONFIG = {
    "host": os.getenv("PGHOST", "localhost"),
    "port": int(os.getenv("PGPORT", "5432")),
    "dbname": os.getenv("PGDATABASE", "industrial_pump_analytics"),
    "user": os.getenv("PGUSER", "postgres"),
    "password": os.getenv("PGPASSWORD"),
}

app = FastAPI(
    title="Industrial Pump Analytics API",
    description="Simulated industrial pump telemetry and alert analytics.",
    version="1.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


def get_connection():
    if not DB_CONFIG["password"]:
        raise ValueError("PGPASSWORD is missing from the root .env file")
    return psycopg.connect(**DB_CONFIG)


def fetch_dicts(cur):
    columns = [column.name for column in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]


def ensure_alert_lifecycle_columns(cur):
    """Add lifecycle columns without deleting existing alert history."""
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


@app.on_event("startup")
def startup_migration():
    with get_connection() as conn:
        with conn.cursor() as cur:
            ensure_alert_lifecycle_columns(cur)
        conn.commit()


@app.get("/health")
def health_check():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return {"status": "ok", "database": "connected"}
    except (psycopg.Error, ValueError) as exc:
        print(f"Health check failed: {exc}", flush=True)
        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable. Check .env and API terminal.",
        ) from exc


@app.get("/api/assets/summary")
def asset_summary():
    query = """
        SELECT
            a.asset_id,
            a.asset_name,
            a.location,
            a.status,
            COUNT(t.reading_id) AS total_readings,
            ROUND(AVG(t.temperature_c)::numeric, 2) AS avg_temperature,
            ROUND(MAX(t.temperature_c)::numeric, 2) AS max_temperature,
            ROUND(AVG(t.vibration_mm_s)::numeric, 2) AS avg_vibration,
            ROUND(AVG(t.flow_rate_m3_h)::numeric, 2) AS avg_flow,
            ROUND(AVG(t.pressure_bar)::numeric, 2) AS avg_pressure,
            MAX(t.recorded_at) AS last_reading_at
        FROM assets a
        LEFT JOIN telemetry t ON t.asset_id = a.asset_id
        GROUP BY a.asset_id, a.asset_name, a.location, a.status
        ORDER BY a.asset_id;
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                return fetch_dicts(cur)
    except (psycopg.Error, ValueError) as exc:
        print(f"Asset summary failed: {exc}", flush=True)
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve asset summary.",
        ) from exc


@app.get("/api/analytics/overview")
def analytics_overview():
    query = """
        SELECT
            COUNT(*) AS total_readings,
            COUNT(DISTINCT asset_id) AS assets_with_readings,
            ROUND(AVG(temperature_c)::numeric, 2) AS avg_temperature,
            ROUND(AVG(vibration_mm_s)::numeric, 2) AS avg_vibration,
            ROUND(AVG(flow_rate_m3_h)::numeric, 2) AS avg_flow,
            ROUND(AVG(pressure_bar)::numeric, 2) AS avg_pressure,
            ROUND(MAX(temperature_c)::numeric, 2) AS max_temperature,
            MAX(recorded_at) AS last_reading_at
        FROM telemetry;
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                return fetch_dicts(cur)[0]
    except (psycopg.Error, ValueError) as exc:
        print(f"Analytics overview failed: {exc}", flush=True)
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve historical analytics.",
        ) from exc


@app.get("/api/alerts")
def get_alerts(
    status: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    allowed_statuses = {"OPEN", "ACKNOWLEDGED", "RESOLVED"}
    allowed_severities = {"INFO", "WARNING", "CRITICAL"}

    if status and status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="Status must be OPEN, ACKNOWLEDGED, or RESOLVED.",
        )

    if severity and severity not in allowed_severities:
        raise HTTPException(
            status_code=400,
            detail="Severity must be INFO, WARNING, or CRITICAL.",
        )

    query = """
        SELECT
            alert_id,
            asset_id,
            rule_code,
            severity,
            status,
            opened_at,
            acknowledged_at,
            resolved_at,
            condition_recovered,
            recovery_detected_at
        FROM alert_events
        WHERE (%s::text IS NULL OR status = %s::text)
          AND (%s::text IS NULL OR severity = %s::text)
        ORDER BY opened_at DESC
        LIMIT %s;
    """

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    query,
                    (status, status, severity, severity, limit),
                )
                return fetch_dicts(cur)
    except (psycopg.Error, ValueError) as exc:
        print(f"GET /api/alerts failed: {exc}", flush=True)
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve alerts.",
        ) from exc


@app.get("/api/alerts/counts")
def alert_counts():
    query = """
        SELECT
            COUNT(*) FILTER (
                WHERE status = 'OPEN'
            ) AS open_count,
            COUNT(*) FILTER (
                WHERE status = 'ACKNOWLEDGED'
            ) AS acknowledged_count,
            COUNT(*) FILTER (
                WHERE status = 'RESOLVED'
            ) AS resolved_count,
            COUNT(*) FILTER (
                WHERE status IN ('OPEN', 'ACKNOWLEDGED')
            ) AS active_count,
            COUNT(*) FILTER (
                WHERE status IN ('OPEN', 'ACKNOWLEDGED')
                  AND severity = 'CRITICAL'
            ) AS critical_active_count,
            COUNT(*) FILTER (
                WHERE status IN ('OPEN', 'ACKNOWLEDGED')
                  AND severity = 'WARNING'
            ) AS warning_active_count
        FROM alert_events;
    """

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                return fetch_dicts(cur)[0]
    except (psycopg.Error, ValueError) as exc:
        print(f"Alert counts failed: {exc}", flush=True)
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve alert counts.",
        ) from exc


def change_alert_status(alert_id: str, action: str):
    try:
        parsed_id = str(UUID(alert_id))
    except (ValueError, TypeError, AttributeError) as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid alert ID.",
        ) from exc

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                ensure_alert_lifecycle_columns(cur)

                cur.execute(
                    """
                    SELECT alert_id, status, condition_recovered
                    FROM alert_events
                    WHERE alert_id = %s
                    FOR UPDATE
                    """,
                    (parsed_id,),
                )
                row = cur.fetchone()

                if not row:
                    raise HTTPException(
                        status_code=404,
                        detail="Alert not found.",
                    )

                _, status, recovered = row

                if action == "acknowledge":
                    if status != "OPEN":
                        raise HTTPException(
                            status_code=409,
                            detail=(
                                "Only OPEN alerts can be acknowledged; "
                                f"current status is {status}."
                            ),
                        )

                    cur.execute(
                        """
                        UPDATE alert_events
                        SET status = 'ACKNOWLEDGED',
                            acknowledged_at = NOW()
                        WHERE alert_id = %s
                        RETURNING alert_id, status, condition_recovered
                        """,
                        (parsed_id,),
                    )
                else:
                    if status not in ("OPEN", "ACKNOWLEDGED"):
                        raise HTTPException(
                            status_code=409,
                            detail=(
                                "Only active alerts can be resolved; "
                                f"current status is {status}."
                            ),
                        )

                    if not recovered:
                        raise HTTPException(
                            status_code=409,
                            detail=(
                                "Cannot resolve yet: the alert engine has "
                                "not confirmed recovery. Wait for normal telemetry."
                            ),
                        )

                    cur.execute(
                        """
                        UPDATE alert_events
                        SET status = 'RESOLVED',
                            resolved_at = NOW()
                        WHERE alert_id = %s
                        RETURNING alert_id, status, condition_recovered
                        """,
                        (parsed_id,),
                    )

                result = cur.fetchone()

            conn.commit()

        message = (
            "Alert acknowledged successfully."
            if action == "acknowledge"
            else "Alert resolved successfully."
        )

        return {
            "alert_id": str(result[0]),
            "status": result[1],
            "condition_recovered": result[2],
            "message": message,
        }

    except HTTPException:
        raise
    except (psycopg.Error, ValueError) as exc:
        print(f"Alert {action} failed: {exc}", flush=True)
        raise HTTPException(
            status_code=503,
            detail="Could not update alert status.",
        ) from exc


@app.post("/api/alerts/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: str):
    return change_alert_status(alert_id, "acknowledge")


@app.post("/api/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: str):
    return change_alert_status(alert_id, "resolve")


@app.get("/api/telemetry/latest")
def latest_telemetry():
    query = """
        SELECT DISTINCT ON (t.asset_id)
            t.reading_id,
            t.asset_id,
            t.recorded_at,
            t.received_at,
            t.temperature_c,
            t.vibration_mm_s,
            t.pressure_bar,
            t.flow_rate_m3_h,
            t.motor_current_a,
            t.energy_kwh
        FROM telemetry t
        ORDER BY t.asset_id, t.recorded_at DESC, t.reading_id DESC;
    """

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                return fetch_dicts(cur)
    except (psycopg.Error, ValueError) as exc:
        print(f"Latest telemetry failed: {exc}", flush=True)
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve latest telemetry.",
        ) from exc


@app.get("/api/telemetry/history")
def telemetry_history(
    minutes: int = Query(default=5, ge=1, le=30),
    limit: int = Query(default=300, ge=10, le=1000),
):
    query = """
        SELECT
            reading_id,
            asset_id,
            recorded_at,
            received_at,
            temperature_c,
            vibration_mm_s,
            pressure_bar,
            flow_rate_m3_h,
            motor_current_a,
            energy_kwh
        FROM telemetry
        WHERE recorded_at >= NOW() - (%s * INTERVAL '1 minute')
        ORDER BY recorded_at DESC, reading_id DESC
        LIMIT %s;
    """

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (minutes, limit))
                rows = fetch_dicts(cur)

        return list(reversed(rows))

    except (psycopg.Error, ValueError) as exc:
        print(f"Telemetry history failed: {exc}", flush=True)
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve telemetry history.",
        ) from exc