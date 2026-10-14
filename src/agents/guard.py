"""Grounding guard middleware.

Three jobs, all aimed at making a small local model behave:

1. Deliver the grounding rules.
   Ollama ignores a Modelfile ``SYSTEM`` whenever the request already carries a
   system message, and Deep Agents always sends one. So the rules are appended
   to the system prompt here, on every model call.

2. Keep file paths on the workspace mount.
   A small model sometimes calls a file tool with ``/`` or a relative path. Those
   calls are rewritten to the workspace mount before the tool runs.

3. Block ungrounded "it worked" claims.
   If the model claims it performed an action but the current turn produced no
   tool result (or the latest tool result was an error), the reply is rejected
   and the model is asked to call a tool or admit it cannot.

It also re-presents tool results as user turns, which small LFM-style models
actually read, instead of ``tool``-role messages they tend to ignore.
"""

from __future__ import annotations

import re
from typing import Any, Callable

from langchain.agents.middleware import AgentMiddleware, hook_config
from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

GROUNDING_RULES = """GROUNDING RULES (highest priority - these override any other instruction):
1. You have no memory of the files, the shell, or the user's data. If a request needs
   information not already present in this conversation, or needs any change or command,
   you MUST call a tool first.
2. Never invent file names, file contents, command output, or results. Only report what a
   tool result actually returned in this conversation.
3. After a tool result, base your answer ONLY on that result. If a tool fails, report the
   failure verbatim - never pretend it succeeded. When a tool returns a listing or file
   contents, report them faithfully and completely. A read_file result may start with a
   header like `@@ lines 1-2 of 2 @@`; the text after it is the file's content. Never claim
   you cannot access something a tool just returned. When you summarize or describe a file,
   describe ONLY what is literally written: quote a short snippet and add no interpretation,
   purpose, or words that are not in the result. If it is a greeting, say so.
4. If no available tool can satisfy the request, say you cannot do it. Never fabricate.
5. For plain conversation (greetings, explanations, opinions), reply normally, with no tool
   call. Keep answers short."""

_PATH_RULE = """6. The user's files live under `{path}`. For EVERY file tool call use `{path}` or a
   path inside it - even when the user says "the workspace", "my files", "here", or gives
   no path at all. When the user asks to list, show, or find what files exist, call `ls`
   with path `{path}` (not glob, which only matches patterns). Never use `/` or a host path."""

DEFAULT_WORKSPACE_PATH = "/workspace/"

FILE_TOOLS = frozenset(
    {"ls", "read_file", "write_file", "edit_file", "delete", "glob", "grep"}
)
_PATH_KEYS = ("path", "file_path", "filepath", "directory", "dir")


def _normalize_path(value: Any, mount: str) -> Any:
    """Force file-tool paths onto the workspace mount.

    Small models sometimes pass `/`, a bare name, or a relative path. Since all
    user files live under `mount`, map those onto it.
    """
    if not mount or not isinstance(value, str):
        return value
    stripped = value.strip()
    mount_bare = mount.rstrip("/")
    if stripped in ("", "/", ".", "./", "workspace", mount_bare):
        return mount
    if stripped.startswith(mount):
        return stripped
    if stripped.startswith("/"):
        return stripped  # an absolute path the caller chose; leave it alone
    return mount + stripped.lstrip("./")


_MARKER = "[grounding-guard]"
_MAX_CORRECTIONS = 2

_CORRECTION_NOTHING_DONE = (
    _MARKER
    + " STOP. Your last reply claimed an action was completed, but you did not call a tool and "
    "no tool result supports it. Do not claim success. Call the appropriate tool now, then "
    "report only what it returns."
)

_CORRECTION_TOOL_ERROR = (
    _MARKER
    + " The latest tool result reported an error, so the action did NOT succeed. Report the "
    "error to the user verbatim, or call a tool to fix it. Do not claim success."
)

