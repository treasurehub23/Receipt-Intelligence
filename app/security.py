from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv
import jwt
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import User
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
load_dotenv()  # Load environment variables from .env file
import os

from datetime import datetime, timedelta
secret_key = os.getenv("SECRET_KEY")

if not secret_key:
    raise ValueError("SECRET_KEY environment variable is not set.")

def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=30)) -> tuple[str, datetime]:
    """Create a JWT access token."""
    dataa = data.copy()
    expire = datetime.now() + expires_delta
    dataa.update({"exp": expire})
    token = jwt.encode(dataa, secret_key, algorithm="HS256")
    return token, expire

OAuth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
def get_current_user(token: str = Depends(OAuth2_scheme), db:Session = Depends(get_db)) -> User:
    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        subject = payload.get("sub")
        if not isinstance(subject, (str, int)):
            raise  HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_id = int(subject)
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user




print(create_access_token({"sub": "1"}))