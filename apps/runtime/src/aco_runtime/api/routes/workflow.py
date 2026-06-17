"""Workflow HTTP routes. Stub for Phase 0; real impl in Phase 1."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aco_runtime.api.schemas import (
    NewWorkflowRequest,
    NewWorkflowResponse,
    WorkflowState,
)

router = APIRouter()


@router.post("", response_model=NewWorkflowResponse, status_code=201)
async def start_workflow(req: NewWorkflowRequest) -> NewWorkflowResponse:
    """Start a new workflow. Stub for Phase 0."""
    raise HTTPException(
        status_code=501,
        detail="start_workflow not implemented; coming in Phase 1 (see plans/Phase1.md)",
    )


@router.get("/{wf_id}", response_model=WorkflowState | None)
async def get_workflow(wf_id: str) -> WorkflowState | None:
    """Fetch a workflow by id. Stub for Phase 0."""
    raise HTTPException(
        status_code=501,
        detail="get_workflow not implemented; coming in Phase 1",
    )


@router.post("/{wf_id}/cancel", status_code=204)
async def cancel_workflow(wf_id: str) -> None:
    """Cancel an in-flight workflow. Stub for Phase 0."""
    raise HTTPException(
        status_code=501,
        detail="cancel_workflow not implemented; coming in Phase 1",
    )
