import React from 'react';
import { MapPin, Building, Calendar, ExternalLink, Zap, Globe, ShieldCheck, CheckCircle2, Code2 } from 'lucide-react';

const SOURCE_TIER_BADGES = {
    official_api: {
        label: 'Official API',
        className: 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/60 dark:text-blue-300 dark:border-blue-800',
        Icon: ShieldCheck,
    },
    public_ats: {
        label: 'Public ATS',
        className: 'bg-indigo-50 text-indigo-700 border-indigo-200 dark:bg-indigo-950/60 dark:text-indigo-300 dark:border-indigo-800',
        Icon: ShieldCheck,
    },
    official_portal: {
        label: 'Official Portal',
        className: 'bg-sky-50 text-sky-700 border-sky-200 dark:bg-sky-950/60 dark:text-sky-300 dark:border-sky-800',
        Icon: ShieldCheck,
    },
    community_verified: {
        label: 'Community Verified',
        className: 'bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-700/70 dark:text-slate-300 dark:border-slate-600',
        Icon: CheckCircle2,
    },
};

const InternshipCard = ({ internship }) => {
    const formatDate = (dateString) => {
        if (!dateString) return 'Recently';
        try {
            return new Date(dateString).toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
            });
        } catch {
            return 'Recently';
        }
    };

    const getScoreTooltip = (score) => {
        if (score >= 8) return "High chance of sponsorship (F-1 / CPT / OPT / H-1B)";
        if (score >= 5) return "Sponsorship possible (CPT / OPT friendly)";
        return "Sponsorship unlikely or US Citizen / Clearance required";
    };

    const tierKey = internship.source_type || 'community_verified';
    const tierBadge = SOURCE_TIER_BADGES[tierKey] || SOURCE_TIER_BADGES.community_verified;
    const TierIcon = tierBadge.Icon;

    let sourcesCount = 1;
    if (internship.sources_list) {
        try {
            const parsed = JSON.parse(internship.sources_list);
            if (Array.isArray(parsed) && parsed.length > 0) {
                sourcesCount = parsed.length;
            }
        } catch {
            sourcesCount = 1;
        }
    }

    const firstSeenDate = formatDate(internship.first_seen_at || internship.posted_date);
    const verifiedDate = formatDate(internship.last_verified_at || internship.posted_date);

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
                            {/* Full Job Title */}
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
                            <div className="text-sm font-semibold text-slate-500 dark:text-slate-400 mt-0.5 flex items-center gap-1.5 flex-wrap">
                                <span>{internship.company}</span>
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

                {/* Metadata Pills: Location, Provenance, Disclosed Pay, Verified Skills */}
                <div className="flex flex-wrap gap-1.5 text-xs text-slate-600 dark:text-slate-300 my-2.5">
                    <div className="flex items-center gap-1.5 bg-slate-100/90 dark:bg-slate-700/60 px-2.5 py-1 rounded-lg">
                        <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                        <span className="font-medium">{internship.location}</span>
                    </div>

                    {/* Provenance Tier Badge */}
                    <div
                        className={`flex items-center gap-1 px-2.5 py-1 rounded-lg border font-semibold ${tierBadge.className}`}
                        title={`Primary Source: ${internship.source || 'verified'}${sourcesCount > 1 ? ` • Cross-verified across ${sourcesCount} sources` : ''}`}
                    >
                        <TierIcon className="w-3.5 h-3.5 shrink-0" />
                        <span>{tierBadge.label}</span>
                        {sourcesCount > 1 && (
                            <span className="ml-0.5 px-1.5 py-0.2 bg-white/80 dark:bg-slate-900/60 rounded text-[10px] font-bold">
                                +{sourcesCount - 1}
                            </span>
                        )}
                    </div>

                    {/* Disclosed Salary Pill (Only rendered when verified) */}
                    {internship.salary && (
                        <div className="flex items-center gap-1 bg-emerald-50 dark:bg-emerald-950/50 border border-emerald-200/80 dark:border-emerald-800/80 px-2.5 py-1 rounded-lg text-emerald-700 dark:text-emerald-300 font-bold">
                            <span>💰</span>
                            <span>{internship.salary}</span>
                        </div>
                    )}

                    {/* Extracted JD Skills (Only rendered when extracted from real ATS JD) */}
                    {internship.requirements && (
                        <div className="flex items-center gap-1 bg-slate-100/80 dark:bg-slate-700/50 border border-slate-200/70 dark:border-slate-600/60 px-2.5 py-1 rounded-lg text-slate-600 dark:text-slate-300 font-medium">
                            <Code2 className="w-3.5 h-3.5 text-indigo-500 shrink-0" />
                            <span className="truncate max-w-[210px]">{internship.requirements}</span>
                        </div>
                    )}
                </div>

                {/* Timestamps Row: First Seen & Last Verified */}
                <div className="flex items-center justify-between text-[11px] text-slate-400 dark:text-slate-500 mt-1 mb-2.5">
                    <span className="flex items-center gap-1">
                        <Calendar className="w-3 h-3 shrink-0" />
                        First seen {firstSeenDate}
                    </span>
                    <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-medium">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block"></span>
                        Verified {verifiedDate}
                    </span>
                </div>

                {/* Card Footer: Track & Direct Apply Link */}
                <div className="flex items-center justify-between border-t border-slate-100 dark:border-slate-700/80 pt-3 mt-auto">
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
