"""Sponsor integration adapter layer (SHADOW MODE).

Every adapter in this package is:
  * OFF by default and gated behind an environment flag,
  * lazy about importing its SDK (no import cost / crash when disabled),
  * fail-soft — a missing key, down service, or SDK error must never affect the
    demo or the authoritative validation result.

The backend's existing validation engine remains the ONLY source of truth for
pass/fail. Sponsor adapters observe and mirror; they never decide.
"""
