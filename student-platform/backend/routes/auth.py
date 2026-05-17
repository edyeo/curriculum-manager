from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from database import get_db
from models import Student
import auth as auth_utils

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    name: str
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    student_id: int
    token: str
    name: str


@router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(Student).filter(Student.email == req.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    student = Student(
        email=req.email,
        name=req.name,
        hashed_pw=auth_utils.hash_password(req.password),
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return TokenResponse(student_id=student.id, token=auth_utils.create_token(student.id), name=student.name)


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.email == req.email).first()
    if not student or not auth_utils.verify_password(req.password, student.hashed_pw):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(student_id=student.id, token=auth_utils.create_token(student.id), name=student.name)


@router.get("/me")
def me(current_student: Student = Depends(auth_utils.get_current_student)):
    return {"id": current_student.id, "email": current_student.email, "name": current_student.name}
