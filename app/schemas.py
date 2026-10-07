from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, EmailStr, ConfigDict, field_validator

from app.models import JobStatus, CertificateStatus


class RecipientIn(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    extra_text: Optional[str] = None  # e.g. course name, date, score - shown under the name

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v):
        if v is not None and not v.strip():
            return None
        return v


class JobCreateRequest(BaseModel):
    title: str
    recipients: List[RecipientIn]


class JobCreateResponse(BaseModel):
    job_id: str
    status: JobStatus
    total: int


class JobStatusResponse(BaseModel):
    job_id: str
    title: str
    status: JobStatus
    total: int
    completed: int
    failed: int
    pending: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CertificateOut(BaseModel):
    id: str
    recipient_name: Optional[str]
    recipient_email: Optional[str]
    status: CertificateStatus
    error_message: Optional[str]
    download_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
