import React from 'react';
import { MapPin, Building, Calendar, ExternalLink, Zap, Globe, ShieldCheck, CheckCircle2, Code2, Sparkles, AlertTriangle } from 'lucide-react';

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

const ROLE_CATEGORY_BADGES = {
    ai_ml: {
        label: 'AI / ML',
        className: 'bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white border-transparent',
        isGradient: true,
    },
    software_engineering: {
        label: 'Software Eng',
        className: 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/60 dark:text-blue-300 dark:border-blue-800',
    },
    data_analytics: {
        label: 'Data & Analytics',
        className: 'bg-teal-50 text-teal-700 border-teal-200 dark:bg-teal-950/60 dark:text-teal-300 dark:border-teal-800',
    },
    research: {
        label: 'Research',
        className: 'bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-950/60 dark:text-purple-300 dark:border-purple-800',
    },
    other: {
        label: 'Quant / PM / HW',
        className: 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/60 dark:text-amber-300 dark:border-amber-800',
    },
};

const JOB_TYPE_LABELS = {
    internship: 'Internship',
    'co-op': 'Co-op',
    fellowship: 'Fellowship',
    new_grad_full_time: 'New Grad FT',
    other_student_program: 'Student Program',
};

const VISA_STATUS_BADGES = {
    sponsorship_explicitly_supported: {
        label: 'Sponsor Verified',
        className: 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800',
        defaultNote: 'Current posting explicitly supports visa sponsorship or F-1/CPT/OPT work authorization.',
    },
    explicitly_restricted: {
        label: 'Restricted / No Sponsor',
        className: 'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/60 dark:text-rose-300 dark:border-rose-800',
        defaultNote: 'Posting explicitly requires U.S. citizenship/clearance or states no visa sponsorship.',
    },
    needs_review: {
        label: 'Visa Needs Review',
        className: 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/60 dark:text-amber-300 dark:border-amber-800',
        defaultNote: 'Posting contains conditional or conflicting work authorization statements.',
    },
    not_specified: {
        label: 'Visa Not Specified',
        className: 'bg-slate-100 text-slate-600 border-slate-200 dark:bg-slate-700/60 dark:text-slate-300 dark:border-slate-600',
        defaultNote: 'No explicit visa sponsorship or citizenship restriction stated in this posting.',
    },
};

