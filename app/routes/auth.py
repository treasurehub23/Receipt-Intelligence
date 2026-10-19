
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import bcrypt

from db.database import get_db
from db.models import User
from app.schemas import RegisterUserRequest, RegisterUserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=RegisterUserResponse)
def register_user(
    payload: RegisterUserRequest,
    db: Session = Depends(get_db),
):
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(status_code=409, detail="User already exists")

    # Hash the password
    hashed_password = bcrypt.hashpw(payload.password.encode(), bcrypt.gensalt()).decode()

    # Create new user
    new_user = User(
        email=payload.email,
        hashed_password=hashed_password,
    )
    db.add(new_user)
    try:
        db.commit()
        db.refresh(new_user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="User with this email already exists.")

    return RegisterUserResponse(
        id=new_user.id,
        email=new_user.email,
        created_at=new_user.created_at,
    )


@router.post("/login")
def login_user(
    payload: RegisterUserRequest,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not bcrypt.checkpw(payload.password.encode(), user.hashed_password.encode()):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return {"message": "Login successful", "user_id": user.id}