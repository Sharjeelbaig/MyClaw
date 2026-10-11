
from pathlib import Path
import json
import subprocess

from langchain.tools import tool

WORKSPACE = (Path(__file__).resolve().parent.parent / "tmp").resolve()


@tool
def python_executor(mode: str, target: str) -> str:
    """Execute Python code or a Python file in an isolated container.

    Args:
        mode: "file" to execute an existing file, or "code" to execute
              a Python code snippet.
        target: A workspace-relative file path in file mode, or the
                actual Python source code in code mode.

    Returns the exact stdout, stderr, exit code, and execution status.
    Always use file mode to run an existing script.

    IMPORTANT:
    - Never guess or invent output or errors.
    - stdout and stderr must be reported exactly as returned.
    - An empty stdout means the program printed nothing.
    - A nonzero exit code indicates execution failure.
    - If execution fails, report the actual error from stderr.
    """

    if mode not in {"file", "code"}:
        return json.dumps({
            "status": "error",
            "error": "mode must be 'file' or 'code'",
        })

    if mode == "file":
        path = (WORKSPACE / target).resolve()

        if not path.is_relative_to(WORKSPACE):
            return json.dumps({
                "status": "error",
                "error": "File path must remain inside the workspace.",
            })

        if not path.is_file():
            return json.dumps({
                "status": "error",
                "error": f"File not found: {target}",
                "workspace": str(WORKSPACE),
            })

        python_args = [
            "python",
            f"/workspace/{path.relative_to(WORKSPACE)}",
        ]
        input_code = None

    else:
        python_args = ["python", "-"]
        input_code = target

    command = [
        "docker", "run", "--rm", "-i",
        "--network=none",
        "--memory=256m",
        "--cpus=1",
        "-v", f"{WORKSPACE}:/workspace",
        "-w", "/workspace",
        "python:3.12-slim",
        *python_args,
    ]

    try:
        result = subprocess.run(
            command,
            input=input_code,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

        return json.dumps({
            "status": "success" if result.returncode == 0 else "failed",
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }, ensure_ascii=False)

    except subprocess.TimeoutExpired as exc:
        def as_text(value):
            if value is None:
                return ""
            if isinstance(value, bytes):
                return value.decode("utf-8", errors="replace")
            return value

        return json.dumps({
            "status": "timeout",
            "timeout_seconds": 120,
            "stdout": as_text(exc.stdout),
            "stderr": as_text(exc.stderr),
            "error": "Execution exceeded the time limit.",
        }, ensure_ascii=False)

    except FileNotFoundError as exc:
        return json.dumps({
            "status": "error",
            "error": f"Could not start Docker: {exc}",
        }, ensure_ascii=False)

    except OSError as exc:
        return json.dumps({
            "status": "error",
            "error": f"Execution failed: {exc}",
        }, ensure_ascii=False)
