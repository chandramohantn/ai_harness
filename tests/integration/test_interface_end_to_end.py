import pytest

from pathlib import Path

from src.bootstrap import build_default_harness
from src.domain.enums import TaskStatus


def test_submit_task_executes_sequential_workflow(tmp_path: Path) -> None:
    harness = build_default_harness(root_path=tmp_path)
    result = harness.submit_task(
        {
            "task_type": "workflow",
            "payload": {
                "steps": [
                    {
                        "step_id": "write-file",
                        "step_type": "tool_call",
                        "tool_name": "filesystem",
                        "parameters": {
                            "action": "write",
                            "path": "report.txt",
                            "content": "phase1 mvp",
                        },
                    },
                    {
                        "step_id": "search-file",
                        "step_type": "tool_call",
                        "tool_name": "search",
                        "parameters": {"query": "phase1"},
                    },
                ]
            },
            "metadata": {"max_retries": 0},
        }
    )

    assert result.status == TaskStatus.COMPLETED
    assert result.tool_calls[-1].tool_name == "search"
    assert result.output[0]["path"] == "report.txt"
    assert harness.get_task_status(result.task_id) == TaskStatus.COMPLETED
    assert (tmp_path / "report.txt").exists()


def test_submit_task_with_single_tool_payload() -> None:
    harness = build_default_harness()
    result = harness.submit_task(
        {
            "task_type": "echo-task",
            "payload": {
                "tool_name": "echo",
                "parameters": {"value": {"status": "ok"}},
            },
        }
    )

    assert result.status == TaskStatus.COMPLETED
    assert result.output == {"status": "ok"}


def test_submit_task_rejects_invalid_payload() -> None:
    harness = build_default_harness()

    with pytest.raises(ValueError, match="payload"):
        harness.submit_task({"task_type": "bad", "payload": "not-a-dict"})
