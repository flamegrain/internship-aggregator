import os
import json
import logging
import requests
from datetime import datetime
from typing import Optional, Dict, Any
from sqlmodel import Session, select

try:
    from models import CrawlerAlert
except ImportError:
    from backend.models import CrawlerAlert


def record_crawler_alert(
    session: Session,
    source_id: str,
    source_name: str,
    alert_type: str,
    severity: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
) -> Optional[CrawlerAlert]:
    """
    Persist a collection failure or anomaly alert to the database and log it.
    Also dispatches to ALERT_WEBHOOK_URL if configured in environment.
    """
    details_json = json.dumps(details) if details else None
    log_msg = f"[CRAWLER ALERT][{severity.upper()}][{source_id}:{alert_type}] {message}"
    if severity == "critical":
        logging.error(log_msg)
    else:
        logging.warning(log_msg)

    alert = CrawlerAlert(
        source_id=source_id,
        source_name=source_name,
        alert_type=alert_type,
        severity=severity,
        message=message,
        details=details_json,
        created_at=datetime.utcnow(),
        resolved=False,
    )
    try:
        session.add(alert)
        session.flush()
    except Exception as e:
        logging.warning(f"Could not write CrawlerAlert to database: {e}")

    webhook_url = os.getenv("ALERT_WEBHOOK_URL")
    if webhook_url:
        try:
            requests.post(
                webhook_url,
                json={
                    "source_id": source_id,
                    "source_name": source_name,
                    "alert_type": alert_type,
                    "severity": severity,
                    "message": message,
                    "details": details,
                    "timestamp": datetime.utcnow().isoformat(),
                },
                timeout=5,
            )
        except Exception as e:
            logging.warning(f"Failed to send alert webhook: {e}")

    return alert


def resolve_previous_alerts(session: Session, source_id: str) -> int:
    """Mark unresolved alerts for a source as resolved once a healthy run completes."""
    now = datetime.utcnow()
    resolved_count = 0
    try:
        unresolved = session.exec(
            select(CrawlerAlert).where(
                CrawlerAlert.source_id == source_id,
                CrawlerAlert.resolved == False,
            )
        ).all()
        for alert in unresolved:
            alert.resolved = True
            alert.resolved_at = now
            session.add(alert)
            resolved_count += 1
    except Exception as e:
        logging.warning(f"Could not resolve previous alerts for {source_id}: {e}")
    return resolved_count


def evaluate_crawl_run_health(
    session: Session,
    source_config: Dict[str, Any],
    items_fetched: int,
    items_inserted: int,
    items_merged: int,
    items_closed: int = 0,
    error: Optional[str] = None,
    previous_status: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Evaluate the outcome of a single source crawl run, record alerts on anomalies
    (exception, zero results, >80% volume drop), and return the structured status entry.
    """
    source_id = source_config.get("id", "unknown")
    source_name = source_config.get("name", source_id)
    source_tier = source_config.get("source_type", "official_portal")
    now_iso = datetime.utcnow().isoformat()
    today_str = datetime.utcnow().strftime("%Y-%m-%d")

    status_entry = {
        "source_id": source_id,
        "source_name": source_name,
        "source_type": source_tier,
        "date": today_str,
        "timestamp": now_iso,
        "items_fetched": items_fetched,
        "items_saved": items_inserted,
        "items_merged": items_merged,
        "items_closed": items_closed,
        "status": "success",
        "alert": None,
    }

    if error:
        msg = f"Crawler failed for {source_name}: {error}"
        record_crawler_alert(
            session=session,
            source_id=source_id,
            source_name=source_name,
            alert_type="exception",
            severity="critical",
            message=msg,
            details={"error": error, "timestamp": now_iso},
        )
        status_entry["status"] = "failed"
        status_entry["alert"] = msg
        return status_entry

    if items_fetched == 0:
        msg = f"{source_name} returned 0 listings (possible selector drift, anti-bot block, or closed cycle)."
        record_crawler_alert(
            session=session,
            source_id=source_id,
            source_name=source_name,
            alert_type="zero_results",
            severity="warning",
            message=msg,
            details={"items_fetched": 0, "timestamp": now_iso},
        )
        status_entry["status"] = "warning"
        status_entry["alert"] = msg
        return status_entry

    prev_fetched = (previous_status or {}).get("items_fetched", 0)
    if prev_fetched >= 10 and items_fetched < int(prev_fetched * 0.2):
        msg = (
            f"Sharp volume drop for {source_name}: fetched {items_fetched} listings "
            f"(down from {prev_fetched}, >80% drop)."
        )
        record_crawler_alert(
            session=session,
            source_id=source_id,
            source_name=source_name,
            alert_type="volume_drop",
            severity="warning",
            message=msg,
            details={
                "previous_fetched": prev_fetched,
                "current_fetched": items_fetched,
                "timestamp": now_iso,
            },
        )
        status_entry["status"] = "warning"
        status_entry["alert"] = msg
        return status_entry

    # Healthy run: resolve prior unresolved alerts for this source
    resolve_previous_alerts(session, source_id)
    return status_entry
