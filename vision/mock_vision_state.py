"""Mock vision state — built FIRST so the backend and frontend work without a
camera.

The real `color_detector.py` + `zone_mapper.py` pipeline must eventually return
the *exact same shape* this module returns, so it can be dropped in with no
backend changes:

    {
      "objects": [ {"object": "red_block", "zone": "assembly_zone",
                    "bbox": [..], "confidence": 0.98}, ... ],
      "source": "mock",
      "scenario": "step1_done"
    }

`zone == None` means the object is detected but not inside any known zone
(e.g. a tool currently in the operator's hand).
"""
from typing import Optional

# Canonical objects and their home zones. BLOCKS ONLY (no tools in this demo).
OBJECT_HOMES = {
    "red_block": "red_home",
    "blue_block": "blue_home",
    "yellow_block": "yellow_home",
    "green_block": "green_home",
}

# Each scenario maps object -> zone. None = in hand / out of any zone.
# Objects not listed fall back to their home zone.
# Demo sequence: green -> blue -> red -> yellow into assembly, then ALL to
# complete (cumulative). Block-only — no synthetic finished_assembly object.
_ASSEMBLY = "assembly_zone"
_COMPLETE = "complete_zone"
SCENARIOS = {
    # Everything in its home -> station is ready / calibrated.
    "station_ready": {},
    "all_home": {},

    # MPI step progress (cumulative).
    "step1_done": {"green_block": _ASSEMBLY},
    "step2_done": {"green_block": _ASSEMBLY, "blue_block": _ASSEMBLY},
    "step3_done": {"green_block": _ASSEMBLY, "blue_block": _ASSEMBLY, "red_block": _ASSEMBLY},
    "step4_done": {
        "green_block": _ASSEMBLY, "blue_block": _ASSEMBLY,
        "red_block": _ASSEMBLY, "yellow_block": _ASSEMBLY,
    },

    # Step 5: ALL FOUR blocks moved to the complete zone (real, camera-detectable).
    "step5_done": {
        "green_block": _COMPLETE, "blue_block": _COMPLETE,
        "red_block": _COMPLETE, "yellow_block": _COMPLETE,
    },

    # Demo failure: operator moves the BLUE block first (green expected).
    "wrong_sequence": {"blue_block": _ASSEMBLY},

    # Final 6S state: assembly clear, all blocks parked in complete.
    "final_6s_pass": {
        "green_block": _COMPLETE, "blue_block": _COMPLETE,
        "red_block": _COMPLETE, "yellow_block": _COMPLETE,
    },
}

# No partial scenarios remain — every step is camera-detectable now.
PARTIAL_SCENARIOS = set()


def build_state(scenario: str, source: str = "mock") -> dict:
    """Build a full vision state dict for a named scenario."""
    if scenario not in SCENARIOS:
        raise ValueError(
            f"Unknown scenario '{scenario}'. Known: {sorted(SCENARIOS)}"
        )
    overrides = SCENARIOS[scenario]

    objects = []
    if scenario in PARTIAL_SCENARIOS:
        # Emit only the overridden objects so they merge with camera evidence.
        for name, zone in overrides.items():
            objects.append(_obj(name, zone))
    else:
        # Base objects default to their home zone unless overridden.
        for name, home in OBJECT_HOMES.items():
            zone = overrides.get(name, home)
            objects.append(_obj(name, zone))
        # finished_assembly only appears when a scenario places it.
        if "finished_assembly" in overrides:
            objects.append(_obj("finished_assembly", overrides["finished_assembly"]))

    return {"objects": objects, "source": source, "scenario": scenario}


def _obj(name: str, zone: Optional[str]) -> dict:
    # Mock evidence is always simulator-sourced (per-object source tracking).
    return {
        "object": name, "zone": zone, "bbox": None,
        "confidence": 0.99, "source": "simulator",
    }


if __name__ == "__main__":
    import json
    for name in SCENARIOS:
        print(name)
        print(json.dumps(build_state(name)["objects"], indent=2))
        print()
