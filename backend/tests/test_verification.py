"""Tests for the PPE + block-sequence verification workflow.

Runnable as a script (like smoke_test.py) and pytest-compatible:

    cd backend
    ../.venv/bin/python tests/test_verification.py     # or: pytest tests/

Uses a throwaway SQLite DB and the clearly-labeled mock PPE provider, so it
needs no Roboflow key and never touches the real data.
"""
import os
import sys
import tempfile

# --- isolate before importing the app ----------------------------------------
_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

os.environ["PPE_MODEL_PROVIDER"] = "mock"   # development mode, clearly labeled
os.environ["PPE_MOCK_RESULT"] = "pass"
os.environ["PPE_MIN_CONFIDENCE"] = "0.72"
os.environ["PPE_CHECK_EXPIRATION_SECONDS"] = "60"

from app import ppe_store, safety_config  # noqa: E402

# Point both stores at a temp DB BEFORE the app wires up.
_TMP_DB = tempfile.mktemp(suffix="-ppe-test.db")
ppe_store.DB_PATH = _TMP_DB

from starlette.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)
_IMG = ("snap.jpg", b"\xff\xd8\xff\xe0fakejpeg", "image/jpeg")

_results = []


def check(name, cond, extra=""):
    _results.append((name, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {name}{(' -> ' + extra) if extra else ''}")


def _start(wo, worker="op-1"):
    r = client.post("/api/verification-sessions/start",
                    json={"work_order_id": wo, "worker_id": worker})
    return r.json()


def _ppe(sid, result="pass"):
    os.environ["PPE_MOCK_RESULT"] = result
    return client.post(f"/api/verification-sessions/{sid}/ppe-check",
                       files={"image": _IMG}).json()


def _submit(sid, color, extra=None):
    body = {"submitted_color": color}
    if extra:
        body.update(extra)
    return client.post(f"/api/verification-sessions/{sid}/blocks/submit", json=body).json()


# 1. Start a verification session.
def test_start_session():
    s = _start("WO-T1")
    check("1. start session", s["expected_next_color"] == "green"
          and s["can_open_work_order"] is False and s["submitted_sequence"] == [])


# 2. Submit correct sequence green -> blue -> red -> yellow.
def test_correct_sequence():
    s = _start("WO-T2")
    sid = s["session_id"]
    for c in ["green", "blue", "red", "yellow"]:
        r = _submit(sid, c)
    check("2. correct sequence passes", r["accepted"] and r["sequence_passed"]
          and r["expected_next_color"] is None,
          extra=str(r["submitted_sequence"]))


# 3. Wrong block order is caught and logged.
def test_wrong_order_caught():
    s = _start("WO-T3")
    sid = s["session_id"]
    _submit(sid, "green")
    r = _submit(sid, "red")  # expected blue
    logged = client.get(f"/api/verification-sessions/{sid}/status").json()["errors"]
    check("3. wrong order rejected", (not r["accepted"]) and r["error_type"] == "wrong_block_order"
          and r["expected_color"] == "blue" and r["received_color"] == "red"
          and r["can_open_work_order"] is False,
          extra=r["message"])
    check("3b. wrong attempt audited", len(logged) >= 1 and logged[0]["error_type"] == "wrong_block_order")


# 4. WO stays locked when PPE is missing (sequence complete only).
def test_locked_without_ppe():
    s = _start("WO-T4")
    sid = s["session_id"]
    for c in ["green", "blue", "red", "yellow"]:
        _submit(sid, c)
    u = client.post("/api/work-orders/WO-T4/unlock").json()
    check("4. locked without PPE", u["unlocked"] is False
          and "ppe_verification" in u["missing_requirements"], extra=str(u["missing_requirements"]))


# 5. WO stays locked when sequence is incomplete (PPE only).
def test_locked_incomplete_sequence():
    s = _start("WO-T5")
    sid = s["session_id"]
    _ppe(sid, "pass")
    _submit(sid, "green")
    _submit(sid, "blue")
    u = client.post("/api/work-orders/WO-T5/unlock").json()
    check("5. locked with incomplete sequence", u["unlocked"] is False
          and "block_sequence" in u["missing_requirements"], extra=str(u["missing_requirements"]))


# 6. WO unlocks ONLY when PPE verified AND sequence complete.
def test_unlock_when_both():
    s = _start("WO-T6")
    sid = s["session_id"]
    ppe = _ppe(sid, "pass")
    for c in ["green", "blue", "red", "yellow"]:
        last = _submit(sid, c)
    st = client.get(f"/api/verification-sessions/{sid}/status").json()
    u = client.post("/api/work-orders/WO-T6/unlock").json()
    check("6. unlock when both pass", ppe["ppe_verified"] and last["sequence_passed"]
          and st["can_open_work_order"] is True and u["unlocked"] is True
          and u["can_open_work_order"] is True)


# 7. Frontend cannot force can_open_work_order via the payload.
def test_frontend_cannot_force():
    s = _start("WO-T7")
    sid = s["session_id"]
    # Inject can_open_work_order + sequence_passed + accepted in the body with a WRONG color.
    r = _submit(sid, "red", extra={"can_open_work_order": True, "sequence_passed": True, "accepted": True})
    u = client.post("/api/work-orders/WO-T7/unlock").json()
    check("7. cannot force can_open via payload",
          r["accepted"] is False and r["can_open_work_order"] is False and u["unlocked"] is False)


# 8. Required sequence comes from backend config.
def test_required_sequence_from_config():
    s = _start("WO-T8")
    st = client.get(f"/api/verification-sessions/{s['session_id']}/status").json()
    check("8. required sequence from config",
          st["required_sequence"] == safety_config.REQUIRED_BLOCK_SEQUENCE
          == ["green", "blue", "red", "yellow"], extra=str(st["required_sequence"]))


def main():
    for fn in [test_start_session, test_correct_sequence, test_wrong_order_caught,
               test_locked_without_ppe, test_locked_incomplete_sequence,
               test_unlock_when_both, test_frontend_cannot_force,
               test_required_sequence_from_config]:
        fn()
    passed = sum(1 for _, ok in _results if ok)
    total = len(_results)
    print(f"\n{passed}/{total} checks passed.")
    if passed != total:
        print("VERIFICATION TESTS FAILED")
        return 1
    print("ALL VERIFICATION TESTS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
