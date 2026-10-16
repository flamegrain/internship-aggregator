import json
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

try:
    from sqlmodel import Session, select
    try:
        from models import Internship
    except ImportError:
        from backend.models import Internship
except ImportError:
    Session = Any
    select = None
    Internship = Any

# Strictly prohibited placeholder salaries and fictional requirements
BLOCKED_PLACEHOLDER_SALARIES: Set[str] = {
    "$30 - $60 / hr",
    "$30-$60/hr",
    "$40 - $70 / hr",
    "$50 - $90 / hr",
    "competitive",
    "competitive pay",
    "tbd",
    "n/a",
    "unknown",
    "placeholder",
}

BLOCKED_PLACEHOLDER_REQUIREMENTS: Set[str] = {
    "python, react, sql",
    "currently enrolled in bachelor's or master's degree. 3.0+ gpa preferred.",
    "currently enrolled in bachelor's or master's degree",
    "tbd",
    "n/a",
    "none",
}

# Prohibited source types (simulated / mock data)
BLOCKED_SOURCE_TYPES: Set[str] = {
    "simulated_company_listing",
    "simulated",
    "mock",
}

# Source priority hierarchy (Higher = more authoritative)
SOURCE_TIER_PRIORITY: Dict[str, int] = {
    "official_api": 100,
    "public_ats": 90,
    "official_portal": 80,
    "community_verified": 60,
}
SOURCE_PRIORITY = SOURCE_TIER_PRIORITY

# Default internship job_type allowlist
DEFAULT_INTERNSHIP_JOB_TYPES: Set[str] = {
    "internship",
    "co-op",
    "fellowship",
}

# Known company domain mapping for accurate favicon/logo resolution
COMPANY_DOMAIN_MAP: Dict[str, str] = {
    "google": "google.com",
    "alphabet": "abc.xyz",
    "waymo": "waymo.com",
    "meta": "meta.com",
    "apple": "apple.com",
    "amazon": "amazon.com",
    "microsoft": "microsoft.com",
    "goldman sachs": "goldmansachs.com",
    "jpmorgan chase": "jpmorganchase.com",
    "jpmorgan": "jpmorganchase.com",
    "morgan stanley": "morganstanley.com",
    "nasa": "nasa.gov",
    "stripe": "stripe.com",
    "databricks": "databricks.com",
    "cloudflare": "cloudflare.com",
    "scale ai": "scale.com",
    "robinhood": "robinhood.com",
    "figma": "figma.com",
    "coinbase": "coinbase.com",
    "anthropic": "anthropic.com",
    "openai": "openai.com",
    "spacex": "spacex.com",
    "jane street": "janestreet.com",
    "citadel": "citadel.com",
    "optiver": "optiver.com",
    "american express": "americanexpress.com",
    "oracle": "oracle.com",
    "amd": "amd.com",
    "nvidia": "nvidia.com",
    "tiktok": "tiktok.com",
    "bytedance": "bytedance.com",
    "t-mobile": "t-mobile.com",
    "electronic arts": "ea.com",
    "expedia group": "expediagroup.com",
    "servicenow": "servicenow.com",
    "lseg": "lseg.com",
    "cadence design systems": "cadence.com",
    "general dynamics": "gd.com",
    "general dynamics mission systems": "gdmissionsystems.com",
    "general dynamics information technology": "gdit.com",
    "rtx": "rtx.com",
    "boeing": "boeing.com",
    "lockheed martin": "lockheedmartin.com",
    "pinterest": "pinterest.com",
    "duolingo": "duolingo.com",
    "palantir": "palantir.com",
}

TRACKING_QUERY_PARAMS: Set[str] = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "ref",
    "gh_src",
    "source",
    "src",
}

# Job ID query parameter keys that uniquely identify a posting even on a /jobs or /search endpoint
JOB_ID_QUERY_KEYS: Set[str] = {
    "gh_jid",
    "jobid",
    "job_id",
    "pid",
    "requisitionid",
    "reqid",
    "jid",
    "postingid",
    "id",
}


def is_placeholder_salary(salary: Optional[str]) -> bool:
    if not salary:
        return True
    cleaned = salary.strip().lower()
    if not cleaned or cleaned in BLOCKED_PLACEHOLDER_SALARIES:
        return True
    if not re.search(r"\d", cleaned):
        return True
    return False


def is_placeholder_requirements(req: Optional[str]) -> bool:
    if not req:
        return True
    cleaned = req.strip().lower()
    if not cleaned or cleaned in BLOCKED_PLACEHOLDER_REQUIREMENTS:
        return True
    return False


def sanitize_salary(salary: Optional[str]) -> Optional[str]:
    if is_placeholder_salary(salary):
        return None
    return salary.strip()


def sanitize_requirements(req: Optional[str]) -> Optional[str]:
    if is_placeholder_requirements(req):
        return None
    return req.strip()


def canonicalize_url(url: str) -> str:
    """
    Strips marketing/tracking query parameters (like utm_source=Simplify&ref=Simplify)
    while preserving essential ATS job identifier parameters (like gh_jid).
    """
    if not url:
        return ""
    try:
        parsed = urlparse(url.strip())
        query_pairs = parse_qsl(parsed.query, keep_blank_values=False)
        filtered_pairs = [
            (k, v) for k, v in query_pairs
            if k.lower() not in TRACKING_QUERY_PARAMS
        ]
        clean_path = parsed.path.rstrip("/") if parsed.path != "/" else parsed.path
        return urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            clean_path,
            parsed.params,
            urlencode(filtered_pairs, doseq=True),
            ""
        ))
    except Exception:
        return url.strip()


