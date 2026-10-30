from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_active_user, check_patient_access, check_document_access
from app.models import User, Document, DocumentStatus, ExtractedFact, FactStatus
from app.schemas import DocumentResponse, ExtractedFactResponse, ExtractedFactUpdate
from app.services.document_service import (
    save_uploaded_file,
    create_document_record,
    process_document,
    get_patient_documents,
    get_document_facts,
    get_patient_facts,
    update_fact_status,
)

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(status_code=403, detail="Only patients can upload documents")
    
    storage_path, filename = save_uploaded_file(file, current_user.id)
    
    mime_type = file.content_type or "application/pdf"
    file_size = os.path.getsize(storage_path)
    
    document = create_document_record(
        db=db,
        owner_id=current_user.id,
        original_filename=file.filename,
        storage_path=storage_path,
        filename=filename,
        mime_type=mime_type,
        file_size=file_size,
    )
    
    process_document(db, document.id)
    
    db.refresh(document)
    return document


@router.get("", response_model=List[DocumentResponse])
def list_documents(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if current_user.role == UserRole.PATIENT:
        return get_patient_documents(db, current_user.id)
    else:
        raise HTTPException(status_code=403, detail="Access denied")


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if document.owner_id != current_user.id:
        if current_user.role == UserRole.DOCTOR:
            from app.models import AccessGrant
            from datetime import datetime
            grant = db.query(AccessGrant).filter(
                AccessGrant.grantee_id == current_user.id,
                AccessGrant.patient_id == document.owner_id,
                AccessGrant.revoked_at.is_(None),
                (AccessGrant.expires_at.is_(None) | (AccessGrant.expires_at > datetime.utcnow()))
            ).first()
            if not grant:
                raise HTTPException(status_code=403, detail="Access denied")
        else:
            raise HTTPException(status_code=403, detail="Access denied")
    
    return document


@router.get("/{document_id}/facts", response_model=List[ExtractedFactResponse])
def get_facts(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if document.owner_id != current_user.id:
        if current_user.role == UserRole.DOCTOR:
            from app.models import AccessGrant
            from datetime import datetime
            grant = db.query(AccessGrant).filter(
                AccessGrant.grantee_id == current_user.id,
                AccessGrant.patient_id == document.owner_id,
                AccessGrant.revoked_at.is_(None),
                (AccessGrant.expires_at.is_(None) | (AccessGrant.expires_at > datetime.utcnow()))
            ).first()
            if not grant:
                raise HTTPException(status_code=403, detail="Access denied")
        else:
            raise HTTPException(status_code=403, detail="Access denied")
    
    return get_document_facts(db, document_id)


@router.get("/patient/{patient_id}/facts", response_model=List[ExtractedFactResponse])
def get_patient_all_facts(
    patient_id: int,
    status: FactStatus = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if current_user.id != patient_id:
        if current_user.role == UserRole.DOCTOR:
            from app.models import AccessGrant
            from datetime import datetime
            grant = db.query(AccessGrant).filter(
                AccessGrant.grantee_id == current_user.id,
                AccessGrant.patient_id == patient_id,
                AccessGrant.revoked_at.is_(None),
                (AccessGrant.expires_at.is_(None) | (AccessGrant.expires_at > datetime.utcnow()))
            ).first()
            if not grant:
                raise HTTPException(status_code=403, detail="Access denied")
        else:
            raise HTTPException(status_code=403, detail="Access denied")
    
    return get_patient_facts(db, patient_id, status)


@router.patch("/facts/{fact_id}", response_model=ExtractedFactResponse)
def update_fact(
    fact_id: int,
    update_data: ExtractedFactUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    fact = db.query(ExtractedFact).filter(ExtractedFact.id == fact_id).first()
    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found")
    
    if fact.patient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    new_status = update_data.status or fact.status
    return update_fact_status(
        db=db,
        fact_id=fact_id,
        status=new_status,
        reviewer_id=current_user.id,
        uncertainty_reason=update_data.uncertainty_reason,
        extracted_value=update_data.extracted_value,
    )


import os