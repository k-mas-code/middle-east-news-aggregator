/**
 * Main App Component
 *
 * Provides routing for the Middle East News Aggregator frontend.
 */

import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { ReportList } from './components/ReportList';
import { ReportDetail } from './components/ReportDetail';
import { Search } from './components/Search';
import './App.css';

function App() {
  return (
    <Router>
      <div className="app">
        <nav className="navbar">
          <div className="nav-container">
            <Link to="/" className="nav-brand">
              中東ニュース分析システム
            </Link>
            <div className="nav-links">
              <Link to="/" className="nav-link">レポート</Link>
              <Link to="/search" className="nav-link">検索</Link>
            </div>
          </div>
        </nav>

        <main className="main-content">
          <Routes>
            <Route path="/" element={<ReportList />} />
            <Route path="/reports/:id" element={<ReportDetail />} />
            <Route path="/search" element={<Search />} />
          </Routes>
        </main>

        <footer className="footer">
          <p>
            Al Jazeera、Reuters、BBCの中東ニュースを比較分析
          </p>
        </footer>
      </div>
    </Router>
  );
}

export default App;