def is_dedicated_job_detail_url(url: str) -> Tuple[bool, str]:
    """
    Requirement 1: Verify that a URL points to a specific job detail/application page
    with an independent job ID or slug, NOT a generic career search page or homepage.
    """
    if not url or not isinstance(url, str):
        return False, "Empty URL"
    clean = canonicalize_url(url)
    try:
        parsed = urlparse(clean)
    except Exception:
        return False, "Malformed URL"

    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return False, "Missing HTTP scheme or domain"

    host = parsed.netloc.lower()
    path = (parsed.path or "").strip()
    query_dict = {k.lower(): v for k, v in parse_qsl(parsed.query)}

    # Reject raw GitHub README URLs
    if "raw.githubusercontent.com" in host or "github.com/simplifyjobs" in f"{host}{path.lower()}":
        return False, "Repository README URL instead of job application link"

    # Check if query string has an explicit unique job ID parameter (e.g., ?gh_jid=8241260)
    has_query_job_id = any(
        k in JOB_ID_QUERY_KEYS and bool(str(v).strip())
        for k, v in query_dict.items()
    )
    if has_query_job_id:
        return True, f"Valid job ID query parameter in {clean}"

    # Reject root/bare paths without query job ID
    if path in ("", "/"):
        return False, "Root domain homepage without job path or ID"

    path_lower = path.lower()

    # Reject known generic search / listing portals that lack a specific job ID
    generic_search_patterns = [
        r"/jobs/results/?$",
        r"/en/search/?$",
        r"/jobsearch/?$",
        r"/en-us/search/?$",
        r"/career-opportunities-search/?$",
        r"/explore-opportunities(/programs)?/?$",
        r"/programs-and-internships/?$",
        r"/careers/?$",
        r"/jobs/?$",
        r"/search/?$",
        r"/openings/?$",
    ]
    for pat in generic_search_patterns:
        if re.search(pat, path_lower):
            return False, f"Generic search/portal listing path '{path}' without job ID"

    # Reject URLs that have search query parameters (?q=, ?query=, ?base_query=) and no job ID in path
    if any(k in query_dict for k in ("q", "query", "base_query", "search")) and not re.search(r"\d{4,}", path):
        return False, "Generic search query URL without dedicated job ID"

    # Path has multiple segments or an alphanumeric/UUID/numeric job slug
    segments = [seg for seg in path.split("/") if seg]
    if len(segments) >= 2 or re.search(r"\d{3,}", path):
        return True, "Valid dedicated job detail path"

    return False, f"Insufficient job detail path specificity: {path}"


def classify_job_type(role: str, jd_text: Optional[str] = None) -> str:
    """
    Requirement 3: Classify each posting into an explicit job_type:
    - 'co-op'
    - 'fellowship'
    - 'internship'
    - 'new_grad_full_time'
    - 'other_student_program'
    - 'non_student'
    """
    role_clean = (role or "").strip()
    if not role_clean:
        return "non_student"

    # 1. Co-op check
    if re.search(r"\b(co-op|coop|cooperative\s+education)\b", role_clean, re.IGNORECASE):
        return "co-op"

    # 2. Fellowship check
    if re.search(r"\b(fellowship|fellow)\b", role_clean, re.IGNORECASE):
        return "fellowship"

    # 3. Explicit Internship check (must not be a full-time new grad role without intern)
    has_intern_word = bool(
        re.search(
            r"\b(intern|internship|internships|summer\s+analyst|summer\s+associate|winter\s+analyst|fall\s+analyst)\b",
            role_clean,
            re.IGNORECASE,
        )
    )

    # Check if it's explicitly a New Grad / University Grad / Full-Time Analyst program
    is_new_grad = bool(
        re.search(
            r"\b(university\s+grad|new\s+grad|graduate\s+program|graduate\s+programme|full[-\s]time\s+analyst|full[-\s]time\s+technology\s+analyst|early\s+career)\b",
            role_clean,
            re.IGNORECASE,
        )
    )
    if is_new_grad and not has_intern_word:
        return "new_grad_full_time"

    # Check if it's another student program (Apprenticeship, Spring Insight, Industrial Placement, Externship)
    is_other_student = bool(
        re.search(
            r"\b(apprentice|apprenticeship|spring\s+insight|insight\s+event|step\s+in|industrial\s+placement|externship)\b",
            role_clean,
            re.IGNORECASE,
        )
    )
    if is_other_student and not has_intern_word:
        return "other_student_program"

    if has_intern_word:
        return "internship"

    # Check if JD text explicitly identifies it as an internship program even if title is e.g. "2027 Machine Learning Research Associate Program - PhD"
    if re.search(r"\b202[67]\b.*\b(program|programme|summer)\b", role_clean, re.IGNORECASE):
        if re.search(r"\bfull[-\s]time\b", role_clean, re.IGNORECASE):
            return "new_grad_full_time"
        return "other_student_program"

    return "non_student"


