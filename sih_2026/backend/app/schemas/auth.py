from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserRegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Full name or organization name")
    email: EmailStr = Field(..., description="Valid user email address")
    password: str = Field(..., min_length=8, max_length=128, description="Password (at least 8 characters)")
    role: str = Field(default="citizen", description="Role: citizen, student, researcher, university, company, ngo, expert, authority, admin")
    bio: str = Field(default="", max_length=2000)
    location: str = Field(default="", max_length=255)
    skills: list[str] = Field(default_factory=list)


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    display_name: str
    bio: str = ""
    skills: list[Any] = []
    expertise: list[Any] = []
    technologies: list[Any] = []
    resources: list[Any] = []
    projects: list[Any] = []
    interests: list[Any] = []
    location_text: str = ""


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    profile: ProfileResponse | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class ProblemCreateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str = Field(..., min_length=10, max_length=20000)
    category: str | None = Field(default=None, max_length=120)
    location_text: str | None = Field(default=None, max_length=255)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("description")
    @classmethod
    def description_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("description must not be empty")
        return stripped


class ProblemAnalysis(BaseModel):
    summary: str = Field(..., min_length=1, max_length=1000)
    severity: Literal["High", "Medium", "Low"]
    urgency: Literal["Immediate", "Soon", "Planned"]
    required_skills: list[str] = Field(default_factory=list, min_length=1)
    required_expertise: list[str] = Field(default_factory=list)
    required_resources: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class MatchResponse(BaseModel):
    candidate_id: str
    name: str
    role: str
    organization: str
    matching_skills: list[str]
    score: float
    explanation: str
    location: str | None = None
    availability: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    organization_type: str | None = None
    skills: list[Any] = Field(default_factory=list)
    expertise: list[Any] = Field(default_factory=list)
    resources: list[Any] = Field(default_factory=list)
    technologies: list[Any] = Field(default_factory=list)


class CollaboratorProfileResponse(BaseModel):
    candidate_id: str
    name: str
    role: str
    email: EmailStr | None = None
    phone: str | None = None
    organization: str | None = None
    organization_type: str | None = None
    location: str | None = None
    skills: list[Any] = Field(default_factory=list)
    expertise: list[Any] = Field(default_factory=list)
    resources: list[Any] = Field(default_factory=list)
    technologies: list[Any] = Field(default_factory=list)


class CollaborationCreateRequest(BaseModel):
    problem_id: str
    recipient_id: str
    message: str = Field(default="", max_length=2000)


class CollaborationStatusUpdate(BaseModel):
    status: Literal["accepted", "rejected"]


class CollaborationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    problem_id: str
    requester_id: str
    recipient_id: str
    status: Literal["pending", "accepted", "rejected", "cancelled"]
    message: str
    created_at: datetime
    updated_at: datetime
    collaborator: CollaboratorProfileResponse | None = None


class ProblemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    summary: str = ""
    description: str
    category: str | None = None
    status: str
    report_count: int = 0
    created_at: datetime
    updated_at: datetime
    location_text: str = ""
    latitude: float | None = None
    longitude: float | None = None
    media_url: str | None = None
    media_type: str | None = None
    metadata: dict[str, Any] = {}
    creator_id: str | None = None
    location: dict[str, Any] | None = None
    analysis: ProblemAnalysis | None = None
    matches: list[MatchResponse] = Field(default_factory=list)


class ProblemListResponse(BaseModel):
    items: list[ProblemResponse]
    total: int
    page: int = 1
    page_size: int = 20


class SupportStatusResponse(BaseModel):
    problem_id: str
    support_count: int
    has_supported: bool


class UploadResponse(BaseModel):
    url: str
    filename: str
    media_type: Literal["image", "video"]
    size_bytes: int

