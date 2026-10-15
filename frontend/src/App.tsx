import { useCallback, useEffect, useRef, useState } from "react";
import {
  Activity,
  AlertTriangle,
  Bell,
  CheckCircle2,
  Clock3,
  Database,
  Droplets,
  Gauge,
  RefreshCw,
  Thermometer,
  Waves,
  Zap,
  Lightbulb,
  HeartPulse,
  Check,
  ClipboardCheck,
} from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import "./App.css";

const API = "http://127.0.0.1:8000";

type Num = number | null;
type Range = 5 | 15 | 30;
type AlertAction = "acknowledge" | "resolve";

type Asset = {
  asset_id: string;
  asset_name: string;
  location: string | null;
  status: string;
  total_readings: number;
  avg_temperature: Num;
  max_temperature: Num;
  avg_vibration: Num;
  avg_flow: Num;
  avg_pressure: Num;
  last_reading_at: string | null;
};

type Telemetry = {
  reading_id: number;
  asset_id: string;
  recorded_at: string;
  received_at?: string | null;
  temperature_c: Num;
  vibration_mm_s: Num;
  pressure_bar: Num;
  flow_rate_m3_h: Num;
  motor_current_a?: Num;
  energy_kwh?: Num;
};

type ChartPoint = Telemetry & { time: string };

type Alert = {
  alert_id: string;
  asset_id: string;
  rule_code: string;
  severity: string;
  status: string;
  opened_at: string;
  acknowledged_at?: string | null;
  resolved_at?: string | null;
  condition_recovered: boolean;
  recovery_detected_at?: string | null;
};

type Overview = {
  total_readings: number;
  assets_with_readings: number;
  avg_temperature: Num;
  avg_vibration: Num;
  avg_flow: Num;
  avg_pressure: Num;
  max_temperature: Num;
  last_reading_at: string | null;
};

type AlertCounts = {
  open_count: number;
  acknowledged_count: number;
  resolved_count: number;
  active_count: number;
  critical_active_count: number;
  warning_active_count: number;
};

function fmt(value: number | null | undefined, digits = 1): string {
  if (value == null || !Number.isFinite(Number(value))) return "—";
  return Number(value).toFixed(digits);
}

