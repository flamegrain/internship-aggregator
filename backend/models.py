from typing import Optional
from sqlmodel import Field, SQLModel
from datetime import datetime


class Internship(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    company: str = Field(index=True)
    role: str
    location: str
    industry: Optional[str] = None

    # Requirement 3: Explicit job_type classification
    # Values: "internship", "co-op", "fellowship", "new_grad_full_time", "other_student_program", "non_student"
    job_type: str = Field(default="internship", index=True)

    # Requirement 6: Explicit role category taxonomy & evidence
    # Values: "ai_ml", "software_engineering", "data_analytics", "research", "other", "unclassified"
    role_category: str = Field(default="unclassified", index=True)
    category_evidence: Optional[str] = None
    ai_label: bool = Field(default=False)  # True only when role_category == "ai_ml"

    summary: Optional[str] = None

    # Requirement 5: Structured compensation, required/preferred skills & verbatim evidence
    salary: Optional[str] = None  # Formatted display string when salary_min/max exist
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_period: Optional[str] = None  # "hour" | "month" | "year"
    currency: Optional[str] = None       # e.g. "USD"
    requirements: Optional[str] = None   # Summary of required_skills for compatibility
    required_skills: Optional[str] = None
    preferred_skills: Optional[str] = None
    extraction_evidence: Optional[str] = None  # JSON object with verbatim quotes

    deadline: Optional[datetime] = None

    # Requirement 4: Auditable work authorization / visa classification & evidence
    # Values: "explicitly_restricted", "sponsorship_explicitly_supported", "not_specified", "needs_review"
    visa_status: str = Field(default="not_specified", index=True)
    visa_evidence: Optional[str] = None
    visa_source_url: Optional[str] = None
    visa_verified_at: Optional[datetime] = None
    international_score: Optional[int] = Field(default=None)  # Deprecated; kept null to avoid unbacked 8/10 scores

    logo_url: Optional[str] = None
    url: str = Field(unique=True, index=True)

    # Provenance & multi-source tracking
    source: str = Field(default="simplify_jobs_github", index=True)
    source_type: str = Field(default="community_verified", index=True)
    sources_list: Optional[str] = Field(default=None)
    canonical_key: Optional[str] = Field(default=None, index=True)

    # Requirement 2: Separated timestamps
    posted_at: Optional[datetime] = Field(default=None, index=True)  # Employer's real posted date; null if unknown
    posted_date: Optional[datetime] = Field(default=None)            # Compatibility alias
    first_seen_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    last_verified_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    # Requirement 1 & 7: Lifecycle status & authority protection
    # Values: "active", "closed", "expired", "stale", "pending_review"
    status: str = Field(default="active", index=True)
    status_authority: Optional[str] = Field(default="community_verified")


class Subscription(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)
    last_sent_at: Optional[datetime] = None


class CrawlerAlert(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source_id: str = Field(index=True)
    source_name: str
    alert_type: str  # "exception" | "zero_results" | "volume_drop" | "blocked_simulated_source"
    severity: str = Field(default="warning")  # "info" | "warning" | "critical"
    message: str
    details: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    resolved: bool = Field(default=False, index=True)
    resolved_at: Optional[datetime] = None
