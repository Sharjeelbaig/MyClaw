import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = Path(os.getenv("AGENT_WORKSPACE", PROJECT_ROOT / "tmp")).resolve()