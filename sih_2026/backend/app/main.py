import math
import os
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from contextlib import asynccontextmanager
from sqlalchemy import exc, func, select
from sqlalchemy.orm import Session

from app.db import get_db, init_db
from app.dependencies.auth import (
    get_current_user,
    get_optional_current_user,
    require_roles,
    verify_ownership,
)
from app.models import AIAnalysis, CollaborationRequest, CollaborationStatus, Match, Organization, Problem, ProblemStatus, Profile, Report, Support, User
from app.routers.auth import router as auth_router
from app.schemas.auth import CollaboratorProfileResponse, CollaborationCreateRequest, CollaborationResponse, CollaborationStatusUpdate, MatchResponse, ProblemAnalysis, ProblemCreateRequest, ProblemListResponse, ProblemResponse, SupportStatusResponse, UploadResponse, UserResponse
from app.security import hash_password
from app.services.ai_service import AIService, create_ai_service

# Load root .env
env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(env_path)

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="jansethu API", version="0.2.0", lifespan=lifespan)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")



@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={
            "detail": "Validation error",
            "errors": exc.errors(),
        },
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)

ai_service: AIService = create_ai_service()

PROBLEMS: list[dict[str, Any]] = [
    {
        "id": "flooding-school",
        "title": "School access road floods after heavy rain",
        "description": "During heavy rain, the road outside our school becomes flooded and children cannot safely enter.",
        "place": "Vijayawada, Andhra Pradesh",
        "severity": "High",
        "urgency": "Immediate",
        "reports": 38,
        "status": "Team forming",
        "tags": ["Drainage", "GIS", "Public safety"],
        "progress": 42,
        "created_at": "2026-09-03T08:00:00Z",
        "x": 68,
        "y": 26,
        "analysis": {
            "title": "School access road floods after heavy rain",
            "severity": "High",
            "urgency": "Immediate",
            "needs": ["Drainage analysis", "GIS mapping", "Public safety", "Culvert clearing"],
            "stakeholders": ["School children & parents", "Municipal Corporation", "Local Commuters"],
            "solution_areas": ["Culvert desilting", "Elevation and storm drain expansion", "Community alert sensor"],
            "rationale": "High safety risk for school children during morning hours with complete roadway submersion.",
        },
    },
    {
        "id": "waste-market",
        "title": "Market waste is blocking the evening walkway",
        "description": "Waste piles up beside the market after closing and blocks the walkway.",
        "place": "Indore, Madhya Pradesh",
        "severity": "Medium",
        "urgency": "Soon",
        "reports": 19,
        "status": "Prototype",
        "tags": ["Waste systems", "Civic design", "Public health"],
        "progress": 68,
        "created_at": "2026-08-30T08:00:00Z",
        "x": 40,
        "y": 57,
        "analysis": {
            "title": "Market waste is blocking the evening walkway",
            "severity": "Medium",
            "urgency": "Soon",
            "needs": ["Waste segregation", "Micro-composting", "Civic logistics"],
            "stakeholders": ["Market vendors", "Evening pedestrians", "Sanitation department"],
            "solution_areas": ["Decentralized night collection", "Organic composting drums"],
            "rationale": "High odor and walkway blockage impacting hundreds of daily pedestrians.",
        },
    },
    {
        "id": "water-tank",
        "title": "Community water tank needs a reliable level signal",
        "description": "The overhead water tank runs dry unexpectedly because there is no automated level display for residents.",
        "place": "Nashik, Maharashtra",
        "severity": "Medium",
        "urgency": "Soon",
        "reports": 12,
        "status": "New report",
        "tags": ["IoT sensors", "Water access", "Community tech"],
        "progress": 18,
        "created_at": "2026-09-01T10:00:00Z",
        "x": 78,
        "y": 72,
        "analysis": {
            "title": "Community water tank needs a reliable level signal",
            "severity": "Medium",
            "urgency": "Soon",
            "needs": ["Ultrasonic sensors", "LoRa telemetry", "Solar battery"],
            "stakeholders": ["Housing society residents", "Water valve operator"],
            "solution_areas": ["Low-cost wireless tank sensor", "Display board at entrance"],
            "rationale": "Prevents daily dry-tap scenarios and reduces pump motor burnout.",
        },
    },
]

