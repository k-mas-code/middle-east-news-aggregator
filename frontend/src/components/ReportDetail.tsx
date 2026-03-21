/**
 * Report Detail Component
 *
 * Displays detailed report with articles and bias comparison.
 * Validates: Requirements 5.2, 5.3, 5.4
 */

import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { format } from 'date-fns';
import { ja } from 'date-fns/locale';
import { getReport } from '../api/client';
import type { Report } from '../types/api';
import { BiasChart } from './BiasChart';
import './ReportDetail.css';

export function ReportDetail() {
  const { id } = useParams<{ id: string }>();
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchReport() {
      if (!id) return;

      try {
        setLoading(true);
        const data = await getReport(id);
        setReport(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load report');
      } finally {
        setLoading(false);
      }
    }

    fetchReport();
  }, [id]);

  if (loading) {
    return <div className="loading">レポートを読み込み中...</div>;
  }

  if (error || !report) {
    return (
      <div className="error">
        <p>エラー: {error || 'レポートが見つかりません'}</p>
        <Link to="/">← レポート一覧に戻る</Link>
      </div>
    );
  }

  return (
    <div className="report-detail">
      <Link to="/" className="back-link">← レポート一覧に戻る</Link>

      <header className="report-header">
        <h1>{report.cluster.topic_name}</h1>
        <div className="report-info">
          <span>生成日時: {format(new Date(report.generated_at), 'PPpp', { locale: ja })}</span>
          <span>{report.cluster.articles.length} 件の記事</span>
          <span>バイアス差: {(report.comparison.bias_diff * 100).toFixed(1)}%</span>
        </div>
      </header>

      <section className="report-summary">
        <h2>サマリー</h2>
        <p>{report.summary}</p>
      </section>

      <section className="bias-comparison">
        <h2>バイアス比較</h2>
        <BiasChart comparison={report.comparison} />
      </section>

      <section className="articles">
        <h2>記事一覧</h2>
        {report.cluster.media_names.map((media) => {
          const mediaArticles = report.cluster.articles.filter(
            (a) => a.media_name === media
          );

          return (
            <div key={media} className="media-section">
              <h3>{media}</h3>
              {mediaArticles.map((article) => (
                <article key={article.id} className="article">
                  <h4>{article.title}</h4>
                  <div className="article-meta">
                    <span>{format(new Date(article.published_at), 'PPpp', { locale: ja })}</span>
                    <a href={article.url} target="_blank" rel="noopener noreferrer">
                      原文を読む →
                    </a>
                  </div>
                  <p>{article.content.substring(0, 300)}...</p>
                </article>
              ))}
            </div>
          );
        })}
      </section>

      {report.comparison.common_entities.length > 0 && (
        <section className="entities">
          <h2>共通エンティティ</h2>
          <div className="entity-list">
            {report.comparison.common_entities.map((entity, idx) => (
              <span key={idx} className="entity-tag">
                {entity.text} ({entity.label})
              </span>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