const InternshipCard = ({ internship }) => {
    const formatDate = (dateString) => {
        if (!dateString) return null;
        try {
            return new Date(dateString).toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
            });
        } catch {
            return null;
        }
    };

    const tierKey = internship.source_type || 'community_verified';
    const tierBadge = SOURCE_TIER_BADGES[tierKey] || SOURCE_TIER_BADGES.community_verified;
    const TierIcon = tierBadge.Icon;

    const visaStatusKey = internship.visa_status || 'not_specified';
    const visaBadge = VISA_STATUS_BADGES[visaStatusKey] || VISA_STATUS_BADGES.not_specified;

    const roleCatKey = internship.role_category || (internship.ai_label ? 'ai_ml' : 'unclassified');
    const roleCatBadge = ROLE_CATEGORY_BADGES[roleCatKey] || null;
    const jobTypeLabel = JOB_TYPE_LABELS[internship.job_type] || 'Internship';

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

    let evidenceObj = null;
    if (internship.extraction_evidence) {
        try {
            evidenceObj = JSON.parse(internship.extraction_evidence);
        } catch {
            evidenceObj = null;
        }
    }

    const postedAtDate = formatDate(internship.posted_at);
    const firstSeenDate = formatDate(internship.first_seen_at || internship.posted_date) || 'Recently';
    const verifiedDate = formatDate(internship.last_verified_at || internship.posted_date) || 'Recently';

    const requiredSkills = internship.required_skills || internship.requirements;
    const preferredSkills = internship.preferred_skills;

    return (
        <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-xs hover:shadow-md transition-all duration-200 border border-slate-200/80 dark:border-slate-700/80 group h-full flex flex-col relative hover:border-blue-300 dark:hover:border-slate-600">
            <div className="p-5 flex-1 flex flex-col">
                {/* Header Row: Logo, Role, Auditable Visa Status & Role Category */}
                <div className="flex justify-between items-start mb-3 gap-3">
                    <div className="flex items-start gap-3 min-w-0 flex-1">
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
                                <span className="text-slate-300 dark:text-slate-600">•</span>
                                <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
                                    {jobTypeLabel}
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* Top-Right Auditable Badges: Visa Classification & Explicit Role Category */}
                    <div className="flex flex-col items-end gap-1.5 shrink-0 pt-0.5">
                        {/* Auditable Visa Status Badge with Verbatim Evidence Tooltip */}
                        <div className="relative group/tooltip">
                            <span className={`cursor-help text-[11px] px-2.5 py-0.5 rounded-full font-bold flex items-center gap-1 border shadow-xs whitespace-nowrap ${visaBadge.className}`}>
                                {visaStatusKey === 'needs_review' ? (
                                    <AlertTriangle className="w-3 h-3 shrink-0" />
                                ) : (
                                    <Globe className="w-3 h-3 shrink-0" />
                                )}
                                <span>{visaBadge.label}</span>
                            </span>
                            <div className="absolute bottom-full right-0 mb-2 w-64 p-2.5 bg-slate-900 dark:bg-slate-950 text-white text-xs rounded-xl opacity-0 group-hover/tooltip:opacity-100 transition-opacity pointer-events-none z-30 text-left shadow-xl border border-slate-700 leading-relaxed">
                                <div className="font-bold text-slate-200 mb-0.5">
                                    Work Authorization Status: {visaBadge.label}
                                </div>
                                <div className="text-slate-300 text-[11px]">
                                    {internship.visa_evidence
                                        ? `Evidence: "${internship.visa_evidence}"`
                                        : visaBadge.defaultNote}
                                </div>
                            </div>
                        </div>

                        {/* Role Category Badge */}
                        {roleCatBadge && (
                            <span
                                className={`text-[11px] px-2.5 py-0.5 rounded-full font-bold flex items-center gap-1 border shadow-xs whitespace-nowrap ${roleCatBadge.className}`}
                                title={internship.category_evidence || `Classified as ${roleCatBadge.label}`}
                            >
                                {roleCatKey === 'ai_ml' && <Zap className="w-3 h-3 fill-current shrink-0" />}
                                <span>{roleCatBadge.label}</span>
                            </span>
                        )}
                    </div>
                </div>

                {/* Metadata Pills: Location, Provenance, Structured Compensation, Required & Preferred Skills */}
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

                    {/* Disclosed Structured Salary Pill with Verbatim Quote Tooltip */}
                    {internship.salary && (
                        <div
                            className="flex items-center gap-1 bg-emerald-50 dark:bg-emerald-950/50 border border-emerald-200/80 dark:border-emerald-800/80 px-2.5 py-1 rounded-lg text-emerald-700 dark:text-emerald-300 font-bold cursor-help"
                            title={
                                evidenceObj?.salary_quote
                                    ? `Verbatim JD Salary Quote: "${evidenceObj.salary_quote}"`
                                    : `Structured Compensation: ${internship.salary}`
                            }
                        >
                            <span>💰</span>
                            <span>{internship.salary}</span>
                        </div>
                    )}

                    {/* Required Skills Pill */}
                    {requiredSkills && (
                        <div
                            className="flex items-center gap-1 bg-slate-100/80 dark:bg-slate-700/50 border border-slate-200/70 dark:border-slate-600/60 px-2.5 py-1 rounded-lg text-slate-700 dark:text-slate-200 font-medium cursor-help"
                            title={
                                evidenceObj?.required_skills_quote
                                    ? `Required Skills Evidence: "${evidenceObj.required_skills_quote}"`
                                    : `Required Skills: ${requiredSkills}`
                            }
                        >
                            <Code2 className="w-3.5 h-3.5 text-indigo-500 shrink-0" />
                            <span className="truncate max-w-[200px]">Req: {requiredSkills}</span>
                        </div>
                    )}

                    {/* Preferred Skills Pill */}
                    {preferredSkills && (
                        <div
                            className="flex items-center gap-1 bg-violet-50/70 dark:bg-violet-950/40 border border-violet-200/60 dark:border-violet-800/60 px-2.5 py-1 rounded-lg text-violet-700 dark:text-violet-300 font-medium cursor-help"
                            title={
                                evidenceObj?.preferred_skills_quote
                                    ? `Preferred Skills Evidence: "${evidenceObj.preferred_skills_quote}"`
                                    : `Preferred Skills: ${preferredSkills}`
                            }
                        >
                            <Sparkles className="w-3 h-3 text-violet-500 shrink-0" />
                            <span className="truncate max-w-[180px]">Pref: {preferredSkills}</span>
                        </div>
                    )}
                </div>

                {/* Separated Timestamps Row: Employer Posted Date (when authentic), First Seen & Last Verified */}
                <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-400 dark:text-slate-500 mt-1 mb-2.5">
                    <div className="flex items-center gap-2.5 flex-wrap">
                        {postedAtDate && (
                            <span
                                className="flex items-center gap-1 text-slate-600 dark:text-slate-300 font-semibold"
                                title="Authentic publication date provided by employer / ATS"
                            >
                                <Calendar className="w-3 h-3 text-blue-500 shrink-0" />
                                Posted {postedAtDate}
                            </span>
                        )}
                        <span
                            className="flex items-center gap-1"
                            title="Timestamp when our system first discovered this posting"
                        >
                            {!postedAtDate && <Calendar className="w-3 h-3 shrink-0" />}
                            First seen {firstSeenDate}
                        </span>
                    </div>
                    <span
                        className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-medium"
                        title="Timestamp when our system most recently confirmed this posting is active"
                    >
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block"></span>
                        Verified {verifiedDate}
                    </span>
                </div>

                {/* Card Footer: Industry & Direct Dedicated Apply Link */}
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
