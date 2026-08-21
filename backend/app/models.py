"""
SQLAlchemy models implementing the schema from Section 7 of the assessment doc:
employees, projects, seats, seat_allocations.
"""
import enum
import datetime
from sqlalchemy import (
    Column, Integer, String, Date, DateTime, ForeignKey, Enum, UniqueConstraint, Boolean
)
from sqlalchemy.orm import relationship
from app.database import Base


class EmploymentStatus(str, enum.Enum):
    active = "active"
    pending_allocation = "pending_allocation"
    inactive = "inactive"


class SeatStatus(str, enum.Enum):
    available = "available"
    occupied = "occupied"
    reserved = "reserved"
    maintenance = "maintenance"


class ProjectStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class AllocationStatus(str, enum.Enum):
    active = "active"
    released = "released"


class UserRole(str, enum.Enum):
    admin = "admin"
    employee = "employee"


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), unique=True, nullable=False, index=True)
    description = Column(String(500), default="")
    manager_name = Column(String(120), default="")
    status = Column(Enum(ProjectStatus), default=ProjectStatus.active, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    employees = relationship("Employee", back_populates="project")


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    employee_code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(150), nullable=False, index=True)
    email = Column(String(150), unique=True, nullable=False, index=True)
    department = Column(String(100), nullable=False)
    role = Column(String(100), nullable=False)
    joining_date = Column(Date, nullable=False)
    status = Column(Enum(EmploymentStatus), default=EmploymentStatus.pending_allocation, nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    project = relationship("Project", back_populates="employees")
    allocations = relationship("SeatAllocation", back_populates="employee")


class Seat(Base):
    __tablename__ = "seats"

    id = Column(Integer, primary_key=True, index=True)
    floor = Column(Integer, nullable=False, index=True)
    zone = Column(String(10), nullable=False, index=True)
    bay = Column(String(10), nullable=False)
    seat_number = Column(String(20), nullable=False, index=True)
    status = Column(Enum(SeatStatus), default=SeatStatus.available, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    allocations = relationship("SeatAllocation", back_populates="seat")

    __table_args__ = (
        UniqueConstraint("floor", "zone", "seat_number", name="uq_seat_floor_zone_number"),
    )


class SeatAllocation(Base):
    __tablename__ = "seat_allocations"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    seat_id = Column(Integer, ForeignKey("seats.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    allocation_status = Column(Enum(AllocationStatus), default=AllocationStatus.active, nullable=False)
    allocation_date = Column(DateTime, default=datetime.datetime.utcnow)
    released_date = Column(DateTime, nullable=True)

    employee = relationship("Employee", back_populates="allocations")
    seat = relationship("Seat", back_populates="allocations")


class User(Base):
    """
    Login accounts for the system. Roles: admin can create employees and
    allocate/release seats; employee accounts are read-only (search, dashboard,
    AI assistant, and their own record) and optionally link to an Employee row
    so 'my seat' style queries can auto-fill their identity.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(60), unique=True, nullable=False, index=True)
    password_hash = Column(String(200), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.employee, nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
