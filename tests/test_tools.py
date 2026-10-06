from datetime import date

from knowledge import get_kb
from tools import book_slot, cancel_booking, check_availability, run_tool, SLOT_CAPACITY

TODAY = date(2026, 10, 5)  # a Monday


def test_policy_search_finds_id_rules():
    results = get_kb().search("what ID do I need to bring")
    assert results and results[0]["title"] == "What ID to bring"


def test_policy_search_finds_hours():
    assert get_kb().search("when do you close on friday")[0]["title"] == "Hours of operation"


def test_availability_weekday_and_saturday():
    tue = check_availability("2026-10-06", today=TODAY)
    sat = check_availability("2026-10-10", today=TODAY)
    assert tue["ok"] and len(tue["available_slots"]) == 6
    assert sat["ok"] and [s["time"] for s in sat["available_slots"]] == ["09:00", "10:00"]


def test_availability_rejects_sunday_past_and_far_future():
    assert not check_availability("2026-10-11", today=TODAY)["ok"]
    assert not check_availability("2026-10-05", today=TODAY)["ok"]
    assert not check_availability("2026-12-01", today=TODAY)["ok"]
    assert not check_availability("next tuesday", today=TODAY)["ok"]


def test_booking_and_capacity():
    for i in range(SLOT_CAPACITY):
        r = book_slot(f"Student {i}", "STAT 2100", "2026-10-06", "14:00", today=TODAY)
        assert r["ok"] and r["confirmation_code"].startswith("PP-")
    full = book_slot("Late Student", "STAT 2100", "2026-10-06", "14:00", today=TODAY)
    assert not full["ok"]
    times = [s["time"] for s in check_availability("2026-10-06", today=TODAY)["available_slots"]]
    assert "14:00" not in times


def test_duplicate_booking_blocked():
    book_slot("Ana Lee", "CS 101", "2026-10-07", "10:00", today=TODAY)
    again = book_slot("ana lee", "CS 101", "2026-10-07", "10:00", today=TODAY)
    assert not again["ok"]


def test_invalid_time_rejected():
    r = book_slot("Ana Lee", "CS 101", "2026-10-07", "12:00", today=TODAY)
    assert not r["ok"] and "valid_times" in r


def test_cancel_frees_seat():
    code = book_slot("Ana Lee", "CS 101", "2026-10-07", "10:00", today=TODAY)["confirmation_code"]
    assert cancel_booking(code)["ok"]
    assert not cancel_booking(code)["ok"]


def test_run_tool_handles_unknown_and_bad_args():
    assert not run_tool("delete_everything", {})["ok"]
    assert not run_tool("book_slot", {"student_name": "x"})["ok"]