COLLABORATIONS: list[dict[str, Any]] = [
    {
        "id": "collab-1",
        "problem_id": "flooding-school",
        "title": "School Road Drainage & Flood Prevention Project",
        "location": "Vijayawada, Andhra Pradesh",
        "status": "Active",
        "stage": "Prototype Design",
        "progress": 42,
        "partners": [
            {"name": "Riverline University", "type": "University", "role": "Hydrology & Catchment Study"},
            {"name": "Delta Infra Systems", "type": "Industry partner", "role": "Excavation & Culvert Materials"},
            {"name": "CivicStack Student Lab", "type": "Student team", "role": "IoT Early Warning Sensor"},
        ],
        "milestones": [
            {"title": "Initial topographic and drainage survey", "completed": True},
            {"title": "Hydraulic discharge calculations", "completed": True},
            {"title": "Prototype drainage diversion design", "completed": False, "due": "Sep 15, 2026"},
            {"title": "Municipal permissions & trial installation", "completed": False, "due": "Oct 05, 2026"},
        ],
        "tasks": [
            {"title": "Install temporary rainfall logger", "status": "Done"},
            {"title": "Draft culvert modification blueprint", "status": "In progress"},
            {"title": "Submit proposal to Vijayawada Works Cell", "status": "Pending"},
        ],
    },
    {
        "id": "collab-2",
        "problem_id": "waste-market",
        "title": "Decentralized Night Market Composting Initiative",
        "location": "Indore, Madhya Pradesh",
        "status": "Active",
        "stage": "Pilot Testing",
        "progress": 68,
        "partners": [
            {"name": "Center for Urban Waste Circularity", "type": "University", "role": "Microbial Inoculant Design"},
            {"name": "CleanCity Biowaste Systems", "type": "Industry partner", "role": "200L Composter Drums"},
        ],
        "milestones": [
            {"title": "Vendor waste volume audit", "completed": True},
            {"title": "Install two rotary composting drums", "completed": True},
            {"title": "Vendor training on source segregation", "completed": True},
            {"title": "Quality testing of first compost batch", "completed": False, "due": "Sep 12, 2026"},
        ],
        "tasks": [
            {"title": "Daily temperature log of compost drum #1", "status": "In progress"},
            {"title": "Distribute color-coded crates to 40 vendors", "status": "Done"},
        ],
    },
    {
        "id": "collab-3",
        "problem_id": "water-tank",
        "title": "Solar IoT Community Water Tank Signal",
        "location": "Nashik, Maharashtra",
        "status": "Planning",
        "stage": "Team Formation",
        "progress": 18,
        "partners": [
            {"name": "Polytechnic Embedded Electronics Club", "type": "Student team", "role": "ESP32 Sensor Build"},
            {"name": "Apex Sensors", "type": "Industry partner", "role": "Component Sourcing"},
        ],
        "milestones": [
            {"title": "Tank physical inspection & signal test", "completed": True},
            {"title": "Circuit breadboard validation", "completed": False, "due": "Sep 20, 2026"},
            {"title": "Enclosure weatherproofing & deployment", "completed": False, "due": "Sep 30, 2026"},
        ],
        "tasks": [
            {"title": "Bench-test ultrasonic sensor with water", "status": "In progress"},
            {"title": "Set up community Telegram/SMS alert webhook", "status": "Todo"},
        ],
    },
]


class SupportRequest(BaseModel):
    user_id: str = "anonymous"


class ChatRequest(BaseModel):
    message: str


class SettingsUpdate(BaseModel):
    api_key: str
    model: str = "gemini-3.6-flash"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "jansethu-api"}


