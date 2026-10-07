from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CertificateRecord, CertificateStatus

router = APIRouter(prefix="/api/certificates", tags=["certificates"])


@router.get("/{certificate_id}/download")
def download_certificate(certificate_id: str, db: Session = Depends(get_db)):
    record = db.query(CertificateRecord).filter(CertificateRecord.id == certificate_id).first()
    if record is None:
        raise HTTPException(status_code=404, detail="certificate not found")

    if record.status != CertificateStatus.GENERATED or not record.file_path:
        raise HTTPException(status_code=409, detail=f"certificate is {record.status.value}, not available for download")

    path = Path(record.file_path)
    if not path.exists():
        raise HTTPException(status_code=410, detail="certificate file is missing from storage")

    filename = f"{(record.recipient_name or 'certificate').replace(' ', '_')}.png"
    return FileResponse(path, media_type="image/png", filename=filename)
