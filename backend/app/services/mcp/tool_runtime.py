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

# 공용 도구 — 에이전트 삭제와 무관하게 영구 보존된다.
_SHARED_DIR = Path(settings.upload_dir).parent / "shared_tools"
_SHARED_DIR.mkdir(parents=True, exist_ok=True)

# 레포에 보관된 공용 도구 정식 소스 (시작 시 _SHARED_DIR 로 복사한다).
_SHARED_SRC_DIR = Path(__file__).parent / "shared_tools_src"


def ensure_shared_tools() -> None:
    """레포의 공용 도구 소스를 런타임 shared_tools 디렉터리로 복사·갱신한다.

    앱 시작 시 호출한다. 라이브러리 모듈(.py)과 도구 디렉터리를 모두 동기화한다.
    """
    import shutil

    if not _SHARED_SRC_DIR.exists():
        return
    for item in _SHARED_SRC_DIR.iterdir():
        dst = _SHARED_DIR / item.name
        try:
            if item.is_dir():
                shutil.copytree(item, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dst)
        except Exception as exc:  # noqa: BLE001
            log.warning("공용 도구 동기화 실패: %s (%s)", item.name, exc)
    log.info("공용 도구 동기화 완료: %s", _SHARED_DIR)


def _resolve_tool_dir(tool_id: str) -> Path | None:
    """tool_id 로 도구 디렉터리를 찾는다 (생성 도구 → 공용 도구 순)."""
    gen = _TOOLS_DIR / tool_id
    if (gen / "tool.py").exists():
        return gen
    shared = _SHARED_DIR / tool_id
    if (shared / "tool.py").exists():
        return shared
    return None


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


def _builtin_tools() -> list[dict[str, Any]]:
    """앱 내부에서 직접 실행되는 내장(builtin) 도구 목록."""
    from app.services.mcp import rag_tool

    return [{
        "tool_id": rag_tool.TOOL_ID,
        "name": "RAG Search (내장)",
        "description": "Synapse 지식베이스 하이브리드 검색(벡터+BM25+그래프).",
        "functions": rag_tool.FUNCTIONS,
        "path": "builtin://rag",
        "has_code": True,
        "shared": True,
        "builtin": True,
        "category": "retrieval",
    }]