@app.get("/api/v1/settings")
async def get_settings() -> dict[str, Any]:
    global ai_service
    test_result = await ai_service.test_connection()
    key = os.getenv("AI_API_KEY", "").strip()
    masked_key = f"{key[:6]}...{key[-4:]}" if len(key) > 10 else ("Configured" if key else "")
    return {
        "has_api_key": bool(key),
        "masked_key": masked_key,
        "model": os.getenv("AI_MODEL", "gemini-3.6-flash"),
        "provider": "gemini" if key else "demo",
        "connection_status": test_result.get("status", "unknown"),
        "details": test_result,
    }


@app.post("/api/v1/settings")
async def update_settings(payload: SettingsUpdate) -> dict[str, Any]:
    global ai_service
    key = payload.api_key.strip()
    model = payload.model.strip() or "gemini-3.6-flash"

    # Write to root .env
    env_file = Path(__file__).resolve().parents[2] / ".env"
    os.environ["AI_API_KEY"] = key
    os.environ["AI_MODEL"] = model

    with open(env_file, "w", encoding="utf-8") as f:
        f.write(f"AI_API_KEY={key}\nAI_PROVIDER=gemini\nAI_MODEL={model}\nDATABASE_URL=sqlite:///./jansethu.db\nFRONTEND_URL=http://localhost:3000\nNEXT_PUBLIC_API_URL=http://localhost:8000/api/v1\n")

    ai_service = create_ai_service(key, model)
    test_result = await ai_service.test_connection()
    return {"success": True, "connection_status": test_result.get("status"), "details": test_result}


def _profile_match_data(db: Session, problem: Problem, limit: int = 3) -> list[dict[str, Any]]:
    analysis_record = db.scalar(
        select(AIAnalysis)
        .where(AIAnalysis.problem_id == problem.id)
        .order_by(AIAnalysis.created_at.desc())
    )
    analysis = analysis_record.data if analysis_record else None
    if not analysis:
        return []

    def tokens(value: str) -> set[str]:
        normalized = value.lower().replace("/", " ").replace("-", " ").replace(",", " ")
        return {part for part in normalized.split() if len(part) > 2}

    required_groups = {
        "skills": [str(item) for item in analysis.get("required_skills", [])],
        "expertise": [str(item) for item in analysis.get("required_expertise", [])],
        "resources": [str(item) for item in analysis.get("required_resources", [])],
        "tags": [str(item) for item in analysis.get("tags", [])],
    }
    weights = {"skills": 0.45, "expertise": 0.3, "resources": 0.15, "tags": 0.1}

    def overlap(required: list[str], available: list[str]) -> tuple[set[str], float]:
        required_tokens = {token for item in required for token in tokens(item)}
        available_tokens = {token for item in available for token in tokens(item)}
        matched_tokens = required_tokens & available_tokens
        return matched_tokens, len(matched_tokens) / max(len(required_tokens), 1)

    candidates = db.execute(
        select(Profile, User, Organization)
        .join(User, User.id == Profile.user_id)
        .outerjoin(Organization, Organization.profile_id == Profile.id)
        .where(Profile.user_id != problem.creator_id)
    ).all()
    matches: list[dict[str, Any]] = []
    for profile, user, organization in candidates:
        profile_items = [
            *(profile.skills or []),
            *(profile.expertise or []),
            *(profile.technologies or []),
            *(profile.resources or []),
        ]
        profile_groups = {
            "skills": [*(profile.skills or []), *(profile.technologies or [])],
            "expertise": profile.expertise or [],
            "resources": profile.resources or [],
            "tags": [*(profile.skills or []), *(profile.expertise or []), *(profile.interests or [])],
        }
        group_matches: dict[str, set[str]] = {}
        group_scores: dict[str, float] = {}
        for group, required in required_groups.items():
            group_matches[group], group_scores[group] = overlap(required, profile_groups[group])

        weighted_score = sum(weights[group] * group_scores[group] for group in weights)
        matched_tokens = set().union(*group_matches.values())
        if weighted_score == 0:
            continue
        location_bonus = 5 if tokens(problem.location_text or "") & tokens(profile.location_text or "") else 0
        score = round(min(100, weighted_score * 100 + location_bonus), 1)
        matching_skills = list(dict.fromkeys(
            str(item)
            for item in profile_items
            if tokens(str(item)) & matched_tokens
        ))
        organization_name = organization.name if organization else profile.display_name
        matches.append(
            {
                "candidate_id": user.id,
                "name": profile.display_name,
                "role": user.role,
                "organization": organization_name,
                "matching_skills": matching_skills,
                "score": score,
                "explanation": f"Matches {', '.join(matching_skills[:3])} across the AI-identified skills, expertise, and resources.",
                "location": profile.location_text or None,
                "availability": None,
                "email": user.email,
                "phone": None,
                "organization_type": organization.organization_type if organization else None,
                "skills": profile.skills or [],
                "expertise": profile.expertise or [],
                "resources": profile.resources or [],
                "technologies": profile.technologies or [],
                "profile_id": profile.id,
            }
        )

    matches.sort(key=lambda item: item["score"], reverse=True)
    return matches[:limit]