# Requirement 4: Auditable Work Authorization / Visa Classification Patterns
RESTRICTED_VISA_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"[^\n]*?\b(?:u\.?s\.?\s*citizen(?:ship)?|united\s+states\s+citizen(?:ship)?)\s+(?:is\s+)?(?:required|only|mandatory)[^\n]*", re.IGNORECASE), "U.S. citizenship required"),
    (re.compile(r"[^\n]*?\bmust\s+be\s+a\s+u\.?s\.?\s*(?:citizen|person|national)[^\n]*", re.IGNORECASE), "Must be a U.S. Citizen / U.S. Person"),
    (re.compile(r"[^\n]*?\b(?:active\s+|top\s+secret\s+|secret\s+)?security\s+clearance\s+(?:is\s+)?required[^\n]*", re.IGNORECASE), "Security clearance required"),
    (re.compile(r"[^\n]*?\b(?:unable\s+to|do\s+not|does\s+not|will\s+not|cannot)\s+(?:offer\s+|provide\s+)?(?:visa\s+|work\s+authorization\s+|immigration\s+)?sponsor(?:ship)?(?!\s+for\s+an\s+export\s+license)[^\n]*", re.IGNORECASE), "Does not offer visa sponsorship"),
    (re.compile(r"[^\n]*?\bno\s+visa\s+sponsorship[^\n]*", re.IGNORECASE), "No visa sponsorship available"),
    (re.compile(r"[^\n]*?\bwithout\s+(?:the\s+need\s+for\s+)?(?:current\s+or\s+future\s+)?(?:visa|immigration|work\s+authorization)\s+sponsorship[^\n]*", re.IGNORECASE), "Requires work authorization without current or future visa sponsorship"),
    (re.compile(r"[^\n]*?\bitar\b[^\n]*?(?:u\.?s\.?\s*person|u\.?s\.?\s*citizen|lawful\s+permanent\s+resident)[^\n]*", re.IGNORECASE), "ITAR U.S. Person / citizenship requirement"),
]

SUPPORTED_VISA_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"[^.!?\n]*\bvisa\s+sponsorship\s+is\s+available[^.!?\n]*", re.IGNORECASE), "Visa sponsorship is available"),
    (re.compile(r"[^.!?\n]*\b(?:will|can|able\s+to)\s+sponsor\s+(?:visas?|work\s+authorization|h-?1b)[^.!?\n]*", re.IGNORECASE), "Explicitly sponsors visas"),
    (re.compile(r"[^.!?\n]*\b(?:accepts?|welcomes?|supports?|eligible\s+for)\s+(?:f-?1|cpt|opt|stem\s+opt)\b[^.!?\n]*", re.IGNORECASE), "Explicitly accepts F-1 / CPT / OPT work authorization"),
    (re.compile(r"[^.!?\n]*\bsponsorship\s+available\s+for\s+qualified\s+candidates[^.!?\n]*", re.IGNORECASE), "Sponsorship available for qualified candidates"),
]

AMBIGUOUS_VISA_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"[^.!?\n]*\bsponsorship\s+(?:may\s+be|is\s+limited|case[-\s]by[-\s]case)[^.!?\n]*", re.IGNORECASE), "Ambiguous or conditional sponsorship statement"),
]


