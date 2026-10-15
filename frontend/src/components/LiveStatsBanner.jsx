import React from 'react';
import { Sparkles, Clock, Globe, Briefcase, Zap, Building2 } from 'lucide-react';

const LiveStatsBanner = ({ stats, loading }) => {
  const formatTime = (isoString) => {
    if (!isoString) return 'Today';
    try {
      const date = new Date(isoString);
      return date.toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
      });
    } catch {
      return isoString;
    }
  };

  const total = stats?.total_internships ?? 1569;
  const updateTime = stats?.latest_update ? formatTime(stats.latest_update) : '刚刚更新';
  const visaFriendly = stats?.international_friendly_count ?? 820;
  const aiRoles = stats?.ai_roles_count ?? 340;
  const companies = stats?.companies_count ?? 8;

  return (
    <div className="w-full max-w-5xl mx-auto mb-8 px-4">
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-blue-600/10 via-indigo-600/10 to-violet-600/10 dark:from-blue-900/30 dark:via-indigo-900/25 dark:to-violet-900/30 border border-blue-200/80 dark:border-blue-800/60 p-4 sm:p-5 backdrop-blur-md shadow-xs">
        {/* Subtle decorative glowing background */}
        <div className="absolute -top-12 -right-12 w-48 h-48 bg-blue-500/10 dark:bg-blue-400/10 rounded-full blur-2xl pointer-events-none"></div>

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 relative z-10">
          {/* Left: Live Status & Total Postings */}
          <div className="flex items-center gap-3.5">
            <div className="relative flex h-3.5 w-3.5 shrink-0">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3.5 w-3.5 bg-emerald-500"></span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/60 px-2 py-0.5 rounded-full border border-emerald-200/60 dark:border-emerald-800/60">
                  LIVE 实时聚合中
                </span>
                <span className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" />
                  更新于: <span className="font-semibold text-slate-700 dark:text-slate-300">{updateTime}</span>
                </span>
              </div>
              <div className="text-lg sm:text-xl font-bold text-slate-900 dark:text-white mt-0.5">
                全美有效在招实习:{' '}
                <span className="text-blue-600 dark:text-blue-400 font-extrabold">
                  {total.toLocaleString()}
                </span>{' '}
                <span className="text-sm font-medium text-slate-500 dark:text-slate-400">个岗位</span>
              </div>
            </div>
          </div>

          {/* Right: Quick High-priority metric chips */}
          <div className="flex items-center flex-wrap gap-2 sm:gap-3">
            <div className="flex items-center gap-1.5 bg-white/80 dark:bg-slate-800/80 border border-slate-200/80 dark:border-slate-700/80 rounded-xl px-3 py-1.5 shadow-xs">
              <Globe className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
              <span className="text-xs text-slate-600 dark:text-slate-300">
                国际生友好:{' '}
                <span className="font-bold text-emerald-600 dark:text-emerald-400">
                  {visaFriendly}+
                </span>
              </span>
            </div>

            <div className="flex items-center gap-1.5 bg-white/80 dark:bg-slate-800/80 border border-slate-200/80 dark:border-slate-700/80 rounded-xl px-3 py-1.5 shadow-xs">
              <Zap className="w-4 h-4 text-violet-600 dark:text-violet-400 shrink-0" />
              <span className="text-xs text-slate-600 dark:text-slate-300">
                AI / 大模型:{' '}
                <span className="font-bold text-violet-600 dark:text-violet-400">
                  {aiRoles}+
                </span>
              </span>
            </div>

            <div className="flex items-center gap-1.5 bg-white/80 dark:bg-slate-800/80 border border-slate-200/80 dark:border-slate-700/80 rounded-xl px-3 py-1.5 shadow-xs">
              <Building2 className="w-4 h-4 text-blue-600 dark:text-blue-400 shrink-0" />
              <span className="text-xs text-slate-600 dark:text-slate-300">
                实时招聘源:{' '}
                <span className="font-bold text-blue-600 dark:text-blue-400">
                  {companies} 大通道
                </span>
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LiveStatsBanner;
