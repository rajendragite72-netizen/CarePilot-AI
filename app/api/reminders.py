from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models import User, UserRole, ExtractedFact, FactStatus
from app.schemas import ReminderPreview, ReminderConfirm, ReminderResponse
from app.services.reminder_service import (
    create_reminder_preview,
    create_reminder,
    get_patient_reminders,
    update_reminder_status,
)
from app.services.document_service import get_patient_facts

router = APIRouter(prefix="/api/reminders", tags=["reminders"])


@router.get("/preview/{fact_id}", response_model=ReminderPreview)
def preview_reminder(
    fact_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    fact = db.query(ExtractedFact).filter(ExtractedFact.id == fact_id).first()
    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found")
    
    if fact.patient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if fact.fact_type not in ["medication", "medication_dose", "instruction"]:
        raise HTTPException(status_code=400, detail="Fact is not a medication instruction")
    
    if fact.status not in [FactStatus.PATIENT_CONFIRMED, FactStatus.CLINICIAN_REVIEWED]:
        raise HTTPException(
            status_code=400,
            detail="Fact must be confirmed before creating a reminder"
        )
    
    return create_reminder_preview(fact)


@router.post("/confirm", response_model=ReminderResponse)
def confirm_reminder(
    confirm_data: ReminderConfirm,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if not confirm_data.confirmed:
        raise HTTPException(status_code=400, detail="Reminder not confirmed")
    
    preview = confirm_data.reminder
    
    if preview.fact_id:
        fact = db.query(ExtractedFact).filter(ExtractedFact.id == preview.fact_id).first()
        if not fact or fact.patient_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        if fact.status not in [FactStatus.PATIENT_CONFIRMED, FactStatus.CLINICIAN_REVIEWED]:
            raise HTTPException(status_code=400, detail="Fact must be confirmed first")
    
    reminder = create_reminder(
        db=db,
        patient_id=current_user.id,
        preview=preview,
        confirmed_by=current_user.id,
    )
    
    return reminder


@router.get("", response_model=List[ReminderResponse])
def list_reminders(
    status: str = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    from app.models import ReminderStatus
    status_enum = ReminderStatus(status) if status else None
    return get_patient_reminders(db, current_user.id, status_enum)


@router.patch("/{reminder_id}/status", response_model=ReminderResponse)
def change_reminder_status(
    reminder_id: int,
    status: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    from app.models import ReminderStatus
    try:
        status_enum = ReminderStatus(status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    reminder = update_reminder_status(db, reminder_id, status_enum, current_user.id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    
    return reminder