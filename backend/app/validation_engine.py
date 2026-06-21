"""Validation engine — the only place can_advance is ever set to True.

The fake MES is the source of truth, the vision system provides evidence,
and this engine decides whether the evidence satisfies the expected MPI step.
It is intentionally pure: given a step definition, a vision state, and a
mutable progress dict, it returns a result dict. No I/O, no flow control.

Demo scope: BLOCKS ONLY. The active MPI sequence is red -> blue -> green ->
yellow -> finished (see data/mpi_steps.json). No tool zones or tool steps are
part of the verification path; station readiness checks blocks only.
"""
import logging

log = logging.getLogger("mpi")

# Objects that count as "parts" for sequence / clear-zone checks.
PART_NAMES = {
    "red_block", "blue_block", "yellow_block", "green_block", "finished_assembly",
}


def _zone_of(objects, name):
    for obj in objects:
        if obj.get("object") == name:
            return obj.get("zone")
    return None


def _h(name):
    """Humanize an object/zone id, e.g. 'red_block' -> 'red block'."""
    return (name or "").replace("_", " ")


def _result(status, can_advance, message, objects):
    return {
        "status": status,
        "can_advance": can_advance,
        "message": message,
        "detected_objects": objects,
    }


def _move_steps_to(all_steps, to_zone):
    """Ordered list of block objects that 'move' steps place into `to_zone`."""
    return [
        s["object"] for s in (all_steps or [])
        if s.get("type") == "move" and s.get("to_zone") == to_zone
    ]


def validate_step(step, vision_state, progress, already_placed=None, all_steps=None):
    """Validate the current step against the latest vision evidence — CUMULATIVELY.

    Every step re-checks the FULL required state up to and including itself, not
    just the current block. So if an earlier block is moved back out of the
    assembly zone, a later step fails. `all_steps` is the full ordered step list
    (the source of truth for what each step requires); it is derived from
    mpi_steps.json, so the rules follow the configured sequence with no hardcoding.
    """
    objects = vision_state.get("objects", [])
    stype = step["type"]
    step_no = step["step"]

    if stype == "move":
        to_zone = step["to_zone"]
        # Cumulative requirement: every block this MPI moves into `to_zone` at or
        # before the current step must currently be in `to_zone`.
        sequence = _move_steps_to(all_steps, to_zone)  # ordered: e.g. green,blue,red,yellow
        required = [s["object"] for s in all_steps
                    if s.get("type") == "move" and s.get("to_zone") == to_zone
                    and s["step"] <= step_no]
        not_yet = [s["object"] for s in all_steps
                   if s.get("type") == "move" and s.get("to_zone") == to_zone
                   and s["step"] > step_no]

        missing = [o for o in required if _zone_of(objects, o) != to_zone]
        too_early = [o for o in not_yet if _zone_of(objects, o) == to_zone]
        inside = not missing and not too_early

        log.info(
            "[verify] step=%s required=%s not_yet=%s zone=%s detected=%s "
            "missing=%s too_early=%s decision=%s",
            step_no, required, not_yet, to_zone,
            [(o.get("object"), o.get("zone")) for o in objects],
            missing, too_early, "PASS" if inside else "BLOCK",
        )

        if too_early:
            o = too_early[0]
            return _result(
                "blocked", False,
                f"Sequence blocked: {_h(o)} was placed too early — it must not be "
                f"in the {_h(to_zone)} until its step. Remove it and place the "
                f"required blocks in order ({', '.join(_h(b) for b in sequence)}).",
                objects,
            )
        if missing:
            # Distinguish "the block for THIS step isn't placed yet" from
            # "an earlier block was moved back out" — both must fail.
            current = step["object"]
            if current in missing:
                return _result(
                    "blocked", False,
                    f"Step blocked: move the {_h(current)} into the {_h(to_zone)}.",
                    objects,
                )
            return _result(
                "blocked", False,
                f"Step blocked: {_h(missing[0])} must still be in the {_h(to_zone)} "
                f"(an earlier block was moved out).",
                objects,
            )
        return _result(
            "passed", True,
            f"Step {step_no} passed: {', '.join(_h(o) for o in required)} in the {_h(to_zone)}.",
            objects,
        )

    if stype == "move_all":
        # Final block step: ALL listed blocks must be in `to_zone` (e.g. every
        # block in complete_zone). No synthetic 'finished_assembly' object — the
        # real block detections are the only source of truth.
        to_zone = step["to_zone"]
        required = list(step.get("objects", []))
        missing = [o for o in required if _zone_of(objects, o) != to_zone]
        inside = not missing
        log.info(
            "[verify] step=%s move_all required=%s zone=%s detected=%s missing=%s decision=%s",
            step_no, required, to_zone,
            [(o.get("object"), o.get("zone")) for o in objects],
            missing, "PASS" if inside else "BLOCK",
        )
        if missing:
            return _result(
                "blocked", False,
                f"Step blocked: move ALL blocks to the {_h(to_zone)} — still "
                f"missing {', '.join(_h(o) for o in missing)}.",
                objects,
            )
        return _result(
            "passed", True,
            f"Step {step_no} passed: all blocks ({', '.join(_h(o) for o in required)}) "
            f"in the {_h(to_zone)}.",
            objects,
        )

    return _result("blocked", False, f"Unknown step type: {stype}", objects)


