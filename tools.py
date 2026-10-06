"""Tools the agent can call: policy search, availability, booking, cancelling, escalation."""
from datetime import date, datetime, timedelta

from db import get_conn
from knowledge import get_kb

SLOT_CAPACITY = 3  # seats per two-hour slot
WEEKDAY_SLOTS = ["09:00", "10:00", "11:00", "13:00", "14:00", "15:00"]
SATURDAY_SLOTS = ["09:00", "10:00"]
MAX_DAYS_AHEAD = 30


def _slots_for(day: date) -> list[str]:
    if day.weekday() < 5:
        return WEEKDAY_SLOTS
    if day.weekday() == 5:
        return SATURDAY_SLOTS
    return []


def _parse_date(value: str) -> date | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _date_problem(day: date | None, today: date) -> str | None:
    if day is None:
        return "Date must be in YYYY-MM-DD format."
    if day <= today:
        return "Exams must be booked at least 24 hours in advance."
    if day > today + timedelta(days=MAX_DAYS_AHEAD):
        return f"Exams can only be booked up to {MAX_DAYS_AHEAD} days ahead."
    if not _slots_for(day):
        return "The testing center is closed on Sundays."
    return None


def _seats_taken(conn, exam_date: str, start_time: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) FROM bookings WHERE exam_date=? AND start_time=? AND status='booked'",
        (exam_date, start_time),
    ).fetchone()
    return row[0]


def search_policies(query: str) -> dict:
    results = get_kb().search(query)
    if not results:
        return {"found": False, "message": "No matching policy. Offer to connect the student with staff."}
    return {"found": True, "results": [{"title": r["title"], "text": r["text"]} for r in results]}


def check_availability(exam_date: str, today: date | None = None) -> dict:
    today = today or date.today()
    day = _parse_date(exam_date)
    problem = _date_problem(day, today)
    if problem:
        return {"ok": False, "error": problem}
    with get_conn() as conn:
        slots = [
            {"time": t, "seats_left": SLOT_CAPACITY - _seats_taken(conn, exam_date, t)}
            for t in _slots_for(day)
        ]
    open_slots = [s for s in slots if s["seats_left"] > 0]
    return {
        "ok": True,
        "date": exam_date,
        "weekday": day.strftime("%A"),
        "available_slots": open_slots,
        "fully_booked": not open_slots,
    }


def book_slot(student_name: str, course: str, exam_date: str, start_time: str,
              today: date | None = None) -> dict:
    today = today or date.today()
    day = _parse_date(exam_date)
    problem = _date_problem(day, today)
    if problem:
        return {"ok": False, "error": problem}
    if start_time not in _slots_for(day):
        return {"ok": False, "error": f"{start_time} is not a valid start time on that day.",
                "valid_times": _slots_for(day)}
    if not student_name.strip() or not course.strip():
        return {"ok": False, "error": "Student name and course are required."}
    with get_conn() as conn:
        duplicate = conn.execute(
            "SELECT id FROM bookings WHERE lower(student_name)=lower(?) AND exam_date=? "
            "AND start_time=? AND status='booked'",
            (student_name.strip(), exam_date, start_time),
        ).fetchone()
        if duplicate:
            return {"ok": False, "error": "This student already has that slot booked.",
                    "confirmation_code": f"PP-{duplicate['id']:04d}"}
        if _seats_taken(conn, exam_date, start_time) >= SLOT_CAPACITY:
            return {"ok": False, "error": "That slot is full. Check availability for other times."}
        cur = conn.execute(
            "INSERT INTO bookings (student_name, course, exam_date, start_time) VALUES (?, ?, ?, ?)",
            (student_name.strip(), course.strip(), exam_date, start_time),
        )
        booking_id = cur.lastrowid
    return {
        "ok": True,
        "confirmation_code": f"PP-{booking_id:04d}",
        "student_name": student_name.strip(),
        "course": course.strip(),
        "exam_date": exam_date,
        "start_time": start_time,
    }


def cancel_booking(confirmation_code: str) -> dict:
    try:
        booking_id = int(confirmation_code.upper().replace("PP-", "").strip())
    except (AttributeError, ValueError):
        return {"ok": False, "error": "Confirmation codes look like PP-0007."}
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM bookings WHERE id=?", (booking_id,)).fetchone()
        if row is None or row["status"] != "booked":
            return {"ok": False, "error": "No active booking found with that code."}
        conn.execute("UPDATE bookings SET status='cancelled' WHERE id=?", (booking_id,))
    return {"ok": True, "cancelled": f"PP-{booking_id:04d}",
            "exam_date": row["exam_date"], "start_time": row["start_time"]}


def escalate_to_staff(reason: str, contact: str = "") -> dict:
    with get_conn() as conn:
        cur = conn.execute("INSERT INTO escalations (reason, contact) VALUES (?, ?)",
                           (reason, contact))
    return {"ok": True, "ticket": f"ESC-{cur.lastrowid:04d}",
            "message": "A staff member will follow up during open hours."}


TOOL_SCHEMAS = [
    {
        "name": "search_policies",
        "description": "Search the testing center policy FAQ. Use for any question about hours, "
                       "location, ID, rules, make-ups, accommodations, or other policies.",
        "input_schema": {"type": "object",
                         "properties": {"query": {"type": "string"}},
                         "required": ["query"]},
    },
    {
        "name": "check_availability",
        "description": "List open two-hour exam slots for a date.",
        "input_schema": {"type": "object",
                         "properties": {"exam_date": {"type": "string", "description": "YYYY-MM-DD"}},
                         "required": ["exam_date"]},
    },
    {
        "name": "book_slot",
        "description": "Book an exam slot. Only call after the student has confirmed name, course, "
                       "date, and start time.",
        "input_schema": {"type": "object",
                         "properties": {
                             "student_name": {"type": "string"},
                             "course": {"type": "string"},
                             "exam_date": {"type": "string", "description": "YYYY-MM-DD"},
                             "start_time": {"type": "string", "description": "24-hour HH:MM, e.g. 14:00"},
                         },
                         "required": ["student_name", "course", "exam_date", "start_time"]},
    },
    {
        "name": "cancel_booking",
        "description": "Cancel a booking by confirmation code (format PP-0007).",
        "input_schema": {"type": "object",
                         "properties": {"confirmation_code": {"type": "string"}},
                         "required": ["confirmation_code"]},
    },
    {
        "name": "escalate_to_staff",
        "description": "Hand off to a human staff member when the student asks for a person, "
                       "the question isn't covered by policy, or the request can't be completed.",
        "input_schema": {"type": "object",
                         "properties": {"reason": {"type": "string"},
                                        "contact": {"type": "string",
                                                    "description": "Student email or phone, if given"}},
                         "required": ["reason"]},
    },
]

_REGISTRY = {
    "search_policies": search_policies,
    "check_availability": check_availability,
    "book_slot": book_slot,
    "cancel_booking": cancel_booking,
    "escalate_to_staff": escalate_to_staff,
}


def run_tool(name: str, args: dict) -> dict:
    fn = _REGISTRY.get(name)
    if fn is None:
        return {"ok": False, "error": f"Unknown tool {name}"}
    try:
        return fn(**args)
    except TypeError as exc:
        return {"ok": False, "error": f"Bad arguments: {exc}"}
