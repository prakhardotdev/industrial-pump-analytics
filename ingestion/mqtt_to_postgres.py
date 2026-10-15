
import math
from uuid import UUID
from datetime import datetime

import json
import os
from datetime import datetime
from uuid import UUID

import paho.mqtt.client as mqtt
import psycopg
from dotenv import load_dotenv

load_dotenv()

MQTT_HOST = os.getenv("MQTT_HOST", "127.0.0.1")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
TOPIC = "synoquant/factory-01/+/telemetry"

DB_CONFIG = {
    "host": os.getenv("PGHOST", "localhost"),
    "port": int(os.getenv("PGPORT", "5432")),
    "dbname": os.getenv("PGDATABASE", "industrial_pump_analytics"),
    "user": os.getenv("PGUSER", "postgres"),
    "password": os.getenv("PGPASSWORD"),
}

INSERT_SQL = """
INSERT INTO telemetry (
    asset_id, event_id, recorded_at,
    temperature_c, vibration_mm_s, pressure_bar,
    flow_rate_m3_h, motor_current_a, energy_kwh
)
VALUES (
    %(asset_id)s, %(event_id)s, %(recorded_at)s,
    %(temperature_c)s, %(vibration_mm_s)s, %(pressure_bar)s,
    %(flow_rate_m3_h)s, %(motor_current_a)s, %(energy_kwh)s
)
ON CONFLICT (event_id) DO NOTHING
"""



def save_reading(payload):
    if not DB_CONFIG["password"]:
        raise ValueError("Set PGPASSWORD in your .env file")

    if not isinstance(payload, dict):
        raise ValueError("Message must be a JSON object")

    required = {"asset_id", "event_id", "recorded_at"}
    missing = required - payload.keys()

    if missing:
        raise ValueError(
            f"Missing required fields: {', '.join(sorted(missing))}"
        )

    asset_id = payload["asset_id"]

    if not isinstance(asset_id, str) or not asset_id.strip():
        raise ValueError("asset_id must be a non-empty string")

    asset_id = asset_id.strip()

    try:
        event_id = str(UUID(payload["event_id"]))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("event_id must be a valid UUID") from exc

    try:
        recorded_at = datetime.fromisoformat(
            payload["recorded_at"].replace("Z", "+00:00")
        )
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("recorded_at must be a valid ISO timestamp") from exc

    if recorded_at.tzinfo is None or recorded_at.utcoffset() is None:
        raise ValueError("recorded_at must include a timezone")

    fields = [
        "temperature_c",
        "vibration_mm_s",
        "pressure_bar",
        "flow_rate_m3_h",
        "motor_current_a",
        "energy_kwh",
    ]

    values = {}

    for key in fields:
        value = payload.get(key)

        if value is None:
            values[key] = None
            continue

        # Booleans are not valid sensor measurements.
        if isinstance(value, bool):
            raise ValueError(f"{key} must be numeric, not boolean")

        try:
            number = float(value)
        except (ValueError, TypeError, OverflowError) as exc:
            raise ValueError(f"{key} must be numeric") from exc

        if not math.isfinite(number):
            raise ValueError(f"{key} must be finite")

        values[key] = number

    if all(values[key] is None for key in fields):
        raise ValueError("At least one sensor value is required")

    if (
        values["temperature_c"] is not None
        and values["temperature_c"] < -273.15
    ):
        raise ValueError("Invalid temperature")

    for key in fields[1:]:
        value = values[key]

        if value is not None and value < 0:
            raise ValueError(f"{key} cannot be negative")

    row = {
        "asset_id": asset_id,
        "event_id": event_id,
        "recorded_at": recorded_at,
        **values,
    }

    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM assets WHERE asset_id = %s",
                (asset_id,),
            )

            if cur.fetchone() is None:
                raise ValueError(f"Unknown asset: {asset_id}")

            cur.execute(INSERT_SQL, row)
            inserted = cur.rowcount == 1

    print(
        f"{'Inserted' if inserted else 'Duplicate ignored'}: "
        f"{asset_id} | {event_id}",
        flush=True,
    )



def on_connect(client, userdata, flags, reason_code, properties):
    print(f"MQTT connection reason: {reason_code}")
    if reason_code.is_failure:
        print(f"MQTT connection failed: {reason_code}")
        return

    print("Connected to MQTT broker")
    client.subscribe(TOPIC, qos=1)
    print(f"Subscribed to {TOPIC}")



def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        save_reading(payload)

    except (
        ValueError,
        KeyError,
        TypeError,
        UnicodeDecodeError,
        OverflowError,
    ) as exc:
        print(f"Invalid message on {msg.topic}: {exc}", flush=True)

    except psycopg.Error as exc:
        print(f"Database error on {msg.topic}: {exc}", flush=True)


client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    client_id="pump-postgres-ingestion",
)
client.on_connect = on_connect
client.on_message = on_message

print("Starting MQTT-to-PostgreSQL ingestion...", flush=True)

try:
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    print("MQTT connection initiated", flush=True)
    client.loop_forever()

except Exception as exc:
    print(f"Connection/runtime error: {exc}", flush=True)

finally:
    client.disconnect()