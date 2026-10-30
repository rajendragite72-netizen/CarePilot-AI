import enum
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Enum, Boolean, JSON, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class UserRole(str, enum.Enum):
    PATIENT = "patient"
    DOCTOR = "doctor"
    STAFF = "staff"
    ADMIN = "admin"


class DocumentStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FactStatus(str, enum.Enum):
    EXTRACTED_UNREVIEWED = "extracted_unreviewed"
    UNCERTAIN = "uncertain"
    PATIENT_CONFIRMED = "patient_confirmed"
    CLINICIAN_REVIEWED = "clinician_reviewed"
    SUPERSEDED = "superseded"


class ReminderStatus(str, enum.Enum):
    PREVIEW = "preview"
    CONFIRMED = "confirmed"
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CONSUMED = "consumed"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.PATIENT)
    is_active = Column(Boolean, default=True)
    is_synthetic = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient_profile = relationship("PatientProfile", back_populates="user", uselist=False)
    doctor_profile = relationship("DoctorProfile", back_populates="user", uselist=False)
    staff_profile = relationship("StaffProfile", back_populates="user", uselist=False)
    documents = relationship("Document", back_populates="owner")
    timeline_events = relationship("TimelineEvent", back_populates="patient")
    reminders = relationship("Reminder", back_populates="patient", foreign_keys="Reminder.patient_id")
    conversations = relationship("Conversation", back_populates="patient")
    audit_events = relationship("AuditEvent", back_populates="actor")
    granted_access = relationship("AccessGrant", back_populates="granter", foreign_keys="AccessGrant.granter_id")
    received_access = relationship("AccessGrant", back_populates="grantee", foreign_keys="AccessGrant.grantee_id")


class PatientProfile(Base):
    __tablename__ = "patient_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    date_of_birth = Column(DateTime, nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    emergency_contact = Column(String(255), nullable=True)
    insurance_info = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="patient_profile")


class DoctorProfile(Base):
    __tablename__ = "doctor_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    license_number = Column(String(100), nullable=False)
    specialty = Column(String(100), nullable=True)
    hospital_affiliation = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="doctor_profile")
    access_grants = relationship("AccessGrant", back_populates="doctor")


class StaffProfile(Base):
    __tablename__ = "staff_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    employee_id = Column(String(100), nullable=False)
    department = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="staff_profile")


class AccessGrant(Base):
    __tablename__ = "access_grants"

    id = Column(Integer, primary_key=True, index=True)
    granter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    grantee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctor_profiles.id"), nullable=True)
    scope = Column(String(500), nullable=False)
    expires_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    revoked_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    granter = relationship("User", back_populates="granted_access", foreign_keys=[granter_id])
    grantee = relationship("User", back_populates="received_access", foreign_keys=[grantee_id])
    patient = relationship("User", foreign_keys=[patient_id])
    doctor = relationship("DoctorProfile", back_populates="access_grants", foreign_keys=[doctor_id])


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    storage_path = Column(String(500), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    page_count = Column(Integer, nullable=True)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.UPLOADED)
    extracted_text = Column(Text, nullable=True)
    processing_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="documents")
    facts = relationship("ExtractedFact", back_populates="document")
    timeline_events = relationship("TimelineEvent", back_populates="document")


class ExtractedFact(Base):
    __tablename__ = "extracted_facts"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    page_number = Column(Integer, nullable=True)
    section = Column(String(255), nullable=True)
    source_text = Column(Text, nullable=False)
    fact_type = Column(String(100), nullable=False)
    extracted_value = Column(Text, nullable=False)
    uncertainty_reason = Column(Text, nullable=True)
    status = Column(Enum(FactStatus), default=FactStatus.EXTRACTED_UNREVIEWED)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    document = relationship("Document", back_populates="facts")
    reviewer = relationship("User", foreign_keys=[reviewed_by])


class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    event_type = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    event_date = Column(DateTime, nullable=False)
    source_fact_id = Column(Integer, ForeignKey("extracted_facts.id"), nullable=True)
    event_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("User", back_populates="timeline_events")
    document = relationship("Document", back_populates="timeline_events")


class Reminder(Base):
    __tablename__ = "reminders"
    __table_args__ = (
        UniqueConstraint("patient_id", "fact_id", name="uq_patient_fact_reminder"),
    )

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    fact_id = Column(Integer, ForeignKey("extracted_facts.id"), nullable=True)
    medication_name = Column(String(255), nullable=False)
    dose = Column(String(100), nullable=True)
    route = Column(String(100), nullable=True)
    frequency = Column(String(100), nullable=True)
    times = Column(JSON, nullable=True)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    timezone = Column(String(50), default="UTC")
    status = Column(Enum(ReminderStatus), default=ReminderStatus.PREVIEW)
    notes = Column(Text, nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    confirmed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = relationship("User", back_populates="reminders", foreign_keys=[patient_id])
    fact = relationship("ExtractedFact")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    sources = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")


class PendingAction(Base):
    __tablename__ = "pending_actions"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action_type = Column(String(100), nullable=False)
    target_type = Column(String(100), nullable=False)
    target_id = Column(Integer, nullable=True)
    parameters = Column(JSON, nullable=False)
    status = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING)
    idempotency_key = Column(String(255), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    executed_at = Column(DateTime, nullable=True)
    result = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    actor = relationship("User", foreign_keys=[actor_id])
    approver = relationship("User", foreign_keys=[approved_by])


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    actor = relationship("User", back_populates="audit_events")


Index("ix_access_grants_patient_grantee", AccessGrant.patient_id, AccessGrant.grantee_id)
Index("ix_timeline_events_patient_date", TimelineEvent.patient_id, TimelineEvent.event_date)
Index("ix_reminders_patient_status", Reminder.patient_id, Reminder.status)
Index("ix_audit_events_actor_created", AuditEvent.actor_id, AuditEvent.created_at)