def list_tools(include_shared: bool = True) -> list[dict[str, Any]]:
    """저장된 모든 MCP 도구 목록을 반환한다 (내장·공용 도구 포함)."""
    tools = list(_builtin_tools())
    dirs = [_TOOLS_DIR]
    if include_shared:
        dirs.append(_SHARED_DIR)

    for base in dirs:
        if not base.exists():
            continue
        is_shared = base == _SHARED_DIR
        for tool_dir in sorted(base.iterdir()):
            if not tool_dir.is_dir():
                continue
            tool_path = tool_dir / "tool.py"
            if not tool_path.exists():
                continue

            meta = {}
            meta_path = tool_dir / "metadata.json"
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    pass

            tools.append({
                "tool_id": tool_dir.name,
                "path": str(tool_path),
                "has_code": True,
                "shared": is_shared,
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


def delete_tool(tool_id: str) -> bool:
    """단일 도구 디렉터리를 삭제한다. 삭제되면 True."""
    import shutil

    tool_dir = _TOOLS_DIR / tool_id
    if tool_dir.is_dir():
        shutil.rmtree(tool_dir, ignore_errors=True)
        log.info("도구 삭제: %s", tool_id)
        return True
    return False


def delete_tools_for_agent(agent_id: str, keep: set[str] | None = None) -> int:
    """특정 에이전트에 속한 도구를 삭제한다. 삭제된 도구 수를 반환.

    keep 에 포함된 tool_id 는 보호되어 삭제되지 않는다 (공용/필수/심판 보존).
    """
    import shutil

    keep = keep or set()
    deleted = 0
    if not _TOOLS_DIR.exists():
        return deleted

    for tool_dir in list(_TOOLS_DIR.iterdir()):
        if not tool_dir.is_dir():
            continue
        if tool_dir.name in keep:
            continue
        if tool_dir.name.startswith(f"{agent_id}__"):
            shutil.rmtree(tool_dir, ignore_errors=True)
            deleted += 1
            log.info("도구 삭제: %s", tool_dir.name)

    return deleted


# 단계 분류 키워드 — email/schedule 을 summarize 보다 먼저 검사해
# "send_digest_email"(digest+email) 같은 이름이 summarize 로 오분류되는 것을 막는다.
_DEDUP_STAGE_KEYWORDS = [
    ("fetch", ("fetch", "scrape", "crawl", "download")),
    ("schedule", ("schedule", "cron", "timer")),
    ("email", ("send", "email", "mail", "notify")),
    ("check", ("check", "freshness", "dedup", "validate", "filter", "robots")),
    ("summarize", ("summarize", "extract", "parse", "analyze", "digest")),
]


def _stage_of_tool_name(tool_id: str) -> str:
    """tool_id 의 함수명 부분(접두사 제거)으로 파이프라인 단계를 분류한다."""
    suffix = tool_id.split("__", 1)[-1].lower()
    for stage, kws in _DEDUP_STAGE_KEYWORDS:
        if any(kw in suffix for kw in kws):
            return stage
    return "other"


def dedupe_generated_tools() -> dict[str, Any]:
    """에이전트별로 같은 단계의 중복 도구를 1개만 남기고 삭제한다.

    - 에이전트 접두사(`{agent}__`)로 그룹핑한다.
    - 단계(fetch/check/summarize/email/schedule)마다 1개만 유지한다.
    - fetch 는 공용 파서(universal_parser)를 쓰는 도구를 우선 보존한다.
    - 단계 분류가 안 되는 'other' 도구는 모두 보존한다.
    """
    import shutil

    if not _TOOLS_DIR.exists():
        return {"deleted": [], "kept": [], "groups": 0}

    groups: dict[str, list[str]] = {}
    for tool_dir in sorted(_TOOLS_DIR.iterdir()):
        if not tool_dir.is_dir() or not (tool_dir / "tool.py").exists():
            continue
        prefix = tool_dir.name.split("__", 1)[0]
        groups.setdefault(prefix, []).append(tool_dir.name)

    deleted: list[str] = []
    kept: list[str] = []

    for prefix, names in groups.items():
        chosen: dict[str, str] = {}  # stage → 보존할 tool_id

        # fetch 는 공용 파서 사용 도구를 우선 채택하도록 미리 고른다.
        for name in names:
            if _stage_of_tool_name(name) != "fetch":
                continue
            code = ""
            try:
                code = (_TOOLS_DIR / name / "tool.py").read_text(encoding="utf-8")
            except OSError:
                pass
            if "universal_parser" in code:
                chosen["fetch"] = name
                break

        for name in names:
            stage = _stage_of_tool_name(name)
            if stage == "other":
                kept.append(name)
                continue
            if stage not in chosen:
                chosen[stage] = name
                kept.append(name)
            elif chosen[stage] == name:
                kept.append(name)
            else:
                shutil.rmtree(_TOOLS_DIR / name, ignore_errors=True)
                deleted.append(name)
                log.info("중복 도구 삭제: %s (단계=%s, 보존=%s)", name, stage, chosen[stage])

    log.info("도구 중복 정리: %d개 삭제, %d개 보존 (그룹 %d)",
             len(deleted), len(kept), len(groups))
    return {"deleted": deleted, "kept": kept, "groups": len(groups)}


def remove_orphan_tools(known_agent_ids: set[str]) -> dict[str, Any]:
    """레지스트리에 없는(삭제된) 에이전트의 잔여 도구 그룹을 삭제한다.

    known_agent_ids 에는 레지스트리 agent_id 와 도구 접두사(provisioner snake_case)를
    모두 넣어 전달한다.
    """
    import shutil

    if not _TOOLS_DIR.exists():
        return {"deleted": [], "kept_groups": []}

    deleted: list[str] = []
    kept_groups: set[str] = set()
    for tool_dir in sorted(_TOOLS_DIR.iterdir()):
        if not tool_dir.is_dir():
            continue
        prefix = tool_dir.name.split("__", 1)[0]
        if prefix in known_agent_ids:
            kept_groups.add(prefix)
            continue
        shutil.rmtree(tool_dir, ignore_errors=True)
        deleted.append(tool_dir.name)
        log.info("고아 도구 삭제: %s (에이전트 없음)", tool_dir.name)

    return {"deleted": deleted, "kept_groups": sorted(kept_groups)}


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

    내장(builtin) 도구(RAG 검색 등)는 앱 내부 서비스(Milvus/Neo4j)에 접근해야
    하므로 subprocess 대신 in-process 로 직접 실행한다.
    """
    # 내장 RAG 도구는 in-process 로 위임한다 (지연 import 로 순환참조 회피).
    from app.services.mcp import rag_tool

    if tool_id == rag_tool.TOOL_ID:
        return await rag_tool.call(function_name, arguments)

    tool_dir = _resolve_tool_dir(tool_id)
    if tool_dir is None:
        return {"error": f"Tool not found: {tool_id}", "status": "not_found"}
    tool_path = tool_dir / "tool.py"

    runner_code = _build_runner_code(str(tool_path), function_name)

    import os
    env = dict(os.environ)
    if env_vars:
        env.update(env_vars)

    # 인자(context)는 명령행이 아니라 stdin으로 전달한다.
    # (HTML 본문 등 대용량 데이터를 -c 인자에 넣으면 ARG_MAX 초과로 Errno 7 발생)
    stdin_payload = json.dumps(arguments or {}, ensure_ascii=False).encode("utf-8")

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-c", runner_code,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(tool_path.parent),
            env=env,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=stdin_payload), timeout=timeout,
        )

        stdout_text = stdout.decode("utf-8", errors="replace").strip()
        stderr_text = stderr.decode("utf-8", errors="replace").strip()

        if proc.returncode != 0:
            structured = _parse_tool_error(stdout_text)
            if structured:
                where = f" (tool.py:{structured['line']})" if structured.get("line") else ""
                log.error(
                    "도구 실행 실패: %s/%s — %s: %s%s",
                    tool_id, function_name,
                    structured.get("error_type"), structured.get("error_message"), where,
                )
                return {
                    "status": "error",
                    "exit_code": proc.returncode,
                    "tool_id": tool_id,
                    "function": function_name,
                    **structured,
                    "stderr": stderr_text[:2000],
                }
            log.error("도구 실행 실패: %s/%s, stderr=%s", tool_id, function_name, stderr_text[:300])
            return {
                "status": "error",
                "exit_code": proc.returncode,
                "tool_id": tool_id,
                "function": function_name,
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


def _parse_tool_error(stdout_text: str) -> dict[str, Any] | None:
    """런너가 출력한 구조화된 도구 에러(JSON)를 파싱한다.

    마지막 JSON 라인에서 __tool_error__ 마커를 찾는다.
    """
    if not stdout_text:
        return None
    for line in reversed(stdout_text.splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and data.get("__tool_error__"):
            data.pop("__tool_error__", None)
            return data
    return None


def _build_runner_code(tool_path: str, function_name: str) -> str:
    """도구를 실행하는 임시 Python 코드를 생성한다.

    함수 시그니처를 검사하여 context(arguments)에서 일치하는 인자만 전달하고,
    값이 없는 필수 인자는 빈 문자열로 채워 TypeError를 방지한다.
    인자(context)는 stdin(JSON)으로 받는다 — 대용량 데이터의 ARG_MAX 초과 방지.
    """
    return f"""\
import sys, json, importlib.util, asyncio, inspect, traceback

TOOL_PATH = {tool_path!r}
FUNC_NAME = {function_name!r}
SHARED_DIR = {str(_SHARED_DIR)!r}

# 공용 라이브러리(universal_parser 등)를 어떤 도구든 import 할 수 있게 한다.
if SHARED_DIR not in sys.path:
    sys.path.insert(0, SHARED_DIR)


def _emit_error(stage, exc):
    \"\"\"예외 발생 위치를 도구 파일 기준으로 찾아 구조화해 출력한다.\"\"\"
    tb = traceback.extract_tb(exc.__traceback__)
    loc = None
    for frame in tb:
        if frame.filename == TOOL_PATH:
            loc = frame  # 도구 파일 안에서 마지막으로 실행된 줄
    err = {{
        "__tool_error__": True,
        "stage": stage,
        "function": FUNC_NAME,
        "error_type": type(exc).__name__,
        "error_message": str(exc),
        "traceback": traceback.format_exc()[-2000:],
    }}
    if loc is not None:
        err["line"] = loc.lineno
        err["code"] = (loc.line or "").strip()
    print(json.dumps(err, ensure_ascii=False))
    sys.exit(2)


try:
    spec = importlib.util.spec_from_file_location("tool", TOOL_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
except Exception as exc:
    _emit_error("load", exc)

func = getattr(mod, FUNC_NAME, None)
if func is None:
    print(json.dumps({{"__tool_error__": True, "stage": "lookup",
                       "function": FUNC_NAME,
                       "error_type": "AttributeError",
                       "error_message": "함수를 찾을 수 없습니다: " + FUNC_NAME}}))
    sys.exit(2)

_stdin = sys.stdin.read()
context = json.loads(_stdin) if _stdin.strip() else {{}}

try:
    sig = inspect.signature(func)
    kwargs = {{}}
    accepts_var_kw = any(
        p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
    )
    if accepts_var_kw:
        kwargs = dict(context)
    else:
        for name, p in sig.parameters.items():
            if p.kind in (inspect.Parameter.VAR_POSITIONAL,):
                continue
            if name in context:
                kwargs[name] = context[name]
            elif p.default is inspect.Parameter.empty:
                kwargs[name] = ""
except (ValueError, TypeError):
    kwargs = dict(context)

try:
    if asyncio.iscoroutinefunction(func):
        result = asyncio.run(func(**kwargs))
    else:
        result = func(**kwargs)
except Exception as exc:
    _emit_error("run", exc)

if result is None:
    result = {{"status": "ok"}}
elif not isinstance(result, (dict, list)):
    result = {{"output": str(result)}}

print(json.dumps(result, ensure_ascii=False, default=str))
"""
