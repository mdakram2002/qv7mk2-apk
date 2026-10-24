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
  expected_hourly_intervals: number;
  eligible_forecast_intervals: number;
  forecast_availability_percent: number | null;
  hourly_actual_coverage_percent: number | null;
  expected_actual_intervals: number;
  actual_records_observed: number;
  actual_coverage_percent: number | null;
  missing_forecasts: number;
  missing_hourly_actuals: number;
  quality_counts: Record<string, number>;
};
type Interval = {
  startTime: string;
  actual_generation_mw: number | null;
  forecast_generation_mw: number | null;
  selected_publishTime: string | null;
  decision_cutoff: string;
  eligible_forecast_versions?: number;
  selection_status?: string;
  selection_reason?: string;
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
type ForecastVersion = {
  startTime: string;
  publishTime: string;
  generation_mw: number;
  actual_generation_mw: number | null;
  eligible: boolean;
  selected: boolean;
  reason: string;
};
type ForecastHistory = {
  startTime: string;
  decision_cutoff: string;
  eligible_version_count: number;
  selection_status: string;
  versions: ForecastVersion[];
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
const paths: Record<string, string> = { Overview: "/", Intervals: "/intervals", "Forecast history": "/forecast-history", "Data quality": "/data-quality", "About this analysis": "/about" };

export default function App() {
  const location = useLocation();
  const navigate = useNavigate();
  const page = Object.entries(paths).find(([, path]) => path === location.pathname)?.[0] ?? "Overview";
  const setPage = (name: string) => navigate(paths[name] ?? "/");
  const [cutoff, setCutoff] = useState("10:00");
  const [day, setDay] = useState("2026-01-01");
  const [historyTime, setHistoryTime] = useState("12:00");
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
    queryKey: ["history", day, historyTime, cutoff],
    queryFn: () =>
      get<ForecastHistory>(
        `forecast-versions?start_time=${encodeURIComponent(`${day}T${historyTime}:00Z`)}&cutoff_time=${cutoff}`,
      ),
    enabled: page === "Forecast history",
  });
  const quality = useQuery({
    queryKey: ["quality", cutoff],
    queryFn: () => get<Record<string, unknown>>(`data-quality?cutoff_time=${cutoff}`),
  });
  const rows = series.data ?? [];
  const chartRows = rows.map((r) => ({
      ...r,
      time: new Date(r.startTime).toLocaleString("en-GB", {
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
        timeZone: "Europe/London",
      }),
    }));
  const s = summary.data;
  const error = summary.error || series.error || daily.error || quality.error;
  const retrievedAt = typeof quality.data?.retrieved_at === "string"
    ? new Date(quality.data.retrieved_at).toLocaleString("en-GB", { timeZone: "Europe/London" })
    : null;
  const qualityCount = (key: string) => {
    const value = quality.data?.[key];
    return typeof value === "number" ? value : null;
  };
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
              aria-current={page === label ? "page" : undefined}
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
          <button className="side-help" onClick={() => setPage("About this analysis")}>
            <CircleHelp size={16} />
            <span>About this analysis</span>
          </button>
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
            <span className="icon-btn" aria-hidden="true">
              <CircleHelp size={18} />
            </span>
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
                    Forecasts published by <strong>{cutoff} Europe/London</strong> on the
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
                  note={`Mean absolute error across ${fmt(s?.sample_count)} matched hourly pairs`}
                  color="mint"
                />
                <Metric
                  title="ROOT MEAN SQUARE ERROR"
                  value={fmt(s?.rmse_mw)}
                  unit="MW"
                  icon={<Gauge size={16} />}
                  note="Square root of mean squared error · MW"
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
                  note={`Mean signed error · ${(s?.bias_mw ?? 0) >= 0 ? "over-forecast" : "under-forecast"}`}
                  color="purple"
                />
                <Metric
                  title="WAPE"
                  value={fmt(s?.wape_percent, 1)}
                  unit="%"
                  icon={<BarChart3 size={16} />}
                  note="Total absolute error ÷ total actual · %"
                  color="orange"
                />
                <div className="coverage-card">
                  <div className="coverage-top">
                    <div>
                      <span className="metric-title">HOURLY MATCHED COVERAGE</span>
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
                      {fmt(s?.matched_intervals)} of {fmt(s?.expected_hourly_intervals)} hourly starts
                    </span>
                    <span className="quality-status">
                      <i /> {s ? "Updated" : "Awaiting data"}
                    </span>
                  </div>
                  <div className="coverage-foot">
                    <span>Forecast starts available: {fmt(s?.forecast_availability_percent, 1)}%</span>
                    <span>Half-hour actuals: {fmt(s?.actual_coverage_percent, 1)}%</span>
                  </div>
                </div>
              </div>
              {s && (s.coverage_percent !== 100 || s.actual_coverage_percent !== 100 || s.forecast_availability_percent !== 100) && (
                <div className="alert" role="status">
                  <AlertTriangle size={18} />
                  <div>
                    <b>Source coverage is incomplete</b>
                    <span>Hourly forecast availability is {fmt(s.forecast_availability_percent, 1)}%; hourly matched coverage is {fmt(s.coverage_percent, 1)}%; half-hour actual coverage is {fmt(s.actual_coverage_percent, 1)}%. Missing source intervals are not filled.</span>
                  </div>
                </div>
              )}
              <div className="chart-grid">
                <section className="panel main-chart">
                  <div className="panel-head">
                    <div>
                      <div className="panel-title">Forecast vs actual</div>
                      <div className="panel-sub">
                        Hourly forecast and actual wind generation <span>·</span> MW
                      </div>
                    </div>
                    <span className="subtle-button">
                      January <ChevronDown size={14} />
                    </span>
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
                      <Empty text="Ingest genuine Elexon records to render the hourly comparison." />
                    )}
                  </div>
                  <div className="chart-xlabel">
                    Actual MW is the average of the two half-hour FUELHH records for each hour · Europe/London
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
                  <span className="dots" aria-hidden="true">···</span>
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
                    {retrievedAt ? `Retrieved ${retrievedAt} Europe/London` : "Ingestion time unavailable"}
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
                    Hourly forecast and paired actual average
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
                    href={`${API}/api/v1/export/matched.csv?start_date=${day}&end_date=${nextDay(day)}&cutoff_time=${cutoff}${filter === "all" ? "" : `&quality_status=${filter}`}`}
                  >
                    <Download size={15} /> Export CSV
                  </a>
                </div>
              </div>
              <div className="table-scroll">
                <table aria-label="Wind generation interval observations">
                  <thead>
                    <tr>
                      <th>DELIVERY INTERVAL</th>
                      <th>FORECAST · MW</th>
                      <th>ACTUAL · MW</th>
                      <th>SIGNED ERROR</th>
                      <th>ABS. ERROR</th>
                      <th>PUBLISHED AT (UK)</th>
                      <th>ELIGIBLE VERSIONS</th>
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
                            ? new Date(row.selected_publishTime).toLocaleString("en-GB", {
                                timeZone: "Europe/London",
                              })
                            : "—"}
                        </td>
                        <td title={row.selection_reason ?? row.selection_status ?? ""}>{row.eligible_forecast_versions ?? 0}</td>
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
                {intervalData.isLoading && <div role="status" className="empty-state">Loading interval records…</div>}
                {intervalData.error && <div role="alert" className="alert">Interval records are unavailable: {(intervalData.error as Error).message}</div>}
                {!intervalData.isLoading && !intervalData.error && !intervalData.data?.items.length && (
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
                    Retrieved WINDFOR versions for the selected delivery interval
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
                <label className="control-label">
                  DELIVERY START (UK TIME)
                  <select value={historyTime} onChange={(e) => setHistoryTime(e.target.value)}>
                    {Array.from({ length: 24 }, (_, hour) => `${String(hour).padStart(2, "0")}:00`).map((time) => <option key={time} value={time}>{time}</option>)}
                  </select>
                </label>
              </div>
              <div className="history-callout">
                <Clock3 size={16} /> Historical selection cutoff:{" "}
                <b>{cutoff} Europe/London on the prior day</b>. Later
                publications are excluded from accuracy metrics.
              </div>
              {history.isLoading ? <div role="status" className="empty-state">Loading forecast history…</div> : history.error ? <div role="alert" className="alert">Forecast history is unavailable: {(history.error as Error).message}</div> : history.data?.versions.length ? (
                <div className="table-scroll">
                  <p className="panel-sub">Delivery start: {new Date(history.data.startTime).toLocaleString("en-GB", { timeZone: "Europe/London" })} Europe/London · {history.data.eligible_version_count} eligible version(s) at cutoff</p>
                  <table>
                    <thead>
                      <tr>
                        <th>DELIVERY START</th>
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
                          <td>{new Date(row.startTime).toLocaleString("en-GB", { timeZone: "Europe/London" })}</td>
                          <td>{new Date(row.publishTime).toLocaleString("en-GB", { timeZone: "Europe/London" })}</td>
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
                  <Empty text="No WINDFOR versions were retrieved for this delivery start in the current dataset." />
              )}
            </section>
          )}
          {page === "Data quality" && (
            <section className="quality-layout">
              {quality.error && <div role="alert" className="alert">Data quality report is unavailable: {(quality.error as Error).message}</div>}
              {quality.isLoading && <div role="status" className="alert">Loading the ingestion and data-quality report…</div>}
              <div className="quality-cards">
                <div className="panel quality-tile">
                  <div className="metric-title">EXPECTED ACTUAL INTERVALS</div>
                  <strong>{fmt(qualityCount("expected_actual_intervals"))}</strong>
                  <small>Half-hour slots in January</small>
                </div>
                <div className="panel quality-tile">
                  <div className="metric-title">ACTUAL RECORDS OBSERVED</div>
                  <strong>{fmt(qualityCount("actual_records_observed"))}</strong>
                  <small>FUELHH · WIND</small>
                </div>
                <div className="panel quality-tile">
                  <div className="metric-title">FORECAST VERSIONS</div>
                  <strong>{fmt(qualityCount("forecast_versions"))}</strong>
                  <small>WINDFOR versions within delivery month</small>
                </div>
                <div className="panel quality-tile">
                  <div className="metric-title">EXPECTED HOURLY STARTS</div>
                  <strong>{fmt(qualityCount("expected_hourly_delivery_starts"))}</strong>
                  <small>Independent hourly delivery denominator</small>
                </div>
                <div className="panel quality-tile">
                  <div className="metric-title">ELIGIBLE FORECAST STARTS</div>
                  <strong>{fmt(qualityCount("eligible_forecast_delivery_intervals"))}</strong>
                  <small>At {cutoff} Europe/London cutoff</small>
                </div>
                <div className="panel quality-tile">
                  <div className="metric-title">MATCHED HOURLY INTERVALS</div>
                  <strong>{fmt(qualityCount("matched_intervals_at_cutoff"))}</strong>
                  <small>Both hourly actual and forecast available</small>
                </div>
                <div className="panel quality-tile">
                  <div className="metric-title">MISSING HOURLY FORECASTS</div>
                  <strong>{fmt(qualityCount("missing_forecasts_at_cutoff"))}</strong>
                  <small>Expected hourly starts without an eligible version</small>
                </div>
                <div className="panel quality-tile">
                  <div className="metric-title">MISSING HALF-HOUR ACTUALS</div>
                  <strong>{fmt(qualityCount("missing_actuals"))}</strong>
                  <small>Invalid source records: {fmt(qualityCount("invalid_source_records"))}</small>
                </div>
              </div>
              <section className="panel quality-details">
                <div className="panel-title">Ingestion & provenance</div>
                <p className="panel-sub">
                  The displayed forecast counts and matches use the selected cutoff. Raw files and retrieval details are available below.
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
                  href={`${API}/api/v1/export/ingestion-report.json?cutoff_time=${cutoff}`}
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
          {page === "About this analysis" && (
            <section className="quality-layout">
              <div className="panel">
                <div className="panel-title">Purpose and scope</div>
                <p className="panel-sub">WindLens compares UK national wind forecasts with actual generation to support day-ahead forecast review. It does not calculate a procurement volume, cost, or saving.</p>
              </div>
              <div className="bottom-grid">
                <section className="panel">
                  <div className="panel-title">Official sources</div>
                  <p className="panel-sub">FUELHH actual generation filtered to WIND, and WINDFOR forecast versions. Raw source fields are retained before normalization.</p>
                </section>
                <section className="panel">
                  <div className="panel-title">Historical cutoff</div>
                  <p className="panel-sub">The selected forecast is the latest version published by {cutoff} Europe/London on the preceding delivery date. This is an analytical assumption, not a confirmed market deadline.</p>
                </section>
                <section className="panel">
                  <div className="panel-title">Resolution and matching</div>
                  <p className="panel-sub">Forecasts are hourly while FUELHH actuals are half-hourly. Hourly actual MW is the mean of both half-hour readings that start in that hour. If either is unavailable, the hourly actual is missing.</p>
                </section>
                <section className="panel">
                  <div className="panel-title">Metrics</div>
                  <p className="panel-sub">Error is forecast minus actual. MAE is average absolute error; RMSE penalizes larger errors; bias is mean signed error (positive means overforecast); WAPE is total absolute error divided by total actual generation.</p>
                </section>
              </div>
              <div className="panel quality-details">
                <div className="panel-title">Limitations</div>
                <p className="panel-sub">The cached forecast publication search begins 18 December 2025, so older publication history is not proven complete. Accuracy describes the retrieved sample and cutoff assumption. Demand, prices, and other generation are outside this analysis.</p>
                <button className="download" onClick={() => setPage("Data quality")}>View data quality and provenance</button>
              </div>
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
      <b>No records available</b>
      <span>{text}</span>
    </div>
  );
}
function nextDay(day: string) {
  const d = new Date(`${day}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + 1);
  return d.toISOString().slice(0, 10);
}
