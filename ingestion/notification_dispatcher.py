
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

import psycopg
from dotenv import load_dotenv


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

DB_CONFIG = {
    "host": os.getenv("PGHOST", "localhost"),
    "port": int(os.getenv("PGPORT", "5432")),
    "dbname": os.getenv(
        "PGDATABASE",
        "industrial_pump_analytics",
    ),
    "user": os.getenv("PGUSER", "postgres"),
    "password": os.getenv("PGPASSWORD"),
}

WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")

POLL_SECONDS = 3
REQUEST_TIMEOUT = 15
MAX_ATTEMPTS = 8
STALE_PROCESSING_MINUTES = 5


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

def get_connection():
    if not DB_CONFIG["password"]:
        raise ValueError(
            "PGPASSWORD is missing from root .env"
        )

    if not WEBHOOK_URL:
        raise ValueError(
            "N8N_WEBHOOK_URL is missing from root .env"
        )

    return psycopg.connect(**DB_CONFIG)


def ensure_outbox_columns():
    """Ensure the dispatcher tracking column exists."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                ALTER TABLE alert_notification_outbox
                ADD COLUMN IF NOT EXISTS updated_at
                TIMESTAMPTZ NOT NULL DEFAULT NOW()
            """)
        conn.commit()


# --------------------------------------------------
# CLAIM ONE EVENT SAFELY
# --------------------------------------------------

def claim_event():
    """
    Claim one due event inside a transaction.

    FOR UPDATE SKIP LOCKED prevents two concurrent
    dispatcher instances from claiming the same row
    simultaneously.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:

            # Recover events abandoned by a crashed
            # dispatcher, provided retries remain.
            cur.execute("""
                UPDATE alert_notification_outbox
                SET delivery_status = 'FAILED',
                    next_attempt_at = NOW(),
                    last_error =
                        'Recovered stale PROCESSING event',
                    updated_at = NOW()
                WHERE delivery_status = 'PROCESSING'
                  AND updated_at <
                      NOW() - (%s * INTERVAL '1 minute')
                  AND attempts < %s
            """, (
                STALE_PROCESSING_MINUTES,
                MAX_ATTEMPTS,
            ))

            # Do not retry exhausted events.
            cur.execute("""
                UPDATE alert_notification_outbox
                SET delivery_status = 'FAILED',
                    last_error = COALESCE(
                        last_error,
                        'Maximum delivery attempts reached'
                    ),
                    updated_at = NOW()
                WHERE delivery_status = 'PROCESSING'
                  AND updated_at <
                      NOW() - (%s * INTERVAL '1 minute')
                  AND attempts >= %s
            """, (
                STALE_PROCESSING_MINUTES,
                MAX_ATTEMPTS,
            ))

            cur.execute("""
                SELECT event_id, payload, attempts
                FROM alert_notification_outbox
                WHERE delivery_status IN ('PENDING', 'FAILED')
                  AND next_attempt_at <= NOW()
                  AND attempts < %s
                ORDER BY created_at
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            """, (MAX_ATTEMPTS,))

            row = cur.fetchone()

            if row is None:
                return None

            event_id, payload, attempts = row

            cur.execute("""
                UPDATE alert_notification_outbox
                SET delivery_status = 'PROCESSING',
                    attempts = attempts + 1,
                    updated_at = NOW()
                WHERE event_id = %s
            """, (event_id,))

        # Commit the claim before making an HTTP request.
        conn.commit()

    if isinstance(payload, str):
        payload = json.loads(payload)

    if not isinstance(payload, dict):
        raise ValueError(
            f"Event {event_id} payload must be a JSON object"
        )

    # Ensure the downstream workflow receives a stable ID.
    # Preserve all existing payload fields.
    payload["event_id"] = str(event_id)

    return str(event_id), payload, attempts + 1


# --------------------------------------------------
# SEND EVENT TO N8N
# --------------------------------------------------

def send_to_n8n(payload):
    body = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        WEBHOOK_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Event-ID": payload["event_id"],
        },
        method="POST",
    )

    with urllib.request.urlopen(
        request,
        timeout=REQUEST_TIMEOUT,
    ) as response:

        status = response.status
        response.read()

    if not 200 <= status < 300:
        raise RuntimeError(
            f"Unexpected HTTP status: {status}"
        )


# --------------------------------------------------
# UPDATE DELIVERY STATUS
# --------------------------------------------------

def mark_delivered(event_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE alert_notification_outbox
                SET delivery_status = 'DELIVERED',
                    delivered_at = NOW(),
                    last_error = NULL,
                    updated_at = NOW()
                WHERE event_id = %s
            """, (event_id,))

        conn.commit()


def mark_failed(event_id, attempt, error):
    """
    Exponential backoff:
    5, 10, 20, 40 ... seconds, capped at 15 minutes.
    """

    delay_seconds = min(
        5 * (2 ** (attempt - 1)),
        900,
    )

    with get_connection() as conn:
        with conn.cursor() as cur:

            # Keep exhausted events FAILED for inspection,
            # but schedule no further retry.
            if attempt >= MAX_ATTEMPTS:
                cur.execute("""
                    UPDATE alert_notification_outbox
                    SET delivery_status = 'FAILED',
                        last_error = %s,
                        updated_at = NOW()
                    WHERE event_id = %s
                """, (
                    str(error)[:2000],
                    event_id,
                ))
            else:
                cur.execute("""
                    UPDATE alert_notification_outbox
                    SET delivery_status = 'FAILED',
                        next_attempt_at =
                            NOW() + (%s * INTERVAL '1 second'),
                        last_error = %s,
                        updated_at = NOW()
                    WHERE event_id = %s
                """, (
                    delay_seconds,
                    str(error)[:2000],
                    event_id,
                ))

        conn.commit()


# --------------------------------------------------
# MAIN DISPATCH LOOP
# --------------------------------------------------

def main():
    ensure_outbox_columns()

    print(
        "Notification dispatcher started.",
        flush=True,
    )
    print(
        f"Polling every {POLL_SECONDS} seconds.",
        flush=True,
    )
    print(
        f"Maximum attempts: {MAX_ATTEMPTS}.",
        flush=True,
    )

    while True:
        try:
            event = claim_event()

            if event is None:
                time.sleep(POLL_SECONDS)
                continue

            event_id, payload, attempt = event

            print(
                f"PROCESSING | event={event_id} "
                f"| attempt={attempt}",
                flush=True,
            )

            try:
                send_to_n8n(payload)
                mark_delivered(event_id)

                print(
                    f"WEBHOOK ACCEPTED | event={event_id} "
                    f"| attempt={attempt}",
                    flush=True,
                )

            except Exception as exc:
                try:
                    mark_failed(event_id, attempt, exc)
                except Exception as db_error:
                    print(
                        f"STATUS UPDATE FAILED | "
                        f"event={event_id} | {db_error}",
                        flush=True,
                    )

                print(
                    f"DELIVERY FAILED | event={event_id} "
                    f"| attempt={attempt} | {exc}",
                    flush=True,
                )

        except KeyboardInterrupt:
            print(
                "Dispatcher stopped.",
                flush=True,
            )
            break

        except Exception as exc:
            print(
                f"Dispatcher error: {exc}",
                flush=True,
            )
            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
