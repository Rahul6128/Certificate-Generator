import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Integer, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_ERRORS = "COMPLETED_WITH_ERRORS"
    FAILED = "FAILED"


class CertificateStatus(str, enum.Enum):
    PENDING = "PENDING"
    GENERATED = "GENERATED"
    FAILED = "FAILED"


class GenerationJob(Base):
    """One bulk certificate-generation request."""

    __tablename__ = "generation_jobs"

    id = Column(String, primary_key=True, default=_uuid)
    title = Column(String, nullable=False)
    status = Column(Enum(JobStatus), nullable=False, default=JobStatus.PENDING)

    total_count = Column(Integer, nullable=False, default=0)
    completed_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    certificates = relationship(
        "CertificateRecord", back_populates="job", cascade="all, delete-orphan"
    )


class CertificateRecord(Base):
    """One recipient's certificate within a job."""

    __tablename__ = "certificate_records"

    id = Column(String, primary_key=True, default=_uuid)
    job_id = Column(String, ForeignKey("generation_jobs.id"), nullable=False, index=True)

    recipient_name = Column(String, nullable=True)
    recipient_email = Column(String, nullable=True)
    extra_text = Column(String, nullable=True)

    status = Column(Enum(CertificateStatus), nullable=False, default=CertificateStatus.PENDING)
    file_path = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    job = relationship("GenerationJob", back_populates="certificates")
