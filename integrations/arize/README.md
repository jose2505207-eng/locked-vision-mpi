# Arize / Terac — Vision Evaluation & Labeling

**Track:** Best Use of Arize (or Terac). Optional.

## Why it fits

The vision system is the evidence layer. To trust it, we need to measure it:
how often does color detection / zone mapping agree with ground truth? Arize
(observability/eval) or Terac (data labeling) closes that loop.

## Planned usage (placeholder)

- **Log inferences:** every `vision-state` (object, zone, confidence) plus the
  operator-confirmed outcome becomes an eval record.
- **Metrics:** per-object precision/recall, zone-mapping accuracy, confidence
  calibration, drift when lighting changes.
- **Labeling loop (Terac):** route low-confidence snapshots from
  `vision/snapshots/` for human labeling to grow the dataset.

## Wiring sketch

```bash
pip install arize
export ARIZE_API_KEY="..."
export ARIZE_SPACE_ID="..."
```

Emit one record per detection alongside the audit log. Fully optional — no core
behavior depends on it.
