# Backend Testing Guide

> Part of the two-role handoff — see
> [`docs/HANDOFF_TWO_ROLE_EXECUTION_PLAN.md`](../HANDOFF_TWO_ROLE_EXECUTION_PLAN.md).

## Run the backend locally

```bash
cd backend
python -m venv ../.venv && source ../.venv/bin/activate   # first time only
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Interactive API docs: http://localhost:8000/docs

The verification workflow runs with **no Roboflow key** — PPE uses a clearly
labeled mock (`mode: "mock"`). Set `PPE_MODEL_PROVIDER=mock` + `PPE_MOCK_RESULT=fail`
to exercise the failure path.

## Run the tests

```bash
cd backend
../.venv/bin/python tests/test_verification.py   # PPE + block-sequence workflow
../.venv/bin/python smoke_test.py                # existing MPI flow (no regressions)
```

`tests/test_verification.py` uses a throwaway SQLite DB and the mock PPE provider,
so it needs no key and never touches real data. It covers:

1. Starting a session · 2. Correct sequence green→blue→red→yellow ·
3. Wrong order is caught + logged · 4. Locked without PPE · 5. Locked with
incomplete sequence · 6. Unlocks only when both pass · 7. Frontend cannot force
`can_open_work_order` via payload · 8. Required sequence comes from config.

(If you have `pytest` installed, `pytest tests/` also works — the test functions
are `test_*`.)

## Example curl walkthrough

```bash
B=http://localhost:8000

# 1) Start a session
SID=$(curl -s -X POST $B/api/verification-sessions/start \
  -H 'content-type: application/json' \
  -d '{"work_order_id":"WO-001","worker_id":"operator-001"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['session_id'])")
echo "session: $SID"

# 2) PPE check (any image; mock provider ignores pixels)
curl -s -X POST $B/api/verification-sessions/$SID/ppe-check \
  -F "image=@/path/to/snapshot.jpg;type=image/jpeg"

# 3) Submit the block sequence (try a wrong one first to see the gate)
curl -s -X POST $B/api/verification-sessions/$SID/blocks/submit \
  -H 'content-type: application/json' -d '{"submitted_color":"red"}'   # wrong: expected green
for c in green blue red yellow; do
  curl -s -X POST $B/api/verification-sessions/$SID/blocks/submit \
    -H 'content-type: application/json' -d "{\"submitted_color\":\"$c\"}"
done

# 4) Status — read can_open_work_order
curl -s $B/api/verification-sessions/$SID/status

# 5) Unlock the Work Order
curl -s -X POST $B/api/work-orders/WO-001/unlock
```

Expected: the wrong submission returns `accepted: false`,
`error_type: "wrong_block_order"`; after PPE + the full correct sequence,
`status` and `unlock` return `can_open_work_order: true`.

## What "good" looks like

- Wrong color → `400`-free `200` body with `accepted:false`, WO stays locked, the
  attempt appears in `status.errors`.
- `can_open_work_order` is `true` **only** after PPE verified (not expired) **and**
  the full sequence passed.
- Sending `{"submitted_color":"green","can_open_work_order":true}` does **not**
  unlock anything — the backend ignores client-sent truth.
