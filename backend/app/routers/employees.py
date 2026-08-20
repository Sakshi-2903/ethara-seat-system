import random
import string
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import get_db
from app import models, schemas, auth

router = APIRouter(prefix="/employees", tags=["Employees"])


def generate_employee_code(db: Session) -> str:
    while True:
        code = "ETH" + "".join(random.choices(string.digits, k=5))
        if not db.query(models.Employee).filter(models.Employee.employee_code == code).first():
            return code


@router.post("", response_model=schemas.EmployeeOut)
def create_employee(
    payload: schemas.EmployeeCreate,
    db: Session = Depends(get_db),
    _: auth.CurrentUser = Depends(auth.require_write_access),
):
    if db.query(models.Employee).filter(models.Employee.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Duplicate employee email is not allowed")

    if payload.project_id:
        project = db.query(models.Project).filter(models.Project.id == payload.project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

    employee = models.Employee(
        employee_code=generate_employee_code(db),
        name=payload.name,
        email=payload.email,
        department=payload.department,
        role=payload.role,
        joining_date=payload.joining_date,
        project_id=payload.project_id,
        status=payload.status or models.EmploymentStatus.pending_allocation,
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


@router.get("", response_model=List[schemas.EmployeeOut])
def list_employees(
    db: Session = Depends(get_db),
    search: Optional[str] = Query(None, description="Search name, email, or employee code"),
    project_id: Optional[int] = None,
    status: Optional[models.EmploymentStatus] = None,
    department: Optional[str] = None,
    limit: int = Query(50, le=500),
    offset: int = 0,
    _: auth.CurrentUser = Depends(auth.get_current_user),
):
    q = db.query(models.Employee)
    if search:
        like = f"%{search}%"
        q = q.filter(or_(models.Employee.name.ilike(like),
                          models.Employee.email.ilike(like),
                          models.Employee.employee_code.ilike(like)))
    if project_id:
        q = q.filter(models.Employee.project_id == project_id)
    if status:
        q = q.filter(models.Employee.status == status)
    if department:
        q = q.filter(models.Employee.department.ilike(f"%{department}%"))
    return q.order_by(models.Employee.id).offset(offset).limit(limit).all()


@router.get("/{employee_id}", response_model=schemas.EmployeeDetailOut)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    _: auth.CurrentUser = Depends(auth.get_current_user),
):
    employee = db.query(models.Employee).filter(models.Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    result = schemas.EmployeeDetailOut.model_validate(employee)
    if employee.project:
        result.project_name = employee.project.name

    allocation = (
        db.query(models.SeatAllocation)
        .filter(models.SeatAllocation.employee_id == employee_id,
                models.SeatAllocation.allocation_status == models.AllocationStatus.active)
        .first()
    )
    if allocation:
        seat = db.query(models.Seat).filter(models.Seat.id == allocation.seat_id).first()
        if seat:
            result.seat = f"{seat.zone}{seat.bay}-{seat.seat_number}"
            result.floor = seat.floor
            result.zone = seat.zone
    return result


@router.put("/{employee_id}", response_model=schemas.EmployeeOut)
def update_employee(
    employee_id: int,
    payload: schemas.EmployeeUpdate,
    db: Session = Depends(get_db),
    _: auth.CurrentUser = Depends(auth.require_write_access),
):
    employee = db.query(models.Employee).filter(models.Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    if payload.email and payload.email != employee.email:
        if db.query(models.Employee).filter(models.Employee.email == payload.email).first():
            raise HTTPException(status_code=400, detail="Duplicate employee email is not allowed")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(employee, field, value)

    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


@router.delete("/{employee_id}")
def deactivate_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    _: auth.CurrentUser = Depends(auth.require_write_access),
):
    employee = db.query(models.Employee).filter(models.Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    employee.status = models.EmploymentStatus.inactive
    db.add(employee)

    # Release any active seat allocation
    allocation = (
        db.query(models.SeatAllocation)
        .filter(models.SeatAllocation.employee_id == employee_id,
                models.SeatAllocation.allocation_status == models.AllocationStatus.active)
        .first()
    )
    if allocation:
        from app.seat_logic import release_seat
        release_seat(db, employee_id=employee_id)

    db.commit()
    return {"message": f"Employee {employee.name} deactivated"}
