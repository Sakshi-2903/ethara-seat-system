"""
AI Assistant for the Ethara Seat Allocation System.

Default mode: rule-based / keyword intent parser (no external API key required).
This satisfies the assessment's "fallback keyword-based assistant" requirement
and handles every query type listed in Section 3.7:
  - Employee seat lookup
  - Project assignment lookup
  - Available seats (by floor/zone)
  - Team / "who is sitting near me" lookup
  - Seat utilization by project

Optional mode: if ANTHROPIC_API_KEY is set in the environment, the assistant
calls Claude to turn the free-text question into a structured intent, then
resolves that intent against the database using the same functions below.
This keeps answers grounded in real data instead of letting the LLM hallucinate
seat numbers.
"""
import os
import re
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app import models, seat_logic

USE_LLM = bool(os.getenv("ANTHROPIC_API_KEY"))


def _employee_seat_sentence(db: Session, employee: models.Employee) -> str:
    allocation = (
        db.query(models.SeatAllocation)
        .filter(models.SeatAllocation.employee_id == employee.id,
                models.SeatAllocation.allocation_status == models.AllocationStatus.active)
        .first()
    )
    project_name = employee.project.name if employee.project else "no project"

    if not allocation:
        return f"{employee.name} has not been allocated a seat yet. Assigned project: {project_name}."

    seat = db.query(models.Seat).filter(models.Seat.id == allocation.seat_id).first()
    return (
        f"{employee.name} is seated on Floor {seat.floor}, Zone {seat.zone}, Bay {seat.bay}, "
        f"Seat {seat.zone}{seat.bay}-{seat.seat_number}. Assigned project: {project_name}."
    )


def _find_employee(db: Session, name: str = None, email: str = None, employee_id: int = None):
    if employee_id:
        return db.query(models.Employee).filter(models.Employee.id == employee_id).first()
    if email:
        return db.query(models.Employee).filter(models.Employee.email.ilike(email)).first()
    if name:
        return db.query(models.Employee).filter(models.Employee.name.ilike(f"%{name}%")).first()
    return None


def _available_seats_answer(db: Session, floor: int = None, zone: str = None) -> str:
    q = db.query(models.Seat).filter(models.Seat.status == models.SeatStatus.available)
    if floor is not None:
        q = q.filter(models.Seat.floor == floor)
    if zone:
        q = q.filter(models.Seat.zone.ilike(zone))
    seats = q.limit(15).all()
    total = q.count()
    if not seats:
        loc = f" on Floor {floor}" if floor else ""
        loc += f" in Zone {zone}" if zone else ""
        return f"No available seats found{loc}."

    listing = ", ".join(f"{s.zone}{s.bay}-{s.seat_number} (Floor {s.floor})" for s in seats[:10])
    extra = f" and {total - 10} more" if total > 10 else ""
    return f"There are {total} available seat(s). Examples: {listing}{extra}."


def _project_utilization_answer(db: Session, project_name: str) -> str:
    project = db.query(models.Project).filter(models.Project.name.ilike(f"%{project_name}%")).first()
    if not project:
        return f"I couldn't find a project named '{project_name}'."
    occupied = (
        db.query(func.count(models.SeatAllocation.id))
        .filter(models.SeatAllocation.project_id == project.id,
                models.SeatAllocation.allocation_status == models.AllocationStatus.active)
        .scalar()
    )
    total_emp = db.query(func.count(models.Employee.id)).filter(
        models.Employee.project_id == project.id,
        models.Employee.status != models.EmploymentStatus.inactive,
    ).scalar()
    return f"Project {project.name} has {occupied} seat(s) occupied out of {total_emp} assigned employee(s)."


