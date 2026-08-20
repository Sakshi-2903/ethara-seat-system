from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas, seat_logic, auth

router = APIRouter(prefix="/seats", tags=["Seats"])


@router.post("", response_model=schemas.SeatOut)
def create_seat(
    payload: schemas.SeatCreate,
    db: Session = Depends(get_db),
    _: auth.CurrentUser = Depends(auth.require_write_access),
):
    existing = (
        db.query(models.Seat)
        .filter(models.Seat.floor == payload.floor,
                models.Seat.zone == payload.zone,
                models.Seat.seat_number == payload.seat_number)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Duplicate seat number on this floor/zone is not allowed")

    seat = models.Seat(**payload.model_dump())
    db.add(seat)
    db.commit()
    db.refresh(seat)
    return seat


@router.get("", response_model=List[schemas.SeatOut])
def list_seats(
    db: Session = Depends(get_db),
    floor: Optional[int] = None,
    zone: Optional[str] = None,
    status: Optional[models.SeatStatus] = None,
    limit: int = Query(100, le=1000),
    offset: int = 0,
    _: auth.CurrentUser = Depends(auth.get_current_user),
):
    q = db.query(models.Seat)
    if floor is not None:
        q = q.filter(models.Seat.floor == floor)
    if zone:
        q = q.filter(models.Seat.zone == zone)
    if status:
        q = q.filter(models.Seat.status == status)
    return q.order_by(models.Seat.floor, models.Seat.zone, models.Seat.seat_number).offset(offset).limit(limit).all()


@router.get("/available", response_model=List[schemas.SeatOut])
def list_available_seats(
    db: Session = Depends(get_db),
    floor: Optional[int] = None,
    zone: Optional[str] = None,
    limit: int = Query(100, le=1000),
    _: auth.CurrentUser = Depends(auth.get_current_user),
):
    q = db.query(models.Seat).filter(models.Seat.status == models.SeatStatus.available)
    if floor is not None:
        q = q.filter(models.Seat.floor == floor)
    if zone:
        q = q.filter(models.Seat.zone == zone)
    return q.limit(limit).all()


@router.post("/allocate", response_model=schemas.SeatAllocationOut)
def allocate(
    payload: schemas.SeatAllocateRequest,
    db: Session = Depends(get_db),
    current_user: auth.CurrentUser = Depends(auth.get_current_user),
):
    """
    Admin/HR can allocate a seat to any employee. Employees can only book a
    seat for themselves — their own employee_id is used automatically, and
    if they pass someone else's employee_id it's rejected.
    """
    target_employee_id = payload.employee_id

    if current_user.role in ("admin", "hr"):
        if not target_employee_id:
            raise HTTPException(status_code=400, detail="employee_id is required.")
    elif current_user.role == "employee":
        if not current_user.employee_id:
            raise HTTPException(
                status_code=400,
                detail="Your login isn't linked to an employee record, so you can't book a seat. Contact HR.",
            )
        if target_employee_id and target_employee_id != current_user.employee_id:
            raise HTTPException(status_code=403, detail="You can only book a seat for yourself.")
        target_employee_id = current_user.employee_id
    else:
        raise HTTPException(status_code=403, detail="Not authorized to allocate seats.")

    try:
        return seat_logic.allocate_seat(
            db,
            employee_id=target_employee_id,
            seat_id=payload.seat_id,
            preferred_floor=payload.preferred_floor,
            preferred_zone=payload.preferred_zone,
        )
    except seat_logic.SeatAllocationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/release", response_model=schemas.SeatAllocationOut)
def release(
    payload: schemas.SeatReleaseRequest,
    db: Session = Depends(get_db),
    current_user: auth.CurrentUser = Depends(auth.get_current_user),
):
    """
    Admin/HR can release any seat/employee's allocation. Employees can only
    release their own — attempting to target someone else's seat or
    employee_id is rejected.
    """
    employee_id = payload.employee_id
    seat_id = payload.seat_id

    if current_user.role in ("admin", "hr"):
        pass  # unrestricted
    elif current_user.role == "employee":
        if not current_user.employee_id:
            raise HTTPException(
                status_code=400,
                detail="Your login isn't linked to an employee record, so there's no seat to release.",
            )
        if employee_id and employee_id != current_user.employee_id:
            raise HTTPException(status_code=403, detail="You can only release your own seat.")
        if seat_id:
            active = (
                db.query(models.SeatAllocation)
                .filter(
                    models.SeatAllocation.seat_id == seat_id,
                    models.SeatAllocation.allocation_status == models.AllocationStatus.active,
                )
                .first()
            )
            if not active or active.employee_id != current_user.employee_id:
                raise HTTPException(status_code=403, detail="You can only release your own seat.")
        employee_id = current_user.employee_id
    else:
        raise HTTPException(status_code=403, detail="Not authorized to release seats.")

    if not employee_id and not seat_id:
        raise HTTPException(status_code=400, detail="Provide employee_id or seat_id")
    try:
        return seat_logic.release_seat(db, employee_id=employee_id, seat_id=seat_id)
    except seat_logic.SeatAllocationError as e:
        raise HTTPException(status_code=400, detail=str(e))
