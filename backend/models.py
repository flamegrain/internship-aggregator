from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class Internship(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    company: str = Field(index=True)
    role: str
    location: str
    industry: str = "Technology"
    ai_label: bool = False
    summary: Optional[str] = None
    requirements: Optional[str] = None
    salary: Optional[str] = None
    deadline: Optional[datetime] = None
    international_score: Optional[int] = Field(
        default=5,
        description="1-10 score indicating friendliness to international students"
    )
    logo_url: Optional[str] = None
    url: str = Field(index=True)

    # Provenance & Verification Metadata
    source: str = Field(
        default="simplify_jobs_github",
        index=True,
        description="Primary/original data source ID (e.g., 'microsoft_official', 'greenhouse_stripe')"
    )
    source_type: str = Field(
        default="community_verified",
        index=True,
        description="Source tier: 'official_api', 'public_ats', 'official_portal', 'community_verified'"
    )
    sources_list: Optional[str] = Field(
        default=None,
        description="JSON list of all source IDs that discovered/verified this posting"
    )
    canonical_key: Optional[str] = Field(
        default=None,
        index=True,
        description="Normalized deduplication fingerprint (company::role::location)"
    )

    # Lifecycle Timestamps & Status
    posted_date: datetime = Field(default_factory=datetime.utcnow)
    first_seen_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when this job was first discovered"
    )
    last_verified_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when this job was last verified as active"
    )
    status: str = Field(
        default="active",
        index=True,
        description="Job status: 'active', 'closed', 'expired', 'stale'"
    )


class CrawlerAlert(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source_id: str = Field(index=True)
    source_name: str
    alert_type: str = Field(
        default="crawl_failure",
        description="Type of alert: 'crawl_exception', 'zero_results', 'volume_drop', 'link_expired'"
    )
    severity: str = Field(
        default="warning",
        description="Severity: 'critical', 'warning', 'info'"
    )
    message: str
    details: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved: bool = Field(default=False, index=True)
    resolved_at: Optional[datetime] = None


class Subscription(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)
