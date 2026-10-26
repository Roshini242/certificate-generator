from datetime import datetime

from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.database import Base

# Allowed status values (kept in one place so we never mistype them)
JOB_PENDING = "pending"
JOB_PROCESSING = "processing"
JOB_COMPLETED = "completed"
JOB_COMPLETED_WITH_ERRORS = "completed_with_errors"

CERT_PENDING = "pending"
CERT_SUCCESS = "success"
CERT_FAILED = "failed"


class Job(Base):
    """One bulk request. Contains many certificates."""
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, nullable=False, default=JOB_PENDING)
    total = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # One job -> many certificates
    certificates = relationship(
        "Certificate", back_populates="job", cascade="all, delete-orphan"
    )


class Certificate(Base):
    """One certificate for one recipient."""
    __tablename__ = "certificates"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)

    recipient_name = Column(String, nullable=False)
    course_name = Column(String, nullable=False)
    issue_date = Column(Date, nullable=False)

    status = Column(String, nullable=False, default=CERT_PENDING)
    file_path = Column(String, nullable=True)       # filled when generation succeeds
    error_message = Column(Text, nullable=True)     # filled when generation fails

    job = relationship("Job", back_populates="certificates")