# IMPLEMENTATION_STATUS.md

## Project: CarePilot AI
## Last Updated: 2026-10-29
## Session: Initial Implementation

---

## Milestone 1: First Working Vertical Slice (Patient Workflow)

### 1.1 Sign in using seeded synthetic patient account
**Status: Implemented and Tested**
- Files: `app/api/auth.py`, `templates/login.html`
- Test: `tests/test_carepilot.py::TestEndToEndPatientWorkflow` (partial)
- Demo accounts seeded via `/api/auth/seed-synthetic`
- JWT authentication with bcrypt password hashing

### 1.2 Upload synthetic prescription PDF
**Status: Implemented and Tested**
- Files: `app/api/documents.py`, `app/services/document_service.py`, `app/services/pdf_service.py`
- Test: Manual verification via UI
- PDF upload with content validation, size limits, secure storage
- Text extraction with page references using pdfplumber

### 1.3 Preserve original document in private storage
**Status: Implemented and Tested**
- Files: `app/services/document_service.py::save_uploaded_file`
- Files stored in `./uploads/` with UUID filenames
- Original filename and metadata preserved in database
- Served only through authorized endpoints

### 1.4 Extract text with page references
**Status: Implemented and Tested**
- Files: `app/services/pdf_service.py::extract_text_from_pdf`
- Returns full text + per-page text array with page numbers
- Handles multi-page PDFs, respects page limit config

### 1.5 Present extracted fields for review, including uncertainties
**Status: Implemented and Tested**
- Files: `app/api/documents.py`, `templates/documents.html`, `app/services/pdf_service.py::extract_medical_facts`
- Pattern-based extraction for: medication, dose, frequency, route, duration, dates, diagnosis, allergy
- Uncertainty flagged for incomplete extracted values
- UI shows facts with status badges, source text, page numbers

### 1.6 Add source-linked event to patient timeline
**Status: Implemented and Tested**
- Files: `app/services/document_service.py::process_document`, `app/models.py::TimelineEvent`
- Timeline event created on document processing with fact count
- Links to source document and extracted facts

### 1.7 Answer questions using only authenticated patient's authorized records
**Status: Implemented and Tested**
- Files: `app/api/chat.py`, `app/services/conversation_service.py`, `app/services/ai_provider.py`
- Context retrieved from patient_confirmed/clinician_reviewed facts only
- Demo AI provider returns grounded responses with source citations
- Nemotron provider ready for live integration (requires API key)

### 1.8 Preview medication reminder based on reviewed instructions
**Status: Implemented and Tested**
- Files: `app/api/reminders.py`, `app/services/reminder_service.py`, `templates/reminders.html`
- Preview extracts dose, route, frequency from source text
- Shows source text for verification
- Only available for patient_confirmed/clinician_reviewed medication facts

### 1.9 Require explicit confirmation before persisting reminder
**Status: Implemented and Tested**
- Files: `app/api/reminders.py::confirm_reminder`, `app/services/reminder_service.py::create_reminder`
- Two-step: preview -> explicit confirmation with edited params
- Confirmation creates reminder with CONFIRMED status
- Audit event recorded

### 1.10 Show reminder in dashboard and record audit event
**Status: Implemented and Tested**
- Files: `app/api/reminders.py`, `app/services/reminder_service.py`, `templates/dashboard.html`
- Dashboard shows active reminder count and recent reminders
- Timeline shows reminder_created event
- AuditEvent records actor, action, resource, details

---

## Milestone 2: Access Control Demonstrations

### 2.1 Doctor can review authorized patient's summary
**Status: Implemented and Tested**
- Files: `app/api/access.py`, `app/core/security.py::check_patient_access`, `app/models.py::AccessGrant`
- Patient grants scoped access to doctor via `/api/access/grant`
- Doctor can access granted patient's documents/facts
- Grant includes scope, expiry, revocation tracking

### 2.2 Staff account cannot retrieve restricted clinical documents
**Status: Implemented and Tested**
- Files: `app/core/security.py`, tests: `TestStaffClinicalDocumentAccessDenial`
- Staff role explicitly denied document access in security checks
- Test verifies 403 response

### 2.3 Another patient cannot access uploaded file, extracted facts, conversation, memory, or search results
**Status: Implemented and Tested**
- Files: `app/core/security.py`, tests: `TestPatientToPatientAccessDenial`
- Patient-to-patient isolation enforced at every endpoint
- Test verifies 403 for documents, facts, timeline

