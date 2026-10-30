import os
import uuid
import shutil
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException
from app.core.config import settings
from app.models import Document, DocumentStatus, ExtractedFact, FactStatus, TimelineEvent, User
from app.services.pdf_service import extract_text_from_pdf, extract_medical_facts, validate_pdf_file


def save_uploaded_file(file: UploadFile, owner_id: int) -> tuple[str, str]:
    """Save uploaded file and return (storage_path, filename)."""
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in [".pdf", ".txt"]:
        raise HTTPException(status_code=400, detail="Only PDF and TXT files are supported")
    
    unique_filename = f"{owner_id}_{uuid.uuid4().hex}{file_ext}"
    storage_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
    
    with open(storage_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    file_size = os.path.getsize(storage_path)
    if file_size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        os.remove(storage_path)
        raise HTTPException(status_code=400, detail=f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE_MB}MB")
    
    return storage_path, unique_filename


def create_document_record(
    db: Session,
    owner_id: int,
    original_filename: str,
    storage_path: str,
    filename: str,
    mime_type: str,
    file_size: int
) -> Document:
    """Create document record in database."""
    document = Document(
        owner_id=owner_id,
        original_filename=original_filename,
        storage_path=storage_path,
        filename=filename,
        mime_type=mime_type,
        file_size=file_size,
        status=DocumentStatus.UPLOADED,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def process_document(db: Session, document_id: int) -> Document:
    """Process document: extract text and medical facts."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    document.status = DocumentStatus.PROCESSING
    db.commit()
    
    try:
        if document.mime_type == "application/pdf":
            full_text, page_texts, page_count = extract_text_from_pdf(document.storage_path)
            document.page_count = page_count
        else:
            with open(document.storage_path, "r") as f:
                full_text = f.read()
            page_texts = [{"page_number": 1, "text": full_text}]
            document.page_count = 1
        
        document.extracted_text = full_text
        document.status = DocumentStatus.COMPLETED
        db.commit()
        
        facts = extract_medical_facts(page_texts)
        for fact_data in facts:
            fact = ExtractedFact(
                patient_id=document.owner_id,
                document_id=document.id,
                page_number=fact_data["page_number"],
                section=fact_data["section"],
                source_text=fact_data["source_text"],
                fact_type=fact_data["fact_type"],
                extracted_value=fact_data["extracted_value"],
                uncertainty_reason=fact_data["uncertainty_reason"],
                status=FactStatus.UNCERTAIN if fact_data["uncertainty_reason"] else FactStatus.EXTRACTED_UNREVIEWED,
            )
            db.add(fact)
        
        if facts:
            event = TimelineEvent(
                patient_id=document.owner_id,
                document_id=document.id,
                event_type="document_uploaded",
                title=f"Uploaded: {document.original_filename}",
                description=f"Extracted {len(facts)} medical facts for review",
                event_date=datetime.utcnow(),
                metadata={"fact_count": len(facts)},
            )
            db.add(event)
        
        db.commit()
        return document
    
    except Exception as e:
        document.status = DocumentStatus.FAILED
        document.processing_error = str(e)
        db.commit()
        raise


def get_patient_documents(db: Session, patient_id: int) -> List[Document]:
    """Get all documents for a patient."""
    return db.query(Document).filter(Document.owner_id == patient_id).order_by(Document.created_at.desc()).all()


def get_document_facts(db: Session, document_id: int) -> List[ExtractedFact]:
    """Get all extracted facts for a document."""
    return db.query(ExtractedFact).filter(ExtractedFact.document_id == document_id).all()


def get_patient_facts(db: Session, patient_id: int, status: Optional[FactStatus] = None) -> List[ExtractedFact]:
    """Get all facts for a patient, optionally filtered by status."""
    query = db.query(ExtractedFact).filter(ExtractedFact.patient_id == patient_id)
    if status:
        query = query.filter(ExtractedFact.status == status)
    return query.order_by(ExtractedFact.created_at.desc()).all()


def update_fact_status(
    db: Session,
    fact_id: int,
    status: FactStatus,
    reviewer_id: int,
    uncertainty_reason: Optional[str] = None,
    extracted_value: Optional[str] = None
) -> ExtractedFact:
    """Update fact review status."""
    fact = db.query(ExtractedFact).filter(ExtractedFact.id == fact_id).first()
    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found")
    
    fact.status = status
    fact.reviewed_by = reviewer_id
    fact.reviewed_at = datetime.utcnow()
    if uncertainty_reason is not None:
        fact.uncertainty_reason = uncertainty_reason
    if extracted_value is not None:
        fact.extracted_value = extracted_value
    
    db.commit()
    db.refresh(fact)
    return fact