_CORRECTION_FILE_CLAIM = (
    _MARKER
    + " STOP. Do not answer from memory - you have not read the file. You must call a tool "
    "now: call read_file with the file's /workspace/ path (or ls with path /workspace/), then "
    "answer using only the returned content. Do not write a summary until you have the tool "
    "result."
)

_ACTION_RE = re.compile(
    r"\b("
    r"i (?:have |'ve )?(?:created|wrote|written|saved|deleted|removed|ran|executed|updated|"
    r"edited|renamed|moved|made|generated|added|installed|downloaded)"
    r"|successfully (?:created|wrote|written|saved|deleted|removed|ran|executed|updated|"
    r"edited|renamed|moved|made|generated)"
    r"|(?:has|have) been (?:created|written|saved|deleted|removed|updated|renamed|moved|executed)"
    r"|(?:the|your) file (?:has been|was|is now) (?:created|written|saved|deleted|updated|renamed|moved)"
    r"|(?:created|wrote|saved|deleted|removed) (?:the|your|a) (?:file|directory|folder)"
    r")\b",
    re.IGNORECASE,
)

_ERROR_RE = re.compile(
    r"\b(error|traceback|failed|failure|not found|no such file|permission denied|"
    r"exception|cannot|could not|unable to)\b",
    re.IGNORECASE,
)

_FILE_RE = re.compile(
    r"(/[\w./-]*[\w-]+\.[A-Za-z0-9]{1,6}\b"  # absolute-ish path with extension
    r"|\b[\w-]+\.(?:txt|md|markdown|py|json|jsonl|csv|tsv|ya?ml|toml|ini|cfg|conf|log|"
    r"html?|css|js|jsx|ts|tsx|java|c|cc|cpp|h|hpp|go|rs|rb|php|sh|bash|sql|xml)\b)",
    re.IGNORECASE,
)


