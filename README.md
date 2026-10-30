# CarePilot AI

A personal healthcare AI agent for patients, doctors, and healthcare staff. Built with FastAPI, SQLAlchemy, and NVIDIA Nemotron AI integration.

## Features

- **Secure Document Upload**: Upload prescriptions and medical documents (PDF/Text)
- **AI-Powered Extraction**: Extract medical facts with page references
- **Fact Review Workflow**: Review and confirm extracted information
- **Medication Reminders**: Create reminders from confirmed facts with explicit confirmation
- **AI Health Assistant**: Chat about your medical records (grounded in your data only)
- **Role-Based Access Control**: Patient, Doctor, Staff, Admin roles with granular permissions
- **Audit Trail**: Complete timeline and audit logging
- **Demo Mode**: Deterministic AI responses for testing without API keys

## Quick Start

### Prerequisites

- Python 3.10+
- pip

### Installation

```bash
cd carepilot
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your settings
python -m app.main
```

The server will start at `http://localhost:8000`

### Demo Accounts

Run the demo seeder at `/demo` or via API:

```bash
curl -X POST http://localhost:8000/api/auth/seed-synthetic
```

Default accounts:
| Role | Email | Password |
|------|-------|----------|
| Patient | patient@carepilot.demo | patient123 |
| Doctor | doctor@carepilot.demo | doctor123 |
| Staff | staff@carepilot.demo | staff123 |
| Admin | admin@carepilot.demo | admin123 |

## Usage Walkthrough

1. **Login** as patient at `/login`
2. **Upload** a prescription PDF at `/documents`
3. **Review** extracted facts - mark medications as "Confirmed"
4. **Create Reminders** at `/reminders` from confirmed facts
5. **Chat** with AI at `/chat` about your medications
6. **View Timeline** at `/timeline` for complete history

## Architecture

```
carepilot/
├── app/
│   ├── api/          # FastAPI routes
│   ├── core/         # Config, auth, database, security
│   ├── models/       # SQLAlchemy models
│   ├── schemas/      # Pydantic schemas
│   ├── services/     # Business logic
│   └── main.py       # Application entry
├── templates/        # Jinja2 HTML templates
├── static/           # Static assets
├── tests/            # Pytest tests
└── requirements.txt
```

## AI Provider

Configure in `.env`:

```env
AI_PROVIDER=demo          # or "nemotron"
NEMOTRON_API_KEY=your_key # Required for nemotron mode
NEMOTRON_MODEL=nvidia/nemotron-3-ultra
```

Demo mode provides deterministic responses for testing.

## Testing

```bash
pytest tests/ -v
```

## Security

- Passwords hashed with bcrypt
- JWT tokens with configurable expiry
- Role-based access control on every endpoint
- Patient data isolation enforced at database level
- Audit logging for all sensitive operations
- No raw medical data in logs

## Limitations (Demo)

- SQLite database (not production-ready)
- Demo AI provider (not real medical AI)
- No OCR for scanned PDFs
- No external notification delivery
- No backup/restore implementation
- In-memory reminder worker (not durable)

## License

MIT License - See LICENSE file for details.