import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Header, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import create_engine, String, Text, Integer, DateTime, select, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://nawar:nawar@postgres:5432/nawarjob")
ADMIN_KEY = os.getenv("ADMIN_KEY", "change-me")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

class Lead(Base):
    __tablename__ = "leads"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(255), index=True)
    phone: Mapped[str] = mapped_column(String(100))
    country: Mapped[str] = mapped_column(String(160))
    starting_point: Mapped[str] = mapped_column(String(180))
    background: Mapped[str] = mapped_column(Text)
    available_time: Mapped[str] = mapped_column(String(120))
    budget: Mapped[str] = mapped_column(String(120), index=True)
    timeline: Mapped[str] = mapped_column(String(120), index=True)
    model: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    risk_preference: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    goal: Mapped[str] = mapped_column(Text)
    source: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    utm_source: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    utm_medium: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    utm_campaign: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    referrer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    priority: Mapped[str] = mapped_column(String(30), default="Low", index=True)
    status: Mapped[str] = mapped_column(String(30), default="New", index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

Base.metadata.create_all(engine)

app = FastAPI(title="Nawar Project Desk")
app.mount("/static", StaticFiles(directory="/app/static"), name="static")

class LeadCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    phone: str = Field(min_length=4, max_length=100)
    country: str = Field(min_length=2, max_length=160)
    starting_point: str
    background: str
    available_time: str
    budget: str
    timeline: str
    model: Optional[str] = None
    risk_preference: Optional[str] = None
    goal: str = Field(min_length=10)
    source: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    referrer: Optional[str] = None

class LeadPatch(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None

ALLOWED_STATUSES = {"New", "Contacted", "Qualified", "Proposal", "Won", "Lost"}

def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def require_admin(x_admin_key: str = Header(default="")):
    if not ADMIN_KEY or x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

def score_lead(data: LeadCreate) -> tuple[int, str]:
    score = 0
    budget_points = {"Under $2,000": 5, "$2,000–$10,000": 15, "$10,000–$50,000": 25, "$50,000–$150,000": 35, "$150,000+": 45, "Not decided yet": 8}
    timeline_points = {"Immediately": 25, "Within 30 days": 20, "Within 3 months": 12, "Within 6 months": 8, "Later / exploring": 2}
    score += budget_points.get(data.budget, 0)
    score += timeline_points.get(data.timeline, 0)
    if data.starting_point in {"I already have an idea", "I want to grow an existing business", "I have capital and want an opportunity"}:
        score += 15
    if data.available_time in {"Full-time", "I want an operator or team to run it"}:
        score += 10
    if len(data.goal.strip()) >= 120:
        score += 5
    return score, "High" if score >= 60 else "Medium" if score >= 35 else "Low"

@app.get("/")
def home():
    return FileResponse("/app/static/index.html")

@app.get("/thanks.html")
def thanks():
    return FileResponse("/app/static/thanks.html")

@app.get("/admin")
def admin():
    return FileResponse("/app/static/admin.html")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/leads", status_code=201)
def create_lead(payload: LeadCreate, session: Session = Depends(db)):
    score, priority = score_lead(payload)
    lead = Lead(**payload.model_dump(), score=score, priority=priority, status="New")
    session.add(lead)
    session.commit()
    session.refresh(lead)
    return {"id": lead.id, "priority": lead.priority, "score": lead.score}

@app.get("/api/admin/stats", dependencies=[Depends(require_admin)])
def stats(session: Session = Depends(db)):
    total = session.scalar(select(func.count(Lead.id))) or 0
    rows = session.execute(select(Lead.status, func.count(Lead.id)).group_by(Lead.status)).all()
    return {"total": total, "by_status": {status: count for status, count in rows}}

@app.get("/api/admin/leads", dependencies=[Depends(require_admin)])
def list_leads(
    status: Optional[str] = Query(default=None),
    priority: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    session: Session = Depends(db),
):
    stmt = select(Lead).order_by(Lead.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(Lead.status == status)
    if priority:
        stmt = stmt.where(Lead.priority == priority)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where((Lead.name.ilike(like)) | (Lead.email.ilike(like)) | (Lead.phone.ilike(like)) | (Lead.country.ilike(like)))
    leads = session.scalars(stmt).all()
    return [{
        "id": l.id, "created_at": l.created_at.isoformat(), "name": l.name, "email": l.email, "phone": l.phone,
        "country": l.country, "starting_point": l.starting_point, "background": l.background, "available_time": l.available_time,
        "budget": l.budget, "timeline": l.timeline, "model": l.model, "risk_preference": l.risk_preference, "goal": l.goal,
        "score": l.score, "priority": l.priority, "status": l.status, "notes": l.notes,
        "source": l.source, "utm_source": l.utm_source, "utm_medium": l.utm_medium, "utm_campaign": l.utm_campaign, "referrer": l.referrer
    } for l in leads]

@app.patch("/api/admin/leads/{lead_id}", dependencies=[Depends(require_admin)])
def update_lead(lead_id: int, payload: LeadPatch, session: Session = Depends(db)):
    lead = session.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if payload.status is not None:
        if payload.status not in ALLOWED_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid status")
        lead.status = payload.status
    if payload.notes is not None:
        lead.notes = payload.notes
    session.commit()
    return {"ok": True, "id": lead.id, "status": lead.status}
