import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import type { DashboardStats } from "../types";

interface Props {
  onBack: () => void;
}

function formatWhen(value?: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function Dashboard({ onBack }: Props) {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getAdminDashboard();
      setStats(data);
    } catch (err) {
      setStats(null);
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const summary = stats?.summary;

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div>
          <h1>Dashboard</h1>
          <p>Subscribers and access activity</p>
        </div>
        <div className="dashboard-header-actions">
          <button type="button" className="sidebar-menu-btn" onClick={() => void load()}>
            Refresh
          </button>
          <button type="button" className="sidebar-menu-btn" onClick={onBack}>
            Back to chat
          </button>
        </div>
      </header>

      {loading && <div className="dashboard-status">Loading…</div>}
      {error && <div className="dashboard-error">{error}</div>}

      {!loading && !error && summary && (
        <>
          <section className="dashboard-section">
            <h2>Summary</h2>
            <div className="dashboard-metrics">
              <div className="dashboard-metric">
                <span className="dashboard-metric-label">Total users</span>
                <strong>{summary.total_users}</strong>
              </div>
              <div className="dashboard-metric">
                <span className="dashboard-metric-label">Google sign-ups</span>
                <strong>{summary.google_users}</strong>
              </div>
              <div className="dashboard-metric">
                <span className="dashboard-metric-label">Legacy User ID</span>
                <strong>{summary.legacy_users}</strong>
              </div>
              <div className="dashboard-metric">
                <span className="dashboard-metric-label">Logins today</span>
                <strong>{summary.logins_today}</strong>
              </div>
              <div className="dashboard-metric">
                <span className="dashboard-metric-label">Unique visitors today</span>
                <strong>{summary.active_users_today}</strong>
              </div>
              <div className="dashboard-metric">
                <span className="dashboard-metric-label">Logins (7 days)</span>
                <strong>{summary.logins_7d}</strong>
              </div>
              <div className="dashboard-metric">
                <span className="dashboard-metric-label">Unique visitors (7 days)</span>
                <strong>{summary.active_users_7d}</strong>
              </div>
              <div className="dashboard-metric">
                <span className="dashboard-metric-label">Tasks / messages</span>
                <strong>
                  {summary.total_tasks} / {summary.total_messages}
                </strong>
              </div>
            </div>
          </section>

          <section className="dashboard-section">
            <h2>Daily access (last 14 days)</h2>
            {stats.daily_logins.length === 0 ? (
              <p className="dashboard-empty">No login records yet.</p>
            ) : (
              <div className="dashboard-table-wrap">
                <table className="dashboard-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Logins</th>
                      <th>Unique users</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...stats.daily_logins].reverse().map((row) => (
                      <tr key={row.date}>
                        <td>{row.date}</td>
                        <td>{row.logins}</td>
                        <td>{row.unique_users}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="dashboard-section">
            <h2>Subscribers</h2>
            <div className="dashboard-table-wrap">
              <table className="dashboard-table">
                <thead>
                  <tr>
                    <th>User</th>
                    <th>Auth</th>
                    <th>Tasks</th>
                    <th>Messages</th>
                    <th>Logins</th>
                    <th>First activity</th>
                    <th>Last activity</th>
                    <th>Last login</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.users.map((user) => (
                    <tr key={user.user_id}>
                      <td className="dashboard-user-cell">{user.user_id}</td>
                      <td>{user.is_google ? "Google" : "Legacy"}</td>
                      <td>{user.task_count}</td>
                      <td>{user.message_count}</td>
                      <td>{user.login_count}</td>
                      <td>{formatWhen(user.first_seen)}</td>
                      <td>{formatWhen(user.last_active)}</td>
                      <td>{formatWhen(user.last_login)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="dashboard-section">
            <h2>Recent access</h2>
            {stats.recent_logins.length === 0 ? (
              <p className="dashboard-empty">
                Login events are recorded from Google (or local bypass) sign-in.
              </p>
            ) : (
              <div className="dashboard-table-wrap">
                <table className="dashboard-table">
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>User</th>
                      <th>Name</th>
                      <th>Method</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.recent_logins.map((login) => (
                      <tr key={login.id}>
                        <td>{formatWhen(login.logged_at)}</td>
                        <td className="dashboard-user-cell">{login.user_id}</td>
                        <td>{login.name || "—"}</td>
                        <td>{login.method}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
