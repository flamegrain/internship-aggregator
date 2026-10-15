import React from 'react';
import { MapPin, Building, Calendar, ExternalLink, Zap, Globe } from 'lucide-react';

const InternshipCard = ({ internship }) => {
    const formatDate = (dateString) => {
        return new Date(dateString).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
        });
    };

    const getScoreTooltip = (score) => {
        if (score >= 8) return "High chance of sponsorship (F-1 / CPT / OPT / H-1B)";
        if (score >= 5) return "Sponsorship possible but role-dependent";
        return "Sponsorship unlikely or US Citizen / Green Card preferred";
    };

    return (
        <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-xs hover:shadow-md transition-all duration-200 border border-slate-200/80 dark:border-slate-700/80 group h-full flex flex-col relative hover:border-blue-300 dark:hover:border-slate-600">
            <div className="p-5 flex-1 flex flex-col">
                {/* Header Row: Logo, Role, Score & Badges */}
                <div className="flex justify-between items-start mb-3 gap-3">
                    <div className="flex items-start gap-3 min-w-0 flex-1">
                        {/* High-contrast crisp white logo tile for dark & light mode */}
                        {internship.logo_url ? (
                            <div className="w-11 h-11 rounded-xl bg-white border border-slate-200/90 dark:border-slate-600 p-1.5 flex items-center justify-center shrink-0 shadow-xs">
                                <img
                                    src={internship.logo_url}
                                    alt={`${internship.company} logo`}
                                    className="w-full h-full object-contain"
                                    onError={(e) => {
                                        e.target.onerror = null;
                                        e.target.src = "https://ui-avatars.com/api/?name=" + encodeURIComponent(internship.company) + "&background=6366f1&color=fff";
                                    }}
                                />
                            </div>
                        ) : (
                            <div className="w-11 h-11 rounded-xl bg-blue-50 dark:bg-slate-700 border border-blue-100 dark:border-slate-600 flex items-center justify-center text-blue-600 dark:text-blue-400 shrink-0">
                                <Building className="w-5 h-5" />
                            </div>
                        )}
                        <div className="min-w-0 flex-1">
                            {/* Full Job Title (No cutoff, wraps beautifully) */}
                            <h3 className="text-base font-bold text-slate-900 dark:text-white leading-snug break-words">
                                <a
                                    href={internship.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                                >
                                    {internship.role}
                                </a>
                            </h3>
                            <div className="text-sm font-semibold text-slate-500 dark:text-slate-400 mt-0.5">
                                {internship.company}
                            </div>
                        </div>
                    </div>

                    {/* Badges: F-1 Score & AI Label */}
                    <div className="flex items-center gap-1.5 shrink-0 pt-0.5">
                        {internship.international_score && (
                            <div className="relative group/tooltip">
                                <span className={`cursor-help text-xs px-2.5 py-1 rounded-full font-bold flex items-center gap-1 border shadow-xs ${
                                    internship.international_score >= 8 
                                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/50 dark:text-emerald-300 dark:border-emerald-800' 
                                        : internship.international_score >= 5 
                                            ? 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/50 dark:text-amber-300 dark:border-amber-800' 
                                            : 'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/50 dark:text-rose-300 dark:border-rose-800'
                                }`}>
                                    <Globe className="w-3 h-3" />
                                    <span>{internship.international_score}</span>
                                </span>
                                {/* Tooltip */}
                                <div className="absolute bottom-full right-0 mb-2 w-52 p-2.5 bg-slate-900 dark:bg-slate-950 text-white text-xs rounded-xl opacity-0 group-hover/tooltip:opacity-100 transition-opacity pointer-events-none z-30 text-center shadow-xl border border-slate-700">
                                    {getScoreTooltip(internship.international_score)}
                                </div>
                            </div>
                        )}
                        {internship.ai_label && (
                            <span className="bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white text-xs px-2.5 py-1 rounded-full font-bold flex items-center gap-1 shadow-xs">
                                <Zap className="w-3 h-3 fill-current" />
                                AI
                            </span>
                        )}
                    </div>
                </div>

                {/* Metadata Pills: Location, Date, Compensation */}
                <div className="flex flex-wrap gap-2 text-xs text-slate-600 dark:text-slate-300 my-3">
                    <div className="flex items-center gap-1.5 bg-slate-100/90 dark:bg-slate-700/60 px-2.5 py-1 rounded-lg">
                        <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                        <span className="font-medium">{internship.location}</span>
                    </div>
                    <div className="flex items-center gap-1.5 bg-slate-100/90 dark:bg-slate-700/60 px-2.5 py-1 rounded-lg">
                        <Calendar className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                        <span>Posted {formatDate(internship.posted_date)}</span>
                    </div>
                    {internship.salary && (
                        <div className="flex items-center gap-1 bg-emerald-50 dark:bg-emerald-950/50 border border-emerald-200/80 dark:border-emerald-800/80 px-2.5 py-1 rounded-lg text-emerald-700 dark:text-emerald-300 font-bold">
                            <span>💰</span>
                            <span>{internship.salary}</span>
                        </div>
                    )}
                </div>

                {/* Card Footer: Track & Direct Apply Link */}
                <div className="flex items-center justify-between border-t border-slate-100 dark:border-slate-700/80 pt-3.5 mt-auto">
                    <span className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
                        {internship.industry || 'Tech'}
                    </span>
                    <a
                        href={internship.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 text-sm font-bold text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 hover:underline"
                    >
                        Apply Direct
                        <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                </div>
            </div>
        </div>
    );
};

export default InternshipCard;
