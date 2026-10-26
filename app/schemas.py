from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------- Incoming data ----------

class RecipientIn(BaseModel):
    """One person who should receive a certificate."""
    # Remove spaces at the start/end before checking length
    model_config = ConfigDict(str_strip_whitespace=True)

    recipient_name: str = Field(min_length=1, max_length=100)
    course_name: str = Field(min_length=1, max_length=150)
    issue_date: date  # expects "YYYY-MM-DD", e.g. "2025-01-15"


class JobCreate(BaseModel):
    """The whole bulk request: a list of recipients."""
    recipients: List[RecipientIn] = Field(min_length=1, max_length=1000)


# ---------- Outgoing data ----------

class CertificateOut(BaseModel):
    """How one certificate is shown in responses."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    recipient_name: str
    course_name: str
    issue_date: date
    status: str
    error_message: Optional[str] = None


class JobCreatedOut(BaseModel):
    """Response right after creating a job."""
    job_id: int
    status: str
    total: int


class JobStatusOut(BaseModel):
    """Response when checking progress of a job."""
    job_id: int
    status: str
    total: int
    succeeded: int
    failed: int
    pending: int
    created_at: datetime
    certificates: List[CertificateOut]