def _ensure_development_profiles(db: Session) -> None:
    seed_profiles = [
        ("Aarav Mehta", "student", "seed.student@solvebridge.dev", "CivicTech Student Lab", "student", ["GIS mapping", "Community survey", "IoT sensors"], ["Rapid prototyping"], ["Field survey equipment"]),
        ("Dr. Meera Iyer", "researcher", "seed.researcher@solvebridge.dev", "Institute for Urban Water Research", "university", ["Hydrological modeling", "Water quality", "Data analysis"], ["Urban hydrology", "Climate resilience"], ["Water testing equipment"]),
        ("Nikhil Rao", "expert", "seed.expert@solvebridge.dev", "Rao Infrastructure Advisory", "company", ["Road engineering", "Safety audit", "Project planning"], ["Public infrastructure", "Risk assessment"], ["Civil inspection tools"]),
        ("Prof. Kavya Sen", "university", "seed.university@solvebridge.dev", "National University Civic Design Centre", "university", ["Civic design", "Waste systems", "Service design"], ["Circular economy", "Public systems"], ["Materials lab", "Design studio"]),
        ("GreenStep Foundation", "ngo", "seed.ngo@solvebridge.dev", "GreenStep Foundation", "ngo", ["Community mobilization", "Sanitation", "Field research"], ["Community health", "Environmental justice"], ["Volunteer network"]),
        ("Maya Industries CSR Team", "company", "seed.company@solvebridge.dev", "Maya Industries", "company", ["Solar power", "Sensor deployment", "Fabrication"], ["CSR implementation", "Manufacturing"], ["Fabrication workshop", "CSR funding"]),
        ("Ward 18 Engineering Cell", "authority", "seed.authority@solvebridge.dev", "Ward 18 Municipal Authority", "authority", ["Public works", "Drainage maintenance", "Local permits"], ["Municipal governance", "Emergency response"], ["Ward equipment", "Implementation authority"]),
        ("Ishaan Verma", "expert", "seed.ai@solvebridge.dev", "Open Civic AI Collective", "company", ["Machine learning", "Data engineering", "Software development"], ["Artificial intelligence", "Civic technology"], ["Cloud computing", "AI lab"]),
        ("Anika Thomas", "expert", "seed.electrical@solvebridge.dev", "Thomas Electrical Systems", "company", ["Electrical engineering", "Power systems", "Embedded systems"], ["Energy management", "Electronics"], ["Electrical testing equipment"]),
        ("Dr. Rohan Kapoor", "expert", "seed.healthcare@solvebridge.dev", "Community Health Research Unit", "university", ["Public health", "Healthcare delivery", "Health data analysis"], ["Epidemiology", "Rural healthcare"], ["Mobile clinic", "Health survey tools"]),
    ]
    for name, role, email, organization_name, organization_type, skills, expertise, resources in seed_profiles:
        if db.scalar(select(User).where(User.email == email)):
            continue
        user = User(email=email, password_hash=hash_password("Development123!"), role=role, is_active=True)
        db.add(user)
        db.flush()
        profile = Profile(
            user_id=user.id,
            display_name=name,
            bio=f"Development profile for {organization_name}.",
            skills=skills,
            expertise=expertise,
            resources=resources,
            technologies=[],
            projects=[],
            interests=[],
            location_text="India",
        )
        db.add(profile)
        db.flush()
        db.add(Organization(profile_id=profile.id, name=organization_name, organization_type=organization_type))
    db.commit()


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0  # Earth radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def _serialize_problem(problem: Problem, db: Session, user_lat: float | None = None, user_lng: float | None = None) -> dict[str, Any]:
    analysis_record = db.scalar(
        select(AIAnalysis)
        .where(AIAnalysis.problem_id == problem.id)
        .order_by(AIAnalysis.created_at.desc())
    )
    analysis = analysis_record.data if analysis_record else None
    matches = _profile_match_data(db, problem)
    meta = dict(problem.metadata_json or {})
    media_url = meta.get("media_url")
    media_type = meta.get("media_type")

    distance_km = None
    if user_lat is not None and user_lng is not None and problem.latitude is not None and problem.longitude is not None:
        distance_km = round(haversine_distance(user_lat, user_lng, problem.latitude, problem.longitude), 2)
        meta["distance_km"] = distance_km

    return {
        "id": problem.id,
        "title": problem.title,
        "summary": problem.summary,
        "description": problem.description,
        "category": problem.category,
        "status": problem.status,
        "report_count": problem.report_count or 0,
        "created_at": problem.created_at.isoformat() if problem.created_at else None,
        "updated_at": problem.updated_at.isoformat() if problem.updated_at else None,
        "location_text": problem.location_text,
        "latitude": problem.latitude,
        "longitude": problem.longitude,
        "media_url": media_url,
        "media_type": media_type,
        "metadata": meta,
        "creator_id": problem.creator_id,
        "analysis": analysis,
        "matches": [MatchResponse.model_validate(item).model_dump() for item in matches],
        "location": {
            "latitude": problem.latitude,
            "longitude": problem.longitude,
            "address": problem.location_text,
            "location_text": problem.location_text,
            "distance_km": distance_km,
        }
        if problem.latitude is not None and problem.longitude is not None
        else None,
    }


