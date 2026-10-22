
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import bcrypt
from fastapi.security import OAuth2PasswordRequestForm
from app.security import create_access_token, get_current_user
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
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
)->dict:
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not bcrypt.checkpw(form_data.password.encode(), user.hashed_password.encode()):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    info = {"sub": str(user.id)}
    token, expire = create_access_token(info)

    return {"access_token": token, "token_type": "bearer", "expires_in": expire} 
