"""
Core seat allocation business rules (Section 8 of the assessment doc):
- One employee -> one active seat.
- One seat -> one active employee.
- Released seats become available again.
- Reserved seats cannot be allocated unless status is changed first.
- New joiners are prioritized for seats near their project team (same floor/zone
  as teammates on the same project); falls back to nearest alternate zone/floor,
  then any available seat.
"""
import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from app import models


class SeatAllocationError(Exception):
    pass


def find_best_seat_for_employee(db: Session, employee: models.Employee,
                                 preferred_floor: int = None,
                                 preferred_zone: str = None) -> models.Seat:
    """
    Seat suggestion algorithm:
    1. If the caller gave an explicit preferred_floor and/or preferred_zone,
       that always wins — an explicit request is never overridden by
       project-based inference.
    2. Otherwise, if the employee has a project, prefer a floor/zone where
       teammates on the same project already sit (most common floor+zone
       combo for that project).
    3. Try to find an available seat in the resulting floor+zone.
    4. If none, fall back to same floor (any zone).
    5. If none, fall back to any available seat anywhere (alternate zone suggestion).
    """
    target_floor, target_zone = preferred_floor, preferred_zone

    if employee.project_id and target_floor is None and target_zone is None:
        # No explicit preference given — infer from where the project team sits.
        row = (
            db.query(models.Seat.floor, models.Seat.zone, func.count(models.Seat.id).label("cnt"))
            .join(models.SeatAllocation, models.SeatAllocation.seat_id == models.Seat.id)
            .filter(
                models.SeatAllocation.project_id == employee.project_id,
                models.SeatAllocation.allocation_status == models.AllocationStatus.active,
            )
            .group_by(models.Seat.floor, models.Seat.zone)
            .order_by(func.count(models.Seat.id).desc())
            .first()
        )
        if row:
            target_floor, target_zone = row[0], row[1]

    # Step 3: exact floor + zone match
    if target_floor is not None and target_zone:
        seat = (
            db.query(models.Seat)
            .filter(
                models.Seat.status == models.SeatStatus.available,
                models.Seat.floor == target_floor,
                models.Seat.zone == target_zone,
            )
            .first()
        )
        if seat:
            return seat

    # Step 4: same floor, any zone
    if target_floor is not None:
        seat = (
            db.query(models.Seat)
            .filter(
                models.Seat.status == models.SeatStatus.available,
                models.Seat.floor == target_floor,
            )
            .first()
        )
        if seat:
            return seat

    # Step 5: any available seat (alternate zone/floor)
    seat = db.query(models.Seat).filter(models.Seat.status == models.SeatStatus.available).first()
    return seat


def allocate_seat(db: Session, employee_id: int, seat_id: int = None,
                   preferred_floor: int = None, preferred_zone: str = None) -> models.SeatAllocation:
    employee = db.query(models.Employee).filter(models.Employee.id == employee_id).first()
    if not employee:
        raise SeatAllocationError("Employee not found")

    # Rule: one employee can have only one active seat
    existing = (
        db.query(models.SeatAllocation)
        .filter(
            models.SeatAllocation.employee_id == employee_id,
            models.SeatAllocation.allocation_status == models.AllocationStatus.active,
        )
        .first()
    )
    if existing:
        raise SeatAllocationError(
            f"Employee already has an active seat allocation (allocation id {existing.id}). "
            "Release it before allocating a new one."
        )

    if seat_id:
        seat = db.query(models.Seat).filter(models.Seat.id == seat_id).first()
        if not seat:
            raise SeatAllocationError("Seat not found")
        if seat.status != models.SeatStatus.available:
            raise SeatAllocationError(f"Seat {seat.seat_number} is not available (status: {seat.status.value})")
    else:
        seat = find_best_seat_for_employee(db, employee, preferred_floor, preferred_zone)
        if not seat:
            raise SeatAllocationError("No available seats in the system")

    # Rule: one seat can be allocated to only one active employee (enforced by status check above)
    seat.status = models.SeatStatus.occupied

    allocation = models.SeatAllocation(
        employee_id=employee.id,
        seat_id=seat.id,
        project_id=employee.project_id,
        allocation_status=models.AllocationStatus.active,
        allocation_date=datetime.datetime.utcnow(),
    )
    employee.status = models.EmploymentStatus.active

    db.add(allocation)
    db.add(seat)
    db.add(employee)
    db.commit()
    db.refresh(allocation)
    return allocation


def release_seat(db: Session, employee_id: int = None, seat_id: int = None) -> models.SeatAllocation:
    query = db.query(models.SeatAllocation).filter(
        models.SeatAllocation.allocation_status == models.AllocationStatus.active
    )
    if employee_id:
        query = query.filter(models.SeatAllocation.employee_id == employee_id)
    if seat_id:
        query = query.filter(models.SeatAllocation.seat_id == seat_id)

    allocation = query.first()
    if not allocation:
        raise SeatAllocationError("No active allocation found for the given employee/seat")

    allocation.allocation_status = models.AllocationStatus.released
    allocation.released_date = datetime.datetime.utcnow()

    seat = db.query(models.Seat).filter(models.Seat.id == allocation.seat_id).first()
    if seat:
        # Rule: released seats become available again
        seat.status = models.SeatStatus.available
        db.add(seat)

    employee = db.query(models.Employee).filter(models.Employee.id == allocation.employee_id).first()
    if employee:
        employee.status = models.EmploymentStatus.pending_allocation
        db.add(employee)

    db.add(allocation)
    db.commit()
    db.refresh(allocation)
    return allocation
