/**
 * Search Component
 *
 * Provides keyword search functionality for reports.
 * Validates: Requirement 5.5
 */

import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { format } from 'date-fns';
import { ja } from 'date-fns/locale';
import { searchReports } from '../api/client';
import type { Report } from '../types/api';
import './Search.css';

export function Search() {
  const [keyword, setKeyword] = useState('');
  const [results, setResults] = useState<Report[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  async function handleSearch(e: FormEvent) {
    e.preventDefault();

    if (!keyword.trim()) return;

    try {
      setLoading(true);
      setError(null);
      const data = await searchReports(keyword);
      setResults(data);
      setSearched(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="search">
      <Link to="/" className="back-link">← レポート一覧に戻る</Link>

      <h1>レポート検索</h1>

      <form onSubmit={handleSearch} className="search-form">
        <input
          type="text"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          placeholder="キーワードを入力 (例: Gaza, Israel, Syria)..."
          className="search-input"
          disabled={loading}
        />
        <button type="submit" className="search-button" disabled={loading}>
          {loading ? '検索中...' : '検索'}
        </button>
      </form>

      {error && <div className="error">エラー: {error}</div>}

      {searched && !loading && (
        <div className="search-results">
          <h2>検索結果 ({results.length}件)</h2>

          {results.length === 0 ? (
            <p>「{keyword}」に一致するレポートが見つかりませんでした</p>
          ) : (
            <ul className="results-list">
              {results.map((report) => (
                <li key={report.id} className="result-item">
                  <Link to={`/reports/${report.id}`} className="result-link">
                    <h3>{report.cluster.topic_name}</h3>
                    <div className="result-meta">
                      <span>{report.cluster.media_names.join(', ')}</span>
                      <span>{report.cluster.articles.length} 件の記事</span>
                      <span>{format(new Date(report.generated_at), 'yyyy年M月d日', { locale: ja })}</span>
                    </div>
                    <p>{report.summary}</p>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