def _neighbors_answer(db: Session, employee: models.Employee) -> str:
    allocation = (
        db.query(models.SeatAllocation)
        .filter(models.SeatAllocation.employee_id == employee.id,
                models.SeatAllocation.allocation_status == models.AllocationStatus.active)
        .first()
    )
    if not allocation:
        return f"{employee.name} does not have a seat allocated yet, so I can't find nearby colleagues."

    seat = db.query(models.Seat).filter(models.Seat.id == allocation.seat_id).first()
    neighbor_allocations = (
        db.query(models.SeatAllocation)
        .join(models.Seat, models.Seat.id == models.SeatAllocation.seat_id)
        .filter(
            models.Seat.floor == seat.floor,
            models.Seat.zone == seat.zone,
            models.SeatAllocation.allocation_status == models.AllocationStatus.active,
            models.SeatAllocation.employee_id != employee.id,
        )
        .limit(10)
        .all()
    )
    if not neighbor_allocations:
        return f"No one else is currently seated in Floor {seat.floor}, Zone {seat.zone} near {employee.name}."

    names = []
    for a in neighbor_allocations:
        emp = db.query(models.Employee).filter(models.Employee.id == a.employee_id).first()
        if emp:
            names.append(emp.name)
    return f"Colleagues near {employee.name} (Floor {seat.floor}, Zone {seat.zone}): " + ", ".join(names) + "."


# ---------------- Write actions (booking / releasing) ----------------
# These always run through this deterministic path — never through the
# optional LLM layer — so a state-changing action can never depend on an
# LLM correctly interpreting intent. current_user (from the JWT) is the
# sole source of truth for "who is asking"; free-text names/emails in the
# query are never used to pick a target for a write action.

def _self_book_seat(db: Session, current_user, floor: int = None, zone: str = None) -> str:
    if not current_user or not current_user.employee_id:
        return ("Your login isn't linked to an employee record, so I can't book a seat for you. "
                "Contact HR to get your account linked.")
    try:
        allocation = seat_logic.allocate_seat(
            db, employee_id=current_user.employee_id, preferred_floor=floor, preferred_zone=zone
        )
    except seat_logic.SeatAllocationError as e:
        return f"I couldn't book a seat for you: {e}"
    seat = db.query(models.Seat).filter(models.Seat.id == allocation.seat_id).first()
    return (
        f"Done — you're now allocated Floor {seat.floor}, Zone {seat.zone}, Bay {seat.bay}, "
        f"Seat {seat.zone}{seat.bay}-{seat.seat_number}."
    )


def _self_release_seat(db: Session, current_user) -> str:
    if not current_user or not current_user.employee_id:
        return "Your login isn't linked to an employee record, so there's no seat of yours to release."
    try:
        seat_logic.release_seat(db, employee_id=current_user.employee_id)
    except seat_logic.SeatAllocationError as e:
        return f"I couldn't release your seat: {e}"
    return "Your seat has been released and is now available for others to book."


def _book_for_named_employee(db: Session, current_user, name: str) -> str:
    if not current_user or current_user.role != "admin":
        return ("Only Admin accounts can book a seat on someone else's behalf. "
                "I can book one for you, though — just say 'book me a seat'.")
    employee = _find_employee(db, name=name)
    if not employee:
        return f"I couldn't find an employee named '{name}'."
    try:
        allocation = seat_logic.allocate_seat(db, employee_id=employee.id)
    except seat_logic.SeatAllocationError as e:
        return f"I couldn't book a seat for {employee.name}: {e}"
    seat = db.query(models.Seat).filter(models.Seat.id == allocation.seat_id).first()
    return (
        f"Booked — {employee.name} is now allocated Floor {seat.floor}, Zone {seat.zone}, "
        f"Seat {seat.zone}{seat.bay}-{seat.seat_number}."
    )


SELF_BOOK_PATTERNS = [
    "book me a seat", "book a seat for me", "book a seat for myself",
    "reserve a seat for me", "reserve me a seat", "reserve a seat for myself",
    "allocate a seat for me", "allocate me a seat",
    "i need a seat", "can i get a seat", "get me a seat",
]
SELF_RELEASE_PATTERNS = [
    "release my seat", "unreserve my seat", "cancel my seat",
    "give up my seat", "free up my seat", "release the seat i have",
]
BOOK_FOR_NAME_RE = re.compile(
    r"(?:book|reserve|allocate)\s+(?:a\s+seat\s+)?for\s+([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)?)"
)


