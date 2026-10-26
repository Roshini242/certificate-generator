import io
import os
import re
import zipfile

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import Base, engine, get_db
from app.services import process_job

# Create the tables in certificates.db if they don't exist yet
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Bulk Certificate Generator")


# ---------- Helpers ----------

def get_job_or_404(db: Session, job_id: int) -> models.Job:
    job = db.get(models.Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job


def safe_filename(text: str) -> str:
    """Keep only letters, numbers, dash and underscore (safe inside a ZIP)."""
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", text).strip("_")
    return cleaned or "certificate"


# ---------- Endpoints ----------

@app.get("/")
def health_check():
    return {"message": "Certificate Generator API is running"}


@app.post(
    "/jobs",
    response_model=schemas.JobCreatedOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_job(
    payload: schemas.JobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Accepts a list of recipients, saves them, and starts generation
    in the background. Returns immediately with a job id.
    """
    job = models.Job(status=models.JOB_PENDING, total=len(payload.recipients))
    db.add(job)
    db.flush()  # assigns job.id without finishing the transaction

    for r in payload.recipients:
        db.add(
            models.Certificate(
                job_id=job.id,
                recipient_name=r.recipient_name,
                course_name=r.course_name,
                issue_date=r.issue_date,
                status=models.CERT_PENDING,
            )
        )

    db.commit()
    db.refresh(job)

    background_tasks.add_task(process_job, job.id)

    return schemas.JobCreatedOut(job_id=job.id, status=job.status, total=job.total)


@app.get("/jobs/{job_id}", response_model=schemas.JobStatusOut)
def get_job_status(job_id: int, db: Session = Depends(get_db)):
    """Shows progress: counts plus the status of every certificate."""
    job = get_job_or_404(db, job_id)

    certificates = (
        db.query(models.Certificate)
        .filter(models.Certificate.job_id == job_id)
        .order_by(models.Certificate.id)
        .all()
    )

    succeeded = sum(1 for c in certificates if c.status == models.CERT_SUCCESS)
    failed = sum(1 for c in certificates if c.status == models.CERT_FAILED)
    pending = len(certificates) - succeeded - failed

    return schemas.JobStatusOut(
        job_id=job.id,
        status=job.status,
        total=job.total,
        succeeded=succeeded,
        failed=failed,
        pending=pending,
        created_at=job.created_at,
        certificates=certificates,
    )


@app.get("/jobs/{job_id}/certificates/{certificate_id}")
def download_certificate(
    job_id: int, certificate_id: int, db: Session = Depends(get_db)
):
    """Downloads one generated certificate PDF."""
    get_job_or_404(db, job_id)

    cert = (
        db.query(models.Certificate)
        .filter(
            models.Certificate.id == certificate_id,
            models.Certificate.job_id == job_id,  # must belong to this job
        )
        .first()
    )
    if cert is None:
        raise HTTPException(status_code=404, detail="Certificate not found in this job")

    if cert.status != models.CERT_SUCCESS:
        raise HTTPException(
            status_code=409,
            detail=f"Certificate is not available (status: {cert.status})",
        )

    if not cert.file_path or not os.path.exists(cert.file_path):
        raise HTTPException(status_code=404, detail="Certificate file is missing on disk")

    return FileResponse(
        cert.file_path,
        media_type="application/pdf",
        filename=f"{safe_filename(cert.recipient_name)}_certificate.pdf",
    )


@app.get("/jobs/{job_id}/download")
def download_all_certificates(job_id: int, db: Session = Depends(get_db)):
    """Downloads all successfully generated certificates of a job as a ZIP."""
    job = get_job_or_404(db, job_id)

    if job.status in (models.JOB_PENDING, models.JOB_PROCESSING):
        raise HTTPException(
            status_code=409,
            detail=f"Job is still {job.status}. Check /jobs/{job_id} and try again later.",
        )

    certificates = (
        db.query(models.Certificate)
        .filter(
            models.Certificate.job_id == job_id,
            models.Certificate.status == models.CERT_SUCCESS,
        )
        .order_by(models.Certificate.id)
        .all()
    )

    buffer = io.BytesIO()
    files_added = 0
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for cert in certificates:
            if cert.file_path and os.path.exists(cert.file_path):
                zf.write(
                    cert.file_path,
                    arcname=f"{cert.id}_{safe_filename(cert.recipient_name)}.pdf",
                )
                files_added += 1

    if files_added == 0:
        raise HTTPException(status_code=404, detail="No generated certificates to download")

    return Response(
        content=buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="job_{job_id}_certificates.zip"'},
    )