def validate_final_6s(final_cfg, vision_state):
    """Validate the final 6S reset. Work order cannot close until this passes."""
    objects = vision_state.get("objects", [])
    failures = []

    for tool in final_cfg.get("tools_home", []):
        if _zone_of(objects, tool["object"]) != tool["zone"]:
            failures.append(f"return {_h(tool['object'])} to {_h(tool['zone'])}")

    for part in final_cfg.get("parts_home", []):
        if _zone_of(objects, part["object"]) != part["zone"]:
            failures.append(
                f"return the unused {_h(part['object'])} to {_h(part['zone'])}"
            )

    clear_zone = final_cfg.get("assembly_clear_zone")
    if clear_zone:
        leftover = [
            o["object"] for o in objects
            if o.get("zone") == clear_zone and o["object"] in PART_NAMES
        ]
        if leftover:
            names = ", ".join(_h(n) for n in leftover)
            failures.append(f"clear the {_h(clear_zone)} (found {names})")

    finished = final_cfg.get("finished_assembly")
    if finished and _zone_of(objects, finished["object"]) != finished["zone"]:
        failures.append(
            f"move the {_h(finished['object'])} to the {_h(finished['zone'])}"
        )

    if failures:
        return _result(
            "blocked", False,
            "Final 6S blocked: " + "; ".join(failures) + ".",
            objects,
        )
    return _result(
        "passed", True,
        "Final 6S passed: station reset verified — work order can close.",
        objects,
    )


# Home zones used for the pre-start station-readiness check. BLOCKS ONLY —
# tools are not part of this demo and are never required for readiness.
READINESS_HOMES = {
    "red_block": "red_home",
    "blue_block": "blue_home",
    "yellow_block": "yellow_home",
    "green_block": "green_home",
}
REQUIRED_BLOCKS = ["red_block", "blue_block", "yellow_block", "green_block"]
CLEAR_BEFORE_START = ["assembly_zone", "complete_zone"]


def validate_readiness(vision_state):
    """Pre-start gate: all blocks home and work zones clear. BLOCKS ONLY.

    The camera sees the four colored blocks; readiness requires each to be in
    its home zone and the assembly/complete zones clear. Tools are intentionally
    ignored — they are not part of this demo.
    """
    objects = vision_state.get("objects", [])
    if not objects:
        return {
            "status": "blocked",
            "can_start": False,
            "message": "No vision evidence yet. Show the station to the camera "
                       "or post simulator state.",
            "missing_or_wrong": [],
        }

    wrong = []

    # Blocks must be present AND home.
    for obj in REQUIRED_BLOCKS:
        actual = _zone_of(objects, obj)
        expected = READINESS_HOMES[obj]
        if actual != expected:
            wrong.append({
                "object": obj, "expected_zone": expected, "actual_zone": actual,
            })

    # Work zones must be clear of parts before starting.
    for z in CLEAR_BEFORE_START:
        for o in objects:
            if o.get("zone") == z and o.get("object") in PART_NAMES:
                name = o["object"]
                if not any(w["object"] == name for w in wrong):
                    wrong.append({
                        "object": name,
                        "expected_zone": READINESS_HOMES.get(name, "home"),
                        "actual_zone": z,
                    })

    if wrong:
        items = ", ".join(
            f"{_h(w['object'])} ({_h(w['actual_zone'] or 'missing')})" for w in wrong
        )
        return {
            "status": "blocked",
            "can_start": False,
            "message": "Station not ready — fix: " + items + ".",
            "missing_or_wrong": wrong,
        }

    return {
        "status": "ready",
        "can_start": True,
        "message": "Station ready: all blocks home, work zones clear.",
        "missing_or_wrong": [],
    }
