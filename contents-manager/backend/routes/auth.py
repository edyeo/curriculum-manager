import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models import User
import auth as auth_utils

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not auth_utils.verify_password(req.password, user.hashed_pw):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = auth_utils.create_token(user.id, user.role)
    return {"access_token": token, "token_type": "bearer", "expires_in": 86400}


@router.get("/me")
def me(current_user: User = Depends(auth_utils.get_current_user)):
    return {"id": current_user.id, "email": current_user.email, "role": current_user.role}
