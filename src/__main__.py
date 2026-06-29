"""Command-line entry point for the default harness.

This module lets developers execute the package directly with
``python -m src``. If no task payload is supplied, it runs a small echo
workflow so the runtime can be smoke-tested quickly.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from src.bootstrap import build_default_harness


def _load_task_payload(argv: list[str]) -> dict[str, Any]:
    """Load a task payload from argv.

    Args:
        argv: Raw command-line arguments.

    Returns:
        A task payload dictionary suitable for ``InterfaceManager.submit_task``.
    """

    if len(argv) < 2:
        return {
            "task_type": "echo-task",
            "payload": {
                "tool_name": "echo",
                "parameters": {"value": {"message": "src package is ready"}},
            },
        }

    candidate = Path(argv[1])
    if candidate.exists():
        return json.loads(candidate.read_text())
    return json.loads(argv[1])


def main() -> int:
    """Run the default harness command-line flow.

    Returns:
        Process exit code. Zero indicates task success.
    """

    harness = build_default_harness(root_path=Path.cwd())
    task_payload = _load_task_payload(sys.argv)
    result = harness.submit_task(task_payload)
    print(json.dumps(result.to_dict(), indent=2, default=str))
    return 0 if result.is_success() else 1


if __name__ == "__main__":
    raise SystemExit(main())
