from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import verify_password, get_password_hash, create_access_token
from app.core.security import get_current_active_user
from app.models import User, UserRole, PatientProfile, DoctorProfile, StaffProfile
from app.schemas import (
    UserCreate, UserResponse, Token, PatientProfileCreate, PatientProfileResponse,
    DoctorProfileCreate, DoctorProfileResponse, StaffProfileCreate, StaffProfileResponse,
    SyntheticAccount,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user_data.password)
    user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        role=user_data.role,
        is_synthetic=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    if user_data.role == UserRole.PATIENT:
        profile = PatientProfile(user_id=user.id)
        db.add(profile)
    elif user_data.role == UserRole.DOCTOR:
        profile = DoctorProfile(user_id=user.id, license_number="PENDING")
        db.add(profile)
    elif user_data.role == UserRole.STAFF:
        profile = StaffProfile(user_id=user.id, employee_id="PENDING")
        db.add(profile)
    
    db.commit()
    return user


@router.post("/login", response_model=Token)
def login(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.id})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    return current_user


@router.post("/seed-synthetic", response_model=list[SyntheticAccount])
def seed_synthetic_accounts(db: Session = Depends(get_db)):
    """Create synthetic demo accounts for testing."""
    accounts = [
        SyntheticAccount(
            email="patient@carepilot.demo",
            password="patient123",
            role=UserRole.PATIENT,
            full_name="Synthetic Patient John Doe",
        ),
        SyntheticAccount(
            email="doctor@carepilot.demo",
            password="doctor123",
            role=UserRole.DOCTOR,
            full_name="Dr. Synthetic Smith",
        ),
        SyntheticAccount(
            email="staff@carepilot.demo",
            password="staff123",
            role=UserRole.STAFF,
            full_name="Synthetic Staff Nurse",
        ),
        SyntheticAccount(
            email="admin@carepilot.demo",
            password="admin123",
            role=UserRole.ADMIN,
            full_name="Synthetic Admin",
        ),
    ]
    
    created = []
    for acc in accounts:
        existing = db.query(User).filter(User.email == acc.email).first()
        if existing:
            created.append(acc)
            continue
        
        hashed_password = get_password_hash(acc.password)
        user = User(
            email=acc.email,
            full_name=acc.full_name,
            hashed_password=hashed_password,
            role=acc.role,
            is_synthetic=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        if acc.role == UserRole.PATIENT:
            profile = PatientProfile(user_id=user.id, date_of_birth="1980-01-01")
            db.add(profile)
        elif acc.role == UserRole.DOCTOR:
            profile = DoctorProfile(user_id=user.id, license_number="SYNTH-001", specialty="Internal Medicine")
            db.add(profile)
        elif acc.role == UserRole.STAFF:
            profile = StaffProfile(user_id=user.id, employee_id="SYNTH-STAFF-001", department="Nursing")
            db.add(profile)
        
        db.commit()
        created.append(acc)
    
    return created


@router.get("/demo-accounts")
def list_demo_accounts():
    """List demo account credentials."""
    return {
        "patient": {"email": "patient@carepilot.demo", "password": "patient123"},
        "doctor": {"email": "doctor@carepilot.demo", "password": "doctor123"},
        "staff": {"email": "staff@carepilot.demo", "password": "staff123"},
        "admin": {"email": "admin@carepilot.demo", "password": "admin123"},
    }