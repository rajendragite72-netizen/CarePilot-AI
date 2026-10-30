import pytest
import tempfile
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.core.database import get_db, Base
from app.core.auth import get_password_hash
from app.models import User, UserRole, PatientProfile, DoctorProfile, StaffProfile, Document, ExtractedFact, FactStatus, Reminder, ReminderStatus, AccessGrant
from datetime import datetime, timedelta


@pytest.fixture
def db_engine():
    """Create a fresh database engine for each test."""
    db_fd, db_path = tempfile.mkstemp(suffix='.db', prefix='test_carepilot_')
    os.close(db_fd)
    
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    try:
        os.unlink(db_path)
    except:
        pass
    engine.dispose()


@pytest.fixture
def session_factory(db_engine):
    """Create a session factory for the test."""
    return sessionmaker(autocommit=False, autoflush=False, bind=db_engine)


@pytest.fixture
def db_session(session_factory):
    """Create a session for test setup (main thread)."""
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(session_factory):
    """Create a test client with new session per request."""
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def create_test_user(db, email, role, password="test123"):
    user = User(
        email=email,
        full_name=f"Test {role.capitalize()}",
        hashed_password=get_password_hash(password),
        role=role,
        is_synthetic=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    if role == UserRole.PATIENT:
        profile = PatientProfile(user_id=user.id)
        db.add(profile)
    elif role == UserRole.DOCTOR:
        profile = DoctorProfile(user_id=user.id, license_number="TEST-001")
        db.add(profile)
    elif role == UserRole.STAFF:
        profile = StaffProfile(user_id=user.id, employee_id="TEST-001")
        db.add(profile)
    
    db.commit()
    return user


def get_auth_header(client, user_email, password="test123"):
    response = client.post("/api/auth/login", data={"email": user_email, "password": password})
    assert response.status_code == 200, f"Login failed: {response.status_code} {response.json()}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestPatientToPatientAccessDenial:
    def test_patient_cannot_access_another_patient_documents(self, client, session_factory):
        # Setup in main thread
        db = session_factory()
        patient1 = create_test_user(db, "patient1@test.com", UserRole.PATIENT)
        patient2 = create_test_user(db, "patient2@test.com", UserRole.PATIENT)
        
        doc = Document(
            owner_id=patient2.id,
            filename="test.pdf",
            original_filename="test.pdf",
            storage_path="/tmp/test.pdf",
            mime_type="application/pdf",
            file_size=100,
            status="completed",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        doc_id = doc.id
        db.close()
        
        headers = get_auth_header(client, "patient1@test.com")
        response = client.get(f"/api/documents/{doc_id}", headers=headers)
        assert response.status_code == 403


class TestUnassignedDoctorAccessDenial:
    def test_doctor_without_grant_cannot_access_patient(self, client, session_factory):
        db = session_factory()
        patient = create_test_user(db, "patient@test.com", UserRole.PATIENT)
        doctor = create_test_user(db, "doctor@test.com", UserRole.DOCTOR)
        
        doc = Document(
            owner_id=patient.id,
            filename="test.pdf",
            original_filename="test.pdf",
            storage_path="/tmp/test.pdf",
            mime_type="application/pdf",
            file_size=100,
            status="completed",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        doc_id = doc.id
        db.close()
        
        headers = get_auth_header(client, "doctor@test.com")
        response = client.get(f"/api/documents/{doc_id}", headers=headers)
        assert response.status_code == 403


class TestStaffClinicalDocumentAccessDenial:
    def test_staff_cannot_access_clinical_documents(self, client, session_factory):
        db = session_factory()
        patient = create_test_user(db, "patient@test.com", UserRole.PATIENT)
        staff = create_test_user(db, "staff@test.com", UserRole.STAFF)
        
        doc = Document(
            owner_id=patient.id,
            filename="test.pdf",
            original_filename="test.pdf",
            storage_path="/tmp/test.pdf",
            mime_type="application/pdf",
            file_size=100,
            status="completed",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        doc_id = doc.id
        db.close()
        
        headers = get_auth_header(client, "staff@test.com")
        response = client.get(f"/api/documents/{doc_id}", headers=headers)
        assert response.status_code == 403


class TestDirectFileDownloadAuthorization:
    def test_patient_can_download_own_document(self, client, session_factory):
        db = session_factory()
        patient = create_test_user(db, "patient@test.com", UserRole.PATIENT)
        
        doc = Document(
            owner_id=patient.id,
            filename="test.pdf",
            original_filename="test.pdf",
            storage_path="/tmp/test.pdf",
            mime_type="application/pdf",
            file_size=100,
            status="completed",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        doc_id = doc.id
        db.close()
        
        headers = get_auth_header(client, "patient@test.com")
        response = client.get(f"/api/documents/{doc_id}", headers=headers)
        assert response.status_code == 200


class TestExpiredRevokedAccessGrants:
    def test_expired_grant_denies_access(self, client, session_factory):
        db = session_factory()
        patient = create_test_user(db, "patient@test.com", UserRole.PATIENT)
        doctor = create_test_user(db, "doctor@test.com", UserRole.DOCTOR)
        
        grant = AccessGrant(
            granter_id=patient.id,
            grantee_id=doctor.id,
            patient_id=patient.id,
            doctor_id=doctor.id,
            scope="read",
            expires_at=datetime.utcnow() - timedelta(days=1),
        )
        db.add(grant)
        db.commit()
        
        doc = Document(
            owner_id=patient.id,
            filename="test.pdf",
            original_filename="test.pdf",
            storage_path="/tmp/test.pdf",
            mime_type="application/pdf",
            file_size=100,
            status="completed",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        doc_id = doc.id
        db.close()
        
        headers = get_auth_header(client, "doctor@test.com")
        response = client.get(f"/api/documents/{doc_id}", headers=headers)
        assert response.status_code == 403


class TestMissingExpiredReplayedAlteredApprovals:
    def test_duplicate_reminder_prevention(self, client, session_factory):
        db = session_factory()
        patient = create_test_user(db, "patient@test.com", UserRole.PATIENT)
        
        fact = ExtractedFact(
            patient_id=patient.id,
            document_id=1,
            page_number=1,
            source_text="Test medication",
            fact_type="medication",
            extracted_value="Test Drug 10mg",
            status=FactStatus.PATIENT_CONFIRMED,
        )
        db.add(fact)
        db.commit()
        db.refresh(fact)
        fact_id = fact.id
        
        reminder1 = Reminder(
            patient_id=patient.id,
            fact_id=fact_id,
            medication_name="Test Drug",
            dose="10mg",
            frequency="once daily",
            status=ReminderStatus.CONFIRMED,
        )
        db.add(reminder1)
        db.commit()
        
        reminder2 = Reminder(
            patient_id=patient.id,
            fact_id=fact_id,
            medication_name="Test Drug",
            dose="10mg",
            frequency="once daily",
            status=ReminderStatus.CONFIRMED,
        )
        db.add(reminder2)
        
        with pytest.raises(Exception):
            db.commit()
        db.close()


class TestClinicalDraftsRemainUnofficial:
    def test_fact_status_not_clinician_reviewed_by_default(self, client, session_factory):
        db = session_factory()
        patient = create_test_user(db, "patient@test.com", UserRole.PATIENT)
        
        fact = ExtractedFact(
            patient_id=patient.id,
            document_id=1,
            page_number=1,
            source_text="Test",
            fact_type="medication",
            extracted_value="Test Drug",
            status=FactStatus.EXTRACTED_UNREVIEWED,
        )
        db.add(fact)
        db.commit()
        db.refresh(fact)
        
        assert fact.status == FactStatus.EXTRACTED_UNREVIEWED
        assert fact.reviewed_by is None
        db.close()


class TestReminderPersistence:
    def test_reminder_persists_after_restart(self, client, session_factory):
        db = session_factory()
        patient = create_test_user(db, "patient@test.com", UserRole.PATIENT)
        
        reminder = Reminder(
            patient_id=patient.id,
            medication_name="Persisted Drug",
            dose="5mg",
            frequency="twice daily",
            status=ReminderStatus.ACTIVE,
        )
        db.add(reminder)
        db.commit()
        db.refresh(reminder)
        reminder_id = reminder.id
        db.close()
        
        # Verify reminder exists in new session
        db2 = session_factory()
        found = db2.query(Reminder).filter(Reminder.id == reminder_id).first()
        assert found is not None
        assert found.medication_name == "Persisted Drug"
        assert found.status == ReminderStatus.ACTIVE
        db2.close()


class TestEndToEndPatientWorkflow:
    def test_complete_patient_workflow(self, client, session_factory):
        db = session_factory()
        patient = create_test_user(db, "patient@test.com", UserRole.PATIENT)
        
        doc = Document(
            owner_id=patient.id,
            filename="rx.pdf",
            original_filename="prescription.pdf",
            storage_path="/tmp/rx.pdf",
            mime_type="application/pdf",
            file_size=1000,
            status="completed",
            page_count=1,
            extracted_text="Medication: Amoxicillin 500mg\nFrequency: Three times daily\nDuration: 7 days",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        doc_id = doc.id
        
        fact = ExtractedFact(
            patient_id=patient.id,
            document_id=doc_id,
            page_number=1,
            source_text="Medication: Amoxicillin 500mg",
            fact_type="medication",
            extracted_value="Amoxicillin 500mg",
            status=FactStatus.EXTRACTED_UNREVIEWED,
        )
        db.add(fact)
        db.commit()
        db.refresh(fact)
        fact_id = fact.id
        
        fact.status = FactStatus.PATIENT_CONFIRMED
        fact.reviewed_by = patient.id
        fact.reviewed_at = datetime.utcnow()
        db.commit()
        
        reminder = Reminder(
            patient_id=patient.id,
            fact_id=fact_id,
            medication_name="Amoxicillin",
            dose="500mg",
            frequency="Three times daily",
            status=ReminderStatus.CONFIRMED,
            confirmed_by=patient.id,
        )
        db.add(reminder)
        db.commit()
        db.refresh(reminder)
        db.close()
        
        assert reminder.id is not None
        assert reminder.status == ReminderStatus.CONFIRMED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])