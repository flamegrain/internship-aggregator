import React from 'react';
import { 
  MapPin, 
  DollarSign, 
  Globe, 
  Building2, 
  RotateCcw, 
  Sparkles,
  Check
} from 'lucide-react';

const CITIES = [
  { label: '全部地点', value: '' },
  { label: '🏠 远程 Remote', value: 'Remote' },
  { label: '🗽 纽约 NYC', value: 'New York' },
  { label: '🌉 旧金山/湾区 SF', value: 'San Francisco' },
  { label: '🌲 西雅图 Seattle', value: 'Seattle' },
  { label: '🤠 奥斯汀 Austin', value: 'Austin' },
  { label: '🎓 波士顿 Boston', value: 'Boston' },
];

const VISA_OPTIONS = [
  { label: '不限签证', value: '' },
  { label: '🌟 极高概率 (Score 8+)', value: 8 },
  { label: '👍 友好支持 (Score 5+)', value: 5 },
];

const SALARY_OPTIONS = [
  { label: '不限薪资', value: '' },
  { label: '💰 $45+/hr (约$7,200/月)', value: true },
];

const COMPANY_TYPES = [
  { label: '全部公司', value: '' },
  { label: '🏢 Big Tech 科技巨头', value: 'big_tech' },
  { label: '📈 Quant 量化/投行金融', value: 'quant_finance' },
  { label: '🤖 AI & 大模型独角兽', value: 'ai_ml' },
  { label: '🚀 Aerospace 航天/军工', value: 'defense_aerospace' },
];

const PRESETS = [
  { id: 'visa8', label: '🌟 国际生 Sponsor 首选', apply: { min_score: 8, location: '', company_type: '', high_salary: false, ai_only: false } },
  { id: 'ai', label: '🤖 AI / 大模型专场', apply: { ai_only: true, company_type: 'ai_ml', min_score: null, location: '', high_salary: false } },
  { id: 'salary', label: '💰 高薪实习 ($45+/hr)', apply: { high_salary: true, min_score: null, location: '', company_type: '', ai_only: false } },
  { id: 'remote', label: '🏠 纯远程 Remote', apply: { location: 'Remote', min_score: null, company_type: '', high_salary: false, ai_only: false } },
  { id: 'nyc', label: '🗽 纽约华尔街/大厂', apply: { location: 'New York', min_score: null, company_type: '', high_salary: false, ai_only: false } },
  { id: 'bigtech', label: '🏢 硅谷 Big Tech', apply: { company_type: 'big_tech', min_score: null, location: '', high_salary: false, ai_only: false } },
];

const QuickFilterNav = ({ filters, onFilterChange, onReset }) => {
  const activeCount = Object.entries(filters).filter(([key, val]) => {
    if (key === 'source') return false; // Source handled separately
    if (typeof val === 'boolean') return val;
    return val !== null && val !== undefined && val !== '';
  }).length;

  return (
    <div className="w-full max-w-6xl mx-auto mb-8 px-4">
      <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-xs p-4 sm:p-5 transition-colors">
        {/* Header & Reset */}
        <div className="flex items-center justify-between mb-3.5 pb-2.5 border-b border-slate-100 dark:border-slate-700/80">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-blue-600 dark:text-blue-400" />
            <h3 className="text-sm font-bold text-slate-800 dark:text-slate-100">
              留学生专属快捷导航 • 核心条件筛选
            </h3>
            {activeCount > 0 && (
              <span className="bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 text-xs font-semibold px-2 py-0.5 rounded-full">
                已启用 {activeCount} 项
              </span>
            )}
          </div>
          {activeCount > 0 && (
            <button
              onClick={onReset}
              className="text-xs font-medium text-slate-500 hover:text-red-600 dark:text-slate-400 dark:hover:text-red-400 flex items-center gap-1 transition-colors cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              清空筛选
            </button>
          )}
        </div>

        {/* 1-Click Fast Presets */}
        <div className="mb-4">
          <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar py-1">
            <span className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider shrink-0 mr-1">
              精选速选:
            </span>
            {PRESETS.map((p) => {
              const isMatch = 
                (p.id === 'visa8' && filters.min_score === 8) ||
                (p.id === 'ai' && (filters.ai_only || filters.company_type === 'ai_ml')) ||
                (p.id === 'salary' && filters.high_salary) ||
                (p.id === 'remote' && filters.location === 'Remote') ||
                (p.id === 'nyc' && filters.location === 'New York') ||
                (p.id === 'bigtech' && filters.company_type === 'big_tech');

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
                      ? 'bg-blue-600 text-white border-blue-600 shadow-xs'
                      : 'bg-slate-50 dark:bg-slate-700/60 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-600 hover:border-blue-400 hover:text-blue-600 dark:hover:text-blue-300'
                  }`}
                >
                  {p.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* 4 Multi-Select / Filter Dropdown Pickers */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {/* Location */}
          <div>
            <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1.5 flex items-center gap-1">
              <MapPin className="w-3.5 h-3.5 text-blue-500" />
              城市 / 地点 (Location)
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

          {/* Visa Friendliness */}
          <div>
            <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1.5 flex items-center gap-1">
              <Globe className="w-3.5 h-3.5 text-emerald-500" />
              国际生友好度 (CPT/OPT)
            </label>
            <select
              value={filters.min_score || ''}
              onChange={(e) => onFilterChange({ min_score: e.target.value ? Number(e.target.value) : null })}
              className="w-full text-xs sm:text-sm bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 cursor-pointer"
            >
              {VISA_OPTIONS.map((v) => (
                <option key={v.label} value={v.value}>
                  {v.label}
                </option>
              ))}
            </select>
          </div>

          {/* Salary */}
          <div>
            <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1.5 flex items-center gap-1">
              <DollarSign className="w-3.5 h-3.5 text-amber-500" />
              实习薪资门槛 (Hourly Pay)
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

          {/* Company Type */}
          <div>
            <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1.5 flex items-center gap-1">
              <Building2 className="w-3.5 h-3.5 text-indigo-500" />
              公司领域类型 (Company)
            </label>
            <select
              value={filters.company_type || ''}
              onChange={(e) => onFilterChange({ company_type: e.target.value })}
              className="w-full text-xs sm:text-sm bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 cursor-pointer"
            >
              {COMPANY_TYPES.map((t) => (
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
