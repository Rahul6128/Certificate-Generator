from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.models import GenerationJob, CertificateRecord
from app.schemas import JobCreateRequest, JobCreateResponse, JobStatusResponse, CertificateOut
from app.services.job_service import create_job, process_job

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _run_job_in_background(job_id: str):
    # BackgroundTasks share the request, but the request's db session gets
    # closed once the response is sent - so the background job needs its
    # own session rather than reusing the one from the route.
    db = SessionLocal()
    try:
        process_job(job_id, db)
    finally:
        db.close()


@router.post("", response_model=JobCreateResponse, status_code=201)
def create_generation_job(
    payload: JobCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if not payload.recipients:
        raise HTTPException(status_code=422, detail="recipients list cannot be empty")

    job = create_job(db, payload)
    background_tasks.add_task(_run_job_in_background, job.id)

    return JobCreateResponse(job_id=job.id, status=job.status, total=job.total_count)


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")

    pending = job.total_count - job.completed_count - job.failed_count
    return JobStatusResponse(
        job_id=job.id,
        title=job.title,
        status=job.status,
        total=job.total_count,
        completed=job.completed_count,
        failed=job.failed_count,
        pending=max(pending, 0),
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get("/{job_id}/certificates", response_model=list[CertificateOut])
def list_job_certificates(job_id: str, db: Session = Depends(get_db)):
    job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")

    records = db.query(CertificateRecord).filter(CertificateRecord.job_id == job_id).all()
    results = []
    for r in records:
        out = CertificateOut.model_validate(r)
        if r.status == "GENERATED":
            out.download_url = f"/api/certificates/{r.id}/download"
        results.append(out)
    return results