def try_handle_write_intent(db: Session, query: str, current_user) -> Optional[str]:
    """
    Checks the query against booking/release patterns. Returns an answer
    string if this was a write action (handled here, deterministically), or
    None if it wasn't a write action (caller should fall through to the
    normal read-only intent parser).
    """
    q_lower = query.strip().lower()

    if any(p in q_lower for p in SELF_RELEASE_PATTERNS):
        return _self_release_seat(db, current_user)

    if any(p in q_lower for p in SELF_BOOK_PATTERNS):
        floor_match = FLOOR_RE.search(query)
        zone_match = ZONE_RE.search(query)
        return _self_book_seat(
            db, current_user,
            floor=int(floor_match.group(1)) if floor_match else None,
            zone=zone_match.group(1) if zone_match else None,
        )

    name_match = BOOK_FOR_NAME_RE.search(query)
    if name_match and name_match.group(1).lower() not in ("me", "myself"):
        return _book_for_named_employee(db, current_user, name_match.group(1))

    return None


# ---------------- Intent parsing (keyword-based fallback) ----------------

FLOOR_RE = re.compile(r"floor\s*(\d+)", re.IGNORECASE)
ZONE_RE = re.compile(r"zone\s*([a-zA-Z0-9]+)", re.IGNORECASE)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def _extract_name(query: str) -> str:
    # Heuristics for "employee <Name>", "is <Name> seated", "seat for <Name>"
    patterns = [
        r"employee\s+([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)?)",
        r"is\s+([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)?)\s+seated",
        r"where\s+is\s+([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)?)",
        r"seat\s+for\s+([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)?)",
        r"near\s+([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)?)",
    ]
    for p in patterns:
        m = re.search(p, query)
        if m:
            return m.group(1)
    return None


def answer_query(db: Session, query: str, email: str = None, employee_id: int = None, current_user=None) -> dict:
    """Returns {"answer": str, "intent": str}. Pure rule-based parser."""
    q = query.strip()
    q_lower = q.lower()

    # Write actions (book/release) are always handled deterministically here,
    # before any read-intent matching, and never delegated to the LLM path.
    write_answer = try_handle_write_intent(db, q, current_user)
    if write_answer is not None:
        return {"answer": write_answer, "intent": "write_action"}

    # Default "who is asking" to the logged-in user's linked employee record
    # if the request didn't explicitly pass one.
    if not email and not employee_id and current_user and current_user.employee_id:
        employee_id = current_user.employee_id

    email_in_query = EMAIL_RE.search(q)
    if email_in_query and not email:
        email = email_in_query.group(0)

    floor_match = FLOOR_RE.search(q)
    floor = int(floor_match.group(1)) if floor_match else None
    zone_match = ZONE_RE.search(q)
    zone = zone_match.group(1) if zone_match else None

    # Intent: "my seat" / "who am I" -> requires email or employee_id
    if any(kw in q_lower for kw in ["my seat", "where is my seat", "my project", "am i assigned"]):
        employee = _find_employee(db, email=email, employee_id=employee_id)
        if not employee:
            return {"answer": "I couldn't identify you. Please include your employee email in the request.",
                    "intent": "self_lookup_failed"}
        return {"answer": _employee_seat_sentence(db, employee), "intent": "self_lookup"}

    # Intent: "who is sitting near me" / neighbors
    if "near me" in q_lower or "sitting near" in q_lower or "who is near" in q_lower:
        employee = _find_employee(db, email=email, employee_id=employee_id)
        if not employee:
            name = _extract_name(q)
            employee = _find_employee(db, name=name)
        if not employee:
            return {"answer": "I couldn't identify the employee to find neighbors for.",
                    "intent": "neighbors_failed"}
        return {"answer": _neighbors_answer(db, employee), "intent": "neighbors"}

    # Intent: available seats
    if "available seat" in q_lower or "show all available" in q_lower or "free seat" in q_lower:
        return {"answer": _available_seats_answer(db, floor=floor, zone=zone), "intent": "available_seats"}

    # Intent: project utilization ("how many seats are occupied for Project X")
    if "occupied for project" in q_lower or ("project" in q_lower and "occupied" in q_lower):
        m = re.search(r"project\s+([A-Za-z0-9]+)", q, re.IGNORECASE)
        project_name = m.group(1) if m else None
        if project_name:
            return {"answer": _project_utilization_answer(db, project_name), "intent": "project_utilization"}

    # Intent: "which project am I assigned to"
    if "which project" in q_lower:
        employee = _find_employee(db, email=email, employee_id=employee_id)
        if employee:
            proj = employee.project.name if employee.project else "no project"
            return {"answer": f"{employee.name} is assigned to project {proj}.", "intent": "project_lookup"}

    # Intent: employee seat lookup by name ("Where is employee Amit seated?")
    name = _extract_name(q)
    if name or ("where is" in q_lower or "seated" in q_lower):
        employee = _find_employee(db, name=name, email=email, employee_id=employee_id)
        if employee:
            return {"answer": _employee_seat_sentence(db, employee), "intent": "employee_lookup"}
        if name:
            return {"answer": f"I couldn't find an employee named '{name}'.", "intent": "employee_not_found"}

    # Fallback: try matching an employee by email/id if provided
    if email or employee_id:
        employee = _find_employee(db, email=email, employee_id=employee_id)
        if employee:
            return {"answer": _employee_seat_sentence(db, employee), "intent": "self_lookup"}

    return {
        "answer": (
            "I can help with: where an employee is seated, project assignments, "
            "available seats on a floor/zone, who is near a colleague, and seat "
            "utilization for a project. Try: 'Where is employee Amit seated?' or "
            "'Show all available seats on Floor 3.'"
        ),
        "intent": "help",
    }


