/**
 * Report List Component
 *
 * Displays a list of all reports with topic names and media sources.
 * Validates: Requirements 5.1, 5.6
 */

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { format } from 'date-fns';
import { ja } from 'date-fns/locale';
import { getReports, getStatus } from '../api/client';
import type { Report, SystemStatus } from '../types/api';
import './ReportList.css';

export function ReportList() {
  const [reports, setReports] = useState<Report[]>([]);
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        const [reportsData, statusData] = await Promise.all([
          getReports(),
          getStatus(),
        ]);

        setReports(reportsData);
        setStatus(statusData);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load reports');
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, []);

  if (loading) {
    return <div className="loading">レポートを読み込み中...</div>;
  }

  if (error) {
    return <div className="error">エラー: {error}</div>;
  }

  return (
    <div className="report-list">
      <header className="report-list-header">
        <h1>中東ニュース分析レポート</h1>
        {status && status.last_collection && (
          <div className="last-update">
            最終更新: {format(new Date(status.last_collection), 'PPpp', { locale: ja })}
          </div>
        )}
        {status && (
          <div className="stats">
            {status.total_reports} 件のレポート • {status.total_articles} 件の記事
          </div>
        )}
      </header>

      {reports.length === 0 ? (
        <div className="no-reports">レポートがありません</div>
      ) : (
        <ul className="reports">
          {reports.map((report) => (
            <li key={report.id} className="report-item">
              <Link to={`/reports/${report.id}`} className="report-link">
                <h2>{report.cluster.topic_name}</h2>
                <div className="report-meta">
                  <span className="media-sources">
                    {report.cluster.media_names.join(', ')}
                  </span>
                  <span className="article-count">
                    {report.cluster.articles.length} 件の記事
                  </span>
                  <span className="generated-at">
                    {format(new Date(report.generated_at), 'yyyy年M月d日', { locale: ja })}
                  </span>
                </div>
                <p className="report-summary">{report.summary}</p>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
