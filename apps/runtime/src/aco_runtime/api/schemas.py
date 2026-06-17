"""Pydantic v2 schemas. Mirrors `packages/shared` (codegen target)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Liveness probe response."""

    status: Literal["ok", "degraded", "down"]
    version: str


class NewWorkflowRequest(BaseModel):
    """Request to start a new workflow."""

    text: str = Field(min_length=1, max_length=10_000)
    project_id: str | None = None


class NewWorkflowResponse(BaseModel):
    """Response with the new workflow id."""

    id: str


class WorkflowState(BaseModel):
    """A workflow snapshot."""

    id: str
    state: str
    phase: str
    final_status: Literal["DONE", "FAILED", "ABORTED"] | None
    created_at: int
    updated_at: int
