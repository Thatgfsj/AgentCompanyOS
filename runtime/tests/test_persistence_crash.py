"""Tests for WorkflowLog crash-safety (v0.2 P0 fix)."""

from __future__ import annotations

from pathlib import Path

import pytest
from aco_runtime_lib import State
from aco_runtime_lib.workflow import WorkflowLog, iter_entries_sync


@pytest.mark.asyncio
async def test_seq_count_correct_after_partial_line_truncation(tmp_path: Path) -> None:
    """A file ending without newline (crash mid-write) must produce
    the correct seq on next append, not off-by-one.
    """
    log_path = tmp_path / "wf_crash.jsonl"
    # Write 3 complete lines + 1 partial (no trailing newline)
    log_path.write_text(
        '{"ts":"t","wf_id":"w","seq":1,"from_state":null,"to_state":"REQ_RECEIVED",'
        '"event":"e","actor":"a","context":{}}\n'
        '{"ts":"t","wf_id":"w","seq":2,"from_state":"REQ_RECEIVED",'
        '"to_state":"REQ_ANALYZING","event":"e","actor":"a","context":{}}\n'
        '{"ts":"t","wf_id":"w","seq":3,"from_state":"REQ_ANALYZING",'
        '"to_state":"REQ_CLARIFIED","event":"e","actor":"a","context":{}}\n'
        '{"ts":"t","wf_id":"w","seq":4,"from_state":"REQ_CLARIFIED",'
        '"to_state":"PLAN_DRAFTING","event":"e","actor":"a","contex',  # partial
        encoding="utf-8",
    )
    # Reopen — partial line should be dropped, seq counter = 3
    log = WorkflowLog(log_path)
    await log.open()
    # Next append should be seq=4
    entry = await log.append(
        wf_id="w",
        from_state=State.REQ_CLARIFIED,
        to_state=State.DONE,
        event="finalize",
        actor="agent:chief",
    )
    await log.close()
    assert entry.seq == 4, f"expected seq=4, got {entry.seq}"

    # Re-read the file: should have exactly 4 complete lines
    entries = list(iter_entries_sync(log_path))
    assert len(entries) == 4
    assert entries[-1].seq == 4
    assert entries[-1].to_state == "DONE"


@pytest.mark.asyncio
async def test_seq_count_correct_for_clean_file(tmp_path: Path) -> None:
    """A file with N complete lines should yield seq=N+1 on next append."""
    log_path = tmp_path / "wf_clean.jsonl"
    log = WorkflowLog(log_path)
    await log.open()
    for s in (State.REQ_RECEIVED, State.REQ_ANALYZING, State.REQ_CLARIFIED):
        await log.append("w", None, s, "e", "a")
    await log.close()

    log2 = WorkflowLog(log_path)
    await log2.open()
    entry = await log2.append("w", State.REQ_CLARIFIED, State.DONE, "e", "a")
    await log2.close()
    assert entry.seq == 4


@pytest.mark.asyncio
async def test_seq_count_for_wholly_corrupt_file(tmp_path: Path) -> None:
    """A file with NO complete lines (all garbage) starts fresh at seq=1."""
    log_path = tmp_path / "wf_corrupt.jsonl"
    log_path.write_text('{"partial": "junk', encoding="utf-8")
    log = WorkflowLog(log_path)
    await log.open()
    entry = await log.append("w", None, State.REQ_RECEIVED, "e", "a")
    await log.close()
    assert entry.seq == 1
