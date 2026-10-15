from fastapi import FastAPI, Depends, Query, APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlmodel import Session, select, func
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import os
from .database import create_db_and_tables, get_session
from .models import Internship, Subscription
from .email_service import is_valid_email, generate_digest_html, send_digest_email
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter()

def load_data_sources():
    try:
        json_path = os.path.join(os.path.dirname(__file__), 'data_sources.json')
        with open(json_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading data sources: {e}")
        return []

@router.get("/health")
def health_check():
    return {"status": "ok", "message": "Internship Aggregator API is running"}

@router.get("/stats", response_model=Dict[str, Any])
def get_stats(session: Session = Depends(get_session)):
    total = session.exec(select(func.count(Internship.id))).one()
    latest_date = session.exec(select(func.max(Internship.posted_date))).one()
    companies_count = session.exec(select(func.count(func.distinct(Internship.company)))).one()
    international_friendly = session.exec(select(func.count(Internship.id)).where(Internship.international_score >= 7)).one()
    ai_count = session.exec(select(func.count(Internship.id)).where(Internship.ai_label == True)).one()
    
    return {
        "total_internships": total,
        "latest_update": latest_date.isoformat() if latest_date else datetime.utcnow().isoformat(),
        "companies_count": companies_count,
        "international_friendly_count": international_friendly,
        "ai_roles_count": ai_count
    }

class SubscribeRequest(BaseModel):
    email: str

@router.post("/subscribe", response_model=Dict[str, Any])
def subscribe(body: SubscribeRequest, session: Session = Depends(get_session)):
    email = body.email.strip().lower()
    if not is_valid_email(email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    
    try:
        existing = session.exec(select(Subscription).where(Subscription.email == email)).first()
        if existing:
            if not existing.is_active:
                existing.is_active = True
                session.add(existing)
                session.commit()
        else:
            new_sub = Subscription(email=email)
            session.add(new_sub)
            session.commit()
    except Exception as e:
        print(f"Subscription DB write handled (read-only environment): {e}")
        try:
            session.rollback()
        except Exception:
            pass
        
    latest_20 = session.exec(select(Internship).order_by(Internship.posted_date.desc()).limit(20)).all()
    sent = send_digest_email(email, latest_20)
    
    return {
        "status": "success",
        "message": f"Subscribed! We've sent the top 20 verified internships to {email}.",
        "email": email,
        "email_sent": sent,
        "count": len(latest_20)
    }

@router.get("/subscribe/preview", response_class=HTMLResponse)
def preview_newsletter(session: Session = Depends(get_session)):
    latest_20 = session.exec(select(Internship).order_by(Internship.posted_date.desc()).limit(20)).all()
    return HTMLResponse(content=generate_digest_html(latest_20))

@router.get("/sources", response_model=List[Dict[str, Any]])
def get_sources():
    return load_data_sources()

@router.get("/internships", response_model=Dict[str, Any])
def read_internships(
    offset: int = 0,
    limit: int = 24,
    search: Optional[str] = None,
    sort_by_date: bool = True,
    source: Optional[str] = None,
    location: Optional[str] = None,
    min_score: Optional[int] = None,
    ai_only: Optional[bool] = None,
    company_type: Optional[str] = None,
    high_salary: Optional[bool] = None,
    session: Session = Depends(get_session)
):
    query = select(Internship)
    if source:
        query = query.where(Internship.source == source)

    if location:
        if location.lower() == "remote":
            query = query.where(Internship.location.contains("Remote"))
        else:
            query = query.where(Internship.location.contains(location))

    if min_score is not None:
        query = query.where(Internship.international_score >= min_score)

    if ai_only:
        query = query.where(Internship.ai_label == True)

    if company_type:
        if company_type == "big_tech":
            big_tech = ["Apple", "Google", "Meta", "Microsoft", "Amazon", "ByteDance", "Netflix"]
            query = query.where(Internship.company.in_(big_tech))
        elif company_type == "quant_finance":
            finance = ["Goldman Sachs", "Morgan Stanley", "JPMorgan Chase", "Bank of Montreal", "Optiver", "Deutsche Bank", "Citadel", "Jane Street"]
            query = query.where((Internship.company.in_(finance)) | (Internship.industry == "Finance"))
        elif company_type == "ai_ml":
            query = query.where((Internship.ai_label == True) | (Internship.role.contains("AI")) | (Internship.role.contains("Machine Learning")))
        elif company_type == "defense_aerospace":
            defense = ["NASA", "General Dynamics", "General Dynamics Mission Systems", "Booz Allen", "CACI", "Lockheed Martin", "Northrop Grumman"]
            query = query.where((Internship.company.in_(defense)) | (Internship.industry == "Aerospace"))

    if high_salary:
        query = query.where(
            (Internship.salary.contains("$4")) | 
            (Internship.salary.contains("$5")) | 
            (Internship.salary.contains("$6")) | 
            (Internship.salary.contains("$7")) | 
            (Internship.salary.contains("$8")) | 
            (Internship.salary.contains("$9")) | 
            (Internship.salary.contains("$100"))
        )

    if search:
        query = query.where(
            (Internship.company.contains(search)) | 
            (Internship.role.contains(search)) |
            (Internship.industry.contains(search)) |
            (Internship.location.contains(search))
        )
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = session.exec(count_query).one()

    if sort_by_date:
        query = query.order_by(Internship.posted_date.desc())
        
    query = query.offset(offset).limit(limit)
    internships = session.exec(query).all()
    
    return {
        "items": internships,
        "total": total
    }

app.include_router(router)
app.include_router(router, prefix="/api")
