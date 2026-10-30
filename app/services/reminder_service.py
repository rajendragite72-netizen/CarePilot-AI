from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models import Reminder, ReminderStatus, ExtractedFact, FactStatus, TimelineEvent, AuditEvent, User
from app.schemas import ReminderPreview


def create_reminder_preview(fact: ExtractedFact) -> ReminderPreview:
    """Create a reminder preview from an extracted fact."""
    source_text = fact.source_text.lower()
    
    dose = None
    route = None
    frequency = None
    times = None
    
    import re
    dose_match = re.search(r'(?i)(?:dose|dosage)[:\s]+([^\n]+)', source_text)
    if dose_match:
        dose = dose_match.group(1).strip()
    
    route_match = re.search(r'(?i)(?:route|via)[:\s]+([^\n]+)', source_text)
    if route_match:
        route = route_match.group(1).strip()
    
    freq_match = re.search(r'(?i)(?:frequency|freq)[:\s]+([^\n]+)', source_text)
    if freq_match:
        frequency = freq_match.group(1).strip()
    
    med_name = fact.extracted_value
    if fact.fact_type != "medication":
        med_match = re.search(r'(?i)(?:medication|drug|prescription|rx)[:\s]+([^\n]+)', source_text)
        if med_match:
            med_name = med_match.group(1).strip()
    
    return ReminderPreview(
        medication_name=med_name,
        dose=dose,
        route=route,
        frequency=frequency,
        times=times,
        fact_id=fact.id,
        source_text=fact.source_text,
    )


def create_reminder(
    db: Session,
    patient_id: int,
    preview: ReminderPreview,
    confirmed_by: int,
    notes: Optional[str] = None
) -> Reminder:
    """Create a confirmed reminder."""
    reminder = Reminder(
        patient_id=patient_id,
        fact_id=preview.fact_id,
        medication_name=preview.medication_name,
        dose=preview.dose,
        route=preview.route,
        frequency=preview.frequency,
        times=preview.times,
        start_date=preview.start_date,
        end_date=preview.end_date,
        timezone=preview.timezone,
        notes=notes,
        status=ReminderStatus.CONFIRMED,
        confirmed_at=datetime.utcnow(),
        confirmed_by=confirmed_by,
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    
    event = TimelineEvent(
        patient_id=patient_id,
        event_type="reminder_created",
        title=f"Medication reminder: {reminder.medication_name}",
        description=f"Reminder confirmed for {reminder.frequency or 'as directed'}",
        event_date=datetime.utcnow(),
        metadata={"reminder_id": reminder.id},
    )
    db.add(event)
    
    audit = AuditEvent(
        actor_id=confirmed_by,
        action="reminder_created",
        resource_type="reminder",
        resource_id=reminder.id,
        details={"medication": reminder.medication_name, "frequency": reminder.frequency},
    )
    db.add(audit)
    
    db.commit()
    return reminder


def get_patient_reminders(db: Session, patient_id: int, status: Optional[ReminderStatus] = None) -> List[Reminder]:
    """Get reminders for a patient."""
    query = db.query(Reminder).filter(Reminder.patient_id == patient_id)
    if status:
        query = query.filter(Reminder.status == status)
    return query.order_by(Reminder.created_at.desc()).all()


def update_reminder_status(
    db: Session,
    reminder_id: int,
    status: ReminderStatus,
    actor_id: int
) -> Reminder:
    """Update reminder status."""
    reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
    if not reminder:
        raise ValueError("Reminder not found")
    
    if reminder.patient_id != actor_id:
        raise ValueError("Unauthorized")
    
    old_status = reminder.status
    reminder.status = status
    db.commit()
    db.refresh(reminder)
    
    audit = AuditEvent(
        actor_id=actor_id,
        action="reminder_status_changed",
        resource_type="reminder",
        resource_id=reminder.id,
        details={"old_status": old_status.value, "new_status": status.value},
    )
    db.add(audit)
    db.commit()
    
    return reminder