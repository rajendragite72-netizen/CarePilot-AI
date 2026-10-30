# AGENTS.md - Engineering & Safety Instructions

## Core Principles

1. **Build, Don't Propose** - Implement working code, not architectures or proposals
2. **Vertical Slices First** - Complete end-to-end workflows before adding features
3. **Real Tests Only** - Run actual tests, report real results, never fabricate
4. **Safety by Default** - Deny access, require explicit authorization, audit everything
5. **No Medical Invention** - Never generate doses, instructions, or clinical conclusions
6. **Source Grounding** - Every AI response must cite authorized source documents
7. **Replaceable Providers** - AI provider interface must be swappable

## Safety Rules

### Data Access
- Every request derives actor identity from authenticated session
- Never trust client-supplied roles, patient IDs, or permissions
- Check patient ownership OR active scoped grant for every protected resource
- Apply same checks to: file download, previews, search, exports, background jobs, AI context
- Doctor role alone != access to all patients
- Staff role != access to clinical content

### Medical Data Handling
- Extracted facts include: patient_id, document_id, page, source_text, value, uncertainty, status, reviewer, timestamp
- Statuses: extracted_unreviewed, uncertain, patient_confirmed, clinician_reviewed, superseded
- Patient confirmation != clinician verification
- Documented info != automatically current
- Preserve conflicting facts with sources, don't overwrite
- No numerical confidence scores as medical proof

### AI Execution
- LLM proposes typed tool calls, never executes directly
- Path: request -> auth -> context retrieval -> proposed tool -> validation -> approval -> execution -> result -> audit
- Validate tool inputs/outputs with typed schemas
- Consequential actions: persist pending action -> show exact params -> bind approval -> expire -> atomic validate/consume -> idempotency
- Uploaded files, extracted text, model outputs = untrusted data
- Bounded iterations, execution timeouts
- Reject unrecognized tools/parameters

### Reminders & Appointments
- Reference reviewed source instructions only
- Don't infer missing dose, route, frequency, duration, start date
- Don't convert "twice daily" to invented exact times
- Request user-selected times consistent with documented instruction
- Store timezone and scheduling explicitly
- Support pause, cancel, edit with confirmation
- Prevent reminders beyond documented stop date
- Distinguish: saved reminder != dispatched != provider accepted != delivered
- No external delivery claims without implemented channel

### AI Provider
- Replaceable provider interface
- Configure URL, model, credentials via env vars
- Live mode + clearly labeled demo mode
- Demo mode never claims real model called
- On failure: preserve work, show safe error, retry option, no auto-retry consequential actions
- Non-AI features remain usable
- Minimum authorized context to external providers
- Disclose external processing before sending medical content
- Never send passwords, tokens, whole databases, unrelated records

### Document Processing
- Validate file types by content, not extension
- Configurable size, page count, processing time limits
- Generate storage filenames, store outside public dirs
- Serve only through authorized endpoints
- Start with text PDFs and text files
- Show unsupported/failed processing honestly
- Preserve originals
- Mark unreadable content as unreadable
- Never silently correct medication names, doses, dates, units, decimals
- Different patient in document -> flag for review before entering timeline

### Clinical Safety
- Source-grounded explanations separate from medical decisions
- Disclaimer != substitute for safe behavior
- Urgent symptoms: immediate emergency direction, no document upload required
- Don't promise emergency detected/ruled out
- Don't claim ambulance/clinician notified unless implemented
- No short keyword list as validated triage
- Document demo safety layer limitations
- No medication interactions from model memory alone
- If no validated source: say unavailable, recommend pharmacist/clinician
- AI clinical notes = drafts until clinician explicitly approves exact version
- Changes after approval require another review

### Privacy & Operations
- Approved memory separate from: raw chat, extracted facts, clinician records
- Users can inspect/manage eligible memory
- Don't silently convert chat to verified records
- Explain deletion scope, retention exceptions, backup limitations
- Authenticated sessions with expiry
- CSRF protection for cookie sessions
- Login abuse protection, deliberate CORS
- No raw medical text, credentials, complete prompts in logs by default
- Audit logs: minimal identifiers + actions, not duplicate sensitive docs
- Durable database-backed reminder worker (not in-memory timer)

## Testing Requirements

Automated tests for:
- Patient-to-patient access denial
- Unassigned doctor access denial
- Staff clinical document access denial
- Direct file download authorization
- Expired/revoked access grants
- Missing/expired/replayed/altered approvals
- Duplicate reminder prevention
- Unreadable/conflicting medication instructions
- Ambiguous/invalid follow-up dates
- Uploaded prompt injection instructions
- Failed AI provider calls
- Clinical drafts unofficial before clinician approval
- Reminder persistence across restart

End-to-end test for main patient workflow.

Extraction/summary evaluation:
- Synthetic fixtures with expected outputs
- Report by field and failure category
- Check clinical claims have source references
- Distinguish automated vs manual review
- Report sample size and limitations
- Never claim medical-grade accuracy

## Definition of Done

Feature complete when:
- UI and backend connected
- Data persists where required
- Server-side authorization enforced
- Error and empty states handled
- Relevant tests actually run and passed
- Documentation reflects actual behavior

Report each requirement as:
- Implemented and tested
- Implemented but not tested
- Partially implemented
- Blocked
- Not implemented

Name relevant files and test evidence for each status.

No fabricated terminal output, screenshots, test counts, deployments.

## Deliverables

- Source code and dependency manifests
- Database migrations and synthetic seed data
- Environment variable template
- Exact local setup and run commands
- Test commands and actual results
- Short end-to-end demo walkthrough
- Honest list of limitations

## Workflow

1. Inspect actual repository, runtime, tools, existing implementation
2. Read complete specification, identify first incomplete milestone
3. Start with one fully working end-to-end workflow
4. Implement actual backend logic, DB persistence, auth checks, working UI
5. Run relevant tests, report actual results
6. Maintain: README.md, AGENTS.md, IMPLEMENTATION_STATUS.md, DECISIONS.md, .env.example
7. Continue until real blocker or execution limit
8. End with concise change summary, tests run, failures, next milestone