def classify_visa_status(
    jd_text: Optional[str],
    source_url: Optional[str],
    explicit_flags: Optional[Dict[str, bool]] = None,
    verified_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Requirement 4: Classify work authorization into auditable categories with verbatim evidence:
    - 'explicitly_restricted'
    - 'sponsorship_explicitly_supported'
    - 'not_specified'
    - 'needs_review'
    Never fabricates a probabilistic '8/10' score when evidence is absent.
    """
    now = verified_at or datetime.utcnow()
    flags = explicit_flags or {}
    clean_url = canonicalize_url(source_url or "") or None

    restricted_quotes: List[str] = []
    supported_quotes: List[str] = []
    ambiguous_quotes: List[str] = []

    if flags.get("has_us_citizen_flag"):
        restricted_quotes.append("Source explicitly tagged 🇺🇸 (Requires U.S. Citizenship)")
    if flags.get("has_no_sponsor_flag"):
        restricted_quotes.append("Source explicitly tagged 🛂 (Does NOT offer Visa Sponsorship)")

    if jd_text:
        for pat, _ in RESTRICTED_VISA_PATTERNS:
            m = pat.search(jd_text)
            if m:
                snippet = re.sub(r"\s+", " ", m.group(0)).strip()[:240]
                restricted_quotes.append(snippet)
                break

        for pat, _ in SUPPORTED_VISA_PATTERNS:
            m = pat.search(jd_text)
            if m:
                snippet = re.sub(r"\s+", " ", m.group(0)).strip()[:240]
                supported_quotes.append(snippet)
                break

        for pat, _ in AMBIGUOUS_VISA_PATTERNS:
            m = pat.search(jd_text)
            if m:
                snippet = re.sub(r"\s+", " ", m.group(0)).strip()[:240]
                ambiguous_quotes.append(snippet)
                break

    # Conflicting evidence -> needs_review
    if restricted_quotes and supported_quotes:
        return {
            "visa_status": "needs_review",
            "visa_evidence": f"Conflicting statements: [{restricted_quotes[0]}] vs [{supported_quotes[0]}]",
            "visa_source_url": clean_url,
            "visa_verified_at": now,
        }

    if restricted_quotes:
        return {
            "visa_status": "explicitly_restricted",
            "visa_evidence": restricted_quotes[0],
            "visa_source_url": clean_url,
            "visa_verified_at": now,
        }

    if supported_quotes:
        return {
            "visa_status": "sponsorship_explicitly_supported",
            "visa_evidence": supported_quotes[0],
            "visa_source_url": clean_url,
            "visa_verified_at": now,
        }

    if ambiguous_quotes:
        return {
            "visa_status": "needs_review",
            "visa_evidence": ambiguous_quotes[0],
            "visa_source_url": clean_url,
            "visa_verified_at": now,
        }

    return {
        "visa_status": "not_specified",
        "visa_evidence": None,
        "visa_source_url": clean_url,
        "visa_verified_at": now,
    }


def extract_structured_compensation(
    jd_text: Optional[str],
    structured_range: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Requirement 5: Extract structured salary_min, salary_max, salary_period, currency,
    formatted display string, and verbatim salary_quote evidence.
    Returns all None when no verified compensation is present.
    """
    result = {
        "salary": None,
        "salary_min": None,
        "salary_max": None,
        "salary_period": None,
        "currency": None,
        "salary_quote": None,
    }

    # 1. Check structured ATS compensation object first (e.g. Lever salaryRange)
    if isinstance(structured_range, dict) and structured_range.get("min") and structured_range.get("max"):
        try:
            s_min = float(structured_range["min"])
            s_max = float(structured_range["max"])
            currency = (structured_range.get("currency") or "USD").upper()
            interval = (structured_range.get("interval") or "").lower()
            if "hour" in interval and 15 <= s_min <= 250 and s_min <= s_max <= 300:
                disp = f"${int(s_min)} / hr" if s_min == s_max else f"${int(s_min)} - ${int(s_max)} / hr"
                return {
                    "salary": disp,
                    "salary_min": s_min,
                    "salary_max": s_max,
                    "salary_period": "hour",
                    "currency": currency,
                    "salary_quote": f"Structured ATS salaryRange: {currency} {s_min}-{s_max} per {interval}",
                }
            if "month" in interval and 2000 <= s_min <= 35000 and s_min <= s_max <= 40000:
                disp = f"${int(s_min):,} / mo" if s_min == s_max else f"${int(s_min):,} - ${int(s_max):,} / mo"
                return {
                    "salary": disp,
                    "salary_min": s_min,
                    "salary_max": s_max,
                    "salary_period": "month",
                    "currency": currency,
                    "salary_quote": f"Structured ATS salaryRange: {currency} {s_min}-{s_max} per {interval}",
                }
            if ("year" in interval or "annual" in interval) and 40000 <= s_min <= 350000 and s_min <= s_max <= 400000:
                disp = f"${int(s_min):,} / yr" if s_min == s_max else f"${int(s_min):,} - ${int(s_max):,} / yr"
                return {
                    "salary": disp,
                    "salary_min": s_min,
                    "salary_max": s_max,
                    "salary_period": "year",
                    "currency": currency,
                    "salary_quote": f"Structured ATS salaryRange: {currency} {s_min}-{s_max} per {interval}",
                }
        except Exception:
            pass

    if not jd_text:
        return result

    # 2. Match hourly rate or range with surrounding context sentence as verbatim evidence
    hourly_pattern = re.compile(
        r"\$([1-9]\d(?:\.\d{1,2})?)\s*(?:USD\s*)?(?:/\s*(?:hr|hour)|per\s+hour|an\s+hour)?\s*(?:-|–|—|to)\s*\$([1-9]\d{1,2}(?:\.\d{1,2})?)\s*(?:USD\s*)?(?:/\s*(?:hr|hour)|per\s+hour|an\s+hour|hourly)",
        re.IGNORECASE,
    )
    m = hourly_pattern.search(jd_text)
    if m:
        low, high = float(m.group(1)), float(m.group(2))
        if 15 <= low <= 250 and low <= high <= 300:
            start_idx = max(0, m.start() - 45)
            end_idx = min(len(jd_text), m.end() + 45)
            quote = re.sub(r"\s+", " ", jd_text[start_idx:end_idx]).strip()
            disp = f"${int(round(low))} / hr" if int(round(low)) == int(round(high)) else f"${int(round(low))} - ${int(round(high))} / hr"
            if not is_placeholder_salary(disp):
                return {
                    "salary": disp,
                    "salary_min": round(low, 2),
                    "salary_max": round(high, 2),
                    "salary_period": "hour",
                    "currency": "USD",
                    "salary_quote": quote,
                }

    single_hourly = re.compile(
        r"\$([1-9]\d(?:\.\d{1,2})?)\s*(?:USD\s*)?(?:/\s*(?:hr|hour)|per\s+hour|an\s+hour|hourly)",
        re.IGNORECASE,
    )
    m_single = single_hourly.search(jd_text)
    if m_single:
        rate = float(m_single.group(1))
        if 15 <= rate <= 250:
            start_idx = max(0, m_single.start() - 45)
            end_idx = min(len(jd_text), m_single.end() + 45)
            quote = re.sub(r"\s+", " ", jd_text[start_idx:end_idx]).strip()
            val = int(round(rate))
            return {
                "salary": f"${val} / hr",
                "salary_min": round(rate, 2),
                "salary_max": round(rate, 2),
                "salary_period": "hour",
                "currency": "USD",
                "salary_quote": quote,
            }

    # 3. Monthly salary range or single monthly rate
    monthly_pattern = re.compile(
        r"\$([2-9],\d{3}|1\d,\d{3}|2\d,\d{3})\s*(?:-|–|—|to)?\s*(?:\$([2-9],\d{3}|1\d,\d{3}|2\d,\d{3}))?\s*(?:USD\s*)?(?:/\s*(?:mo|month)|per\s+month|monthly)",
        re.IGNORECASE,
    )
    m_month = monthly_pattern.search(jd_text)
    if m_month:
        low_str = m_month.group(1).replace(",", "")
        high_str = (m_month.group(2) or m_month.group(1)).replace(",", "")
        low_v, high_v = float(low_str), float(high_str)
        if 2000 <= low_v <= high_v <= 35000:
            start_idx = max(0, m_month.start() - 45)
            end_idx = min(len(jd_text), m_month.end() + 45)
            quote = re.sub(r"\s+", " ", jd_text[start_idx:end_idx]).strip()
            disp = f"${int(low_v):,} / mo" if low_v == high_v else f"${int(low_v):,} - ${int(high_v):,} / mo"
            return {
                "salary": disp,
                "salary_min": low_v,
                "salary_max": high_v,
                "salary_period": "month",
                "currency": "USD",
                "salary_quote": quote,
            }

    return result


def extract_verified_salary_from_text(text: str) -> Optional[str]:
    """Compatibility wrapper returning the display string from extract_structured_compensation."""
    return extract_structured_compensation(text).get("salary")


SKILL_PATTERNS: List[Tuple[str, str]] = [
    (r"\bPython\b", "Python"),
    (r"\bJava\b", "Java"),
    (r"\bC\+\+", "C++"),
    (r"\bTypeScript\b", "TypeScript"),
    (r"\bJavaScript\b", "JavaScript"),
    (r"\bReact(?:\.js|JS)?\b", "React"),
    (r"\bSQL\b", "SQL"),
    (r"\bGo(?:lang)?\b", "Go"),
    (r"\bRust\b", "Rust"),
    (r"\bKotlin\b", "Kotlin"),
    (r"\bSwift\b", "Swift"),
    (r"\bPyTorch\b", "PyTorch"),
    (r"\bTensorFlow\b", "TensorFlow"),
    (r"\bKubernetes\b", "Kubernetes"),
    (r"\bDocker\b", "Docker"),
    (r"\bAWS\b", "AWS"),
    (r"\bGCP\b", "GCP"),
    (r"\bAzure\b", "Azure"),
    (r"\bLinux\b", "Linux"),
    (r"\bSpark\b", "Spark"),
]


def _find_skills_with_quote(section_text: str, max_skills: int = 6) -> Tuple[Optional[str], Optional[str]]:
    if not section_text:
        return None, None
    found: List[str] = []
    first_match_span: Optional[Tuple[int, int]] = None
    for pattern, canonical in SKILL_PATTERNS:
        m = re.search(pattern, section_text)
        if m:
            found.append(canonical)
            if first_match_span is None:
                first_match_span = (m.start(), m.end())
        if len(found) >= max_skills:
            break
    if not found:
        return None, None
    joined = ", ".join(found)
    if is_placeholder_requirements(joined):
        return None, None
    quote = None
    if first_match_span:
        s_idx = max(0, first_match_span[0] - 40)
        e_idx = min(len(section_text), first_match_span[1] + 100)
        quote = re.sub(r"\s+", " ", section_text[s_idx:e_idx]).strip()
    return joined, quote


def extract_structured_skills(jd_text: Optional[str]) -> Dict[str, Optional[str]]:
    """
    Requirement 5: Separate required_skills and preferred_skills with verbatim quotes.
    """
    res: Dict[str, Optional[str]] = {
        "required_skills": None,
        "preferred_skills": None,
        "required_skills_quote": None,
        "preferred_skills_quote": None,
    }
    if not jd_text:
        return res

    # Split text into required vs preferred sections if preferred heading exists
    pref_split = re.split(
        r"\b(?:preferred\s+qualifications|nice\s+to\s+have|bonus\s+points|preferred\s+skills|desired\s+qualifications)\b",
        jd_text,
        maxsplit=1,
        flags=re.IGNORECASE,
    )
    req_section = pref_split[0]
    pref_section = pref_split[1] if len(pref_split) > 1 else ""

    req_skills, req_quote = _find_skills_with_quote(req_section)
    pref_skills, pref_quote = _find_skills_with_quote(pref_section)

    # Remove skills from preferred_skills that are already in required_skills
    if req_skills and pref_skills:
        req_set = {s.strip() for s in req_skills.split(",")}
        pref_filtered = [s.strip() for s in pref_skills.split(",") if s.strip() not in req_set]
        pref_skills = ", ".join(pref_filtered) if pref_filtered else None
        if not pref_skills:
            pref_quote = None

    res["required_skills"] = req_skills
    res["preferred_skills"] = pref_skills
    res["required_skills_quote"] = req_quote
    res["preferred_skills_quote"] = pref_quote
    return res


def extract_verified_requirements_from_text(text: str) -> Optional[str]:
    """Compatibility wrapper returning required_skills."""
    return extract_structured_skills(text).get("required_skills")


# Requirement 6: Explicit Role Category Taxonomy using complete phrases & word boundaries
ROLE_CATEGORY_RULES: List[Tuple[str, re.Pattern]] = [
    (
        "ai_ml",
        re.compile(
            r"\b(machine\s+learning|artificial\s+intelligence|deep\s+learning|computer\s+vision|natural\s+language\s+processing|generative\s+ai|genai|large\s+language\s+models?|llms?|reinforcement\s+learning|ai\s+engineer(?:ing)?|ai\s+research|ml\s+engineer(?:ing)?|neural\s+networks?|autonomous\s+vehicles?|ai/ml|ml/ai|foundational\s+models?|multimodal|agentic\s+ai)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "research",
        re.compile(
            r"\b(research\s+scientist|research\s+intern(?:ship)?|research\s+fellow(?:ship)?|applied\s+scientist|quantitative\s+research(?:er)?|research\s+associate|phd\s+research|r&d\s+intern|science\s+intern)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "data_analytics",
        re.compile(
            r"\b(data\s+scien(?:ce|tist)|data\s+analy(?:st|tics)|data\s+engineer(?:ing)?|business\s+intelligence|bi\s+analyst|bi\s+engineer|quantitative\s+analyst|analytics\s+intern|decision\s+science|statistician|actuarial\s+intern|data\s+&\s+analytics|data\s+&\s+technology)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "software_engineering",
        re.compile(
            r"\b(software\s+engineer(?:ing)?|software\s+developer|software\s+development|sde\s+intern|swe\s+intern|frontend|front-end|backend|back-end|full\s*stack|ios\s+engineer|android\s+engineer|mobile\s+engineer|systems\s+software|systems\s+engineer|site\s+reliability|sre\s+intern|devops|cloud\s+engineer|platform\s+engineer|security\s+engineer|firmware\s+engineer|embedded\s+software|embedded\s+engineer|web\s+developer|application\s+developer|application\s+development|technology\s+summer\s+analyst|summer\s+technology\s+analyst|technology\s+intern(?:ship)?|tech\s+intern|forward\s+deployed\s+software\s+engineer|developer\s+intern)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "other",
        re.compile(
            r"\b(product\s+manag(?:er|ement)|product\s+design(?:er)?|ux\s+design(?:er)?|ux\s+engineer|ui/ux|hardware\s+engineer(?:ing)?|electrical\s+engineer(?:ing)?|mechanical\s+engineer(?:ing)?|civil\s+engineer(?:ing)?|silicon\s+engineer(?:ing)?|aerospace\s+engineer(?:ing)?|manufacturing\s+engineer|quality\s+engineer|business\s+operations|financial\s+analyst|finance\s+intern|accounting\s+intern|it\s+intern(?:ship)?|information\s+technology\s+intern|cyber\s*security|network\s+engineer|technical\s+program\s+manager|program\s+manager|project\s+manager|quant(?:itative)?\s+trad(?:er|ing)|trading\s+intern|sales\s+&\s+trading|investment\s+banking|wealth\s+management|risk\s+management|supply\s+chain|marketing\s+intern|human\s+resources|hr\s+intern|legal\s+intern|operations\s+intern|solutions?\s+architect|solution\s+engineer|customer\s+success|account\s+executive|account\s+tech\s+strategist|data\s+center\s+technician)\b",
            re.IGNORECASE,
        ),
    ),
]


def classify_role_category(role: str, jd_text: Optional[str] = None) -> Tuple[str, Optional[str]]:
    """
    Requirement 6: Classify role into ('ai_ml', 'software_engineering', 'data_analytics', 'research', 'other', 'unclassified')
    using complete phrase matching and save the exact matched phrase as category_evidence.
    """
    role_clean = (role or "").strip()
    if role_clean:
        for category, pattern in ROLE_CATEGORY_RULES:
            m = pattern.search(role_clean)
            if m:
                matched_phrase = m.group(0)
                return category, f"Role title match: '{matched_phrase}' in '{role_clean}'"

    if jd_text:
        for category, pattern in ROLE_CATEGORY_RULES:
            m = pattern.search(jd_text)
            if m:
                start_i = max(0, m.start() - 30)
                end_i = min(len(jd_text), m.end() + 30)
                snippet = re.sub(r"\s+", " ", jd_text[start_i:end_i]).strip()
                return category, f"JD content match: '{m.group(0)}' (...{snippet}...)"

    return "unclassified", None


def compute_canonical_key(company: str, role: str, location: Optional[str]) -> str:
    """
    Generates a normalized canonical key (company::role::location) to identify and merge
    duplicate job postings across different sources or multiple URLs.
    """
    norm_company = re.sub(r"[^a-z0-9]", "", (company or "").lower())
    norm_role = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", (role or "").lower())).strip()
    norm_loc = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", (location or "remote").lower())).strip()
    return f"{norm_company}::{norm_role}::{norm_loc}"


def resolve_logo_url(company: str, existing_logo_url: Optional[str] = None) -> str:
    """
    Resolves a valid company logo URL, fixing broken '.com' favicons.
    """
    if existing_logo_url and "domain=.com" not in existing_logo_url and existing_logo_url.strip():
        return existing_logo_url.strip()

    company_clean = (company or "").strip().lower()
    for key, domain in COMPANY_DOMAIN_MAP.items():
        if key == company_clean or key in company_clean:
            return f"https://www.google.com/s2/favicons?domain={domain}&sz=128"

    slug = re.sub(r"[^a-z0-9]", "", company_clean)
    if slug:
        return f"https://www.google.com/s2/favicons?domain={slug}.com&sz=128"

    return f"https://ui-avatars.com/api/?name={urlencode({'name': company or 'Job'})}&background=6366f1&color=fff"


def parse_sources_list(sources_str: Optional[str], primary_source: Optional[str] = None) -> List[str]:
    if not sources_str:
        return [primary_source] if primary_source else []
    try:
        parsed = json.loads(sources_str)
        if isinstance(parsed, list):
            return [str(s) for s in parsed if s]
    except Exception:
        pass
    return [s.strip() for s in sources_str.split(",") if s.strip()]


def upsert_or_merge_internship(
    session: Session,
    item_data: Dict[str, Any],
    source_id: Optional[str] = None,
    source_type: Optional[str] = None,
) -> Tuple[Optional[Internship], str]:
    """
    Validates, sanitizes, and inserts or merges an internship posting with full provenance,
    separated timestamps, job_type validation, auditable visa status, structured compensation/skills,
    explicit role_category, and source-authority-protected lifecycle transitions.
    """
    payload = item_data
    source_type = source_type or payload.get("source_type", "community_verified")
    source_id = source_id or payload.get("source") or "unknown"

    # 1. Block simulated / mock jobs from entering production
    if source_type in BLOCKED_SOURCE_TYPES or "simulated" in source_id.lower() or payload.get("is_simulated"):
        logging.warning(f"Rejected simulated job from entering production: {payload.get('company')} - {payload.get('role')}")
        return None, "rejected"

    company = (payload.get("company") or "").strip()
    role = (payload.get("role") or "").strip()
    raw_url = (payload.get("url") or "").strip()

    if not company or not role or not raw_url or not raw_url.startswith("http"):
        return None, "rejected"

    # Requirement 1: Verify dedicated job detail URL (never allow generic search pages as active links)
    clean_url = canonicalize_url(raw_url)
    is_valid_url, url_reason = is_dedicated_job_detail_url(clean_url)
    incoming_status = payload.get("status", "active")
    if not is_valid_url:
        logging.warning(f"URL failed dedicated job detail check ({url_reason}): {clean_url} -> marking pending_review")
        incoming_status = "pending_review"

    location = (payload.get("location") or "United States").strip()
    c_key = compute_canonical_key(company, role, location)
    jd_text = payload.get("jd_text") or payload.get("summary") or ""

    # Requirement 3: Explicit job_type classification
    job_type = payload.get("job_type") or classify_job_type(role, jd_text)

    # Requirement 6: Explicit role_category & category_evidence
    role_category = payload.get("role_category")
    category_evidence = payload.get("category_evidence")
    if not role_category or role_category == "unclassified":
        role_category, category_evidence = classify_role_category(role, jd_text)
    ai_label = role_category == "ai_ml"

    # Requirement 5: Structured compensation & skills with verbatim extraction_evidence
    comp_info = extract_structured_compensation(jd_text, payload.get("structured_salary_range"))
    salary_min = payload.get("salary_min") if payload.get("salary_min") is not None else comp_info["salary_min"]
    salary_max = payload.get("salary_max") if payload.get("salary_max") is not None else comp_info["salary_max"]
    salary_period = payload.get("salary_period") or comp_info["salary_period"]
    currency = payload.get("currency") or comp_info["currency"]
    clean_salary = sanitize_salary(payload.get("salary") or comp_info["salary"])

    skills_info = extract_structured_skills(jd_text)
    req_skills = sanitize_requirements(payload.get("required_skills") or payload.get("requirements") or skills_info["required_skills"])
    pref_skills = sanitize_requirements(payload.get("preferred_skills") or skills_info["preferred_skills"])

    evidence_obj: Dict[str, str] = {}
    if payload.get("extraction_evidence"):
        try:
            evidence_obj = json.loads(payload["extraction_evidence"]) if isinstance(payload["extraction_evidence"], str) else dict(payload["extraction_evidence"])
        except Exception:
            evidence_obj = {}
    if comp_info.get("salary_quote"):
        evidence_obj.setdefault("salary_quote", comp_info["salary_quote"])
    if skills_info.get("required_skills_quote"):
        evidence_obj.setdefault("required_skills_quote", skills_info["required_skills_quote"])
    if skills_info.get("preferred_skills_quote"):
        evidence_obj.setdefault("preferred_skills_quote", skills_info["preferred_skills_quote"])
    extraction_evidence_json = json.dumps(evidence_obj) if evidence_obj else None

    # Requirement 4: Auditable visa_status & evidence
    now = datetime.utcnow()
    if payload.get("visa_status") and payload.get("visa_status") != "not_specified":
        visa_info = {
            "visa_status": payload["visa_status"],
            "visa_evidence": payload.get("visa_evidence"),
            "visa_source_url": payload.get("visa_source_url") or clean_url,
            "visa_verified_at": payload.get("visa_verified_at") or now,
        }
    else:
        visa_info = classify_visa_status(
            jd_text=jd_text,
            source_url=clean_url,
            explicit_flags=payload.get("visa_flags"),
            verified_at=now,
        )

    # Requirement 2: Separate posted_at (null unless verified employer timestamp), first_seen_at, last_verified_at
    posted_at = payload.get("posted_at")  # Only set when employer/ATS provides real publication timestamp
    first_seen = payload.get("first_seen_at") or now
    clean_logo = resolve_logo_url(company, payload.get("logo_url"))

    # Check for existing record by canonical URL or canonical (company, role, location) key
    existing = session.exec(
        select(Internship).where(
            (Internship.url == clean_url) |
            (Internship.url == raw_url) |
            (Internship.canonical_key == c_key)
        )
    ).first()

    if existing:
        existing_sources = parse_sources_list(existing.sources_list, existing.source)
        if source_id not in existing_sources:
            existing_sources.append(source_id)
        existing.sources_list = json.dumps(existing_sources)

        old_priority = SOURCE_TIER_PRIORITY.get(existing.source_type or "community_verified", 0)
        new_priority = SOURCE_TIER_PRIORITY.get(source_type, 0)
        status_auth_priority = SOURCE_TIER_PRIORITY.get(
            existing.status_authority or existing.source_type or "community_verified", 0
        )

        # Promote primary source & URL if incoming source is higher or equal priority and has valid URL
        if new_priority >= old_priority and is_valid_url:
            existing.source = source_id
            existing.source_type = source_type
            existing.url = clean_url

        # Requirement 7: Source-level authority protection for lifecycle status transitions
        existing.last_verified_at = now
        if incoming_status in ("closed", "expired"):
            if new_priority >= status_auth_priority or source_id == existing.source:
                existing.status = incoming_status
                existing.status_authority = source_type
        elif incoming_status == "active" and is_valid_url:
            if existing.status in ("closed", "expired"):
                # Only reactivate a closed/expired posting if the incoming source has >= authority
                # AND is an authoritative official/ATS source (or the exact source that closed it)
                if new_priority > status_auth_priority or (
                    new_priority == status_auth_priority and source_type in ("official_api", "public_ats", "official_portal")
                ):
                    existing.status = "active"
                    existing.status_authority = source_type
            elif existing.status == "pending_review":
                existing.status = "active"
                existing.status_authority = source_type
            else:
                if new_priority >= status_auth_priority:
                    existing.status_authority = source_type

        # Preserve earliest first_seen_at
        if first_seen and existing.first_seen_at and first_seen < existing.first_seen_at:
            existing.first_seen_at = first_seen

        # Enrich posted_at only if employer timestamp is provided
        if posted_at and not existing.posted_at:
            existing.posted_at = posted_at
            existing.posted_date = posted_at

        # Enrich job_type and role_category
        if job_type and (not existing.job_type or new_priority >= old_priority):
            existing.job_type = job_type
        if role_category != "unclassified" and (existing.role_category == "unclassified" or new_priority >= old_priority):
            existing.role_category = role_category
            existing.category_evidence = category_evidence
            existing.ai_label = role_category == "ai_ml"

        # Enrich structured compensation & skills
        if clean_salary and (not existing.salary or new_priority >= old_priority):
            existing.salary = clean_salary
            existing.salary_min = salary_min
            existing.salary_max = salary_max
            existing.salary_period = salary_period
            existing.currency = currency
        if req_skills and (not existing.required_skills or new_priority >= old_priority):
            existing.required_skills = req_skills
            existing.requirements = req_skills
        if pref_skills and (not existing.preferred_skills or new_priority >= old_priority):
            existing.preferred_skills = pref_skills
        if extraction_evidence_json:
            existing.extraction_evidence = extraction_evidence_json

        # Enrich auditable visa status when new evidence exists
        if visa_info["visa_status"] != "not_specified" and (
            existing.visa_status == "not_specified" or new_priority >= old_priority
        ):
            existing.visa_status = visa_info["visa_status"]
            existing.visa_evidence = visa_info["visa_evidence"]
            existing.visa_source_url = visa_info["visa_source_url"]
            existing.visa_verified_at = visa_info["visa_verified_at"]

        existing.logo_url = resolve_logo_url(company, existing.logo_url or clean_logo)
        existing.canonical_key = c_key

        session.add(existing)
        return existing, "merged"

    # Insert brand new verified record
    new_job = Internship(
        company=company,
        role=role,
        location=location,
        industry=payload.get("industry", "Technology"),
        job_type=job_type,
        role_category=role_category,
        category_evidence=category_evidence,
        ai_label=ai_label,
        summary=payload.get("summary"),
        salary=clean_salary,
        salary_min=salary_min,
        salary_max=salary_max,
        salary_period=salary_period,
        currency=currency,
        requirements=req_skills,
        required_skills=req_skills,
        preferred_skills=pref_skills,
        extraction_evidence=extraction_evidence_json,
        deadline=payload.get("deadline"),
        visa_status=visa_info["visa_status"],
        visa_evidence=visa_info["visa_evidence"],
        visa_source_url=visa_info["visa_source_url"],
        visa_verified_at=visa_info["visa_verified_at"],
        international_score=None,
        logo_url=clean_logo,
        url=clean_url,
        source=source_id,
        source_type=source_type,
        sources_list=json.dumps([source_id]),
        canonical_key=c_key,
        posted_at=posted_at,
        posted_date=posted_at or first_seen,
        first_seen_at=first_seen,
        last_verified_at=now,
        status=incoming_status,
        status_authority=source_type,
    )
    session.add(new_job)
    return new_job, "inserted"


def reconcile_source_snapshot(
    session: Session,
    source_id: str,
    seen_canonical_keys: Set[str],
    min_expected_count: int = 5,
) -> int:
    """
    When a full-snapshot source completes a healthy crawl, marks previously active jobs
    exclusive to that source as 'expired' if they are no longer present in the live feed.
    """
    if not seen_canonical_keys or len(seen_canonical_keys) < min_expected_count:
        return 0

    active_from_source = session.exec(
        select(Internship).where(
            Internship.source == source_id,
            Internship.status == "active",
        )
    ).all()

    expired_count = 0
    for job in active_from_source:
        if job.canonical_key and job.canonical_key not in seen_canonical_keys:
            sources = parse_sources_list(job.sources_list, job.source)
            if len(sources) <= 1:
                job.status = "expired"
                job.status_authority = job.source_type
                session.add(job)
                expired_count += 1

    return expired_count


def detect_expired_and_stale_jobs(
    session: Session,
    stale_days: int = 14,
    expired_days: int = 30,
) -> Dict[str, int]:
    """
    Scans active jobs and transitions jobs past their deadline or verification TTL
    to 'stale' or 'expired'.
    """
    now = datetime.utcnow()
    stale_cutoff = now - timedelta(days=stale_days)
    expired_cutoff = now - timedelta(days=expired_days)

    active_jobs = session.exec(
        select(Internship).where(Internship.status == "active")
    ).all()

    marked_expired = 0
    marked_stale = 0

    for job in active_jobs:
        if job.deadline and job.deadline < now:
            job.status = "expired"
            session.add(job)
            marked_expired += 1
            continue

        last_ver = job.last_verified_at or job.first_seen_at
        if last_ver and last_ver < expired_cutoff:
            job.status = "expired"
            session.add(job)
            marked_expired += 1
        elif last_ver and last_ver < stale_cutoff:
            job.status = "stale"
            session.add(job)
            marked_stale += 1

    return {
        "marked_expired": marked_expired,
        "marked_stale": marked_stale,
    }
