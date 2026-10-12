"""File structure memory utilities for the planner."""
from pathlib import Path
from .myclaw_store import MyClawStore
from .context_schema import FileStructure


def update_file_structure_memory(store: MyClawStore) -> FileStructure:
    """Scan workspace and update file structure in .myclaw."""
    fs = store.scan_workspace_structure()
    store.save_file_structure(fs)
    return fs


def get_file_structure_summary(store: MyClawStore, max_items: int = 50) -> str:
    """Get a human-readable summary of file structure."""
    fs = store.load_file_structure()
    if not fs:
        fs = update_file_structure_memory(store)

    lines = [
        f"## Project Structure ({fs.root})",
        f"**Directories:** {len(fs.directories)}  |  **Files:** {len(fs.files)}",
        f"**Last updated:** {fs.updated_at}",
        "",
        "### Directories:",
    ]
    for d in fs.directories[:max_items]:
        lines.append(f"  📁 {d}/")
    if len(fs.directories) > max_items:
        lines.append(f"  ... and {len(fs.directories) - max_items} more")

    lines.append("\n### Key Files:")
    key_files = [f for f in fs.files if not f.startswith(".myclaw")][:max_items]
    for f in key_files:
        lines.append(f"  📄 {f}")
    if len(fs.files) > max_items:
        lines.append(f"  ... and {len(fs.files) - max_items} more")

    return "\n".join(lines)


def find_files_by_pattern(store: MyClawStore, pattern: str) -> list[str]:
    """Find files matching a pattern."""
    fs = store.load_file_structure()
    if not fs:
        fs = update_file_structure_memory(store)

    import fnmatch
    matches = [f for f in fs.files if fnmatch.fnmatch(f, pattern)]
    return matches