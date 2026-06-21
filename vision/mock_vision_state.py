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

# Canonical objects and their home zones.
OBJECT_HOMES = {
    "red_block": "red_home",
    "blue_block": "blue_home",
    "yellow_block": "yellow_home",
    "green_block": "green_home",
    "tool_1": "tool_1_home",
    "tool_2": "tool_2_home",
}

# Each scenario maps object -> zone. None = in hand / out of any zone.
# Objects not listed fall back to their home zone, except finished_assembly
# which only exists when explicitly placed.
SCENARIOS = {
    # Everything in its home -> station is ready / calibrated.
    "station_ready": {},
    "all_home": {},

    # MPI step progress (cumulative).
    "step1_done": {"red_block": "assembly_zone"},
    "step2_done": {"red_block": "assembly_zone", "blue_block": "assembly_zone"},

    # Step 3 tool use is temporal: tool leaves home, then returns.
    "step3_tool_removed": {
        "red_block": "assembly_zone",
        "blue_block": "assembly_zone",
        "tool_1": None,
    },
    "step3_tool_returned": {
        "red_block": "assembly_zone",
        "blue_block": "assembly_zone",
        "tool_1": "tool_1_home",
    },

    "step4_done": {
        "red_block": "assembly_zone",
        "blue_block": "assembly_zone",
        "yellow_block": "assembly_zone",
    },

    # Step 5: blocks combined into finished_assembly, moved to complete zone.
    "step5_done": {
        "finished_assembly": "complete_zone",
    },

    # Demo failure: operator moves the BLUE block first (out of order).
    "wrong_sequence": {"blue_block": "assembly_zone"},

    # Final 6S states.
    "final_6s_pass": {"finished_assembly": "complete_zone"},
    "final_6s_tool_missing": {
        "finished_assembly": "complete_zone",
        "tool_1": None,
    },

    # Partial (hybrid) scenarios — emit ONLY the listed objects so they merge
    # with live camera block evidence instead of overwriting it. Used for the
    # tool step and the finished-assembly step where the camera sees nothing.
    "tool_1_removed_only": {"tool_1": None},
    "tool_1_returned_only": {"tool_1": "tool_1_home"},
    "finished_only": {"finished_assembly": "complete_zone"},
}

# Scenarios that should emit only their overridden objects (not the full set).
PARTIAL_SCENARIOS = {"tool_1_removed_only", "tool_1_returned_only", "finished_only"}


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
