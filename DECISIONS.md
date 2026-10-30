# DECISIONS.md - Architecture Decisions & Tradeoffs

## 1. Technology Stack

### Decision: FastAPI + SQLAlchemy + Jinja2
**Rationale**: 
- FastAPI: Modern, fast, automatic OpenAPI docs, type safety with Pydantic
- SQLAlchemy 2.0: Mature ORM, async support, database agnostic
- Jinja2: Server-side rendering, simple for demo, no SPA complexity
- SQLite: Zero-config for development, easy to swap for PostgreSQL

**Tradeoffs**:
- No reactive frontend (no real-time updates)
- Jinja2 templates couple backend/frontend
- SQLite not production-ready for concurrent writes

### Decision: pdfplumber for PDF Extraction
**Rationale**:
- Pure Python, no system dependencies
- Good text extraction with page coordinates
- Handles most text-based PDFs well

**Tradeoffs**:
- No OCR for scanned documents
- Complex layouts may extract poorly
- No table structure preservation

---

## 2. Data Model

### Decision: Unified User Table with Role Enum + Profile Tables
**Rationale**:
- Single auth table simplifies login/token logic
- Profile tables allow role-specific fields without nullable columns
- Easy to query "all users" or filter by role

**Tradeoffs**:
- Joins needed for role-specific data
- Adding new roles requires new profile table

### Decision: ExtractedFact with Explicit Status Enum
**Rationale**:
- Required by spec: extracted_unreviewed, uncertain, patient_confirmed, clinician_reviewed, superseded
- Status captures review workflow explicitly
- Uncertainty reason separate from status

**Tradeoffs**:
- More complex than boolean "reviewed"
- Status transitions need validation (not yet enforced in DB)

### Decision: Separate TimelineEvent and AuditEvent Tables
**Rationale**:
- Timeline: patient-facing clinical history (documents, reminders, facts)
- Audit: system-facing security/logging (access, modifications, auth)
- Different retention, access control, detail levels

**Tradeoffs**:
- Some duplication (both record "reminder created")
- Two tables to query for complete picture

---

## 3. Authentication & Authorization

### Decision: JWT Bearer Tokens with Short Expiry
**Rationale**:
- Stateless, scales horizontally
- Short expiry (30 min) limits exposure
- Refresh token pattern not implemented (simplicity)

**Tradeoffs**:
- Users logged out frequently in demo
- No token revocation mechanism (blocklist not implemented)
- Token in localStorage vulnerable to XSS

### Decision: Role-Based Access with Explicit Grants
**Rationale**:
- Spec requires: doctor role alone != access to all patients
- Grants provide scoped, time-limited, revocable access
- Patient controls their data sharing

**Tradeoffs**:
- More complex than RBAC alone
- Grant management UI not built
- No emergency access override

### Decision: Authorization at Route Level + Service Level
**Rationale**:
- Defense in depth: route dependencies + service checks
- Service functions reusable outside HTTP context
- Clear separation: route = HTTP concerns, service = business logic

**Tradeoffs**:
- Some duplication of checks
- Must keep both in sync

---

## 4. AI Integration

### Decision: Replaceable Provider Interface
**Rationale**:
- Spec requires: "Keep provider configuration replaceable"
- Demo mode for development/testing without API costs
- Nemotron ready for production

**Tradeoffs**:
- Demo provider is very basic (pattern matching)
- Nemotron integration untested without credentials
- No streaming responses implemented

### Decision: Context = Only Confirmed Facts
**Rationale**:
- Spec: "Answer questions using only authenticated patient's authorized records"
- Only patient_confirmed + clinician_reviewed facts sent to AI
- Prevents hallucination from unreviewed extractions

**Tradeoffs**:
- User must confirm facts before AI can reference them
- Slower initial experience
- No "draft" context for exploration

---

## 5. Document Processing

### Decision: Process Synchronously on Upload
**Rationale**:
- Simple for demo, immediate feedback
- Small PDFs process fast (< 1 second)
- No queue infrastructure needed

**Tradeoffs**:
- Blocks HTTP response during processing
- Large PDFs would timeout
- No retry on failure (must re-upload)

### Decision: Pattern-Based Extraction (Not ML)
**Rationale**:
- No ML dependencies, works offline
- Deterministic, testable
- Transparent: easy to see why fact extracted

**Tradeoffs**:
- Low recall/precision vs trained NER
- Regex patterns brittle, miss variations
- No entity normalization (e.g., "bid" vs "twice daily")

---

## 6. Reminder System

### Decision: Two-Step Preview + Confirmation
**Rationale**:
- Spec: "Require explicit confirmation before saving it"
- Preview shows extracted info + editable fields
- Confirmation creates audit trail

**Tradeoffs**:
- Extra click for user
- No "quick add" for simple cases
- Preview logic duplicates extraction logic

### Decision: Reminder References Source Fact
**Rationale**:
- Spec: "A medication reminder must reference reviewed source instructions"
- Foreign key to ExtractedFact ensures traceability
- Prevents reminder drift from source

**Tradeoffs**:
- Can't create ad-hoc reminders without source fact
- If fact superseded, reminder still points to old fact

---

## 7. Security

### Decision: No Raw Medical Data in Logs
**Rationale**:
- Spec: "Do not log raw medical text, credentials, or complete prompts by default"
- Structured logging with minimal identifiers only
- Audit events record action + resource ID, not content

**Tradeoffs**:
- Harder to debug extraction issues
- Can't replay AI conversations from logs
- Need separate debug mode for development

### Decision: File Storage Outside Public Directory
**Rationale**:
- Spec: "Generate storage filenames and store uploads outside public directories"
- UUID filenames prevent enumeration
- Served through authorized endpoint with access checks

**Tradeoffs**:
- Can't use CDN for static files
- Streaming large files through Python (slower)
- No direct browser caching

---

## 8. Testing

### Decision: Pytest with TestClient + Override DB
**Rationale**:
- FastAPI TestClient for integration tests
- Override get_db for isolated test database
- Synthetic test data, no fixtures needed

**Tradeoffs**:
- SQLite in tests != PostgreSQL in prod
- No parallel test execution (shared test.db)
- Limited end-to-end UI testing

---

## 9. Deployment Considerations (Not Implemented)

### Decision: Single-Process uvicorn for Demo
**Rationale**: Simplicity for hackathon demo

**Production Would Need**:
- Gunicorn + uvicorn workers
- PostgreSQL with connection pooling
- Redis for session/cache
- Reverse proxy (nginx)
- TLS termination
- Health checks, metrics, logging aggregation

---

## 10. Open Questions

1. **Fact Versioning**: How to handle corrected extractions? Current: supersede old fact, create new. Need UI for this.

2. **Grant Scopes**: Spec says "scope" as string. Should be structured (JSON) for granular permissions.

3. **Reminder Worker**: Spec requires "durable database-backed reminder worker". Need APScheduler or Celery beat.

4. **AI Response Streaming**: Better UX for long responses. Not implemented.

5. **Multi-language**: Not addressed. Medical terms need localization.

6. **Offline Support**: PWA with service worker? Not in scope.

7. **Audit Log Retention**: Spec mentions "backup limitations". No retention policy implemented.

8. **Emergency Access**: Break-glass for clinicians? Not implemented.