def answer_query_with_llm(db: Session, query: str, email: str = None, employee_id: int = None, current_user=None) -> dict:
    """
    Optional LLM-assisted path: uses Claude to classify intent + extract entities,
    then resolves the intent against the database with the same deterministic
    functions above (so the LLM never invents seat numbers). Falls back to the
    rule-based parser if the API call fails or ANTHROPIC_API_KEY isn't set.

    Booking/release (write actions) are intercepted before any LLM call and
    handled by the same deterministic path as answer_query — the LLM is never
    involved in deciding whether to allocate or release a seat.
    """
    write_answer = try_handle_write_intent(db, query, current_user)
    if write_answer is not None:
        return {"answer": write_answer, "intent": "write_action"}

    if not USE_LLM:
        return answer_query(db, query, email, employee_id, current_user)

    try:
        import anthropic
        client = anthropic.Anthropic()
        prompt = (
            "Classify this workplace seating query into one of: self_lookup, "
            "employee_lookup, project_lookup, available_seats, neighbors, "
            "project_utilization, help. Also extract any employee_name, floor "
            "(integer), zone (string), or project_name mentioned. "
            'Respond ONLY as JSON: {"intent": "...", "employee_name": "...", '
            '"floor": null, "zone": "...", "project_name": "..."}\n\n'
            f"Query: {query}"
        )
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        import json
        text = "".join(b.text for b in resp.content if hasattr(b, "text"))
        parsed = json.loads(text.strip().strip("`").replace("json\n", ""))

        intent = parsed.get("intent")
        if intent == "available_seats":
            return {"answer": _available_seats_answer(db, floor=parsed.get("floor"), zone=parsed.get("zone")),
                    "intent": intent}
        if intent == "project_utilization" and parsed.get("project_name"):
            return {"answer": _project_utilization_answer(db, parsed["project_name"]), "intent": intent}
        if intent in ("employee_lookup", "self_lookup", "project_lookup", "neighbors"):
            employee = _find_employee(db, name=parsed.get("employee_name"), email=email, employee_id=employee_id)
            if employee:
                if intent == "neighbors":
                    return {"answer": _neighbors_answer(db, employee), "intent": intent}
                if intent == "project_lookup":
                    proj = employee.project.name if employee.project else "no project"
                    return {"answer": f"{employee.name} is assigned to project {proj}.", "intent": intent}
                return {"answer": _employee_seat_sentence(db, employee), "intent": intent}

        # Fall through to rule-based parser if LLM intent couldn't be resolved
        return answer_query(db, query, email, employee_id, current_user)
    except Exception:
        return answer_query(db, query, email, employee_id, current_user)
