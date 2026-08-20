from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas, auth

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=schemas.LoginResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == payload.username).first()
    if not user or not auth.verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect username or password.")

    token = auth.create_access_token(user)
    return schemas.LoginResponse(
        access_token=token,
        username=user.username,
        role=user.role.value,
        employee_id=user.employee_id,
    )


@router.get("/me", response_model=schemas.CurrentUserOut)
def me(current_user: auth.CurrentUser = Depends(auth.get_current_user)):
    return schemas.CurrentUserOut(
        username=current_user.username,
        role=current_user.role,
        employee_id=current_user.employee_id,
    )
