"""Safety configuration — single source of truth for the verification workflow.

Change the required block sequence in ONE place (REQUIRED_BLOCK_SEQUENCE) and the
whole backend follows. PPE model settings are also centralized here so the model
provider can be swapped without touching route or service logic.
"""
import os

# === The one place the block sequence is defined. =============================
REQUIRED_BLOCK_SEQUENCE = ["green", "blue", "red", "yellow"]

# Colors the system understands (used to distinguish "wrong order" from "garbage").
ALL_BLOCK_COLORS = {"green", "blue", "red", "yellow"}


def required_sequence() -> list:
    """Return a copy of the required block sequence."""
    return list(REQUIRED_BLOCK_SEQUENCE)


def normalize_color(color: str) -> str:
    return (color or "").strip().lower()


# === PPE model configuration (environment-driven, provider-swappable). ========

def ppe_config() -> dict:
    """Read PPE config from the environment on each call so .env edits apply.

    PPE_MODEL_PROVIDER selects the provider. When unset, it auto-resolves to
    "roboflow" if a key + model are configured, otherwise "mock" (clearly
    labeled development mode — never silently treated as production).
    """
    api_key = os.getenv("ROBOFLOW_API_KEY", "")
    model_id = os.getenv("ROBOFLOW_PPE_MODEL_ID", "")
    workspace = os.getenv("ROBOFLOW_WORKSPACE", "")
    workflow_id = os.getenv("ROBOFLOW_WORKFLOW_ID", "")
    provider = os.getenv("PPE_MODEL_PROVIDER", "").strip().lower()
    if not provider:
        # Auto-resolve: a Roboflow Workflow (workspace + workflow id) wins, then a
        # single detect model, otherwise labeled mock.
        if api_key and workspace and workflow_id:
            provider = "roboflow_workflow"
        elif api_key and model_id:
            provider = "roboflow"
        else:
            provider = "mock"
    return {
        "provider": provider,
        "api_key": api_key,
        "model_id": model_id,
        "workspace": workspace,
        "workflow_id": workflow_id,
        "api_url": os.getenv("ROBOFLOW_API_URL", "https://serverless.roboflow.com"),
        "detect_url": os.getenv("ROBOFLOW_DETECT_URL", "https://detect.roboflow.com"),
        "min_confidence": float(os.getenv("PPE_MIN_CONFIDENCE", "0.72")),
        "expiration_seconds": int(os.getenv("PPE_CHECK_EXPIRATION_SECONDS", "20")),
        "required": os.getenv("PPE_REQUIRED", "false").strip().lower() in ("1", "true", "yes"),
        # Dev-only knob: what the mock provider should return ("pass" | "fail").
        "mock_result": os.getenv("PPE_MOCK_RESULT", "pass").strip().lower(),
    }
