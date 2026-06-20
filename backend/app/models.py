"""Pydantic models for the Locked Vision MPI backend.

These define the contract between the fake MES, the vision system, and the
frontend. The most important field in the whole project is `can_advance`:
the frontend must NEVER enable the Next Step button unless the backend
returns can_advance=true.
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class VisionObject(BaseModel):
    """A single object the vision system claims to see, mapped to a zone.

    zone is None when the object is detected but not inside any known zone
    (e.g. a tool currently in the operator's hand).
    """
    object: str
    zone: Optional[str] = None
    bbox: Optional[List[float]] = None
    confidence: float = 1.0


class VisionState(BaseModel):
    """Structured evidence from the vision system (mock or real)."""
    objects: List[VisionObject] = Field(default_factory=list)
    source: str = "mock"
    scenario: Optional[str] = None


class ValidationResponse(BaseModel):
    """The canonical response shape for validation/advance/6S endpoints."""
    work_order_id: str
    current_step: int
    status: str  # "passed" | "blocked"
    can_advance: bool
    message: str
    detected_objects: List[VisionObject] = Field(default_factory=list)


class StepResponse(BaseModel):
    work_order_id: str
    current_step: int
    total_steps: int
    status: str
    instruction: str
    step: Optional[dict] = None


class WorkOrderSummary(BaseModel):
    work_order_id: str
    product: str
    mpi_id: str
    status: str
    current_step: int
    total_steps: int
