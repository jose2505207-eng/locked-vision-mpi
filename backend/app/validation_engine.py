"""Validation engine — the only place can_advance is ever set to True.

The fake MES is the source of truth, the vision system provides evidence,
and this engine decides whether the evidence satisfies the expected MPI step.
It is intentionally pure: given a step definition, a vision state, and a
mutable progress dict, it returns a result dict. No I/O, no flow control.
"""

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


def validate_step(step, vision_state, progress):
    """Validate the current step against the latest vision evidence.

    progress is mutated to track temporal conditions (e.g. a tool that must
    leave its home and return).
    """
    objects = vision_state.get("objects", [])
    stype = step["type"]
    step_no = step["step"]

    if stype == "move":
        target = step["object"]
        to_zone = step["to_zone"]
        zone = _zone_of(objects, target)
        if zone == to_zone:
            return _result(
                "passed", True,
                f"Step {step_no} passed: the {_h(target)} is in the {_h(to_zone)}.",
                objects,
            )
        # Out-of-sequence detection: a different part is already in the target
        # zone while the expected part is not. Makes the demo's "wrong move"
        # moment unmistakable.
        unexpected = [
            o["object"] for o in objects
            if o.get("zone") == to_zone and o["object"] != target
            and o["object"] in PART_NAMES
        ]
        if unexpected:
            return _result(
                "blocked", False,
                f"Step blocked: the {_h(unexpected[0])} is in the {_h(to_zone)}, "
                f"but step {step_no} needs the {_h(target)}. Remove it and move "
                f"the {_h(target)} into the {_h(to_zone)}.",
                objects,
            )
        return _result(
            "blocked", False,
            f"Step blocked: move the {_h(target)} into the {_h(to_zone)}.",
            objects,
        )

    if stype == "tool_use":
        tool = step["object"]
        home = step["home_zone"]
        zone = _zone_of(objects, tool)
        removed_key = f"tool_removed_step_{step_no}"
        if zone != home:
            # The tool has left its home — record it and wait for the return.
            progress[removed_key] = True
            return _result(
                "blocked", False,
                f"Step blocked: {_h(tool)} is out of its home. Return {_h(tool)} "
                f"to {_h(home)} to finish step {step_no}.",
                objects,
            )
        if progress.get(removed_key):
            return _result(
                "passed", True,
                f"Step {step_no} passed: {_h(tool)} was used and returned to "
                f"{_h(home)}.",
                objects,
            )
        return _result(
            "blocked", False,
            f"Step blocked: pick up {_h(tool)} to use it, then return it to "
            f"{_h(home)}.",
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
