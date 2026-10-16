import React from 'react';
import { 
  MapPin, 
  DollarSign, 
  Globe, 
  Building2, 
  RotateCcw, 
  SlidersHorizontal
} from 'lucide-react';

const CITIES = [
  { label: 'All Locations', value: '' },
  { label: '🏠 Fully Remote (WFH)', value: 'Remote' },
  { label: '🗽 New York City, NY', value: 'New York' },
  { label: '🌉 San Francisco / Bay Area, CA', value: 'San Francisco' },
  { label: '🌲 Seattle, WA', value: 'Seattle' },
  { label: '🤠 Austin, TX', value: 'Austin' },
  { label: '🎓 Boston, MA', value: 'Boston' },
];

const VISA_OPTIONS = [
  { label: 'All Work Authorization Statuses', value: '' },
  { label: '🌍 Open to F-1 / No Restriction Stated', value: 'open_to_international' },
  { label: '✅ Sponsorship Explicitly Supported', value: 'sponsorship_explicitly_supported' },
  { label: '📄 Not Specified in JD', value: 'not_specified' },
  { label: '🇺🇸 Explicitly Restricted (Citizen / No Sponsor)', value: 'explicitly_restricted' },
];

const SALARY_OPTIONS = [
  { label: 'Any Compensation Status', value: '' },
  { label: '💰 Verified Disclosed Pay Only', value: true },
];

const ROLE_CATEGORIES = [
  { label: 'All Role Categories', value: '' },
  { label: '💻 Software Engineering', value: 'software_engineering' },
  { label: '🤖 AI & Machine Learning', value: 'ai_ml' },
  { label: '📊 Data Science & Analytics', value: 'data_analytics' },
  { label: '🔬 Research Scientist / Intern', value: 'research' },
  { label: '📈 Quant / Product / Hardware', value: 'other' },
];

const PRESETS = [
  { id: 'official', label: '🛡️ Official API & ATS', apply: { source_type: 'official_verified', visa_status: '', role_category: '', location: '', company_type: '', high_salary: false, ai_only: false } },
  { id: 'visa_open', label: '🌍 No Citizenship Restriction', apply: { visa_status: 'open_to_international', source_type: '', role_category: '', location: '', company_type: '', high_salary: false, ai_only: false } },
  { id: 'swe', label: '💻 Software Engineering', apply: { role_category: 'software_engineering', ai_only: false, company_type: '', source_type: '', visa_status: '', location: '', high_salary: false } },
  { id: 'ai', label: '🤖 AI & Machine Learning', apply: { role_category: 'ai_ml', ai_only: false, company_type: '', source_type: '', visa_status: '', location: '', high_salary: false } },
  { id: 'salary', label: '💰 Verified Pay Disclosed', apply: { high_salary: true, source_type: '', visa_status: '', role_category: '', location: '', company_type: '', ai_only: false } },
  { id: 'remote', label: '🏠 Fully Remote (WFH)', apply: { location: 'Remote', source_type: '', visa_status: '', role_category: '', company_type: '', high_salary: false, ai_only: false } },
  { id: 'nyc', label: '🗽 NYC Finance & Tech', apply: { location: 'New York', source_type: '', visa_status: '', role_category: '', company_type: '', high_salary: false, ai_only: false } },
];

