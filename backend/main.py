import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Header, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import create_engine, String, Text, Integer, DateTime, select, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://nawar:nawar@postgres:5432/nawarjob")
ADMIN_KEY = os.getenv("ADMIN_KEY", "").strip()

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(160))
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
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

# Compatibility migration for databases created before email became optional.
if engine.dialect.name == "postgresql":
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE leads ALTER COLUMN email DROP NOT NULL"))

app = FastAPI(title="Venture Studio API")
app.mount("/static", StaticFiles(directory="/app/static"), name="static")


class LeadCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: Optional[EmailStr] = None
    phone: str = Field(min_length=4, max_length=100)
    country: str = Field(default="Not provided", min_length=2, max_length=160)
    starting_point: str = Field(min_length=2, max_length=180)
    background: str = Field(default="Not provided", min_length=2)
    available_time: str = Field(default="Not decided yet", min_length=2, max_length=120)
    budget: str = Field(min_length=2, max_length=120)
    timeline: str = Field(default="Later / exploring", min_length=2, max_length=120)
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

    # The public form currently asks for budget, project stage and project details.
    # Score only what the visitor actually provides instead of hidden legacy fields.
    budget_points = {
        "Under $2,000": 8,
        "$2,000–$10,000": 18,
        "$10,000–$50,000": 30,
        "$50,000–$150,000": 40,
        "$150,000+": 50,
        "Not decided yet": 8,
    }
    starting_point_points = {
        "I need a business idea": 12,
        "I already have an idea": 15,
        "I want to improve an existing business": 15,
        "I am not sure yet": 5,
    }

    score += budget_points.get(data.budget, 0)
    score += starting_point_points.get(data.starting_point, 0)

    goal_length = len(data.goal.strip())
    if goal_length >= 120:
        score += 8
    elif goal_length >= 40:
        score += 4

    return score, "High" if score >= 55 else "Medium" if score >= 30 else "Low"


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
        stmt = stmt.where(
            (Lead.name.ilike(like))
            | (Lead.email.ilike(like))
            | (Lead.phone.ilike(like))
            | (Lead.country.ilike(like))
        )

    leads = session.scalars(stmt).all()
    return [
        {
            "id": lead.id,
            "created_at": lead.created_at.isoformat(),
            "name": lead.name,
            "email": lead.email,
            "phone": lead.phone,
            "country": lead.country,
            "starting_point": lead.starting_point,
            "background": lead.background,
            "available_time": lead.available_time,
            "budget": lead.budget,
            "timeline": lead.timeline,
            "model": lead.model,
            "risk_preference": lead.risk_preference,
            "goal": lead.goal,
            "score": lead.score,
            "priority": lead.priority,
            "status": lead.status,
            "notes": lead.notes,
            "source": lead.source,
            "utm_source": lead.utm_source,
            "utm_medium": lead.utm_medium,
            "utm_campaign": lead.utm_campaign,
            "referrer": lead.referrer,
        }
        for lead in leads
    ]


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