function timeLabel(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";

  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function fullTime(value?: string | null): string {
  if (!value) return "No reading";

  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "No reading"
    : date.toLocaleString();
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API}${path}`);

  if (!response.ok) {
    throw new Error(`${path} failed (${response.status})`);
  }

  return response.json() as Promise<T>;
}

function Kpi({
  icon,
  label,
  value,
  note,
  warning = false,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  note: string;
  warning?: boolean;
}) {
  return (
    <article className={`kpi-card ${warning ? "kpi-warning" : ""}`}>
      <div className="kpi-top">
        <span className="kpi-icon">{icon}</span>
        {warning && (
          <AlertTriangle size={17} className="warning-icon" />
        )}
      </div>

      <p>{label}</p>
      <strong>{value}</strong>
      <span className="kpi-note">{note}</span>
    </article>
  );
}

function TrendChart({
  title,
  subtitle,
  data,
  metricKey,
  unit,
  color,
  assetIds,
}: {
  title: string;
  subtitle: string;
  data: ChartPoint[];
  metricKey:
    | "temperature_c"
    | "vibration_mm_s"
    | "pressure_bar"
    | "flow_rate_m3_h";
  unit: string;
  color: string;
  assetIds: string[];
}) {
  const chartData = data.map((point) => ({
    ...point,
    [point.asset_id]: point[metricKey],
  }));

  const visibleIds = assetIds.filter((id) =>
    data.some(
      (point) => point.asset_id === id && point[metricKey] != null
    )
  );

  return (
    <article className="panel chart-panel">
      <div className="panel-heading">
        <div>
          <h3>{title}</h3>
          <p>{subtitle}</p>
        </div>
        <span className="panel-tag">LIVE TREND</span>
      </div>

      <div className="chart-area">
        {!visibleIds.length ? (
          <div className="empty-state">Waiting for telemetry...</div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={chartData}
              margin={{ top: 8, right: 12, left: -15, bottom: 0 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="#263445"
              />

              <XAxis
                dataKey="time"
                stroke="#8393a8"
                tickLine={false}
                axisLine={false}
                minTickGap={35}
                tick={{ fontSize: 10 }}
              />

              <YAxis
                stroke="#8393a8"
                tickLine={false}
                axisLine={false}
                width={48}
                tick={{ fontSize: 10 }}
              />

              <Tooltip
                contentStyle={{
                  background: "#111c2b",
                  border: "1px solid #304156",
                  borderRadius: 8,
                  color: "#edf4ff",
                }}
                labelFormatter={(_label, payload) =>
                  payload?.[0]?.payload?.recorded_at
                    ? fullTime(payload[0].payload.recorded_at)
                    : String(_label)
                }
                formatter={(value) => [
                  `${fmt(typeof value === "number" ? value : null)} ${unit}`,
                ]}
              />

              {visibleIds.map((id, index) => (
                <Line
                  key={id}
                  type="monotone"
                  dataKey={id}
                  name={id}
                  stroke={index === 0 ? color : "#65b8a6"}
                  strokeWidth={2}
                  dot={false}
                  connectNulls
                  isAnimationActive={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="chart-legend">
        {visibleIds.map((id, index) => (
          <span key={id}>
            <i
              style={{
                background: index === 0 ? color : "#65b8a6",
              }}
            />
            {id}
          </span>
        ))}
        <span className="unit-label">{unit}</span>
      </div>
    </article>
  );
}

function getHealth(asset: Asset, reading?: Telemetry) {
  if (!reading || !asset.last_reading_at) {
    return {
      label: "NO DATA",
      level: "unknown",
      reason: "No telemetry available",
    };
  }

  const timestamp = reading.received_at || reading.recorded_at;
  const ageSeconds =
    (Date.now() - new Date(timestamp).getTime()) / 1000;

  if (!Number.isFinite(ageSeconds) || ageSeconds > 60) {
    return {
      label: "STALE DATA",
      level: "warning",
      reason: "No fresh reading received within 60 seconds",
    };
  }

  if (
    (reading.temperature_c != null &&
      reading.temperature_c >= 85) ||
    (reading.vibration_mm_s != null &&
      reading.vibration_mm_s >= 7)
  ) {
    return {
      label: "CRITICAL",
      level: "critical",
      reason: "A configured simulation threshold was exceeded",
    };
  }

  if (
    (reading.temperature_c != null &&
      reading.temperature_c >= 75) ||
    (reading.vibration_mm_s != null &&
      reading.vibration_mm_s >= 4) ||
    (reading.flow_rate_m3_h != null &&
      reading.flow_rate_m3_h < 20) ||
    (reading.pressure_bar != null &&
      (reading.pressure_bar < 1 || reading.pressure_bar > 6))
  ) {
    return {
      label: "WARNING",
      level: "warning",
      reason: "A configured simulation threshold was exceeded",
    };
  }

  return {
    label: "NORMAL",
    level: "normal",
    reason: "No configured threshold currently exceeded",
  };
}

export default function App() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [latest, setLatest] = useState<Telemetry[]>([]);
  const [history, setHistory] = useState<ChartPoint[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [counts, setCounts] = useState<AlertCounts | null>(null);

  const [range, setRange] = useState<Range>(5);
  const [alertStatus, setAlertStatus] = useState("ALL");
  const [alertSeverity, setAlertSeverity] = useState("ALL");

  const [loading, setLoading] = useState(true);
  const [online, setOnline] = useState(false);
  const [error, setError] = useState("");
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const [actionBusy, setActionBusy] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState("");
  const [actionError, setActionError] = useState(false);

  const mounted = useRef(false);
  const telemetryBusy = useRef(false);
  const summaryBusy = useRef(false);
  const seenIds = useRef(new Set<number>());

  const loadSummary = useCallback(async () => {
    if (summaryBusy.current) return;
    summaryBusy.current = true;

    try {
      const [
        assetData,
        overviewData,
        countData,
        alertData,
      ] = await Promise.all([
        getJson<Asset[]>("/api/assets/summary"),
        getJson<Overview>("/api/analytics/overview"),
        getJson<AlertCounts>("/api/alerts/counts"),
        getJson<Alert[]>("/api/alerts?limit=100"),
      ]);

      if (!mounted.current) return;

      setAssets(assetData);
      setOverview(overviewData);
      setCounts(countData);
      setAlerts(alertData);
    } finally {
      summaryBusy.current = false;
    }
  }, []);

  const loadHistory = useCallback(async (minutes: Range) => {
    const points = await getJson<Telemetry[]>(
      `/api/telemetry/history?minutes=${minutes}&limit=1000`
    );

    if (!mounted.current) return;

    const mapped = points.map((point) => ({
      ...point,
      time: timeLabel(point.recorded_at),
    }));

    seenIds.current = new Set(
      mapped.map((point) => Number(point.reading_id))
    );

    setHistory(mapped);
  }, []);

  const pollTelemetry = useCallback(async () => {
    if (telemetryBusy.current) return;
    telemetryBusy.current = true;

    try {
      const readings = await getJson<Telemetry[]>(
        "/api/telemetry/latest"
      );

      if (!mounted.current) return;

      setLatest(readings);
      setOnline(true);
      setLastChecked(new Date());
      setError("");

      const fresh = readings.filter((reading) => {
        const id = Number(reading.reading_id);

        if (seenIds.current.has(id)) return false;

        seenIds.current.add(id);
        return true;
      });

      if (fresh.length) {
        setHistory((previous) => {
          const existing = new Set(
            previous.map((point) => Number(point.reading_id))
          );

          const additions = fresh
            .filter(
              (point) =>
                !existing.has(Number(point.reading_id))
            )
            .map((point) => ({
              ...point,
              time: timeLabel(point.recorded_at),
            }));

          return [...previous, ...additions]
            .sort(
              (a, b) =>
                new Date(a.recorded_at).getTime() -
                new Date(b.recorded_at).getTime()
            )
            .slice(-1000);
        });
      }
    } catch {
      if (mounted.current) {
        setOnline(false);
        setError(
          "Backend connection failed. Check FastAPI and PostgreSQL."
        );
      }
    } finally {
      telemetryBusy.current = false;
    }
  }, []);

  useEffect(() => {
    mounted.current = true;

    async function initialize() {
      try {
        await Promise.all([
          loadHistory(range),
          loadSummary(),
        ]);
        await pollTelemetry();
      } catch {
        if (mounted.current) {
          setError(
            "Initial dashboard load failed. Check the backend endpoints."
          );
        }
      } finally {
        if (mounted.current) setLoading(false);
      }
    }

    void initialize();

    const liveTimer = window.setInterval(() => {
      void pollTelemetry();
    }, 1000);

    const summaryTimer = window.setInterval(() => {
      void loadSummary().catch(() => {
        if (mounted.current) {
          setError("Could not refresh historical analytics.");
        }
      });
    }, 5000);

    return () => {
      mounted.current = false;
      window.clearInterval(liveTimer);
      window.clearInterval(summaryTimer);
    };
  }, [loadHistory, loadSummary, pollTelemetry]);

  useEffect(() => {
    if (!mounted.current) return;

    void loadHistory(range).catch(() => {
      setError("Could not load the selected chart range.");
    });
  }, [range, loadHistory]);

  async function refresh() {
    setLoading(true);

    try {
      await Promise.all([
        pollTelemetry(),
        loadSummary(),
        loadHistory(range),
      ]);
    } catch {
      setError("Refresh failed. Check the API terminal.");
    } finally {
      setLoading(false);
    }
  }

  async function updateAlert(
    alertId: string,
    action: AlertAction
  ) {
    const actionKey = `${alertId}:${action}`;

    setActionBusy(actionKey);
    setActionMessage("");
    setActionError(false);

    try {
      const response = await fetch(
        `${API}/api/alerts/${alertId}/${action}`,
        { method: "POST" }
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(
          result.detail || `Could not ${action} this alert.`
        );
      }

      setActionMessage(
        result.message ||
          (action === "acknowledge"
            ? "Alert acknowledged successfully."
            : "Alert resolved successfully.")
      );

      await loadSummary();
    } catch (err) {
      setActionError(true);
      setActionMessage(
        err instanceof Error
          ? err.message
          : "Alert action failed."
      );
    } finally {
      setActionBusy(null);
    }
  }

  const filteredAlerts = alerts.filter(
    (alert) =>
      (alertStatus === "ALL" ||
        alert.status === alertStatus) &&
      (alertSeverity === "ALL" ||
        alert.severity === alertSeverity)
  );

  const assetIds = [
    ...new Set([
      ...assets.map((asset) => asset.asset_id),
      ...latest.map((reading) => reading.asset_id),
    ]),
  ];

  const activeCount =
    counts?.active_count ??
    alerts.filter((alert) =>
      ["OPEN", "ACKNOWLEDGED"].includes(alert.status)
    ).length;

  const warmest = [...assets]
    .filter((asset) => asset.avg_temperature != null)
    .sort(
      (a, b) =>
        Number(b.avg_temperature) - Number(a.avg_temperature)
    )[0];

  const mostVibrating = [...assets]
    .filter((asset) => asset.avg_vibration != null)
    .sort(
      (a, b) =>
        Number(b.avg_vibration) - Number(a.avg_vibration)
    )[0];

  const highestFlow = [...assets]
    .filter((asset) => asset.avg_flow != null)
    .sort(
      (a, b) => Number(b.avg_flow) - Number(a.avg_flow)
    )[0];

  const validTemperatures = assets
    .map((asset) => asset.avg_temperature)
    .filter((value): value is number => value != null);

  const temperatureSpread =
    validTemperatures.length >= 2
      ? Math.max(...validTemperatures) -
        Math.min(...validTemperatures)
      : null;

  return (
    <main className="dashboard">
      <header className="topbar">
        <div className="brand">
          <div className="brand-icon">
            <Activity size={23} />
          </div>

          <div>
            <h1>
              Pump<span>IQ</span>
            </h1>
            <p>INDUSTRIAL ANALYTICS PLATFORM</p>
          </div>
        </div>

        <div className="header-right">
          <span className="simulation-badge">SIMULATION</span>

          <span
            className={`live-status ${
              online ? "connected" : "disconnected"
            }`}
          >
            <i />
            {online ? "API Connected" : "Connection issue"}
          </span>

          <button
            className="refresh-button"
            onClick={() => void refresh()}
            disabled={loading}
          >
            <RefreshCw size={16} />
            {loading ? "Loading" : "Refresh"}
          </button>
        </div>
      </header>

      <section className="page-heading">
        <div>
          <p className="eyebrow">OPERATIONS / ANALYTICS</p>
          <h2>Industrial Pump Analytics</h2>
          <p className="subtitle">
            Historical performance, live telemetry and condition
            monitoring.
          </p>
        </div>

        <div className="updated-label">
          <span
            className={`status-dot ${online ? "" : "offline"}`}
          />
          <div>
            <strong>1-second telemetry polling</strong>
            <small>
              Last check:{" "}
              {lastChecked
                ? lastChecked.toLocaleTimeString()
                : "Waiting..."}
            </small>
          </div>
        </div>
      </section>

      {error && (
        <div className="error-banner">
          <AlertTriangle size={18} />
          {error}
        </div>
      )}

      <section className="kpi-grid">
        <Kpi
          icon={<Thermometer />}
          label="Historical average temperature"
          value={`${fmt(overview?.avg_temperature)} °C`}
          note="All recorded telemetry rows"
        />

        <Kpi
          icon={<Droplets />}
          label="Historical average flow"
          value={`${fmt(overview?.avg_flow)} m³/h`}
          note="All recorded telemetry rows"
        />

        <Kpi
          icon={<Waves />}
          label="Historical average vibration"
          value={`${fmt(overview?.avg_vibration)} mm/s`}
          note="All recorded telemetry rows"
        />

        <Kpi
          icon={<Gauge />}
          label="Historical average pressure"
          value={`${fmt(overview?.avg_pressure)} bar`}
          note="All recorded telemetry rows"
        />

        <Kpi
          icon={<Database />}
          label="Total readings"
          value={Number(
            overview?.total_readings ?? 0
          ).toLocaleString()}
          note="Stored in PostgreSQL"
        />

        <Kpi
          icon={<Bell />}
          label="Active alerts"
          value={String(activeCount)}
          note={`${
            counts?.critical_active_count ?? 0
          } critical · ${
            counts?.warning_active_count ?? 0
          } warning`}
          warning={activeCount > 0}
        />
      </section>

      <section className="section-heading">
        <div>
          <h2>Live sensor trends</h2>
          <p>
            Chart range changes independently of one-second telemetry
            polling.
          </p>
        </div>

        <div className="range-selector">
          {([5, 15, 30] as Range[]).map((minutes) => (
            <button
              key={minutes}
              className={range === minutes ? "selected" : ""}
              onClick={() => setRange(minutes)}
            >
              {minutes} min
            </button>
          ))}
        </div>
      </section>

      <section className="charts-grid">
        <TrendChart
          title="Temperature trend"
          subtitle="Operating temperature by pump"
          data={history}
          metricKey="temperature_c"
          unit="°C"
          color="#f4a261"
          assetIds={assetIds}
        />

        <TrendChart
          title="Flow-rate trend"
          subtitle="Fluid flow by pump"
          data={history}
          metricKey="flow_rate_m3_h"
          unit="m³/h"
          color="#5ca8ff"
          assetIds={assetIds}
        />

        <TrendChart
          title="Vibration trend"
          subtitle="Mechanical condition indicator"
          data={history}
          metricKey="vibration_mm_s"
          unit="mm/s"
          color="#c4a7ff"
          assetIds={assetIds}
        />

        <TrendChart
          title="Pressure trend"
          subtitle="Recorded operating pressure"
          data={history}
          metricKey="pressure_bar"
          unit="bar"
          color="#65b8a6"
          assetIds={assetIds}
        />
      </section>

      <section className="section-heading">
        <div>
          <h2>Pump health monitoring</h2>
          <p>
            Illustrative status from configured simulation thresholds,
            not validated safety limits.
          </p>
        </div>
        <span className="panel-tag">{assets.length} ASSETS</span>
      </section>

      <section className="asset-grid">
        {assets.map((asset) => {
          const current = latest.find(
            (reading) => reading.asset_id === asset.asset_id
          );
          const health = getHealth(asset, current);

          return (
            <article className="panel asset-card" key={asset.asset_id}>
              <div className="asset-top">
                <div className="asset-symbol">
                  <HeartPulse size={20} />
                </div>

                <div className="asset-info">
                  <strong>{asset.asset_id}</strong>
                  <span>{asset.asset_name}</span>
                  <small>
                    {asset.location || "Location not specified"}
                  </small>
                </div>

                <span
                  className={`health-badge ${health.level}`}
                >
                  {health.label}
                </span>
              </div>

              <p className="health-reason">{health.reason}</p>

              <div className="sensor-grid">
                <div>
                  <span>
                    <Thermometer size={14} />
                    Temperature
                  </span>
                  <strong>
                    {fmt(current?.temperature_c)}
                    <small> °C</small>
                  </strong>
                </div>

                <div>
                  <span>
                    <Droplets size={14} />
                    Flow rate
                  </span>
                  <strong>
                    {fmt(current?.flow_rate_m3_h)}
                    <small> m³/h</small>
                  </strong>
                </div>

                <div>
                  <span>
                    <Waves size={14} />
                    Vibration
                  </span>
                  <strong>
                    {fmt(current?.vibration_mm_s)}
                    <small> mm/s</small>
                  </strong>
                </div>

                <div>
                  <span>
                    <Gauge size={14} />
                    Pressure
                  </span>
                  <strong>
                    {fmt(current?.pressure_bar)}
                    <small> bar</small>
                  </strong>
                </div>

                <div>
                  <span>
                    <Zap size={14} />
                    Motor current
                  </span>
                  <strong>
                    {fmt(current?.motor_current_a)}
                    <small> A</small>
                  </strong>
                </div>

                <div>
                  <span>
                    <Thermometer size={14} />
                    Historical avg temp
                  </span>
                  <strong>
                    {fmt(asset.avg_temperature)}
                    <small> °C</small>
                  </strong>
                </div>

                <div>
                  <span>
                    <Thermometer size={14} />
                    Historical max temp
                  </span>
                  <strong>
                    {fmt(asset.max_temperature)}
                    <small> °C</small>
                  </strong>
                </div>

                <div>
                  <span>
                    <Droplets size={14} />
                    Historical avg flow
                  </span>
                  <strong>
                    {fmt(asset.avg_flow)}
                    <small> m³/h</small>
                  </strong>
                </div>
              </div>

              <div className="asset-footer">
                <span>
                  <Database size={14} />
                  {Number(asset.total_readings || 0).toLocaleString()}{" "}
                  readings
                </span>

                <span>
                  <Clock3 size={14} />
                  Last:{" "}
                  {fullTime(
                    current?.received_at || current?.recorded_at
                  )}
                </span>
              </div>
            </article>
          );
        })}

        {!loading && assets.length === 0 && (
          <div className="panel empty-state">
            No assets returned by the API.
          </div>
        )}
      </section>

      <section className="section-heading">
        <div>
          <h2>Business insights</h2>
          <p>
            Descriptive comparisons from historical averages;
            differences alone do not prove a fault.
          </p>
        </div>
        <span className="panel-tag">HISTORICAL</span>
      </section>

      <section className="insights-grid">
        <article className="panel insight-card">
          <Lightbulb size={20} />
          <h3>Highest average temperature</h3>
          <strong>{warmest?.asset_id ?? "—"}</strong>
          <p>
            {warmest
              ? `${fmt(warmest.avg_temperature)} °C historical average temperature.`
              : "Not enough readings."}
          </p>
        </article>

        <article className="panel insight-card">
          <Waves size={20} />
          <h3>Highest average vibration</h3>
          <strong>{mostVibrating?.asset_id ?? "—"}</strong>
          <p>
            {mostVibrating
              ? `${fmt(mostVibrating.avg_vibration)} mm/s historical average vibration.`
              : "Not enough readings."}
          </p>
        </article>

        <article className="panel insight-card">
          <Droplets size={20} />
          <h3>Highest average flow</h3>
          <strong>{highestFlow?.asset_id ?? "—"}</strong>
          <p>
            {highestFlow
              ? `${fmt(highestFlow.avg_flow)} m³/h historical average flow.`
              : "Not enough readings."}
          </p>
        </article>

        <article className="panel insight-card">
          <Activity size={20} />
          <h3>Temperature spread</h3>
          <strong>{fmt(temperatureSpread)} °C</strong>
          <p>
            Difference between the highest and lowest asset historical
            average temperature.
          </p>
        </article>
      </section>

      <section className="section-heading">
        <div>
          <h2>Alert management</h2>
          <p>
            Acknowledge active alerts and resolve them only after
            recovery has been detected.
          </p>
        </div>
      </section>

      <section className="alert-summary-grid">
        <article className="panel alert-summary">
          <span>OPEN</span>
          <strong>{counts?.open_count ?? 0}</strong>
        </article>

        <article className="panel alert-summary">
          <span>ACKNOWLEDGED</span>
          <strong>{counts?.acknowledged_count ?? 0}</strong>
        </article>

        <article className="panel alert-summary">
          <span>RESOLVED</span>
          <strong>{counts?.resolved_count ?? 0}</strong>
        </article>
      </section>

      <section className="panel alerts-panel">
        <div className="panel-heading">
          <div>
            <h3>Alert history</h3>
            <p>Latest events from the alert engine</p>
          </div>
          <span className="alert-count">{activeCount} ACTIVE</span>
        </div>

        {actionMessage && (
          <div
            className={`alert-action-message ${
              actionError ? "error" : ""
            }`}
            role="status"
          >
            {actionError ? (
              <AlertTriangle size={16} />
            ) : (
              <CheckCircle2 size={16} />
            )}
            {actionMessage}
          </div>
        )}

        <div className="filters">
          <label>
            Status
            <select
              value={alertStatus}
              onChange={(event) =>
                setAlertStatus(event.target.value)
              }
            >
              <option value="ALL">All statuses</option>
              <option value="OPEN">Open</option>
              <option value="ACKNOWLEDGED">Acknowledged</option>
              <option value="RESOLVED">Resolved</option>
            </select>
          </label>

          <label>
            Severity
            <select
              value={alertSeverity}
              onChange={(event) =>
                setAlertSeverity(event.target.value)
              }
            >
              <option value="ALL">All severities</option>
              <option value="CRITICAL">Critical</option>
              <option value="WARNING">Warning</option>
              <option value="INFO">Info</option>
            </select>
          </label>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Asset</th>
                <th>Rule</th>
                <th>Severity</th>
                <th>Status</th>
                <th>Recovery</th>
                <th>Opened</th>
                <th>Action</th>
              </tr>
            </thead>

            <tbody>
              {filteredAlerts.slice(0, 30).map((alert) => (
                <tr key={alert.alert_id}>
                  <td className="asset-cell">{alert.asset_id}</td>

                  <td>{alert.rule_code.replaceAll("_", " ")}</td>

                  <td>
                    <span
                      className={`severity ${alert.severity.toLowerCase()}`}
                    >
                      {alert.severity}
                    </span>
                  </td>

                  <td>
                    <span
                      className={`alert-status ${alert.status.toLowerCase()}`}
                    >
                      {alert.status}
                    </span>
                  </td>

                  <td>
                    {alert.condition_recovered ? (
                      <span className="alert-recovery recovered">
                        <Check size={14} />
                        Recovered
                      </span>
                    ) : alert.status === "RESOLVED" ? (
                      <span className="muted-action">Closed</span>
                    ) : (
                      <span className="muted-action">
                        Monitoring
                      </span>
                    )}
                  </td>

                  <td>{fullTime(alert.opened_at)}</td>

                  <td>
                    <div className="alert-actions">
                      {alert.status === "OPEN" && (
                        <button
                          className="alert-action-button acknowledge"
                          disabled={actionBusy !== null}
                          onClick={() =>
                            void updateAlert(
                              alert.alert_id,
                              "acknowledge"
                            )
                          }
                        >
                          <ClipboardCheck size={14} />
                          {actionBusy ===
                          `${alert.alert_id}:acknowledge`
                            ? "Working…"
                            : "Acknowledge"}
                        </button>
                      )}

                      {alert.status === "ACKNOWLEDGED" &&
                        (alert.condition_recovered ? (
                          <button
                            className="alert-action-button resolve"
                            disabled={actionBusy !== null}
                            onClick={() =>
                              void updateAlert(
                                alert.alert_id,
                                "resolve"
                              )
                            }
                          >
                            <CheckCircle2 size={14} />
                            {actionBusy ===
                            `${alert.alert_id}:resolve`
                              ? "Working…"
                              : "Resolve"}
                          </button>
                        ) : (
                          <span className="muted-action">
                            Waiting for recovery
                          </span>
                        ))}

                      {alert.status === "RESOLVED" && (
                        <span className="muted-action">Closed</span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}

              {!filteredAlerts.length && (
                <tr>
                  <td colSpan={7} className="empty-cell">
                    No alerts match these filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <footer className="footer">
        <span>
          <Activity size={15} />
          PumpIQ · Industrial Pump Analytics
        </span>
        <span>
          Portfolio project · Simulated telemetry · No machine control
        </span>
      </footer>
    </main>
  );
}