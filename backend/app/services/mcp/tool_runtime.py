"""MCP 도구 런타임 — 생성된 Python MCP 도구를 로드하고 실행한다.

Docker 없이 subprocess로 Python 스크립트를 실행한다.
각 도구는 독립적인 Python 파일로 저장되며, stdin/stdout JSON-RPC로 통신한다.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
import uuid
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.logging import logger

log = logger(__name__)

_TOOLS_DIR = Path(settings.upload_dir).parent / "generated_tools"
_TOOLS_DIR.mkdir(parents=True, exist_ok=True)


def save_tool(tool_id: str, code: str, metadata: dict[str, Any] | None = None) -> Path:
    """생성된 MCP 도구 코드를 파일로 저장한다."""
    tool_dir = _TOOLS_DIR / tool_id
    tool_dir.mkdir(parents=True, exist_ok=True)

    tool_path = tool_dir / "tool.py"
    tool_path.write_text(code, encoding="utf-8")

    if metadata:
        meta_path = tool_dir / "metadata.json"
        meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    log.info("MCP 도구 저장: %s → %s", tool_id, tool_path)
    return tool_path


def list_tools() -> list[dict[str, Any]]:
    """저장된 모든 MCP 도구 목록을 반환한다."""
    tools = []
    if not _TOOLS_DIR.exists():
        return tools

    for tool_dir in sorted(_TOOLS_DIR.iterdir()):
        if not tool_dir.is_dir():
            continue
        meta_path = tool_dir / "metadata.json"
        tool_path = tool_dir / "tool.py"
        if not tool_path.exists():
            continue

        meta = {}
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass

        tools.append({
            "tool_id": tool_dir.name,
            "path": str(tool_path),
            "has_code": True,
            **meta,
        })

    return tools


def resolve_agent_tools(
    agent_id: str,
    project_files: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """레지스트리 agent_id로 실제 도구 목록을 찾는다.

    레지스트리 agent_id(agent-uuid)와 도구 agent_id(provisioner 이름)가
    다를 수 있으므로 여러 방식으로 매칭한다.
    """
    tools = list_tools()

    matched = [t for t in tools if t.get("agent_id") == agent_id]
    if matched:
        return matched

    matched = [t for t in tools if t["tool_id"].startswith(f"{agent_id}__")]
    if matched:
        return matched

    if project_files and isinstance(project_files, dict):
        pf_agent_id = project_files.get("agent_id")
        if pf_agent_id:
            matched = [
                t for t in tools
                if t.get("agent_id") == pf_agent_id
                or t["tool_id"].startswith(f"{pf_agent_id}__")
            ]
            if matched:
                return matched

        pf_tools = project_files.get("tools", [])
        tool_ids = {
            t.get("tool_id") for t in pf_tools if isinstance(t, dict) and t.get("tool_id")
        }
        if tool_ids:
            matched = [t for t in tools if t["tool_id"] in tool_ids]
            if matched:
                return matched

    return []


def delete_tools_for_agent(agent_id: str) -> int:
    """특정 에이전트에 속한 모든 도구를 삭제한다. 삭제된 도구 수를 반환."""
    import shutil

    deleted = 0
    if not _TOOLS_DIR.exists():
        return deleted

    for tool_dir in list(_TOOLS_DIR.iterdir()):
        if not tool_dir.is_dir():
            continue
        if tool_dir.name.startswith(f"{agent_id}__"):
            shutil.rmtree(tool_dir, ignore_errors=True)
            deleted += 1
            log.info("도구 삭제: %s", tool_dir.name)

    return deleted


async def execute_tool(
    tool_id: str,
    function_name: str,
    arguments: dict[str, Any] | None = None,
    timeout: float = 60.0,
    env_vars: dict[str, str] | None = None,
) -> dict[str, Any]:
    """MCP 도구의 함수를 실행한다.

    도구 Python 파일을 subprocess로 실행하고 결과를 반환한다.
    env_vars가 제공되면 subprocess 환경변수로 전달한다.
    """
    tool_path = _TOOLS_DIR / tool_id / "tool.py"
    if not tool_path.exists():
        return {"error": f"Tool not found: {tool_id}", "status": "not_found"}

    runner_code = _build_runner_code(str(tool_path), function_name, arguments or {})

    import os
    env = dict(os.environ)
    if env_vars:
        env.update(env_vars)

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-c", runner_code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(tool_path.parent),
            env=env,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

        stdout_text = stdout.decode("utf-8", errors="replace").strip()
        stderr_text = stderr.decode("utf-8", errors="replace").strip()

        if proc.returncode != 0:
            log.error("도구 실행 실패: %s/%s, stderr=%s", tool_id, function_name, stderr_text[:300])
            return {
                "status": "error",
                "exit_code": proc.returncode,
                "stderr": stderr_text[:2000],
            }

        try:
            result = json.loads(stdout_text)
        except json.JSONDecodeError:
            result = {"output": stdout_text}

        log.info("도구 실행 완료: %s/%s", tool_id, function_name)
        return {"status": "success", "result": result}

    except asyncio.TimeoutError:
        log.error("도구 실행 타임아웃: %s/%s (%.0fs)", tool_id, function_name, timeout)
        return {"status": "timeout", "error": f"Execution timed out after {timeout}s"}
    except Exception as exc:
        log.error("도구 실행 예외: %s/%s, %s", tool_id, function_name, exc)
        return {"status": "error", "error": str(exc)}


def _build_runner_code(tool_path: str, function_name: str, arguments: dict) -> str:
    """도구를 실행하는 임시 Python 코드를 생성한다."""
    args_json = json.dumps(arguments, ensure_ascii=False)
    return f"""\
import sys, json, importlib.util, asyncio

spec = importlib.util.spec_from_file_location("tool", {tool_path!r})
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

func = getattr(mod, {function_name!r}, None)
if func is None:
    print(json.dumps({{"error": "Function not found: {function_name}"}}))
    sys.exit(1)

args = json.loads({args_json!r})

if asyncio.iscoroutinefunction(func):
    result = asyncio.run(func(**args))
else:
    result = func(**args)

if result is None:
    result = {{"status": "ok"}}
elif not isinstance(result, (dict, list)):
    result = {{"output": str(result)}}

print(json.dumps(result, ensure_ascii=False, default=str))
"""
