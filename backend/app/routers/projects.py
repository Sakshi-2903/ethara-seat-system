from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas, auth

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("", response_model=schemas.ProjectOut)
def create_project(
    payload: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    _: auth.CurrentUser = Depends(auth.require_write_access),
):
    if db.query(models.Project).filter(models.Project.name == payload.name).first():
        raise HTTPException(status_code=400, detail="Project with this name already exists")
    project = models.Project(**payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=List[schemas.ProjectOut])
def list_projects(
    db: Session = Depends(get_db),
    _: auth.CurrentUser = Depends(auth.get_current_user),
):
    return db.query(models.Project).order_by(models.Project.name).all()


@router.get("/{project_id}/employees", response_model=List[schemas.EmployeeOut])
def list_project_employees(
    project_id: int,
    db: Session = Depends(get_db),
    _: auth.CurrentUser = Depends(auth.get_current_user),
):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return db.query(models.Employee).filter(models.Employee.project_id == project_id).all()
