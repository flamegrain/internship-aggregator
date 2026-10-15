import React, { useState } from 'react';
import { Search, X, Flame } from 'lucide-react';

const HOT_KEYWORDS = [
  'AI / Machine Learning',
  'Software Engineer',
  'Quant / Trading',
  'Data Science',
  'Fullstack / React',
  'Cybersecurity',
  'Remote (WFH)',
  'New York',
  'San Francisco'
];

const SearchBar = ({ onSearch, value = '' }) => {
  const [query, setQuery] = useState(value);

  const handleSubmit = (e) => {
    e.preventDefault();
    onSearch(query);
  };

  const handleClear = () => {
    setQuery('');
    onSearch('');
  };

  const handleTagClick = (tag) => {
    // If clicking an already active tag, toggle it off
    const newQuery = query.toLowerCase() === tag.toLowerCase() ? '' : tag;
    setQuery(newQuery);
    onSearch(newQuery);
  };

  return (
    <div className="w-full max-w-5xl mx-auto mb-6">
      {/* Search Input Box */}
      <form onSubmit={handleSubmit} className="relative mb-3">
        <div className="relative group flex items-center">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-blue-500 w-5 h-5 transition-colors pointer-events-none" />
          <input
            type="text"
            className="w-full pl-12 pr-28 py-3.5 sm:py-4 rounded-2xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-sm focus:ring-4 focus:ring-blue-100 dark:focus:ring-blue-900/30 focus:border-blue-500 dark:focus:border-blue-500 transition-all outline-none text-slate-800 dark:text-white text-base sm:text-lg placeholder:text-slate-400 dark:placeholder:text-slate-500"
            placeholder="Search roles, tech stack, companies, or cities... (e.g. Citadel, PyTorch, NYC)"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <div className="absolute right-3 flex items-center gap-1.5">
            {query && (
              <button
                type="button"
                onClick={handleClear}
                className="p-1 rounded-full text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors cursor-pointer"
                title="Clear search"
              >
                <X className="w-4 h-4" />
              </button>
            )}
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-semibold shadow-sm transition-all hover:shadow cursor-pointer"
            >
              Search
            </button>
          </div>
        </div>
      </form>

      {/* Fully Displayed Hot Keywords (No cutoff, wraps cleanly) */}
      <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2 pt-1 px-1">
        <div className="flex items-center gap-1 text-xs font-bold text-slate-400 dark:text-slate-500 shrink-0 uppercase tracking-wider pr-1">
          <Flame className="w-4 h-4 text-amber-500 fill-amber-500" />
          <span>Trending:</span>
        </div>
        {HOT_KEYWORDS.map((tag) => {
          const isActive = query.toLowerCase() === tag.toLowerCase();
          return (
            <button
              key={tag}
              type="button"
              onClick={() => handleTagClick(tag)}
              className={`px-3 py-1.5 text-xs sm:text-sm font-medium rounded-xl transition-all cursor-pointer border ${
                isActive
                  ? 'bg-blue-600 text-white border-blue-600 shadow-xs'
                  : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:border-blue-400 dark:hover:border-blue-500 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-blue-50/50 dark:hover:bg-slate-700/80 shadow-xs'
              }`}
            >
              {tag}
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default SearchBar;
