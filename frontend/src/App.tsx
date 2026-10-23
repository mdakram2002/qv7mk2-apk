import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  ChevronDown,
  CircleHelp,
  Clock3,
  Download,
  Gauge,
  LayoutDashboard,
  ListFilter,
  Radio,
  ShieldCheck,
  Wind,
  Zap,
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const API = import.meta.env.VITE_API_URL ?? "";
type Summary = {
  sample_count: number;
  mae_mw: number | null;
  rmse_mw: number | null;
  bias_mw: number | null;
  wape_percent: number | null;
  expected_intervals: number;
  matched_intervals: number;
  coverage_percent: number | null;
  quality_counts: Record<string, number>;
};
type Interval = {
  startTime: string;
  actual_generation_mw: number | null;
  forecast_generation_mw: number | null;
  selected_publishTime: string | null;
  decision_cutoff: string;
  signed_error_mw: number | null;
  absolute_error_mw: number | null;
  data_quality_status: string;
};
type Daily = {
  delivery_date: string;
  sample_count: number;
  mae_mw: number | null;
  bias_mw: number | null;
  coverage_percent?: number;
};
async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${API}/api/v1/${path}`);
  if (!response.ok) throw new Error(`API request failed (${response.status})`);
  return response.json() as Promise<T>;
}
const fmt = (n: number | null | undefined, d = 0) =>
  n == null
    ? "—"
    : n.toLocaleString("en-GB", {
        minimumFractionDigits: d,
        maximumFractionDigits: d,
      });
const nav = [
  ["Overview", LayoutDashboard],
  ["Intervals", ListFilter],
  ["Forecast history", Clock3],
  ["Data quality", ShieldCheck],
] as const;
const paths: Record<string, string> = { Overview: "/", Intervals: "/intervals", "Forecast history": "/forecast-history", "Data quality": "/data-quality" };

export default function App() {
  const location = useLocation();
  const navigate = useNavigate();
  const page = Object.entries(paths).find(([, path]) => path === location.pathname)?.[0] ?? "Overview";
  const setPage = (name: string) => navigate(paths[name] ?? "/");
  const [cutoff, setCutoff] = useState("10:00");
  const [day, setDay] = useState("2026-01-01");
  const [filter, setFilter] = useState("all");
  const [tablePage, setTablePage] = useState(1);
  const [sortBy, setSortBy] = useState("startTime");
  const [sortOrder, setSortOrder] = useState("asc");
  const query = useMemo(
    () => `start_date=2026-01-01&end_date=2026-02-01&cutoff_time=${cutoff}`,
    [cutoff],
  );
  const summary = useQuery({
    queryKey: ["summary", query],
    queryFn: () => get<Summary>(`summary?${query}`),
  });
  const daily = useQuery({
    queryKey: ["daily", cutoff],
    queryFn: () => get<Daily[]>(`accuracy/daily?cutoff_time=${cutoff}`),
  });
  const series = useQuery({
    queryKey: ["series", query],
    queryFn: () => get<Interval[]>(`timeseries?${query}`),
  });
  const intervalData = useQuery({
    queryKey: ["intervals", day, cutoff, filter, tablePage, sortBy, sortOrder],
    queryFn: () =>
      get<{ items: Interval[]; total: number }>(
        `intervals?start_date=${day}&end_date=${nextDay(day)}&cutoff_time=${cutoff}&page=${tablePage}&page_size=24&sort_by=${sortBy}&sort_order=${sortOrder}${filter === "all" ? "" : `&quality_status=${filter}`}`,
      ),
    enabled: page === "Intervals",
  });
  const history = useQuery({
    queryKey: ["history", day, cutoff],
    queryFn: () =>
      get<{ versions: Record<string, unknown>[]; decision_cutoff: string }>(
        `forecast-versions?start_time=${encodeURIComponent(`${day}T12:00:00Z`)}&cutoff_time=${cutoff}`,
      ),
    enabled: page === "Forecast history",
  });
  const quality = useQuery({
    queryKey: ["quality"],
    queryFn: () => get<Record<string, unknown>>("data-quality"),
    enabled: page === "Data quality",
  });
  const rows = series.data ?? [];
  const chartRows = rows
    .filter((_, i) => i % 6 === 0)
    .map((r) => ({
      ...r,
      time: new Date(r.startTime).toLocaleTimeString("en-GB", {
        hour: "2-digit",
        minute: "2-digit",
        timeZone: "Europe/London",
      }),
    }));
  const s = summary.data;
  const error = summary.error || series.error;
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">
            <Wind size={21} />
          </div>
          <div>
            <strong>
              wind<span>lens</span>
            </strong>
            <small>ENERGY INTELLIGENCE</small>
          </div>
        </div>
        <div className="nav-label">WORKSPACE</div>
        <nav>
          {nav.map(([label, Icon]) => (
            <button
              key={label}
              className={`nav-item ${page === label ? "active" : ""}`}
              onClick={() => setPage(label)}
            >
              <Icon size={17} />
              {label}
              {label === "Data quality" && <span className="nav-dot" />}
            </button>
          ))}
        </nav>
        <div className="side-bottom">
          <div className="source-pill">
            <span className="live-dot" />
            <div>
              <b>Elexon BMRS</b>
              <small>Official source</small>
            </div>
            <ShieldCheck size={16} />
          </div>
          <div className="side-help">
            <CircleHelp size={16} />
            <span>About this analysis</span>
          </div>
          <div className="avatar-row">
            <div className="avatar">WL</div>
            <div>
              <b>WindLens</b>
              <small>Analyst workspace</small>
            </div>
            <ChevronDown size={15} />
          </div>
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <div className="breadcrumb">
            Analytics <span>/</span> <b>{page}</b>
          </div>
          <div className="top-right">
            <span className="period">
              <i /> HISTORICAL PERIOD
            </span>
            <span className="period-date">01 — 31 Jan 2026</span>
            <button className="icon-btn" aria-label="Help">
              <CircleHelp size={18} />
            </button>
            <div className="avatar small">AM</div>
          </div>
        </header>
        <section className="content">
          <div className="page-title">
            <div>
              <div className="eyebrow">
                <span className="eyebrow-line" /> NATIONAL WIND PERFORMANCE
              </div>
              <h1>{page === "Overview" ? "Forecast accuracy" : page}</h1>
              <p>
                Compare day-ahead forecasts against actual UK wind generation.
              </p>
            </div>
            <div className="title-actions">
              <label className="control-label">
                DELIVERY PERIOD
                <select defaultValue="january">
                  <option value="january">January 2026</option>
                </select>
              </label>
              <label className="control-label">
                DECISION CUTOFF
                <div className="select-wrap">
                  <Clock3 size={15} />
                  <input
                    type="time"
                    value={cutoff}
                    onChange={(e) => setCutoff(e.target.value)}
                    aria-label="Decision cutoff"
                  />
                </div>
              </label>
            </div>
          </div>
          {error && (
            <div className="alert">
              <AlertTriangle size={18} />
              <div>
                <b>Data unavailable</b>
                <span>
                  {(error as Error).message}. No production values are being
                  shown as real until the dataset is ingested.
                </span>
              </div>
            </div>
          )}
          {page === "Overview" && (
            <>
              <div className="assumption">
                <div className="assumption-icon">
                  <CircleHelp size={17} />
                </div>
                <div>
                  <b>Cutoff assumption</b>
                  <span>
                    Forecasts published by <strong>{cutoff} GMT</strong> on the
                    day before delivery are included. This is an analytical
                    setting, not a verified market gate.
                  </span>
                </div>
                <button onClick={() => setPage("Data quality")}>
                  Methodology <span>↗</span>
                </button>
              </div>
              <div className="metrics-grid">
                <Metric
                  title="FORECAST MAE"
                  value={fmt(s?.mae_mw)}
                  unit="MW"
                  icon={<Activity size={16} />}
                  note={`${fmt(s?.sample_count)} matched intervals`}
                  color="mint"
                />
                <Metric
                  title="ROOT MEAN SQUARE ERROR"
                  value={fmt(s?.rmse_mw)}
                  unit="MW"
                  icon={<Gauge size={16} />}
                  note="Lower is more accurate"
                />
                <Metric
                  title="FORECAST BIAS"
                  value={fmt(s?.bias_mw, 1)}
                  unit="MW"
                  icon={
                    (s?.bias_mw ?? 0) >= 0 ? (
                      <ArrowUpRight size={16} />
                    ) : (
                      <ArrowDownRight size={16} />
                    )
                  }
                  note={
                    (s?.bias_mw ?? 0) >= 0
                      ? "Net over-forecast"
                      : "Net under-forecast"
                  }
                  color="purple"
                />
                <Metric
                  title="WAPE"
                  value={fmt(s?.wape_percent, 1)}
                  unit="%"
                  icon={<BarChart3 size={16} />}
                  note="Weighted absolute percentage error"
                  color="orange"
                />
                <div className="coverage-card">
                  <div className="coverage-top">
                    <div>
                      <span className="metric-title">DATA COVERAGE</span>
                      <strong>
                        {s?.coverage_percent == null
                          ? "—"
                          : `${fmt(s.coverage_percent, 1)}%`}
                      </strong>
                    </div>
                    <div className="coverage-icon">
                      <ShieldCheck size={18} />
                    </div>
                  </div>
                  <div className="coverage-bar">
                    <i style={{ width: `${s?.coverage_percent ?? 0}%` }} />
                  </div>
                  <div className="coverage-foot">
                    <span>
                      {fmt(s?.matched_intervals)} of{" "}
                      {fmt(s?.expected_intervals)} intervals
                    </span>
                    <span className="quality-status">
                      <i /> {s ? "Updated" : "Awaiting data"}
                    </span>
                  </div>
                </div>
              </div>
              <div className="chart-grid">
                <section className="panel main-chart">
                  <div className="panel-head">
                    <div>
                      <div className="panel-title">Forecast vs actual</div>
                      <div className="panel-sub">
                        Half-hourly wind generation <span>·</span> MW
                      </div>
                    </div>
                    <button className="subtle-button">
                      January <ChevronDown size={14} />
                    </button>
                  </div>
                  <div className="legend">
                    <span>
                      <i className="legend-actual" /> Actual
                    </span>
                    <span>
                      <i className="legend-forecast" /> Day-ahead forecast
                    </span>
                  </div>
                  <div className="chart-area">
                    {rows.length ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart
                          data={chartRows}
                          margin={{ top: 12, right: 12, left: 0, bottom: 0 }}
                        >
                          <defs>
                            <linearGradient
                              id="actualFill"
                              x1="0"
                              y1="0"
                              x2="0"
                              y2="1"
                            >
                              <stop
                                offset="0%"
                                stopColor="#14796d"
                                stopOpacity={0.16}
                              />
                              <stop
                                offset="100%"
                                stopColor="#14796d"
                                stopOpacity={0}
                              />
                            </linearGradient>
                          </defs>
                          <CartesianGrid vertical={false} stroke="#e9eef2" />
                          <XAxis
                            dataKey="time"
                            tickLine={false}
                            axisLine={false}
                            tick={{ fill: "#8997a3", fontSize: 11 }}
                            interval="preserveStartEnd"
                          />
                          <YAxis
                            tickLine={false}
                            axisLine={false}
                            tick={{ fill: "#8997a3", fontSize: 11 }}
                            width={44}
                          />
                          <Tooltip />
                          <Area
                            type="monotone"
                            dataKey="actual_generation_mw"
                            name="Actual"
                            stroke="#14796d"
                            fill="url(#actualFill)"
                            strokeWidth={2}
                          />
                          <Line
                            type="monotone"
                            dataKey="forecast_generation_mw"
                            name="Forecast"
                            stroke="#91a1b4"
                            strokeWidth={1.7}
                            dot={false}
                          />
                        </ComposedChart>
                      </ResponsiveContainer>
                    ) : (
                      <Empty text="Ingest genuine Elexon records to render the half-hourly comparison." />
                    )}
                  </div>
                  <div className="chart-xlabel">
                    Delivery intervals · Europe/London
                  </div>
                </section>
                <section className="panel error-chart">
                  <div className="panel-head">
                    <div>
                      <div className="panel-title">Daily accuracy</div>
                      <div className="panel-sub">
                        Mean absolute error <span>·</span> MW
                      </div>
                    </div>
                    <button className="dots">···</button>
                  </div>
                  <div className="chart-area">
                    {daily.data?.length ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart
                          data={daily.data}
                          margin={{ top: 14, right: 4, left: -18, bottom: 0 }}
                        >
                          <defs>
                            <linearGradient
                              id="maeFill"
                              x1="0"
                              y1="0"
                              x2="0"
                              y2="1"
                            >
                              <stop
                                offset="0%"
                                stopColor="#e2a65e"
                                stopOpacity={0.25}
                              />
                              <stop
                                offset="100%"
                                stopColor="#e2a65e"
                                stopOpacity={0}
                              />
                            </linearGradient>
                          </defs>
                          <CartesianGrid vertical={false} stroke="#e9eef2" />
                          <XAxis
                            dataKey="delivery_date"
                            tickLine={false}
                            axisLine={false}
                            tick={{ fill: "#8997a3", fontSize: 10 }}
                            tickFormatter={(v) => v.slice(8)}
                          />
                          <YAxis
                            tickLine={false}
                            axisLine={false}
                            tick={{ fill: "#8997a3", fontSize: 10 }}
                          />
                          <Tooltip />
                          <Area
                            type="monotone"
                            dataKey="mae_mw"
                            name="MAE (MW)"
                            stroke="#d59145"
                            strokeWidth={2}
                            fill="url(#maeFill)"
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    ) : (
                      <Empty text="Daily accuracy will appear once matched intervals are available." />
                    )}
                  </div>
                  <div className="mini-note">
                    <span className="tiny-dot" /> Accuracy across{" "}
                    {daily.data?.length ?? 0} delivery days
                  </div>
                </section>
              </div>
              <div className="bottom-grid">
                <section className="panel error-panel">
                  <div className="panel-head">
                    <div>
                      <div className="panel-title">
                        Forecast error by interval
                      </div>
                      <div className="panel-sub">
                        Forecast minus actual <span>·</span> MW
                      </div>
                    </div>
                    <span className="tag">{fmt(s?.sample_count)} MATCHED</span>
                  </div>
                  <div className="error-plot">
                    {chartRows.some((row) => row.signed_error_mw != null) ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={chartRows.filter((row) => row.signed_error_mw != null)} margin={{ top: 8, right: 6, left: 0, bottom: 0 }}>
                          <CartesianGrid vertical={false} stroke="#e9eef2" />
                          <XAxis dataKey="time" tickLine={false} axisLine={false} tick={{ fill: "#8997a3", fontSize: 9 }} interval="preserveStartEnd" />
                          <YAxis tickLine={false} axisLine={false} tick={{ fill: "#8997a3", fontSize: 9 }} width={40} />
                          <ReferenceLine y={0} stroke="#84949b" />
                          <Tooltip />
                          <Bar dataKey="signed_error_mw" name="Error (MW)" fill="#68a892" radius={[2, 2, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    ) : <Empty text="Interval errors appear when actuals and eligible forecasts are both available." />}
                  </div>
                  <p className="footnote">
                    Positive values indicate an over-forecast; negative values indicate an under-forecast.
                  </p>
                </section>
                <section className="panel source-panel">
                  <div className="source-heading">
                    <div className="source-badge">
                      <Zap size={17} />
                    </div>
                    <div>
                      <b>Source integrity</b>
                      <span>Official BMRS datasets</span>
                    </div>
                    <ShieldCheck className="verified" size={17} />
                  </div>
                  <div className="source-row">
                    <span>Actual generation</span>
                    <b>
                      FUELHH <i className="check">✓</i>
                    </b>
                  </div>
                  <div className="source-row">
                    <span>Forecast versions</span>
                    <b>
                      WINDFOR <i className="check">✓</i>
                    </b>
                  </div>
                  <div className="source-row">
                    <span>Analysis timezone</span>
                    <b>Europe/London</b>
                  </div>
                  <div className="source-updated">
                    <Radio size={13} />
                    {s
                      ? "January data loaded"
                      : "Waiting for verified ingestion"}
                  </div>
                </section>
              </div>
            </>
          )}
          {page === "Intervals" && (
            <section className="panel table-panel">
              <div className="panel-head">
                <div>
                  <div className="panel-title">Interval observations</div>
                  <div className="panel-sub">
                    Actual and selected forecast by half-hourly start time
                  </div>
                </div>
                <div className="table-controls">
                  <label className="control-label">
                    DELIVERY DATE
                    <input
                      type="date"
                      min="2026-01-01"
                      max="2026-01-31"
                      value={day}
                      onChange={(e) => { setDay(e.target.value); setTablePage(1); }}
                    />
                  </label>
                  <label className="control-label">
                    STATUS
                    <select
                      value={filter}
                      onChange={(e) => { setFilter(e.target.value); setTablePage(1); }}
                    >
                      <option value="all">All intervals</option>
                      <option value="matched">Matched</option>
                      <option value="missing_forecast">Missing forecast</option>
                      <option value="missing_actual">Missing actual</option>
                    </select>
                  </label>
                  <label className="control-label">
                    SORT BY
                    <select value={sortBy} onChange={(e) => { setSortBy(e.target.value); setTablePage(1); }}>
                      <option value="startTime">Delivery time</option>
                      <option value="forecast_generation_mw">Forecast MW</option>
                      <option value="actual_generation_mw">Actual MW</option>
                      <option value="signed_error_mw">Signed error</option>
                      <option value="absolute_error_mw">Absolute error</option>
                      <option value="selected_publishTime">Publication time</option>
                    </select>
                  </label>
                  <button className="download" onClick={() => setSortOrder((value) => value === "asc" ? "desc" : "asc")} aria-label="Change sort order">{sortOrder === "asc" ? "Ascending ↑" : "Descending ↓"}</button>
                  <a
                    className="download"
                    href={`${API}/api/v1/export/matched.csv?cutoff_time=${cutoff}`}
                  >
                    <Download size={15} /> Export CSV
                  </a>
                </div>
              </div>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>DELIVERY INTERVAL</th>
                      <th>FORECAST · MW</th>
                      <th>ACTUAL · MW</th>
                      <th>SIGNED ERROR</th>
                      <th>ABS. ERROR</th>
                      <th>PUBLISHED</th>
                      <th>DECISION CUTOFF</th>
                      <th>STATUS</th>
                    </tr>
                  </thead>
                  <tbody>
                    {intervalData.data?.items.map((row) => (
                      <tr key={row.startTime}>
                        <td>
                          {new Date(row.startTime).toLocaleString("en-GB", {
                            timeZone: "Europe/London",
                          })}
                        </td>
                        <td>{fmt(row.forecast_generation_mw)}</td>
                        <td>{fmt(row.actual_generation_mw)}</td>
                        <td>{fmt(row.signed_error_mw)}</td>
                        <td>{fmt(row.absolute_error_mw)}</td>
                        <td>
                          {row.selected_publishTime
                            ? new Date(
                                row.selected_publishTime,
                              ).toLocaleTimeString("en-GB", {
                                timeZone: "Europe/London",
                              })
                            : "—"}
                        </td>
                        <td>{new Date(row.decision_cutoff).toLocaleString("en-GB", { timeZone: "Europe/London" })}</td>
                        <td>
                          <span className={`status ${row.data_quality_status}`}>
                            {row.data_quality_status.replace("_", " ")}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!intervalData.data?.items.length && (
                  <Empty text="No interval records are available for this selection." />
                )}
              </div>
              <div className="table-foot">
                Showing {intervalData.data?.items.length ?? 0} of{" "}
                {intervalData.data?.total ?? 0} intervals{" "}
                <span>
                  <button disabled={tablePage <= 1} onClick={() => setTablePage((n) => Math.max(1, n - 1))}>Previous</button>
                  &nbsp; Page {tablePage} of {Math.max(1, Math.ceil((intervalData.data?.total ?? 0) / 24))} &nbsp;
                  <button disabled={tablePage >= Math.ceil((intervalData.data?.total ?? 0) / 24)} onClick={() => setTablePage((n) => n + 1)}>Next</button>
                </span>
              </div>
            </section>
          )}
          {page === "Forecast history" && (
            <section className="panel history-panel">
              <div className="panel-head">
                <div>
                  <div className="panel-title">
                    Forecast publication history
                  </div>
                  <div className="panel-sub">
                    Every retrieved WINDFOR version for a delivery interval
                  </div>
                </div>
                <label className="control-label">
                  DELIVERY DATE
                  <input
                    type="date"
                    min="2026-01-01"
                    max="2026-01-31"
                    value={day}
                    onChange={(e) => setDay(e.target.value)}
                  />
                </label>
              </div>
              <div className="history-callout">
                <Clock3 size={16} /> Historical selection cutoff:{" "}
                <b>{cutoff} Europe/London on the prior day</b>. Later
                publications are excluded from accuracy metrics.
              </div>
              {history.data?.versions.length ? (
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>PUBLISHED AT</th>
                        <th>FORECAST · MW</th>
                        <th>ACTUAL · MW</th>
                        <th>DECISION</th>
                        <th>SELECTION REASON</th>
                      </tr>
                    </thead>
                    <tbody>
                      {history.data.versions.map((row, i) => (
                        <tr key={i}>
                          <td>{String(row.publishTime)}</td>
                          <td>{String(row.generation_mw)}</td>
                          <td>{String(row.actual_generation_mw ?? "—")}</td>
                          <td>
                            <span
                              className={`status ${row.eligible ? "matched" : "missing_forecast"}`}
                            >
                              {row.selected ? "Selected" : row.eligible ? "Eligible" : "Excluded"}
                            </span>
                          </td>
                          <td>{String(row.reason)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <Empty text="No versions retrieved yet. Historical data will show all publications and cutoff exclusions." />
              )}
            </section>
          )}
          {page === "Data quality" && (
            <section className="quality-layout">
              <div className="quality-cards">
                <div className="panel quality-tile">
                  <div className="metric-title">RAW ACTUAL RECORDS</div>
                  <strong>
                    {fmt(Number(quality.data?.raw_actual_records) || 0)}
                  </strong>
                  <small>FUELHH · WIND</small>
                </div>
                <div className="panel quality-tile">
                  <div className="metric-title">FORECAST VERSIONS</div>
                  <strong>
                    {fmt(Number(quality.data?.forecast_versions) || 0)}
                  </strong>
                  <small>WINDFOR publication history</small>
                </div>
                <div className="panel quality-tile">
                  <div className="metric-title">MISSING FORECASTS</div>
                  <strong>
                    {fmt(Number(quality.data?.missing_forecasts) || 0)}
                  </strong>
                  <small>At configured cutoff</small>
                </div>
                <div className="panel quality-tile">
                  <div className="metric-title">MISSING ACTUALS</div>
                  <strong>{fmt(Number(quality.data?.missing_actuals) || 0)}</strong>
                  <small>FUELHH delivery intervals</small>
                </div>
                <div className="panel quality-tile">
                  <div className="metric-title">DATA ISSUES</div>
                  <strong>
                    {fmt(
                      Number(
                        (
                          quality.data?.quality as
                            | Record<string, number>
                            | undefined
                        )?.invalid_records,
                      ) || 0,
                    )}
                  </strong>
                  <small>Invalid source records</small>
                </div>
              </div>
              <section className="panel quality-details">
                <div className="panel-title">Ingestion & provenance</div>
                <p className="panel-sub">
                  Counts are reported from the latest successful official API
                  ingestion.
                </p>
                <pre>
                  {JSON.stringify(
                    quality.data ?? { status: "Loading report…" },
                    null,
                    2,
                  )}
                </pre>
                <a
                  className="download"
                  href={`${API}/api/v1/export/ingestion-report.json`}
                >
                  <Download size={15} /> Download ingestion report
                </a>
                <div className="download-row">
                  <a href={`${API}/api/v1/export/actuals.csv`}>Actuals CSV</a>
                  <a href={`${API}/api/v1/export/forecasts.csv`}>
                    Forecast versions CSV
                  </a>
                  <a href={`${API}/api/v1/export/daily-accuracy.csv`}>
                    Daily accuracy CSV
                  </a>
                </div>
              </section>
            </section>
          )}
          <footer>
            <span>
              WindLens <b>·</b> Decision support only
            </span>
            <span>
              All times shown in Europe/London <b>·</b> Data: Elexon BMRS
            </span>
          </footer>
        </section>
      </main>
    </div>
  );
}
function Metric({
  title,
  value,
  unit,
  icon,
  note,
  color = "blue",
}: {
  title: string;
  value: string;
  unit: string;
  icon: React.ReactNode;
  note: string;
  color?: string;
}) {
  return (
    <div className="metric-card">
      <div className="metric-head">
        <span className="metric-title">{title}</span>
        <span className={`metric-icon ${color}`}>{icon}</span>
      </div>
      <div className="metric-value">
        {value}
        <small>{unit}</small>
      </div>
      <div className="metric-note">{note}</div>
    </div>
  );
}
function Empty({ text }: { text: string }) {
  return (
    <div className="empty-state">
      <div className="empty-icon">
        <Wind size={20} />
      </div>
      <b>Verified measurements pending</b>
      <span>{text}</span>
    </div>
  );
}
function nextDay(day: string) {
  const d = new Date(`${day}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + 1);
  return d.toISOString().slice(0, 10);
}
