"""
Seed data generator for the Ethara Seat Allocation System.
Meets Section 6 requirements:
  - 5,000 employees
  - Minimum 5 floors
  - Minimum 10 zones
  - Minimum 5,500 seats
  - Minimum 10 projects
  - At least 500 available seats
  - At least 100 reserved seats
  - At least 50 employees pending allocation

Uses chunked bulk inserts (not one-row-at-a-time ORM adds) so this runs
quickly even against a remote database with real network latency, and
prints progress as it goes so it's obvious it's still working rather than
looking "stuck."

Run with: python seed.py
"""
import random
import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from faker import Faker
from sqlalchemy import insert
from app.database import Base, engine, SessionLocal
from app import models, auth

fake = Faker()
Faker.seed(42)
random.seed(42)

PROJECT_NAMES = [
    "Indigo", "Indreed", "Mydreed", "Preed", "Serfy",
    "Oreed", "Bedegreed", "Opreed", "Serry", "Kaary", "Mered",
]

DEPARTMENTS = ["Engineering", "HR", "Finance", "Operations", "Sales", "Marketing", "Design", "Support"]
ROLES = ["Software Engineer", "Senior Engineer", "Analyst", "Manager", "Associate", "Team Lead", "Consultant"]

NUM_EMPLOYEES = 5000
FLOORS = list(range(1, 6))  # 5 floors
ZONES = [chr(65 + i) for i in range(10)]  # Zones A-J (10 zones)
TOTAL_SEATS_TARGET = 5600  # comfortably above the 5,500 minimum
CHUNK = 500  # rows per batch — keeps each network round trip small


