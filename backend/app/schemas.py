import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict
from app.models import EmploymentStatus, SeatStatus, ProjectStatus, AllocationStatus


# ---------- Project ----------
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    manager_name: Optional[str] = ""
    status: Optional[ProjectStatus] = ProjectStatus.active


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str
    manager_name: str
    status: ProjectStatus
    created_at: datetime.datetime


# ---------- Employee ----------
class EmployeeCreate(BaseModel):
    name: str
    email: EmailStr
    department: str
    role: str
    joining_date: datetime.date
    project_id: Optional[int] = None
    status: Optional[EmploymentStatus] = EmploymentStatus.pending_allocation


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    department: Optional[str] = None
    role: Optional[str] = None
    project_id: Optional[int] = None
    status: Optional[EmploymentStatus] = None


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    employee_code: str
    name: str
    email: str
    department: str
    role: str
    joining_date: datetime.date
    status: EmploymentStatus
    project_id: Optional[int]
    created_at: datetime.datetime
    updated_at: datetime.datetime


class EmployeeDetailOut(EmployeeOut):
    project_name: Optional[str] = None
    seat: Optional[str] = None
    floor: Optional[int] = None
    zone: Optional[str] = None


# ---------- Seat ----------
class SeatCreate(BaseModel):
    floor: int
    zone: str
    bay: str
    seat_number: str
    status: Optional[SeatStatus] = SeatStatus.available


class SeatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    floor: int
    zone: str
    bay: str
    seat_number: str
    status: SeatStatus
    created_at: datetime.datetime


class SeatDetailOut(SeatOut):
    employee_name: Optional[str] = None
    project_name: Optional[str] = None


class SeatAllocateRequest(BaseModel):
    employee_id: Optional[int] = None  # required for admin/hr; auto-filled from login for employees
    seat_id: Optional[int] = None  # if omitted, system auto-suggests
    preferred_zone: Optional[str] = None
    preferred_floor: Optional[int] = None


class SeatReleaseRequest(BaseModel):
    employee_id: Optional[int] = None
    seat_id: Optional[int] = None


class SeatAllocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    employee_id: int
    seat_id: int
    project_id: Optional[int]
    allocation_status: AllocationStatus
    allocation_date: datetime.datetime
    released_date: Optional[datetime.datetime]


# ---------- Dashboard ----------
class DashboardSummary(BaseModel):
    total_employees: int
    total_seats: int
    occupied_seats: int
    available_seats: int
    reserved_seats: int
    maintenance_seats: int
    pending_allocation: int


class ProjectUtilization(BaseModel):
    project_id: int
    project_name: str
    employees: int
    seats_occupied: int


class FloorUtilization(BaseModel):
    floor: int
    total_seats: int
    occupied: int
    available: int
    reserved: int
    maintenance: int


# ---------- Auth ----------
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str
    employee_id: Optional[int] = None


class CurrentUserOut(BaseModel):
    username: str
    role: str
    employee_id: Optional[int] = None


# ---------- AI Assistant ----------
class AIQueryRequest(BaseModel):
    query: str
    email: Optional[str] = None
    employee_id: Optional[int] = None


class AIQueryResponse(BaseModel):
    answer: str
    intent: Optional[str] = None