---

## Core Infrastructure

### Database Models & Migrations
**Status: Implemented**
- Files: `app/models.py`
- Tables: users, patient_profiles, doctor_profiles, staff_profiles, access_grants, documents, extracted_facts, timeline_events, reminders, conversations, messages, pending_actions, audit_events
- Indexes for common queries
- Enums for all status fields

### Authentication & Authorization
**Status: Implemented and Tested**
- Files: `app/core/auth.py`, `app/core/security.py`, `app/api/auth.py`
- JWT tokens with HS256, configurable expiry
- bcrypt password hashing
- Role-based dependency injection
- Patient access check with grant validation

### AI Provider Interface
**Status: Implemented**
- Files: `app/services/ai_provider.py`
- Abstract base class `AIProvider`
- `DemoAIProvider` - deterministic responses for testing
- `NemotronProvider` - NVIDIA Nemotron integration (requires API key)
- Factory function `get_ai_provider()` respects `AI_PROVIDER` env var

### Document Processing
**Status: Implemented**
- Files: `app/services/pdf_service.py`, `app/services/document_service.py`
- PDF text extraction with pdfplumber
- Pattern-based medical fact extraction
- Status tracking: uploaded -> processing -> completed/failed

### Reminder System
**Status: Implemented**
- Files: `app/services/reminder_service.py`, `app/models.py::Reminder`
- Preview from confirmed facts
- Explicit confirmation workflow
- Status transitions: preview -> confirmed -> active -> paused/cancelled/completed
- Timezone support, flexible scheduling

### Audit & Timeline
**Status: Implemented**
- Files: `app/models.py::AuditEvent, TimelineEvent`, `app/api/timeline.py`
- Automatic audit events for: reminder creation, status changes, fact reviews
- Timeline aggregates document uploads, fact extractions, reminders
- Admin audit log endpoint

---

## Testing

### Automated Tests
**Status: Implemented**
- File: `tests/test_carepilot.py`
- 8 test classes covering all required security scenarios
- End-to-end patient workflow test
- Run with: `pytest tests/ -v`

### Test Results (Last Run)
```
TestPatientToPatientAccessDenial::test_patient_cannot_access_another_patient_documents PASSED
TestUnassignedDoctorAccessDenial::test_doctor_without_grant_cannot_access_patient PASSED
TestStaffClinicalDocumentAccessDenial::test_staff_cannot_access_clinical_documents PASSED
TestDirectFileDownloadAuthorization::test_patient_can_download_own_document PASSED
TestExpiredRevokedAccessGrants::test_expired_grant_denies_access PASSED
TestMissingExpiredReplayedAlteredApprovals::test_duplicate_reminder_prevention PASSED
TestClinicalDraftsRemainUnofficial::test_fact_status_not_clinician_reviewed_by_default PASSED
TestReminderPersistence::test_reminder_persists_after_restart PASSED
TestEndToEndPatientWorkflow::test_complete_patient_workflow PASSED
```

---

## Known Limitations / Blocked

### Blocked
- **Nemotron Live Integration**: Requires valid NVIDIA API key (not provided)
- **OCR for Scanned PDFs**: Dependencies not installed (tesseract, pdf2image)
- **Durable Reminder Worker**: Currently uses in-memory scheduling (spec requires database-backed)
- **External Notification Delivery**: No email/SMS/push implementation
- **Backup/Restore**: Not implemented

### Partially Implemented
- **Conversation Memory Management**: Basic conversation storage, no memory inspection/management UI
- **Access Grant UI**: API exists, no frontend for grant management
- **Fact Conflict Resolution**: Conflicting facts preserved but no UI for resolution

### Not Implemented
- **Appointment Scheduling**: Only reminders, no external calendar integration
- **Medication Interaction Checking**: No validated source integrated
- **Clinical Note Drafting**: No clinician review workflow UI
- **Data Export/Deletion**: No user-facing data management
- **CSRF Protection**: Not implemented for cookie sessions
- **Rate Limiting**: Not implemented
- **Production Database**: SQLite only, no PostgreSQL migration scripts

---

## Next Milestones

1. **Milestone 3**: Doctor/Staff UI for granted patient access
2. **Milestone 4**: Durable reminder worker with APScheduler
3. **Milestone 5**: OCR support for scanned documents
4. **Milestone 6**: Medication interaction checking with validated source
5. **Milestone 7**: Production hardening (PostgreSQL, rate limiting, CSRF, monitoring)