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

Run with: python seed.py
"""
import random
import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from faker import Faker
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
SEATS_PER_FLOOR_ZONE = 11  # 5 floors * 10 zones * 11 = 550/floor*zone-combo -> total 5*10*11=550... adjust below

TOTAL_SEATS_TARGET = 5600  # comfortably above the 5,500 minimum


def reset_db():
    print("Dropping and recreating tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def seed_projects(db):
    print(f"Creating {len(PROJECT_NAMES)} projects...")
    projects = []
    for name in PROJECT_NAMES:
        p = models.Project(
            name=name,
            description=f"{name} product engineering initiative",
            manager_name=fake.name(),
            status=models.ProjectStatus.active,
        )
        db.add(p)
        projects.append(p)
    db.commit()
    for p in projects:
        db.refresh(p)
    return projects


def seed_seats(db):
    print("Creating seats...")
    seats = []
    seat_counter_per_floor_zone = {}

    # Distribute seats across floors/zones until we reach the target total
    combos = [(f, z) for f in FLOORS for z in ZONES]
    seats_per_combo = TOTAL_SEATS_TARGET // len(combos)  # base count
    remainder = TOTAL_SEATS_TARGET - seats_per_combo * len(combos)

    bays = ["1", "2", "3", "4", "5"]

    seat_number_global = 0
    for idx, (floor, zone) in enumerate(combos):
        count = seats_per_combo + (1 if idx < remainder else 0)
        for i in range(1, count + 1):
            bay = bays[(i - 1) % len(bays)]
            seat_number = f"{i:03d}"
            seat = models.Seat(
                floor=floor,
                zone=zone,
                bay=bay,
                seat_number=seat_number,
                status=models.SeatStatus.available,
            )
            db.add(seat)
            seats.append(seat)
            seat_number_global += 1

    db.commit()
    for s in seats:
        db.refresh(s)
    print(f"Created {len(seats)} seats across {len(FLOORS)} floors and {len(ZONES)} zones.")
    return seats


def seed_employees_and_allocations(db, projects, seats):
    print(f"Creating {NUM_EMPLOYEES} employees and allocating seats...")

    # Reserve at least 120 seats and put ~30 into maintenance, leave 550+ available
    random.shuffle(seats)
    reserved_seats = seats[:120]
    maintenance_seats = seats[120:150]
    for s in reserved_seats:
        s.status = models.SeatStatus.reserved
    for s in maintenance_seats:
        s.status = models.SeatStatus.maintenance
    db.add_all(reserved_seats + maintenance_seats)
    db.commit()

    allocatable_seats = [s for s in seats if s.status == models.SeatStatus.available]

    # Reserve 600 seats to stay empty (available) so we comfortably clear the
    # "at least 500 available seats" requirement after allocations.
    random.shuffle(allocatable_seats)
    seats_to_keep_free = allocatable_seats[:600]
    seats_for_allocation = allocatable_seats[600:]

    free_seat_ids = {s.id for s in seats_to_keep_free}
    seat_pointer = 0

    used_emails = set()
    employees = []
    pending_target = 60  # comfortably above the 50 minimum

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

        is_pending = i < pending_target  # first N employees are new joiners pending allocation

        employee = models.Employee(
            employee_code=f"ETH{i+10001}",
            name=name,
            email=email,
            department=random.choice(DEPARTMENTS),
            role=random.choice(ROLES),
            joining_date=joining_date,
            status=models.EmploymentStatus.pending_allocation if is_pending else models.EmploymentStatus.active,
            project_id=project.id,
        )
        db.add(employee)
        employees.append((employee, project, is_pending))

    db.commit()
    for employee, _, _ in employees:
        db.refresh(employee)

    print("Allocating seats to active employees...")
    allocations = []
    for employee, project, is_pending in employees:
        if is_pending:
            continue
        if seat_pointer >= len(seats_for_allocation):
            # Ran out of allocatable seats; leave remaining employees pending
            employee.status = models.EmploymentStatus.pending_allocation
            db.add(employee)
            continue

        seat = seats_for_allocation[seat_pointer]
        seat_pointer += 1
        seat.status = models.SeatStatus.occupied
        db.add(seat)

        allocation = models.SeatAllocation(
            employee_id=employee.id,
            seat_id=seat.id,
            project_id=project.id,
            allocation_status=models.AllocationStatus.active,
            allocation_date=datetime.datetime.combine(employee.joining_date, datetime.time(9, 0)),
        )
        allocations.append(allocation)

    db.add_all(allocations)
    db.commit()
    print(f"Allocated seats to {len(allocations)} employees.")
    print(f"{sum(1 for _, _, p in employees if p)} employees left pending allocation (new joiners).")


def seed_users(db, sample_employee):
    print("Creating demo login accounts...")
    demo_accounts = [
        ("admin", "admin123", models.UserRole.admin, None),
        ("hr", "hr123", models.UserRole.hr, None),
        ("employee", "employee123", models.UserRole.employee,
         sample_employee.id if sample_employee else None),
    ]
    for username, password, role, employee_id in demo_accounts:
        db.add(models.User(
            username=username,
            password_hash=auth.hash_password(password),
            role=role,
            employee_id=employee_id,
        ))
    db.commit()
    print("Demo accounts: admin/admin123, hr/hr123, employee/employee123")


def re_slug(name: str) -> str:
    return "".join(c.lower() if c.isalnum() else "." for c in name).strip(".").replace("..", ".")


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

        # Pick an already-seated employee so the demo "employee" account
        # has an interesting seat/project to query via 'Where is my seat?'
        sample_employee = (
            db.query(models.Employee)
            .filter(models.Employee.status == models.EmploymentStatus.active)
            .first()
        )
        seed_users(db, sample_employee)

        print_summary(db)
    finally:
        db.close()
