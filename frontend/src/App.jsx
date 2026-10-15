import React, { useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import InternshipCard from './components/InternshipCard';
import SearchBar from './components/SearchBar';
import LiveStatsBanner from './components/LiveStatsBanner';
import QuickFilterNav from './components/QuickFilterNav';
import EmailSubscription from './components/EmailSubscription';
import useDarkMode from './hooks/useDarkMode';
import { 
  LayoutGrid, 
  Sparkles, 
  AlertCircle, 
  Sun, 
  Moon, 
  ChevronLeft, 
  ChevronRight,
  Briefcase,
  Github
} from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const ITEMS_PER_PAGE = 12;

function App() {
  const [internships, setInternships] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSource, setSelectedSource] = useState(null);
  const [sources, setSources] = useState([]);
  const [stats, setStats] = useState(null);
  const [theme, toggleTheme] = useDarkMode();

  const [filters, setFilters] = useState({
    location: '',
    min_score: null,
    ai_only: false,
    company_type: '',
    high_salary: false,
  });

  // Fetch internships with all search and quick filters
  const fetchInternships = useCallback(async (query, pageNum, sourceId, currentFilters) => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        offset: (pageNum - 1) * ITEMS_PER_PAGE,
        limit: ITEMS_PER_PAGE,
      };
      if (query) params.search = query;
      if (sourceId) params.source = sourceId;
      if (currentFilters.location) params.location = currentFilters.location;
      if (currentFilters.min_score) params.min_score = currentFilters.min_score;
      if (currentFilters.ai_only) params.ai_only = true;
      if (currentFilters.company_type) params.company_type = currentFilters.company_type;
      if (currentFilters.high_salary) params.high_salary = true;

      const response = await axios.get(`${API_URL}/internships`, { params });
      const { items, total } = response.data;

      setInternships(items || []);
      setTotal(total || 0);
    } catch (err) {
      console.error(err);
      setError('无法获取实习岗位数据，请检查网络连接或稍后重试。');
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch stats for the live stats hero banner
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await axios.get(`${API_URL}/stats`);
        setStats(response.data);
      } catch (err) {
        console.error('Failed to fetch stats', err);
      }
    };
    fetchStats();
  }, []);

  // Fetch data on page, search, source, or filter change
  useEffect(() => {
    fetchInternships(searchQuery, page, selectedSource, filters);
  }, [page, searchQuery, selectedSource, filters, fetchInternships]);

  // Load sources for company icons row
  useEffect(() => {
    const fetchSources = async () => {
      try {
        const response = await axios.get(`${API_URL}/sources`);
        setSources(response.data.filter((s) => s.enabled));
      } catch (err) {
        console.error('Failed to fetch sources', err);
      }
    };
    fetchSources();
  }, []);

  const handleSearch = (query) => {
    setSearchQuery(query);
    setPage(1);
  };

  const handleSourceSelect = (sourceId) => {
    setSelectedSource((prev) => (prev === sourceId ? null : sourceId));
    setPage(1);
  };

  const handleFilterChange = (newFilters) => {
    setFilters((prev) => ({ ...prev, ...newFilters }));
    setPage(1);
  };

  const handleResetFilters = () => {
    setFilters({
      location: '',
      min_score: null,
      ai_only: false,
      company_type: '',
      high_salary: false,
    });
    setSelectedSource(null);
    setSearchQuery('');
    setPage(1);
  };

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= Math.ceil(total / ITEMS_PER_PAGE)) {
      setPage(newPage);
      window.scrollTo({ top: 380, behavior: 'smooth' });
    }
  };

  const totalPages = Math.ceil(total / ITEMS_PER_PAGE) || 1;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 text-slate-800 dark:text-slate-100 transition-colors duration-300 flex flex-col font-sans">
      {/* Header */}
      <header className="sticky top-0 z-30 backdrop-blur-md bg-white/85 dark:bg-slate-900/85 border-b border-slate-200/80 dark:border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="bg-blue-600 p-2 rounded-xl shadow-xs">
              <LayoutGrid className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-1">
                Internship<span className="text-blue-600 dark:text-blue-400">Aggregator</span>
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-3 sm:gap-4">
            <div className="text-xs sm:text-sm font-semibold text-slate-600 dark:text-slate-300 hidden md:flex items-center gap-1.5 bg-slate-100 dark:bg-slate-800 px-3 py-1.5 rounded-full border border-slate-200 dark:border-slate-700">
              <Sparkles className="w-4 h-4 text-amber-500" />
              Summer 2026 Ready
            </div>

            <a
              href="https://github.com/flamegrain/internship-aggregator"
              target="_blank"
              rel="noopener noreferrer"
              className="p-2 rounded-xl text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
              title="GitHub Repository"
            >
              <Github className="w-5 h-5" />
            </a>

            <button
              onClick={toggleTheme}
              className="p-2 rounded-xl text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
              aria-label="Toggle Dark Mode"
            >
              {theme === 'dark' ? <Sun className="w-5 h-5 text-amber-400" /> : <Moon className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full">
        {/* Hero Title */}
        <div className="text-center mb-6 pt-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 dark:bg-blue-950/50 border border-blue-200/80 dark:border-blue-800 text-blue-700 dark:text-blue-300 text-xs font-semibold mb-3">
            <Briefcase className="w-3.5 h-3.5" />
            留学生与应届生求职首选 • 每日全网实时爬取
          </div>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-extrabold text-slate-900 dark:text-white tracking-tight mb-3">
            Find Your Dream Internship
          </h2>
          <p className="text-base sm:text-lg text-slate-600 dark:text-slate-400 max-w-2xl mx-auto">
            一站式聚合全美科技大厂、量化金融、AI 独角兽与航空国防实习机会，透明展示薪资与 Visa 友好指数
          </p>
        </div>

        {/* 1. Live Stats & Update Time Banner */}
        <LiveStatsBanner stats={stats} loading={!stats} />

        {/* 2. Company Logos Row (High-contrast pure white tile in both light and dark mode) */}
        <div className="mb-6">
          <div className="text-center text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500 mb-3">
            Top Recruiting Companies • 点击直接筛选
          </div>
          <div className="flex items-center justify-start sm:justify-center gap-3 sm:gap-5 overflow-x-auto no-scrollbar py-2 px-2">
            {sources.map((source) => {
              const isSelected = selectedSource === source.id;
              return (
                <button
                  key={source.id}
                  onClick={() => handleSourceSelect(source.id)}
                  className={`flex flex-col items-center gap-1.5 group transition-all duration-200 cursor-pointer shrink-0 ${
                    isSelected ? 'scale-105 opacity-100' : 'opacity-70 hover:opacity-100'
                  }`}
                >
                  {/* Clean pure white tile for crisp logo contrast in both themes */}
                  <div
                    className={`w-14 h-14 sm:w-16 sm:h-16 rounded-2xl bg-white border-2 flex items-center justify-center p-2.5 shadow-xs transition-all ${
                      isSelected
                        ? 'border-blue-600 ring-4 ring-blue-500/20 shadow-md'
                        : 'border-slate-200 dark:border-slate-700 group-hover:border-blue-400 dark:group-hover:border-slate-500'
                    }`}
                  >
                    <img
                      src={source.logo_url}
                      alt={source.name}
                      className="max-w-full max-h-full object-contain transition-transform group-hover:scale-105"
                      onError={(e) => {
                        e.target.onerror = null;
                        e.target.src =
                          'https://ui-avatars.com/api/?name=' +
                          encodeURIComponent(source.name) +
                          '&background=6366f1&color=fff';
                      }}
                    />
                  </div>
                  <span
                    className={`text-xs font-medium whitespace-nowrap transition-colors ${
                      isSelected ? 'text-blue-600 dark:text-blue-400 font-bold' : 'text-slate-600 dark:text-slate-400'
                    }`}
                  >
                    {source.name.split(' ')[0]}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* 3. Search Bar with single-row scrollable hot keywords */}
        <SearchBar onSearch={handleSearch} value={searchQuery} />

        {/* 4. Quick Filter Navigation Bar */}
        <QuickFilterNav
          filters={filters}
          onFilterChange={handleFilterChange}
          onReset={handleResetFilters}
        />

        {/* Results Section */}
        {error ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="bg-rose-50 dark:bg-rose-950/40 p-3 rounded-full mb-4 border border-rose-200 dark:border-rose-900">
              <AlertCircle className="w-8 h-8 text-rose-500" />
            </div>
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">网络或数据加载异常</h3>
            <p className="text-slate-500 dark:text-slate-400 mt-1 max-w-md text-sm">{error}</p>
            <button
              onClick={() => fetchInternships(searchQuery, page, selectedSource, filters)}
              className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700 transition-colors cursor-pointer"
            >
              重新加载
            </button>
          </div>
        ) : (
          <>
            {loading ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 animate-pulse">
                {[...Array(6)].map((_, i) => (
                  <div
                    key={i}
                    className="bg-white dark:bg-slate-800 rounded-xl h-64 border border-slate-200 dark:border-slate-700"
                  ></div>
                ))}
              </div>
            ) : internships.length === 0 ? (
              <div className="text-center py-20 bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-8">
                <Briefcase className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
                <h3 className="text-lg font-bold text-slate-900 dark:text-white">未找到符合条件的实习岗位</h3>
                <p className="text-slate-500 dark:text-slate-400 text-sm mt-1 mb-4">
                  请尝试调整或重置筛选条件、清除搜索关键词
                </p>
                <button
                  onClick={handleResetFilters}
                  className="px-4 py-2 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700 transition-colors cursor-pointer"
                >
                  清空所有筛选
                </button>
              </div>
            ) : (
              <>
                <div className="mb-4 flex items-center justify-between text-xs sm:text-sm text-slate-500 dark:text-slate-400">
                  <div>
                    正在显示第{' '}
                    <span className="font-bold text-slate-800 dark:text-slate-200">
                      {(page - 1) * ITEMS_PER_PAGE + 1}
                    </span>{' '}
                    -{' '}
                    <span className="font-bold text-slate-800 dark:text-slate-200">
                      {Math.min(page * ITEMS_PER_PAGE, total)}
                    </span>{' '}
                    条，共{' '}
                    <span className="font-bold text-blue-600 dark:text-blue-400">{total}</span> 条有效岗位
                  </div>
                  {totalPages > 1 && (
                    <div className="hidden sm:block">
                      页码: {page} / {totalPages}
                    </div>
                  )}
                </div>

                {/* Job Cards Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {internships.map((internship) => (
                    <InternshipCard key={internship.id} internship={internship} />
                  ))}
                </div>

                {/* Pagination Controls */}
                <div className="mt-12 flex items-center justify-center gap-3">
                  <button
                    onClick={() => handlePageChange(page - 1)}
                    disabled={page === 1}
                    className="p-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer shadow-xs"
                    title="Previous Page"
                  >
                    <ChevronLeft className="w-5 h-5" />
                  </button>

                  <span className="px-4 py-2 text-sm font-semibold text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-xs">
                    {page} / {totalPages}
                  </span>

                  <button
                    onClick={() => handlePageChange(page + 1)}
                    disabled={page >= totalPages}
                    className="p-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer shadow-xs"
                    title="Next Page"
                  >
                    <ChevronRight className="w-5 h-5" />
                  </button>
                </div>
              </>
            )}
          </>
        )}

        {/* 5. Email Subscription & Instant 20 Posts Digest Section */}
        <EmailSubscription apiUrl={API_URL} />
      </main>

      {/* Footer */}
      <footer className="mt-auto border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/80 py-8 text-center text-xs text-slate-500 dark:text-slate-400">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <LayoutGrid className="w-4 h-4 text-blue-600 dark:text-blue-400" />
            <span className="font-semibold text-slate-800 dark:text-slate-200">
              Internship Aggregator
            </span>
            <span>• 专为全美留学生与应届生打造的实习聚合平台</span>
          </div>
          <div>
            <span>Data synced daily • Powered by FastAPI & React</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