const QuickFilterNav = ({ filters, onFilterChange, onReset }) => {
  const activeCount = Object.entries(filters).filter(([key, val]) => {
    if (key === 'source') return false;
    if (typeof val === 'boolean') return val;
    return val !== null && val !== undefined && val !== '';
  }).length;

  return (
    <div className="w-full max-w-5xl mx-auto mb-8">
      <div className="bg-white dark:bg-slate-800 rounded-3xl border border-slate-200 dark:border-slate-700 shadow-sm p-4 sm:p-5 transition-colors">
        {/* Top Header & Reset */}
        <div className="flex items-center justify-between mb-3.5 pb-2.5 border-b border-slate-100 dark:border-slate-700/80">
          <div className="flex items-center gap-2">
            <SlidersHorizontal className="w-4 h-4 text-blue-600 dark:text-blue-400" />
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">
              Auditable Student Filters • Evidence-Backed Classification
            </h3>
            {activeCount > 0 && (
              <span className="bg-blue-100 dark:bg-blue-900/60 text-blue-700 dark:text-blue-300 text-xs font-bold px-2 py-0.5 rounded-full">
                {activeCount} active
              </span>
            )}
          </div>
          {activeCount > 0 && (
            <button
              onClick={onReset}
              className="text-xs font-semibold text-slate-500 hover:text-rose-600 dark:text-slate-400 dark:hover:text-rose-400 flex items-center gap-1 transition-colors cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Reset all
            </button>
          )}
        </div>

        {/* 1-Click Fast Presets */}
        <div className="mb-4">
          <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar py-1">
            <span className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider shrink-0 mr-1">
              Quick Picks:
            </span>
            {PRESETS.map((p) => {
              const isMatch = 
                (p.id === 'official' && filters.source_type === 'official_verified') ||
                (p.id === 'visa_open' && filters.visa_status === 'open_to_international') ||
                (p.id === 'swe' && filters.role_category === 'software_engineering') ||
                (p.id === 'ai' && filters.role_category === 'ai_ml') ||
                (p.id === 'salary' && filters.high_salary) ||
                (p.id === 'remote' && filters.location === 'Remote') ||
                (p.id === 'nyc' && filters.location === 'New York');

              return (
                <button
                  key={p.id}
                  onClick={() => {
                    if (isMatch) {
                      onReset();
                    } else {
                      onFilterChange(p.apply);
                    }
                  }}
                  className={`text-xs px-3 py-1.5 rounded-full whitespace-nowrap font-medium transition-all cursor-pointer border ${
                    isMatch
                      ? 'bg-blue-600 text-white border-blue-600 shadow-xs font-semibold'
                      : 'bg-slate-50 dark:bg-slate-700/60 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-600 hover:border-blue-400 hover:text-blue-600 dark:hover:text-blue-300'
                  }`}
                >
                  {p.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* 4 Core Dropdowns */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {/* Location */}
          <div>
            <label className="block text-xs font-bold text-slate-500 dark:text-slate-400 mb-1.5 flex items-center gap-1">
              <MapPin className="w-3.5 h-3.5 text-blue-500" />
              Location & Metro
            </label>
            <select
              value={filters.location || ''}
              onChange={(e) => onFilterChange({ location: e.target.value })}
              className="w-full text-xs sm:text-sm bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 cursor-pointer"
            >
              {CITIES.map((c) => (
                <option key={c.label} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>

          {/* Auditable Visa Status */}
          <div>
            <label className="block text-xs font-bold text-slate-500 dark:text-slate-400 mb-1.5 flex items-center gap-1">
              <Globe className="w-3.5 h-3.5 text-emerald-500" />
              Work Auth / Visa Status
            </label>
            <select
              value={filters.visa_status || ''}
              onChange={(e) => onFilterChange({ visa_status: e.target.value, min_score: null })}
              className="w-full text-xs sm:text-sm bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 cursor-pointer"
            >
              {VISA_OPTIONS.map((v) => (
                <option key={v.label} value={v.value}>
                  {v.label}
                </option>
              ))}
            </select>
          </div>

          {/* Disclosed Compensation */}
          <div>
            <label className="block text-xs font-bold text-slate-500 dark:text-slate-400 mb-1.5 flex items-center gap-1">
              <DollarSign className="w-3.5 h-3.5 text-amber-500" />
              Structured Compensation
            </label>
            <select
              value={filters.high_salary ? 'true' : ''}
              onChange={(e) => onFilterChange({ high_salary: e.target.value === 'true' })}
              className="w-full text-xs sm:text-sm bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 cursor-pointer"
            >
              {SALARY_OPTIONS.map((s) => (
                <option key={s.label} value={s.value ? 'true' : ''}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>

          {/* Role Category */}
          <div>
            <label className="block text-xs font-bold text-slate-500 dark:text-slate-400 mb-1.5 flex items-center gap-1">
              <Building2 className="w-3.5 h-3.5 text-indigo-500" />
              Role Category
            </label>
            <select
              value={filters.role_category || ''}
              onChange={(e) => onFilterChange({ role_category: e.target.value, company_type: '' })}
              className="w-full text-xs sm:text-sm bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 cursor-pointer"
            >
              {ROLE_CATEGORIES.map((t) => (
                <option key={t.label} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>
    </div>
  );
};

export default QuickFilterNav;