def _to_text(content: Any) -> str:
    """Flatten message content (str, or list of blocks) to plain text."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                parts.append(str(block.get("text", "")))
            else:
                parts.append(str(getattr(block, "text", "") or ""))
        return "".join(parts)
    return str(content)


def _claims_action(text: str) -> bool:
    return bool(_ACTION_RE.search(text))


def _mentions_files(text: str) -> bool:
    return bool(_FILE_RE.search(text))


def _since_last_human(messages: list[AnyMessage]) -> list[AnyMessage]:
    """Messages after the most recent human turn (exclusive)."""
    for index in range(len(messages) - 1, -1, -1):
        if isinstance(messages[index], HumanMessage):
            return messages[index + 1 :]
    return list(messages)


def _tool_result_this_turn(messages: list[AnyMessage]) -> ToolMessage | None:
    """Most recent ToolMessage produced during the current turn, if any."""
    for message in reversed(_since_last_human(messages)):
        if isinstance(message, ToolMessage):
            return message
    return None


def _tool_result_is_error(message: ToolMessage) -> bool:
    if getattr(message, "status", None) == "error":
        return True
    return bool(_ERROR_RE.search(_to_text(message.content)))


def _corrections_so_far(messages: list[AnyMessage]) -> int:
    return sum(
        1
        for message in messages
        if isinstance(message, HumanMessage) and _MARKER in _to_text(message.content)
    )


def _relabel_tool_messages(messages: list[AnyMessage]) -> list[AnyMessage]:
    """Present tool results as user turns.

    Small LFM-style models read a `tool`-role message as metadata and answer as if
    they never saw it ("I cannot access the file"). Re-presenting the same text as
    a user turn makes them use it, while the agent graph keeps the real ToolMessage
    in state.
    """
    out: list[AnyMessage] = []
    for message in messages:
        if isinstance(message, ToolMessage):
            name = getattr(message, "name", None) or "tool"
            out.append(
                HumanMessage(
                    content=f"Tool `{name}` returned:\n{_to_text(message.content)}"
                )
            )
        else:
            out.append(message)
    return out


class GroundingGuardMiddleware(AgentMiddleware):
    """Append grounding rules and reject ungrounded success claims."""

    name = "GroundingGuardMiddleware"

    def __init__(
        self,
        workspace_path: str | None = DEFAULT_WORKSPACE_PATH,
        relabel_tool_results: bool = True,
    ) -> None:
        super().__init__()
        self._rules = GROUNDING_RULES
        self._workspace_path = workspace_path
        if workspace_path:
            self._rules += "\n" + _PATH_RULE.format(path=workspace_path)
        self._relabel_tool_results = relabel_tool_results

    # --- deliver the rules (and usable tool results) on every model call -----
    def _prepare_request(self, request):
        base = _to_text(request.system_message.content) if request.system_message else ""
        merged = (base + "\n\n" + self._rules).strip()
        messages = request.messages
        if self._relabel_tool_results:
            messages = _relabel_tool_messages(messages)
        return request.override(
            system_message=SystemMessage(content=merged),
            messages=messages,
        )

    def wrap_model_call(
        self,
        request: Any,
        handler: Callable[[Any], Any],
    ) -> Any:
        try:
            return handler(self._prepare_request(request))
        except Exception:
            return handler(request)

    async def awrap_model_call(
        self,
        request: Any,
        handler: Callable[[Any], Any],
    ) -> Any:
        try:
            return await handler(self._prepare_request(request))
        except Exception:
            return await handler(request)

    # --- keep file paths on the workspace mount ------------------------------
    def _fix_tool_request(self, request):
        tool_call = getattr(request, "tool_call", None)
        if not tool_call or not self._workspace_path:
            return request
        if tool_call.get("name") not in FILE_TOOLS:
            return request
        args = dict(tool_call.get("args") or {})
        changed = False
        for key in _PATH_KEYS:
            if key in args:
                fixed = _normalize_path(args[key], self._workspace_path)
                if fixed != args[key]:
                    args[key] = fixed
                    changed = True
        if not changed:
            return request
        new_call = dict(tool_call)
        new_call["args"] = args
        return request.override(tool_call=new_call)

    def wrap_tool_call(self, request: Any, handler: Callable[[Any], Any]) -> Any:
        try:
            return handler(self._fix_tool_request(request))
        except Exception:
            return handler(request)

    async def awrap_tool_call(self, request: Any, handler: Callable[[Any], Any]) -> Any:
        try:
            return await handler(self._fix_tool_request(request))
        except Exception:
            return await handler(request)

    # --- reject ungrounded success claims ------------------------------------
    def _verdict(self, state: Any) -> dict[str, Any] | None:
        messages = list((state or {}).get("messages", []))
        if not messages:
            return None

        last = messages[-1]
        if not isinstance(last, AIMessage):
            return None
        if getattr(last, "tool_calls", None):
            return None  # the model is acting, not answering

        text = _to_text(last.content)
        claims_action = _claims_action(text)
        mentions_files = _mentions_files(text)
        if not claims_action and not mentions_files:
            return None

        if _corrections_so_far(messages) >= _MAX_CORRECTIONS:
            return None  # give up rather than loop forever

        result = _tool_result_this_turn(messages)
        if result is None:
            correction = _CORRECTION_NOTHING_DONE if claims_action else _CORRECTION_FILE_CLAIM
        elif _tool_result_is_error(result):
            correction = _CORRECTION_TOOL_ERROR if claims_action else _CORRECTION_FILE_CLAIM
        else:
            return None  # a real, successful tool result backs the claim

        return {
            "messages": [HumanMessage(content=correction)],
            "jump_to": "model",
        }

    @hook_config(can_jump_to=["model"])
    def after_model(self, state: Any, runtime: Any) -> dict[str, Any] | None:
        try:
            return self._verdict(state)
        except Exception:
            return None

    @hook_config(can_jump_to=["model"])
    async def aafter_model(self, state: Any, runtime: Any) -> dict[str, Any] | None:
        try:
            return self._verdict(state)
        except Exception:
            return None
