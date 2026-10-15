
import json
import random
import signal
import time
import uuid
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

BROKER = "127.0.0.1"
PORT = 1883
INTERVAL_SECONDS = 2

PUMPS = {
    "PUMP-001": {
        "temperature": 62.0,
        "vibration": 2.1,
        "pressure": 3.2,
        "flow": 45.0,
        "current": 12.5,
        "energy": 0.25,
    },
    "PUMP-002": {
        "temperature": 68.0,
        "vibration": 2.8,
        "pressure": 2.9,
        "flow": 41.0,
        "current": 13.2,
        "energy": 0.28,
    },
}

running = True


def stop_simulator(signum, frame):
    global running
    running = False


signal.signal(signal.SIGINT, stop_simulator)
signal.signal(signal.SIGTERM, stop_simulator)


def generate_reading(asset_id, base):
    # Small normal variations around each pump's baseline.
    temperature = base["temperature"] + random.uniform(-1.5, 1.5)
    vibration = max(0, base["vibration"] + random.uniform(-0.25, 0.25))
    pressure = max(0, base["pressure"] + random.uniform(-0.12, 0.12))
    flow = max(0, base["flow"] + random.uniform(-1.5, 1.5))
    current = max(0, base["current"] + random.uniform(-0.5, 0.5))

    # Interval energy in kWh for this simulated two-second interval.
    # This is illustrative data, not a real electrical measurement.
    energy = max(0, base["energy"] + random.uniform(-0.02, 0.02))

    return {
        "event_id": str(uuid.uuid4()),
        "asset_id": asset_id,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "temperature_c": round(temperature, 2),
        "vibration_mm_s": round(vibration, 2),
        "pressure_bar": round(pressure, 2),
        "flow_rate_m3_h": round(flow, 2),
        "motor_current_a": round(current, 2),
        "energy_kwh": round(energy, 4),
    }


def main():
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="pump-simulator",
    )

    print(f"Connecting to MQTT broker {BROKER}:{PORT}...", flush=True)
    client.connect(BROKER, PORT, keepalive=60)
    client.loop_start()

    try:
        while running:
            for asset_id, baseline in PUMPS.items():
                payload = generate_reading(asset_id, baseline)
                topic = (
                    f"synoquant/factory-01/"
                    f"{asset_id.lower()}/telemetry"
                )

                info = client.publish(
                    topic,
                    json.dumps(payload),
                    qos=1,
                )
                info.wait_for_publish(timeout=5)

                if not info.is_published():
                    print(f"Publish failed: {asset_id}", flush=True)
                    continue

                print(
                    f"Published {asset_id}: "
                    f"temp={payload['temperature_c']}°C, "
                    f"vibration={payload['vibration_mm_s']} mm/s",
                    flush=True,
                )

            time.sleep(INTERVAL_SECONDS)

    finally:
        client.loop_stop()
        client.disconnect()
        print("Simulator stopped.", flush=True)


if __name__ == "__main__":
    main()
