from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app import models, schemas, auth

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=schemas.DashboardSummary)
def summary(db: Session = Depends(get_db), _: auth.CurrentUser = Depends(auth.get_current_user)):
    total_employees = db.query(func.count(models.Employee.id)).filter(
        models.Employee.status != models.EmploymentStatus.inactive
    ).scalar()
    total_seats = db.query(func.count(models.Seat.id)).scalar()
    occupied = db.query(func.count(models.Seat.id)).filter(models.Seat.status == models.SeatStatus.occupied).scalar()
    available = db.query(func.count(models.Seat.id)).filter(models.Seat.status == models.SeatStatus.available).scalar()
    reserved = db.query(func.count(models.Seat.id)).filter(models.Seat.status == models.SeatStatus.reserved).scalar()
    maintenance = db.query(func.count(models.Seat.id)).filter(models.Seat.status == models.SeatStatus.maintenance).scalar()
    pending = db.query(func.count(models.Employee.id)).filter(
        models.Employee.status == models.EmploymentStatus.pending_allocation
    ).scalar()

    return schemas.DashboardSummary(
        total_employees=total_employees,
        total_seats=total_seats,
        occupied_seats=occupied,
        available_seats=available,
        reserved_seats=reserved,
        maintenance_seats=maintenance,
        pending_allocation=pending,
    )


@router.get("/project-utilization", response_model=List[schemas.ProjectUtilization])
def project_utilization(db: Session = Depends(get_db), _: auth.CurrentUser = Depends(auth.get_current_user)):
    results = []
    projects = db.query(models.Project).all()
    for p in projects:
        emp_count = db.query(func.count(models.Employee.id)).filter(
            models.Employee.project_id == p.id,
            models.Employee.status != models.EmploymentStatus.inactive,
        ).scalar()
        seats_occupied = (
            db.query(func.count(models.SeatAllocation.id))
            .filter(models.SeatAllocation.project_id == p.id,
                    models.SeatAllocation.allocation_status == models.AllocationStatus.active)
            .scalar()
        )
        results.append(schemas.ProjectUtilization(
            project_id=p.id, project_name=p.name, employees=emp_count, seats_occupied=seats_occupied
        ))
    return results


@router.get("/floor-utilization", response_model=List[schemas.FloorUtilization])
def floor_utilization(db: Session = Depends(get_db), _: auth.CurrentUser = Depends(auth.get_current_user)):
    floors = [row[0] for row in db.query(models.Seat.floor).distinct().order_by(models.Seat.floor).all()]
    results = []
    for f in floors:
        total = db.query(func.count(models.Seat.id)).filter(models.Seat.floor == f).scalar()
        occupied = db.query(func.count(models.Seat.id)).filter(
            models.Seat.floor == f, models.Seat.status == models.SeatStatus.occupied).scalar()
        available = db.query(func.count(models.Seat.id)).filter(
            models.Seat.floor == f, models.Seat.status == models.SeatStatus.available).scalar()
        reserved = db.query(func.count(models.Seat.id)).filter(
            models.Seat.floor == f, models.Seat.status == models.SeatStatus.reserved).scalar()
        maintenance = db.query(func.count(models.Seat.id)).filter(
            models.Seat.floor == f, models.Seat.status == models.SeatStatus.maintenance).scalar()
        results.append(schemas.FloorUtilization(
            floor=f, total_seats=total, occupied=occupied, available=available,
            reserved=reserved, maintenance=maintenance
        ))
    return results
