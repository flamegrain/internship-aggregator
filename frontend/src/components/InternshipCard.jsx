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
        if (score >= 8) return "High chance of sponsorship (Visa/CPT/OPT)";
        if (score >= 5) return "Sponsorship possible but not guaranteed";
        return "Sponsorship unlikely or US Citizen only";
    };

    return (
        <div className="bg-white dark:bg-slate-800 rounded-xl shadow-xs hover:shadow-md transition-all duration-200 border border-slate-200/80 dark:border-slate-700 group h-full flex flex-col relative hover:border-blue-200 dark:hover:border-slate-600">
            <div className="p-5 sm:p-6 flex-1 flex flex-col">
                <div className="flex justify-between items-start mb-4 gap-3">
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3 mb-2">
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
                            <div className="min-w-0">
                                <h3 className="text-base sm:text-lg font-semibold text-slate-900 dark:text-white leading-tight truncate">
                                    <a
                                        href={internship.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                                        title={internship.role}
                                    >
                                        {internship.role}
                                    </a>
                                </h3>
                                <div className="text-sm font-medium text-slate-500 dark:text-slate-400 truncate">
                                    {internship.company}
                                </div>
                            </div>
                        </div>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                        {internship.international_score && (
                            <div className="relative group/tooltip">
                                <span className={`cursor-help text-xs px-2.5 py-1 rounded-full font-medium flex items-center gap-1 border shadow-xs ${
                                    internship.international_score >= 8 
                                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800' 
                                        : internship.international_score >= 5 
                                            ? 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800' 
                                            : 'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-800'
                                }`}>
                                    <Globe className="w-3 h-3" />
                                    {internship.international_score}
                                </span>
                                {/* Tooltip */}
                                <div className="absolute bottom-full right-0 mb-2 w-48 p-2 bg-slate-900 dark:bg-slate-950 text-white text-xs rounded-lg opacity-0 group-hover/tooltip:opacity-100 transition-opacity pointer-events-none z-30 text-center shadow-lg border border-slate-700">
                                    {getScoreTooltip(internship.international_score)}
                                </div>
                            </div>
                        )}
                        {internship.ai_label && (
                            <span className="bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white text-xs px-2.5 py-1 rounded-full font-medium flex items-center gap-1 shadow-xs">
                                <Zap className="w-3 h-3 fill-current" />
                                AI
                            </span>
                        )}
                    </div>
                </div>

                <div className="flex flex-wrap gap-2 text-xs sm:text-sm text-slate-600 dark:text-slate-300 mb-4">
                    <div className="flex items-center gap-1.5 bg-slate-100/80 dark:bg-slate-700/60 px-2.5 py-1 rounded-lg">
                        <MapPin className="w-3.5 h-3.5 text-slate-400 dark:text-slate-400 shrink-0" />
                        <span className="truncate max-w-[200px]">{internship.location}</span>
                    </div>
                    <div className="flex items-center gap-1.5 bg-slate-100/80 dark:bg-slate-700/60 px-2.5 py-1 rounded-lg">
                        <Calendar className="w-3.5 h-3.5 text-slate-400 dark:text-slate-400 shrink-0" />
                        <span>{formatDate(internship.posted_date)}</span>
                    </div>
                    {internship.salary && (
                        <div className="flex items-center gap-1 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200/60 dark:border-emerald-800/60 px-2.5 py-1 rounded-lg text-emerald-700 dark:text-emerald-300 font-medium">
                            <span>💰</span>
                            <span>{internship.salary}</span>
                        </div>
                    )}
                </div>

                <div className="flex items-center justify-between border-t border-slate-100 dark:border-slate-700/80 pt-3.5 mt-auto">
                    <span className="text-xs font-medium text-slate-400 dark:text-slate-500 uppercase tracking-wide">
                        {internship.industry || 'Tech'}
                    </span>
                    <a
                        href={internship.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 text-sm font-semibold text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 hover:underline"
                    >
                        Apply Now
                        <ExternalLink className="w-4 h-4" />
                    </a>
                </div>
            </div>
        </div>
    );
};

export default InternshipCard;
