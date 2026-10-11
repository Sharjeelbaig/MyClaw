
from pathlib import Path
import json
import os
import subprocess

from langchain.tools import tool

WORKSPACE = (Path(__file__).resolve().parent.parent / "tmp").resolve()

# Configurable via environment variables
DOCKER_IMAGE = os.getenv("PYTHON_EXECUTOR_IMAGE", "python:3.12-slim")
DEFAULT_TIMEOUT = int(os.getenv("PYTHON_EXECUTOR_TIMEOUT", "120"))
MAX_CODE_SIZE = int(os.getenv("PYTHON_EXECUTOR_MAX_CODE_SIZE", "1000000"))  # 1MB
MEMORY_LIMIT = os.getenv("PYTHON_EXECUTOR_MEMORY", "256m")
CPU_LIMIT = os.getenv("PYTHON_EXECUTOR_CPUS", "1")


def _check_docker_available() -> str | None:
    """Check if Docker daemon is running. Returns error message if not."""
    try:
        subprocess.run(
            ["docker", "info"],
            capture_output=True,
            check=True,
            timeout=5,
        )
    except FileNotFoundError:
        return "Docker not installed or not in PATH"
    except subprocess.CalledProcessError:
        return "Docker daemon not running"
    except subprocess.TimeoutExpired:
        return "Docker daemon not responding"
    return None


@tool
def python_executor(mode: str, target: str, timeout: int | None = None) -> str:
    """Execute Python code or a Python file in an isolated container.

    Args:
        mode: "file" to execute an existing file, or "code" to execute
              a Python code snippet.
        target: A workspace-relative file path in file mode, or the
                actual Python source code in code mode.
        timeout: Optional timeout in seconds (default: 120, max: 300).

    Returns the exact stdout, stderr, exit code, and execution status.
    Always use file mode to run an existing script.

    IMPORTANT:
    - Never guess or invent output or errors.
    - stdout and stderr must be reported exactly as returned.
    - An empty stdout means the program printed nothing.
    - A nonzero exit code indicates execution failure.
    - If execution fails, report the actual error from stderr.
    """

    # Pre-flight: check Docker availability
    docker_error = _check_docker_available()
    if docker_error:
        return json.dumps({
            "status": "error",
            "error": docker_error,
        })

    if mode not in {"file", "code"}:
        return json.dumps({
            "status": "error",
            "error": "mode must be 'file' or 'code'",
        })

    # Size limit for code mode
    if mode == "code" and len(target) > MAX_CODE_SIZE:
        return json.dumps({
            "status": "error",
            "error": f"Code exceeds maximum size of {MAX_CODE_SIZE} bytes",
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
                "workspace": "/workspace",
            })

        # Size limit for file mode
        if path.stat().st_size > MAX_CODE_SIZE:
            return json.dumps({
                "status": "error",
                "error": f"File exceeds maximum size of {MAX_CODE_SIZE} bytes",
            })

        python_args = [
            "python",
            f"/workspace/{path.relative_to(WORKSPACE)}",
        ]
        input_code = None

    else:
        python_args = ["python", "-"]
        input_code = target

    # Validate timeout
    exec_timeout = timeout or DEFAULT_TIMEOUT
    if exec_timeout > 300:
        exec_timeout = 300
    elif exec_timeout < 1:
        exec_timeout = 1

    command = [
        "docker", "run", "--rm", "-i",
        "--network=none",
        f"--memory={MEMORY_LIMIT}",
        f"--cpus={CPU_LIMIT}",
        "-v", f"{WORKSPACE}:/workspace",
        "-w", "/workspace",
        DOCKER_IMAGE,
        *python_args,
    ]

    try:
        result = subprocess.run(
            command,
            input=input_code,
            capture_output=True,
            text=True,
            timeout=exec_timeout,
            check=False,
        )

        return json.dumps({
            "status": "success" if result.returncode == 0 else "failed",
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        })

    except subprocess.TimeoutExpired as exc:
        def as_text(value):
            if value is None:
                return ""
            if isinstance(value, bytes):
                return value.decode("utf-8", errors="replace")
            return value

        return json.dumps({
            "status": "timeout",
            "timeout_seconds": exec_timeout,
            "stdout": as_text(exc.stdout),
            "stderr": as_text(exc.stderr),
            "error": "Execution exceeded the time limit.",
        })

    except FileNotFoundError as exc:
        return json.dumps({
            "status": "error",
            "error": f"Could not start Docker: {exc}",
        })

    except OSError as exc:
        return json.dumps({
            "status": "error",
            "error": f"Execution failed: {exc}",
        })
