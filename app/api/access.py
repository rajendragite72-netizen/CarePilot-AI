from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models import User, UserRole, AccessGrant
from app.schemas import AccessGrantCreate, AccessGrantResponse

router = APIRouter(prefix="/api/access", tags=["access"])


@router.post("/grant", response_model=AccessGrantResponse)
def grant_access(
    grant_data: AccessGrantCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(status_code=403, detail="Only patients can grant access")
    
    if grant_data.patient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Can only grant access to own records")
    
    grantee = db.query(User).filter(User.id == grant_data.grantee_id).first()
    if not grantee:
        raise HTTPException(status_code=404, detail="Grantee not found")
    
    if grantee.role not in [UserRole.DOCTOR, UserRole.STAFF]:
        raise HTTPException(status_code=400, detail="Can only grant access to doctors or staff")
    
    existing = db.query(AccessGrant).filter(
        AccessGrant.patient_id == grant_data.patient_id,
        AccessGrant.grantee_id == grant_data.grantee_id,
        AccessGrant.revoked_at.is_(None)
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Active grant already exists")
    
    grant = AccessGrant(
        granter_id=current_user.id,
        grantee_id=grant_data.grantee_id,
        patient_id=grant_data.patient_id,
        scope=grant_data.scope,
        expires_at=grant_data.expires_at,
    )
    db.add(grant)
    db.commit()
    db.refresh(grant)
    
    return grant


@router.get("/grants", response_model=List[AccessGrantResponse])
def list_grants(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if current_user.role == UserRole.PATIENT:
        grants = db.query(AccessGrant).filter(
            AccessGrant.patient_id == current_user.id
        ).all()
    elif current_user.role in [UserRole.DOCTOR, UserRole.STAFF]:
        grants = db.query(AccessGrant).filter(
            AccessGrant.grantee_id == current_user.id
        ).all()
    else:
        grants = db.query(AccessGrant).all()
    
    return grants


@router.delete("/grants/{grant_id}")
def revoke_grant(
    grant_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    grant = db.query(AccessGrant).filter(AccessGrant.id == grant_id).first()
    if not grant:
        raise HTTPException(status_code=404, detail="Grant not found")
    
    if grant.granter_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to revoke this grant")
    
    grant.revoked_at = datetime.utcnow()
    grant.revoked_by = current_user.id
    db.commit()
    
    return {"message": "Grant revoked"}