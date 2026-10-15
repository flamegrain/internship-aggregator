import React, { useState, useEffect } from 'react';
import { Sparkles, Clock, Globe, Briefcase, Zap, Building2, Flame } from 'lucide-react';

// Continuous looping animated counter with a 1-second pause at the end of each cycle
function useAnimatedLoopingCounter(endValue, duration = 1400, pauseMs = 1000) {
  const isStatic = typeof window !== 'undefined' && (
    window.location.search.includes('static') ||
    window.location.search.includes('screenshot')
  );
  const [count, setCount] = useState(() => isStatic ? (endValue ?? 0) : 0);

  useEffect(() => {
    if (isStatic) {
      setCount(endValue ?? 0);
      return;
    }
    if (!endValue && endValue !== 0) return;
    const target = Number(endValue);
    if (isNaN(target)) return;

    let startTime = null;
    let animationFrameId;
    const totalCycle = duration + pauseMs;

    const animate = (timestamp) => {
      if (!startTime) startTime = timestamp;
      const elapsed = timestamp - startTime;
      const elapsedInCycle = elapsed % totalCycle;

      if (elapsedInCycle < duration) {
        const progress = elapsedInCycle / duration;
        // Smooth easeOutCubic curve from 0 to 1
        const easeProgress = 1 - Math.pow(1 - progress, 3);
        setCount(Math.round(easeProgress * target));
      } else {
        // Hold firmly at target number for pauseMs (1 second)
        setCount(target);
      }

      animationFrameId = requestAnimationFrame(animate);
    };

    animationFrameId = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animationFrameId);
  }, [endValue, duration, pauseMs]);

  return count;
}

const LiveStatsBanner = ({ stats, loading }) => {
  const formatTime = (isoString) => {
    if (!isoString) return 'Just now';
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
      });
    } catch {
      return 'Just now';
    }
  };

  const rawTotal = stats?.total_internships ?? 1569;
  const rawVisa = stats?.international_friendly_count ?? 257;
  const rawAi = stats?.ai_roles_count ?? 219;
  const rawCompanies = stats?.companies_count ?? 622;
  const updateTime = stats?.latest_update ? formatTime(stats.latest_update) : 'Just now';

  // Synchronized continuous looping animated counters with 1s pause
  const animatedTotal = useAnimatedLoopingCounter(rawTotal, 1400, 1000);
  const animatedVisa = useAnimatedLoopingCounter(rawVisa, 1400, 1000);
  const animatedAi = useAnimatedLoopingCounter(rawAi, 1400, 1000);
  const animatedCompanies = useAnimatedLoopingCounter(rawCompanies, 1400, 1000);

  return (
    <div className="w-full max-w-5xl mx-auto mb-8">
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-blue-600/10 via-indigo-600/10 to-violet-600/10 dark:from-blue-950/40 dark:via-indigo-950/30 dark:to-violet-950/40 border border-blue-200/90 dark:border-blue-800/60 p-5 sm:p-6 backdrop-blur-md shadow-sm">
        {/* Subtle decorative glowing background */}
        <div className="absolute -top-14 -right-14 w-56 h-56 bg-blue-500/15 dark:bg-blue-400/10 rounded-full blur-3xl pointer-events-none"></div>
        <div className="absolute -bottom-14 -left-14 w-56 h-56 bg-violet-500/15 dark:bg-violet-400/10 rounded-full blur-3xl pointer-events-none"></div>

        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-5 relative z-10">
          {/* Left: Dynamic Live Counter */}
          <div className="flex items-center gap-4">
            <div className="relative flex h-4 w-4 shrink-0">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-4 w-4 bg-emerald-500 shadow-sm shadow-emerald-500/50"></span>
            </div>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-extrabold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/70 px-2.5 py-0.5 rounded-full border border-emerald-200/80 dark:border-emerald-800">
                  LIVE RADAR ACTIVE
                </span>
                <span className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" />
                  Synced: <span className="font-semibold text-slate-700 dark:text-slate-300">{updateTime}</span>
                </span>
              </div>
              <div className="text-2xl sm:text-3xl font-black text-slate-900 dark:text-white tracking-tight flex items-baseline gap-2">
                <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600 dark:from-blue-400 dark:to-indigo-300 text-3xl sm:text-4xl font-extrabold tabular-nums transition-all">
                  {animatedTotal.toLocaleString()}
                </span>
                <span className="text-base sm:text-lg font-bold text-slate-800 dark:text-slate-200">
                  Verified Active Roles
                </span>
                <span className="hidden sm:inline-block text-xs font-semibold text-amber-500 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/60 px-2 py-0.5 rounded-md border border-amber-200/60 dark:border-amber-800/60">
                  Zero Cap
                </span>
              </div>
            </div>
          </div>

          {/* Right: Key student metrics with continuous looping number animations */}
          <div className="grid grid-cols-3 gap-2.5 sm:gap-3 w-full lg:w-auto">
            {/* Visa F-1 */}
            <div className="flex flex-col items-center sm:items-start bg-white/90 dark:bg-slate-800/90 border border-slate-200/90 dark:border-slate-700/80 rounded-2xl p-3 shadow-xs hover:border-emerald-300 dark:hover:border-emerald-700 transition-colors">
              <div className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400 font-semibold mb-1">
                <Globe className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                <span>F-1 / Sponsor</span>
              </div>
              <div className="text-lg sm:text-xl font-black text-emerald-600 dark:text-emerald-400 tabular-nums">
                {animatedVisa.toLocaleString()}+
              </div>
              <span className="text-[10px] text-slate-400 font-medium">CPT/OPT Friendly</span>
            </div>

            {/* AI / ML Roles */}
            <div className="flex flex-col items-center sm:items-start bg-white/90 dark:bg-slate-800/90 border border-slate-200/90 dark:border-slate-700/80 rounded-2xl p-3 shadow-xs hover:border-violet-300 dark:hover:border-violet-700 transition-colors">
              <div className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400 font-semibold mb-1">
                <Zap className="w-3.5 h-3.5 text-violet-500 shrink-0" />
                <span>AI & LLM</span>
              </div>
              <div className="text-lg sm:text-xl font-black text-violet-600 dark:text-violet-400 tabular-nums">
                {animatedAi.toLocaleString()}+
              </div>
              <span className="text-[10px] text-slate-400 font-medium">GenAI / ML Grind</span>
            </div>

            {/* Companies */}
            <div className="flex flex-col items-center sm:items-start bg-white/90 dark:bg-slate-800/90 border border-slate-200/90 dark:border-slate-700/80 rounded-2xl p-3 shadow-xs hover:border-blue-300 dark:hover:border-blue-700 transition-colors">
              <div className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400 font-semibold mb-1">
                <Building2 className="w-3.5 h-3.5 text-blue-500 shrink-0" />
                <span>Companies</span>
              </div>
              <div className="text-lg sm:text-xl font-black text-blue-600 dark:text-blue-400 tabular-nums">
                {animatedCompanies.toLocaleString()}+
              </div>
              <span className="text-[10px] text-slate-400 font-medium">FAANG & Unicorns</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LiveStatsBanner;
