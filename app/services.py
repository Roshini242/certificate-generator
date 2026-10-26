import logging
import os

from app import models
from app.database import SessionLocal
from app.generator import generate_certificate

logger = logging.getLogger(__name__)

# Absolute path to <project>/generated_certificates, so it works from any folder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "generated_certificates")


def process_job(job_id: int) -> None:
    """
    Generates every certificate in a job.
    Runs in the background, so it opens its OWN database session.
    """
    db = SessionLocal()
    try:
        job = db.get(models.Job, job_id)
        if job is None:
            logger.error("Job %s not found", job_id)
            return

        job.status = models.JOB_PROCESSING
        db.commit()

        certificates = (
            db.query(models.Certificate)
            .filter(models.Certificate.job_id == job_id)
            .order_by(models.Certificate.id)
            .all()
        )

        for cert in certificates:
            try:
                # Filename uses the id, NOT the name (names can contain
                # characters that are illegal or unsafe in file names).
                file_path = os.path.join(
                    OUTPUT_DIR, f"job_{job_id}", f"cert_{cert.id}.pdf"
                )
                generate_certificate(
                    recipient_name=cert.recipient_name,
                    course_name=cert.course_name,
                    issue_date=cert.issue_date,
                    output_path=file_path,
                )
                cert.status = models.CERT_SUCCESS
                cert.file_path = file_path
                cert.error_message = None
            except Exception as exc:  # one failure must not stop the others
                logger.exception("Certificate %s failed", cert.id)
                cert.status = models.CERT_FAILED
                cert.error_message = str(exc)

            # Commit after EACH certificate so progress is visible
            # to anyone checking the job status while it runs.
            db.commit()

        # Decide the final job status
        failed_count = sum(1 for c in certificates if c.status == models.CERT_FAILED)
        job.status = (
            models.JOB_COMPLETED_WITH_ERRORS if failed_count else models.JOB_COMPLETED
        )
        db.commit()

    except Exception:
        # Something unexpected broke the whole job (not just one certificate)
        logger.exception("Job %s crashed", job_id)
        db.rollback()
        job = db.get(models.Job, job_id)
        if job:
            job.status = models.JOB_COMPLETED_WITH_ERRORS
            db.commit()
    finally:
        db.close()