@app.get("/api/v1/problems", response_model=ProblemListResponse)
def list_problems(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    latitude: float | None = Query(None),
    longitude: float | None = Query(None),
    radius_km: float | None = Query(None),
    category: str | None = Query(None),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    stmt = select(Problem)
    if category:
        stmt = stmt.where(Problem.category == category)
    items = list(db.scalars(stmt.order_by(Problem.created_at.desc())).all())

    if latitude is not None and longitude is not None:
        def calc_dist(p: Problem):
            if p.latitude is not None and p.longitude is not None:
                return haversine_distance(latitude, longitude, p.latitude, p.longitude)
            return float("inf")

        if radius_km is not None:
            items = [p for p in items if calc_dist(p) <= radius_km]
        items.sort(key=calc_dist)

    total = len(items)
    paginated_items = items[(page - 1) * page_size : page * page_size]
    return {
        "items": [_serialize_problem(item, db, user_lat=latitude, user_lng=longitude) for item in paginated_items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@app.post("/api/v1/chat")
async def chat(request: ChatRequest) -> dict[str, str]:
    if not request.message.strip():
        return {"reply": "Tell me what you would like help with."}
    return {"reply": await ai_service.chat(request.message.strip())}


@app.get("/api/v1/problems/me", response_model=ProblemListResponse)
def get_my_problems(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    query = select(Problem).where(Problem.creator_id == current_user.id).order_by(Problem.created_at.desc())
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    items = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    return {
        "items": [_serialize_problem(item, db) for item in items],
        "total": total or 0,
        "page": page,
        "page_size": page_size,
    }


@app.get("/api/v1/problems/{problem_id}", response_model=ProblemResponse)
def get_problem(problem_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    problem = db.get(Problem, problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    return _serialize_problem(problem, db)


def _estimate_coordinates(location: str) -> tuple[int, int]:
    loc = location.lower()
    if "vijayawada" in loc or "andhra" in loc:
        return 68 + random.randint(-4, 4), 26 + random.randint(-3, 3)
    if "indore" in loc or "madhya" in loc:
        return 40 + random.randint(-4, 4), 57 + random.randint(-3, 3)
    if "nashik" in loc or "maharashtra" in loc or "mumbai" in loc or "pune" in loc:
        return 76 + random.randint(-4, 4), 70 + random.randint(-3, 3)
    if "hyderabad" in loc or "telangana" in loc:
        return 58 + random.randint(-4, 4), 48 + random.randint(-3, 3)
    if "delhi" in loc or "ncr" in loc:
        return 34 + random.randint(-4, 4), 20 + random.randint(-3, 3)
    if "bengaluru" in loc or "bangalore" in loc or "karnataka" in loc:
        return 52 + random.randint(-4, 4), 82 + random.randint(-3, 3)
    if "chennai" in loc or "tamil" in loc:
        return 64 + random.randint(-4, 4), 86 + random.randint(-3, 3)
    return random.randint(25, 80), random.randint(25, 80)


class ProblemUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None


ALLOWED_EXTENSIONS = {
    "image": {".jpg", ".jpeg", ".png", ".webp", ".gif"},
    "video": {".mp4", ".webm", ".mov", ".avi", ".mkv"},
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


@app.post("/api/v1/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
) -> dict[str, Any]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required.")
    ext = Path(file.filename).suffix.lower()
    media_type: Literal["image", "video"]
    if ext in ALLOWED_EXTENSIONS["image"]:
        media_type = "image"
    elif ext in ALLOWED_EXTENSIONS["video"]:
        media_type = "video"
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Allowed: images (jpg, png, webp, gif) and videos (mp4, webm, mov).",
        )
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 50MB.")
    unique_name = f"{uuid4().hex}{ext}"
    dest = UPLOAD_DIR / unique_name
    dest.write_bytes(contents)
    return {
        "url": f"/uploads/{unique_name}",
        "filename": unique_name,
        "media_type": media_type,
        "size_bytes": len(contents),
    }


@app.post("/api/v1/problems", response_model=ProblemResponse, status_code=201)
async def create_problem(
    payload: ProblemCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    title = (payload.title or payload.description.strip()[:80]).strip()
    if not title:
        raise HTTPException(status_code=400, detail="Problem title or description is required")

    meta = dict(payload.metadata or {})
    image_name = meta.get("media_url") or None

    try:
        analysis_data = await ai_service.analyze_problem(
            title=title,
            description=payload.description.strip(),
            location=payload.location_text.strip() if payload.location_text else "",
            image_name=image_name,
        )
    except TypeError as exc:
        if "unexpected keyword" not in str(exc):
            raise
        analysis_data = await ai_service.analyze_problem(payload.description.strip())
    analysis = ProblemAnalysis.model_validate(analysis_data)
    problem = Problem(
        title=title,
        summary=analysis.summary,
        description=payload.description.strip(),
        category=(payload.category.strip() if payload.category else (analysis.tags[0] if analysis.tags else None)),
        status=ProblemStatus.REPORTED.value,
        report_count=1,
        location_text=(payload.location_text.strip() if payload.location_text else ""),
        latitude=payload.latitude,
        longitude=payload.longitude,
        metadata_json=meta,
        creator_id=current_user.id,
    )
    db.add(problem)
    db.flush()

    report = Report(
        problem_id=problem.id,
        reporter_id=current_user.id,
        description=payload.description.strip(),
        evidence_path=meta.get("media_url"),
        evidence_type=meta.get("media_type"),
    )
    db.add(report)

    db.add(AIAnalysis(
        problem_id=problem.id,
        model=os.getenv("AI_MODEL", "local_heuristics"),
        version="phase4",
        data=analysis.model_dump(),
    ))
    _ensure_development_profiles(db)
    db.flush()
    for match in _profile_match_data(db, problem):
        db.add(Match(
            problem_id=problem.id,
            profile_id=match["profile_id"],
            score=match["score"],
            explanation=match["explanation"],
        ))
    db.commit()
    db.refresh(problem)
    return _serialize_problem(problem, db)


@app.put("/api/v1/problems/{problem_id}")
async def update_problem(
    problem_id: str,
    payload: ProblemUpdateRequest,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    problem = next((p for p in PROBLEMS if p["id"] == problem_id), None)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    # Enforce ownership: only creator or admin can update
    verify_ownership(problem.get("creator_id"), current_user)

    if payload.title:
        problem["title"] = payload.title
    if payload.description:
        problem["description"] = payload.description
    if payload.status:
        problem["status"] = payload.status

    return problem


@app.delete("/api/v1/problems/{problem_id}")
async def delete_problem(
    problem_id: str,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    problem = next((p for p in PROBLEMS if p["id"] == problem_id), None)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    # Enforce ownership: only creator or admin can delete
    verify_ownership(problem.get("creator_id"), current_user)

    PROBLEMS.remove(problem)
    return {"status": "deleted", "id": problem_id}


@app.get("/api/v1/admin/users", response_model=list[UserResponse])
def admin_list_users(
    admin_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> list[User]:
    return list(db.scalars(select(User)).all())


@app.post("/api/v1/problems/{problem_id}/support", response_model=SupportStatusResponse, status_code=201)
def support_problem(
    problem_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    problem = db.get(Problem, problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    existing_support = db.scalar(
        select(Support).where(Support.problem_id == problem_id, Support.user_id == current_user.id)
    )
    if existing_support:
        raise HTTPException(status_code=409, detail="You have already supported this problem")

    support = Support(problem_id=problem_id, user_id=current_user.id)
    db.add(support)
    problem.report_count = (problem.report_count or 0) + 1
    db.commit()

    support_count = db.scalar(select(func.count()).select_from(Support).where(Support.problem_id == problem_id)) or 0
    return {
        "problem_id": problem_id,
        "support_count": int(support_count),
        "has_supported": True,
    }


@app.get("/api/v1/problems/{problem_id}/support", response_model=SupportStatusResponse)
def get_problem_support(
    problem_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    problem = db.get(Problem, problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    support_count = db.scalar(select(func.count()).select_from(Support).where(Support.problem_id == problem_id)) or 0
    has_supported = bool(
        db.scalar(select(Support.id).where(Support.problem_id == problem_id, Support.user_id == current_user.id))
    )
    return {
        "problem_id": problem_id,
        "support_count": int(support_count),
        "has_supported": has_supported,
    }


@app.get("/api/v1/problems/{problem_id}/matches")
def get_matches(problem_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    problem = db.get(Problem, problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    matches = [MatchResponse.model_validate(item).model_dump() for item in _profile_match_data(db, problem)]
    return {"problem_id": problem_id, "matches": matches}


def _collaborator_details(db: Session, user_id: str) -> dict[str, Any] | None:
    result = db.execute(
        select(Profile, User, Organization)
        .join(User, User.id == Profile.user_id)
        .outerjoin(Organization, Organization.profile_id == Profile.id)
        .where(User.id == user_id, User.is_active.is_(True))
    ).first()
    if not result:
        return None
    profile, user, organization = result
    return CollaboratorProfileResponse(
        candidate_id=user.id,
        name=profile.display_name,
        role=user.role,
        email=user.email,
        phone=None,
        organization=organization.name if organization else None,
        organization_type=organization.organization_type if organization else None,
        location=profile.location_text or None,
        skills=profile.skills or [],
        expertise=profile.expertise or [],
        resources=profile.resources or [],
        technologies=profile.technologies or [],
    ).model_dump()


def _serialize_collaboration(request: CollaborationRequest, db: Session) -> dict[str, Any]:
    response = CollaborationResponse.model_validate(request).model_dump()
    response["collaborator"] = _collaborator_details(db, request.recipient_id)
    return response


@app.post("/api/v1/collaborations", response_model=CollaborationResponse, status_code=201)
def create_collaboration(
    payload: CollaborationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    problem = db.get(Problem, payload.problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    recipient = db.get(User, payload.recipient_id)
    if not recipient or not recipient.is_active:
        raise HTTPException(status_code=404, detail="Recipient not found")
    if recipient.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot collaborate with yourself")

    matched_candidate_ids = {match["candidate_id"] for match in _profile_match_data(db, problem, limit=100)}
    if recipient.id not in matched_candidate_ids:
        raise HTTPException(status_code=400, detail="Recipient is not a current match for this problem")

    duplicate = db.scalar(
        select(CollaborationRequest).where(
            CollaborationRequest.problem_id == problem.id,
            CollaborationRequest.requester_id == current_user.id,
            CollaborationRequest.recipient_id == recipient.id,
            CollaborationRequest.status == CollaborationStatus.PENDING.value,
        )
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="A pending collaboration request already exists")

    request = CollaborationRequest(
        problem_id=problem.id,
        requester_id=current_user.id,
        recipient_id=recipient.id,
        status=CollaborationStatus.PENDING.value,
        message=payload.message.strip(),
    )
    db.add(request)
    try:
        db.commit()
    except exc.IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A pending collaboration request already exists")
    db.refresh(request)
    return _serialize_collaboration(request, db)


@app.get("/api/v1/collaborations", response_model=list[CollaborationResponse])
def list_collaborations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    requests = db.scalars(
        select(CollaborationRequest)
        .where(
            (CollaborationRequest.requester_id == current_user.id)
            | (CollaborationRequest.recipient_id == current_user.id)
        )
        .order_by(CollaborationRequest.created_at.desc())
    ).all()
    return [_serialize_collaboration(request, db) for request in requests]


@app.patch("/api/v1/collaborations/{request_id}", response_model=CollaborationResponse)
def update_collaboration(
    request_id: str,
    payload: CollaborationStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    request = db.get(CollaborationRequest, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Collaboration request not found")
    if request.recipient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the recipient can update this request")
    if request.status != CollaborationStatus.PENDING.value:
        raise HTTPException(status_code=409, detail="Only pending requests can be updated")

    request.status = payload.status
    request.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(request)
    return _serialize_collaboration(request, db)


@app.delete("/api/v1/collaborations/{request_id}", status_code=204)
def delete_collaboration(
    request_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    request = db.get(CollaborationRequest, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Collaboration request not found")
    if request.requester_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the requester can delete this request")
    if request.status != CollaborationStatus.PENDING.value:
        raise HTTPException(status_code=409, detail="Only pending requests can be deleted")

    db.delete(request)
    db.commit()


@app.get("/api/v1/impact")
def impact() -> dict[str, Any]:
    total_reports = sum(p.get("reports", 1) for p in PROBLEMS)
    return {
        "people_reached": 1284 + total_reports * 15,
        "problems_solved": 12,
        "locations_improved": 8,
        "average_improvement": 72,
        "active_projects": len(COLLABORATIONS),
        "total_problems": len(PROBLEMS),
    }