def reset_db():
    print("Dropping and recreating tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def re_slug(name: str) -> str:
    return "".join(c.lower() if c.isalnum() else "." for c in name).strip(".").replace("..", ".")


def seed_projects(db):
    print(f"Creating {len(PROJECT_NAMES)} projects...")
    rows = [
        {
            "name": name,
            "description": f"{name} product engineering initiative",
            "manager_name": fake.name(),
            "status": models.ProjectStatus.active,
        }
        for name in PROJECT_NAMES
    ]
    db.execute(insert(models.Project), rows)
    db.commit()
    return db.query(models.Project).order_by(models.Project.id).all()


def seed_seats(db):
    print("Creating seats...")
    combos = [(f, z) for f in FLOORS for z in ZONES]
    seats_per_combo = TOTAL_SEATS_TARGET // len(combos)
    remainder = TOTAL_SEATS_TARGET - seats_per_combo * len(combos)
    bays = ["1", "2", "3", "4", "5"]

    rows = []
    for idx, (floor, zone) in enumerate(combos):
        count = seats_per_combo + (1 if idx < remainder else 0)
        for i in range(1, count + 1):
            rows.append({
                "floor": floor,
                "zone": zone,
                "bay": bays[(i - 1) % len(bays)],
                "seat_number": f"{i:03d}",
                "status": models.SeatStatus.available,
            })

    for start in range(0, len(rows), CHUNK):
        chunk = rows[start:start + CHUNK]
        db.execute(insert(models.Seat), chunk)
        db.commit()
        print(f"  ...{min(start + CHUNK, len(rows))}/{len(rows)} seats inserted")

    seats = db.query(models.Seat).order_by(models.Seat.id).all()
    print(f"Created {len(seats)} seats across {len(FLOORS)} floors and {len(ZONES)} zones.")
    return seats


def seed_employees_and_allocations(db, projects, seats):
    print(f"Creating {NUM_EMPLOYEES} employees and allocating seats...")

    # Pick 120 seats to mark reserved and 30 to mark maintenance (bulk UPDATE,
    # not per-object mutation + commit).
    random.shuffle(seats)
    reserved_ids = [s.id for s in seats[:120]]
    maintenance_ids = [s.id for s in seats[120:150]]

    if reserved_ids:
        db.execute(
            models.Seat.__table__.update()
            .where(models.Seat.id.in_(reserved_ids))
            .values(status=models.SeatStatus.reserved)
        )
    if maintenance_ids:
        db.execute(
            models.Seat.__table__.update()
            .where(models.Seat.id.in_(maintenance_ids))
            .values(status=models.SeatStatus.maintenance)
        )
    db.commit()

    reserved_or_maintenance = set(reserved_ids) | set(maintenance_ids)
    allocatable_seats = [s for s in seats if s.id not in reserved_or_maintenance]

    # Keep 600 seats free so "available seats" comfortably clears the minimum.
    random.shuffle(allocatable_seats)
    seats_for_allocation = allocatable_seats[600:]

    used_emails = set()
    employee_rows = []
    meta = []  # (project, is_pending) per row, same order as employee_rows
    pending_target = 60

    for i in range(NUM_EMPLOYEES):
        name = fake.name()
        base_email = re_slug(name)
        email = f"{base_email}@ethara.ai"
        suffix = 1
        while email in used_emails:
            suffix += 1
            email = f"{base_email}{suffix}@ethara.ai"
        used_emails.add(email)

        joining_date = fake.date_between(start_date="-3y", end_date="today")
        project = random.choice(projects)
        is_pending = i < pending_target

        employee_rows.append({
            "employee_code": f"ETH{i+10001}",
            "name": name,
            "email": email,
            "department": random.choice(DEPARTMENTS),
            "role": random.choice(ROLES),
            "joining_date": joining_date,
            "status": models.EmploymentStatus.pending_allocation if is_pending else models.EmploymentStatus.active,
            "project_id": project.id,
        })
        meta.append((project, is_pending))

    print("Inserting employees...")
    for start in range(0, len(employee_rows), CHUNK):
        chunk = employee_rows[start:start + CHUNK]
        db.execute(insert(models.Employee), chunk)
        db.commit()
        print(f"  ...{min(start + CHUNK, len(employee_rows))}/{len(employee_rows)} employees inserted")

    # Bulk re-query once — insertion order matches ascending id order for a
    # fresh auto-increment table, so this preserves the pairing with `meta`.
    refreshed = db.query(models.Employee).order_by(models.Employee.id).all()
    employees = [(emp, project, is_pending) for emp, (project, is_pending) in zip(refreshed, meta)]

    print("Allocating seats to active employees...")
    seat_pointer = 0
    allocation_rows = []
    seat_ids_to_occupy = []
    employee_ids_left_pending = []

    for employee, project, is_pending in employees:
        if is_pending:
            continue
        if seat_pointer >= len(seats_for_allocation):
            employee_ids_left_pending.append(employee.id)
            continue
        seat = seats_for_allocation[seat_pointer]
        seat_pointer += 1
        seat_ids_to_occupy.append(seat.id)
        allocation_rows.append({
            "employee_id": employee.id,
            "seat_id": seat.id,
            "project_id": project.id,
            "allocation_status": models.AllocationStatus.active,
            "allocation_date": datetime.datetime.combine(employee.joining_date, datetime.time(9, 0)),
        })

    for start in range(0, len(allocation_rows), CHUNK):
        chunk = allocation_rows[start:start + CHUNK]
        db.execute(insert(models.SeatAllocation), chunk)
        db.commit()
        print(f"  ...{min(start + CHUNK, len(allocation_rows))}/{len(allocation_rows)} allocations created")

    for start in range(0, len(seat_ids_to_occupy), CHUNK):
        chunk_ids = seat_ids_to_occupy[start:start + CHUNK]
        db.execute(
            models.Seat.__table__.update()
            .where(models.Seat.id.in_(chunk_ids))
            .values(status=models.SeatStatus.occupied)
        )
    db.commit()

    if employee_ids_left_pending:
        db.execute(
            models.Employee.__table__.update()
            .where(models.Employee.id.in_(employee_ids_left_pending))
            .values(status=models.EmploymentStatus.pending_allocation)
        )
        db.commit()

    total_pending = sum(1 for _, _, p in employees if p) + len(employee_ids_left_pending)
    print(f"Allocated seats to {len(allocation_rows)} employees.")
    print(f"{total_pending} employees left pending allocation (new joiners).")


def seed_users(db, sample_employee):
    print("Creating demo login accounts...")
    demo_accounts = [
        ("admin", "admin123", models.UserRole.admin, None),
        ("hr", "hr123", models.UserRole.hr, None),
        ("employee", "employee123", models.UserRole.employee,
         sample_employee.id if sample_employee else None),
    ]
    rows = [
        {
            "username": username,
            "password_hash": auth.hash_password(password),
            "role": role,
            "employee_id": employee_id,
        }
        for username, password, role, employee_id in demo_accounts
    ]
    db.execute(insert(models.User), rows)
    db.commit()
    print("Demo accounts: admin/admin123, hr/hr123, employee/employee123")


def print_summary(db):
    from sqlalchemy import func
    total_employees = db.query(func.count(models.Employee.id)).scalar()
    total_seats = db.query(func.count(models.Seat.id)).scalar()
    available = db.query(func.count(models.Seat.id)).filter(models.Seat.status == models.SeatStatus.available).scalar()
    occupied = db.query(func.count(models.Seat.id)).filter(models.Seat.status == models.SeatStatus.occupied).scalar()
    reserved = db.query(func.count(models.Seat.id)).filter(models.Seat.status == models.SeatStatus.reserved).scalar()
    maintenance = db.query(func.count(models.Seat.id)).filter(models.Seat.status == models.SeatStatus.maintenance).scalar()
    pending = db.query(func.count(models.Employee.id)).filter(
        models.Employee.status == models.EmploymentStatus.pending_allocation).scalar()
    projects = db.query(func.count(models.Project.id)).scalar()
    floors = db.query(models.Seat.floor).distinct().count()
    zones = db.query(models.Seat.zone).distinct().count()

    print("\n=== SEED DATA SUMMARY ===")
    print(f"Employees:            {total_employees}")
    print(f"Projects:             {projects}")
    print(f"Floors:               {floors}")
    print(f"Zones:                {zones}")
    print(f"Total seats:          {total_seats}")
    print(f"  Available:          {available}")
    print(f"  Occupied:           {occupied}")
    print(f"  Reserved:           {reserved}")
    print(f"  Maintenance:        {maintenance}")
    print(f"Pending allocation:   {pending}")
    print("=========================\n")


if __name__ == "__main__":
    reset_db()
    db = SessionLocal()
    try:
        projects = seed_projects(db)
        seats = seed_seats(db)
        seed_employees_and_allocations(db, projects, seats)

        sample_employee = (
            db.query(models.Employee)
            .filter(models.Employee.status == models.EmploymentStatus.active)
            .first()
        )
        seed_users(db, sample_employee)

        print_summary(db)
    finally:
        db.close()