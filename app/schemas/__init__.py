from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field
from app.models import UserRole, DocumentStatus, FactStatus, ReminderStatus, ApprovalStatus


class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: UserRole


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    is_synthetic: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    sub: Optional[int] = None


class PatientProfileBase(BaseModel):
    date_of_birth: Optional[datetime] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    insurance_info: Optional[Dict[str, Any]] = None


class PatientProfileCreate(PatientProfileBase):
    pass


class PatientProfileUpdate(PatientProfileBase):
    pass


class PatientProfileResponse(PatientProfileBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DoctorProfileBase(BaseModel):
    license_number: str
    specialty: Optional[str] = None
    hospital_affiliation: Optional[str] = None


class DoctorProfileCreate(DoctorProfileBase):
    pass


class DoctorProfileResponse(DoctorProfileBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StaffProfileBase(BaseModel):
    employee_id: str
    department: Optional[str] = None


class StaffProfileCreate(StaffProfileBase):
    pass


class StaffProfileResponse(StaffProfileBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentBase(BaseModel):
    filename: str
    original_filename: str
    mime_type: str
    file_size: int


class DocumentCreate(DocumentBase):
    pass


class DocumentResponse(DocumentBase):
    id: int
    owner_id: int
    storage_path: str
    page_count: Optional[int] = None
    status: DocumentStatus
    extracted_text: Optional[str] = None
    processing_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ExtractedFactBase(BaseModel):
    page_number: Optional[int] = None
    section: Optional[str] = None
    source_text: str
    fact_type: str
    extracted_value: str
    uncertainty_reason: Optional[str] = None


class ExtractedFactCreate(ExtractedFactBase):
    document_id: int
    patient_id: int


class ExtractedFactUpdate(BaseModel):
    status: Optional[FactStatus] = None
    uncertainty_reason: Optional[str] = None
    extracted_value: Optional[str] = None


class ExtractedFactResponse(ExtractedFactBase):
    id: int
    patient_id: int
    document_id: int
    status: FactStatus
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TimelineEventBase(BaseModel):
    event_type: str
    title: str
    description: Optional[str] = None
    event_date: datetime
    event_metadata: Optional[Dict[str, Any]] = None


class TimelineEventCreate(TimelineEventBase):
    patient_id: int
    document_id: Optional[int] = None
    source_fact_id: Optional[int] = None


class TimelineEventResponse(TimelineEventBase):
    id: int
    patient_id: int
    document_id: Optional[int] = None
    source_fact_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ReminderBase(BaseModel):
    medication_name: str
    dose: Optional[str] = None
    route: Optional[str] = None
    frequency: Optional[str] = None
    times: Optional[List[str]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    timezone: str = "UTC"
    notes: Optional[str] = None


class ReminderCreate(ReminderBase):
    patient_id: int
    fact_id: Optional[int] = None


class ReminderPreview(ReminderBase):
    fact_id: Optional[int] = None
    source_text: Optional[str] = None


class ReminderConfirm(BaseModel):
    reminder: ReminderPreview
    confirmed: bool


class ReminderResponse(ReminderBase):
    id: int
    patient_id: int
    fact_id: Optional[int] = None
    status: ReminderStatus
    confirmed_at: Optional[datetime] = None
    confirmed_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationBase(BaseModel):
    title: Optional[str] = None


class ConversationCreate(ConversationBase):
    patient_id: int


class ConversationResponse(ConversationBase):
    id: int
    patient_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageBase(BaseModel):
    role: str
    content: str


class MessageCreate(MessageBase):
    conversation_id: int


class MessageResponse(MessageBase):
    id: int
    conversation_id: int
    sources: Optional[List[Dict[str, Any]]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None


class ChatResponse(BaseModel):
    response: str
    sources: List[Dict[str, Any]] = []
    conversation_id: int


class PendingActionBase(BaseModel):
    action_type: str
    target_type: str
    target_id: Optional[int] = None
    parameters: Dict[str, Any]


class PendingActionCreate(PendingActionBase):
    actor_id: int
    idempotency_key: str
    expires_at: datetime


class PendingActionResponse(PendingActionBase):
    id: int
    actor_id: int
    status: ApprovalStatus
    idempotency_key: str
    expires_at: datetime
    approved_at: Optional[datetime] = None
    approved_by: Optional[int] = None
    executed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ApprovalRequest(BaseModel):
    action_id: int
    approved: bool


class AuditEventBase(BaseModel):
    action: str
    resource_type: str
    resource_id: Optional[int] = None
    details: Optional[Dict[str, Any]] = None


class AuditEventResponse(AuditEventBase):
    id: int
    actor_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class AccessGrantBase(BaseModel):
    patient_id: int
    grantee_id: int
    scope: str
    expires_at: Optional[datetime] = None


class AccessGrantCreate(AccessGrantBase):
    pass


class AccessGrantResponse(AccessGrantBase):
    id: int
    granter_id: int
    revoked_at: Optional[datetime] = None
    revoked_by: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SyntheticAccount(BaseModel):
    email: str
    password: str
    role: UserRole
    full_name: str