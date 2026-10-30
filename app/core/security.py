from typing import Optional, List
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import decode_token
from app.models import User, UserRole, AccessGrant
from datetime import datetime

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception
    user_id: int = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    return current_user


def require_role(allowed_roles: List[UserRole]):
    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    return role_checker


async def check_patient_access(
    patient_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> User:
    if current_user.id == patient_id:
        return current_user
    
    if current_user.role == UserRole.DOCTOR:
        grant = db.query(AccessGrant).filter(
            AccessGrant.grantee_id == current_user.id,
            AccessGrant.patient_id == patient_id,
            AccessGrant.revoked_at.is_(None),
            (AccessGrant.expires_at.is_(None) | (AccessGrant.expires_at > datetime.utcnow()))
        ).first()
        if grant:
            return current_user
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied to patient records"
    )


async def check_document_access(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    from app.models import Document
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if document.owner_id == current_user.id:
        return document
    
    if current_user.role == UserRole.DOCTOR:
        grant = db.query(AccessGrant).filter(
            AccessGrant.grantee_id == current_user.id,
            AccessGrant.patient_id == document.owner_id,
            AccessGrant.revoked_at.is_(None),
            (AccessGrant.expires_at.is_(None) | (AccessGrant.expires_at > datetime.utcnow()))
        ).first()
        if grant:
            return document
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied to document"
    )