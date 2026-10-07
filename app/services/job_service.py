"""Core business logic: create jobs, process them, report status.

Design note on sync vs async processing:
Generating one certificate (open template, draw text, save PNG) takes maybe
10-30ms, but a "bulk" request could be a few hundred or a few thousand
recipients. Doing that inline would make the client wait on a single HTTP
request for a long time and risks hitting a request timeout for large jobs.

So: the job row is created and recipients are saved as PENDING certificate
records immediately (fast, the client gets a job_id back right away), and
the actual generation runs afterwards via FastAPI's BackgroundTasks. The
client polls GET /jobs/{id} to see progress.

This is good enough for the scope here. For a "real" production system with
much bigger volumes I'd move this to a proper task queue (Celery/RQ with
Redis) so jobs survive a server restart and can be retried/distributed
across workers - BackgroundTasks run in-process and are lost if the server
crashes mid-job.
"""
from sqlalchemy.orm import Session

from app.models import GenerationJob, CertificateRecord, JobStatus, CertificateStatus
from app.schemas import JobCreateRequest
from app.services.certificate_service import generate_certificate, CertificateGenerationError


def create_job(db: Session, payload: JobCreateRequest) -> GenerationJob:
    job = GenerationJob(title=payload.title, total_count=len(payload.recipients))
    db.add(job)
    db.flush()  # get job.id without committing yet

    for recipient in payload.recipients:
        record = CertificateRecord(
            job_id=job.id,
            recipient_name=recipient.name,
            recipient_email=recipient.email,
            extra_text=recipient.extra_text,
            status=CertificateStatus.PENDING,
        )
        db.add(record)

    db.commit()
    db.refresh(job)
    return job


def _validate_recipient(record: CertificateRecord) -> str | None:
    """Returns an error string if the recipient data is bad, else None."""
    if not record.recipient_name:
        return "recipient name is required"
    if len(record.recipient_name) > 200:
        return "recipient name is too long"
    return None


def process_job(job_id: str, db: Session) -> None:
    """Runs in the background after the job is created. Generates every
    certificate in the job, isolating failures so one bad recipient doesn't
    stop the rest."""
    job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
    if job is None:
        return

    job.status = JobStatus.PROCESSING
    db.commit()

    records = db.query(CertificateRecord).filter(CertificateRecord.job_id == job_id).all()

    for record in records:
        validation_error = _validate_recipient(record)
        if validation_error:
            record.status = CertificateStatus.FAILED
            record.error_message = validation_error
            db.commit()
            continue

        try:
            path = generate_certificate(record.id, record.recipient_name, record.extra_text)
            record.status = CertificateStatus.GENERATED
            record.file_path = str(path)
            record.error_message = None
        except CertificateGenerationError as exc:
            record.status = CertificateStatus.FAILED
            record.error_message = str(exc)
        except Exception as exc:  # belt and braces - one bad record should never kill the job
            record.status = CertificateStatus.FAILED
            record.error_message = f"unexpected error: {exc}"

        db.commit()

    completed = sum(1 for r in records if r.status == CertificateStatus.GENERATED)
    failed = sum(1 for r in records if r.status == CertificateStatus.FAILED)

    job.completed_count = completed
    job.failed_count = failed

    if failed == 0:
        job.status = JobStatus.COMPLETED
    elif completed == 0:
        job.status = JobStatus.FAILED
    else:
        job.status = JobStatus.COMPLETED_WITH_ERRORS

    db.commit()
