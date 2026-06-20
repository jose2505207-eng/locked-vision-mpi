"""Color detector — OpenCV HSV detection for colored LEGO blocks.

This is the bridge from pixels to "objects". It is intentionally simple: HSV
threshold per color, contour -> bounding box. The output feeds zone_mapper.py,
which assigns each box to a zone, producing the same vision-state shape as
mock_vision_state.py.

NOTE: This module degrades gracefully if OpenCV/NumPy are not installed, so the
rest of the repo can run on mock vision during the demo.
"""

# HSV ranges are [H, S, V]. OpenCV hue is 0-179. Tune these against the golden
# view under the actual demo lighting (see calibration.py).
COLOR_RANGES = {
    # object_name: (lower_hsv, upper_hsv)  -- some colors need two ranges (red).
    "red_block": [((0, 120, 70), (10, 255, 255)), ((170, 120, 70), (180, 255, 255))],
    "blue_block": [((100, 120, 70), (130, 255, 255))],
    "yellow_block": [((20, 120, 70), (35, 255, 255))],
    "green_block": [((40, 80, 70), (85, 255, 255))],
}

MIN_CONTOUR_AREA = 800  # ignore noise specks; tune for block size in golden view


def detect_blocks(frame):
    """Detect colored blocks in a BGR frame.

    Returns a list of detections: {"object", "bbox":[x1,y1,x2,y2], "confidence"}.
    Tools (tool_1, tool_2) are NOT color-detected here — add an ArUco tag or a
    template match for tools (see TODO below).
    """
    try:
        import cv2
        import numpy as np
    except ImportError:  # pragma: no cover
        raise RuntimeError(
            "OpenCV/NumPy not installed. Run on mock vision, or "
            "`pip install -r vision/requirements.txt`."
        )

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    detections = []

    for object_name, ranges in COLOR_RANGES.items():
        mask = None
        for (lower, upper) in ranges:
            part = cv2.inRange(hsv, np.array(lower), np.array(upper))
            mask = part if mask is None else cv2.bitwise_or(mask, part)

        # Clean up the mask a little.
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))

        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if not contours:
            continue

        # Keep the largest contour per color for the simple demo (one block
        # per color). TODO: support multiple instances per color if needed.
        largest = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest)
        if area < MIN_CONTOUR_AREA:
            continue
        x, y, w, h = cv2.boundingRect(largest)
        detections.append({
            "object": object_name,
            "bbox": [float(x), float(y), float(x + w), float(y + h)],
            "confidence": min(1.0, area / (frame.shape[0] * frame.shape[1]) * 50),
        })

    # TODO(vision): detect tool_1 / tool_2.
    #   Option A: ArUco markers on each tool (most robust under motion).
    #   Option B: template / feature match against a reference crop.
    #   Either way, append {"object": "tool_1", "bbox": [...]} detections here
    #   so the tool-use step (tool leaves home -> returns) can be verified.

    return detections


# TODO(vision): finished_assembly detection.
#   The MVP can treat "all assembly blocks present" as finished_assembly, or
#   tag the completed build with an ArUco marker. Decide with the backend lead
#   so the object name matches mpi_steps.json.
