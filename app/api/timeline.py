from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_active_user, check_patient_access
from app.models import User, TimelineEvent, AuditEvent
from app.schemas import TimelineEventResponse, AuditEventResponse

router = APIRouter(prefix="/api/timeline", tags=["timeline"])


@router.get("/patient/{patient_id}", response_model=List[TimelineEventResponse])
def get_patient_timeline(
    patient_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    check_patient_access(patient_id, current_user, db)
    
    events = db.query(TimelineEvent).filter(
        TimelineEvent.patient_id == patient_id
    ).order_by(TimelineEvent.event_date.desc()).all()
    
    return events


@router.get("/audit", response_model=List[AuditEventResponse])
def get_audit_log(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    events = db.query(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(100).all()
    return events