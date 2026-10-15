import React, { useState } from 'react';
import { Search, X, Flame } from 'lucide-react';

const RECOMMENDATIONS = [
  'AI / Machine Learning',
  'Software Engineer',
  'Data Science',
  'Quant / Finance',
  'New York',
  'San Francisco',
  'Remote',
  'Frontend / React',
  'Cybersecurity'
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
    setQuery(tag);
    onSearch(tag);
  };

  return (
    <div className="w-full max-w-3xl mx-auto mb-8">
      {/* Search Input Box */}
      <form onSubmit={handleSubmit} className="relative mb-3">
        <div className="relative group flex items-center">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-blue-500 w-5 h-5 transition-colors pointer-events-none" />
          <input
            type="text"
            className="w-full pl-12 pr-28 py-3.5 sm:py-4 rounded-2xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-sm focus:ring-4 focus:ring-blue-100 dark:focus:ring-blue-900/30 focus:border-blue-500 dark:focus:border-blue-500 transition-all outline-none text-slate-800 dark:text-white text-base sm:text-lg placeholder:text-slate-400 dark:placeholder:text-slate-500"
            placeholder="Search roles, companies, tech stacks, or cities..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <div className="absolute right-3 flex items-center gap-1.5">
            {query && (
              <button
                type="button"
                onClick={handleClear}
                className="p-1 rounded-full text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                title="Clear search"
              >
                <X className="w-4 h-4" />
              </button>
            )}
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-medium shadow-sm transition-all hover:shadow"
            >
              Search
            </button>
          </div>
        </div>
      </form>

      {/* Single-row Horizontal Scrollable Trending Tags */}
      <div className="flex items-center gap-2 overflow-x-auto no-scrollbar py-1 px-1">
        <div className="flex items-center gap-1 text-xs font-semibold text-slate-400 dark:text-slate-500 shrink-0 uppercase tracking-wider pl-1">
          <Flame className="w-3.5 h-3.5 text-amber-500 fill-amber-500" />
          <span>Hot:</span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {RECOMMENDATIONS.map((tag) => (
            <button
              key={tag}
              type="button"
              onClick={() => handleTagClick(tag)}
              className={`px-3 py-1 text-xs sm:text-sm whitespace-nowrap rounded-full transition-all cursor-pointer font-medium ${
                query.toLowerCase() === tag.toLowerCase()
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:border-blue-300 dark:hover:border-blue-500 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-blue-50/50 dark:hover:bg-slate-700'
              }`}
            >
              {tag}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default SearchBar;
