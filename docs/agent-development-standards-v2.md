# Agent 개발 표준 (Agent Development Standards)

문서 버전: 2.0
대상 독자: 백엔드/AI 개발자(Agent / Workflow), DevOps 


> 본 문서는 **공통 개발 표준의 하위 도메인 문서**입니다.
> 네이밍·에러코드·로깅·응답 포맷의 **기본 원칙은 공통 표준을 따르고**, 본 문서는 그 위에서
> **LangGraph 기반 에이전트/워크플로우 개발 전반에 적용되는 추가 규칙**을 정의합니다.
>
> **적용 범위**: 본 표준은 특정 에이전트가 아니라 **모든 에이전트에 공통 적용**됩니다.
> 특정 도메인에만 해당하는 규칙은 "**도메인 컨벤션(예시)**"으로 명확히 구분합니다.

---

## 목차

1. 개요
2. 디렉토리 & 모듈 구조 표준
3. 네이밍 컨벤션
4. LangGraph 워크플로우(그래프) 작성 표준
5. 상태(State) 관리 표준
6. 노드(Node) 작성 표준
7. 프롬프트 작성 표준 (ChatPromptTemplate)
8. LLM 호출 공통 래퍼 패턴
9. 멀티에이전트 오케스트레이션 (Supervisor) 표준
10. 서브그래프 합성 & Human-in-the-loop 표준
11. 도구(Tool) 정의 표준
12. 벡터 DB 인덱싱 / 검색 공통 함수 구조
13. 그래프 DB 쿼리 작성 규칙
14. 워커(Worker) 실행 골격 표준
15. FastAPI 라우터 구조 & 에러코드 정의표
16. 로깅 표준
17. 예외 처리 표준
18. 응답 포맷 표준 (JSON)
19. 비동기 통신 / 콜백 표준
20. 주석 및 docstring 작성 기준
21. 설정 / 환경변수 관리
22. 개발 체크리스트

---

## 1. 개요

AI Core는 **LangGraph 기반 Multi-Agent 시스템**으로, 백엔드와 **RabbitMQ(Job 큐) + HTTP 콜백**으로 비동기 통신합니다.
AI Core는 **stateless 분석 엔진**이며 데이터 수집·저장·라우팅은 백엔드가 담당합니다.

| 구분 | 기술 |
|------|------|
| 언어 | Python ≥ 3.10 |
| 에이전트 프레임워크 | LangGraph + LangChain |
| API | FastAPI + Uvicorn (Health / Job 접수) |
| 비동기 통신 | RabbitMQ (Job 소비) → HTTP Callback (결과 반환) |
| LLM | provider 추상화 (huggingface / openai / gemini / anthropic) |
| Vector DB | Qdrant (`VectorStore`) |
| Graph DB | Neo4j (`GraphStore`, bolt) |
| RDB | PostgreSQL (Job / Error / Callback 로그, asyncpg) |
| 패키지 매니저 | uv |

### 1.1 모든 에이전트가 공유하는 7대 공통 규약

도메인이 달라도 **아래 7가지는 모든 에이전트가 동일하게** 따릅니다. (이하 각 장에서 상세)

1. 그래프는 `StateGraph` → `compile()` 로 만든다. (§4)
2. State는 `TypedDict` 로 정의하고, 노드는 **변경된 키만** 반환한다. (§5, §6)
3. 노드는 `async def node(state, config: RunnableConfig)` 시그니처를 가진다. (§6)
4. 프롬프트는 **`ChatPromptTemplate`** 로 작성하고 `prompts.py`로 분리한다. (§7)
5. LLM은 `get_llm_for_agent()` → `await llm.ainvoke(messages)` 로만 호출한다. (§8)
6. LLM의 JSON 응답은 `extract_json_from_llm_response()` 로 파싱한다. (§8)
7. 모든 I/O(LLM·DB·콜백)는 `async`/`await`, 장기 작업은 `check_if_canceled()`로 취소를 확인한다. (§6, §17)

---

## 2. 디렉토리 & 모듈 구조 표준

### 2.1 레이어 구조

| 레이어 | 위치 | 책임 |
|--------|------|------|
| API | `app/api/` | FastAPI 라우터, JWT 검증, Job 접수 |
| 워크플로우 | `app/workflows/` | 도메인 비즈니스 그래프 (meeting, risk_analysis ...) |
| 재사용 에이전트 | `app/agents/common/` | writer/researcher/operator 등 재사용 부품 |
| 서비스 | `app/services/` | MQ 소비자, Worker, Job 관리, RAG |
| 코어 | `app/core/` | 설정, LLM 어댑터, 에러, 로거, enum, DB |
| 도구 | `app/tools/` | 에이전트가 호출하는 외부 도구(Tool Layer) |
| 공통 | `app/common.py` | 자주 쓰는 심볼 재노출(logger, settings, enum 등) |

### 2.2 에이전트 폴더 표준 (전 에이전트 공통)

하나의 에이전트는 **아래 파일 구성**을 따릅니다. (writer / researcher / operator / risk 하위 에이전트 모두 동일)

```
<agent>/
├─ nodes/ (또는 node/)   # 노드 함수 (노드가 여러 개면 폴더 분리)
├─ graph.py              # create_<agent>_workflow() — 그래프 정의 + compile
├─ state.py              # <Agent>State (TypedDict)
└─ prompts.py            # ChatPromptTemplate 모음 (코드와 분리)
```

도메인 내 **공통 노드/State**는 `common/`으로 분리해 각 에이전트가 import 합니다 (예: `risk_analysis/common/`).

> **규칙**: 노드 함수는 공유 가능(`common/`), **그래프 정의·State·프롬프트는 에이전트별로 분리**합니다.

---

## 3. 네이밍 컨벤션

### 3.1 일반 규칙 (공통 표준 상속)

| 대상 | 규칙 | 예시 |
|------|------|------|
| 모듈 / 파일 / 폴더 | `snake_case` | `condition_check.py`, `risk_classify/` |
| 클래스 | `PascalCase` | `WriterState`, `JobContext` |
| 함수 / 변수 | `snake_case` | `get_llm_for_agent`, `raw_payload` |
| 상수 / 환경변수 | `UPPER_SNAKE` | `MAX_ITERATION`, `CALLBACK_URL` |
| Enum 클래스 | `PascalCase` + 값 `UPPER_SNAKE` | `JobStatus.SUCCEEDED` |

### 3.2 에이전트 전용 네이밍 규칙 (전 에이전트 공통)

| 대상 | 규칙 | 예시 |
|------|------|------|
| 그래프 팩토리 함수 | `create_<agent>_workflow` | `create_writer_workflow`, `create_risk_classify_workflow` |
| 노드 함수 (실행형) | `run_<역할>` 또는 `<역할>_node` | `run_planner`, `supervisor_node` |
| 노드 함수 (공통/상태) | `<역할>` | `condition_check`, `result_push` |
| 라우팅 함수 | `route_<기준>` / `check_<기준>` | `route_next`, `route_after_eval` |
| State 클래스 | `<Agent>State` | `WriterState`, `MeetingState`, `RetrievalState` |
| 프롬프트 상수 | `<용도>_PROMPT` | `PLANNER_PROMPT`, `SUPERVISOR_SYSTEM_PROMPT` |
| 에이전트 LLM 설정 | `settings.<AGENT>_AGENT` | `settings.SUPERVISOR_AGENT` |

> `get_llm_for_agent("supervisor")` → `settings.SUPERVISOR_AGENT` 를 찾습니다.
> **agent_name(소문자) ↔ 설정 프로퍼티(`<대문자>_AGENT`)** 가 1:1로 맞아야 합니다.

---

## 4. LangGraph 워크플로우(그래프) 작성 표준

### 4.1 그래프 정의 — 팩토리 함수 (표준)

그래프는 **팩토리 함수**로 정의하고 `compile()` 결과를 반환합니다.

```python
from langgraph.graph import StateGraph, END

def create_writer_workflow():
    """글쓰기 워크플로우"""
    workflow = StateGraph(WriterState)

    workflow.add_node("planner", run_planner)
    workflow.add_node("drafting", run_drafting)
    workflow.add_node("evaluation", run_evaluation)
    workflow.add_node("replanner", run_replanner)

    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "drafting")
    workflow.add_edge("drafting", "evaluation")
    workflow.add_conditional_edges("evaluation", route_after_eval, {
        "output": END,
        "replan": "replanner",
    })
    workflow.add_edge("replanner", "planner")
    return workflow.compile()
```

> **호환 메모**: 일부 레거시 그래프(`meeting/graph.py`)는 모듈 레벨에서 `app = workflow.compile()`로 정의되어 있습니다.
> **신규 그래프는 반드시 팩토리 함수(`create_*_workflow`)** 로 작성합니다 (테스트·재사용·서브그래프 합성에 유리).

### 4.2 보편 규칙 (모든 그래프)

1. State 스키마와 함께 생성: `StateGraph(<Agent>State)`.
2. 노드 등록 이름(문자열)은 함수/역할명과 **일치**시킨다 (추적성).
3. 진입점은 `set_entry_point(...)`로 **명시**한다.
4. 분기는 `add_conditional_edges`에 **이름 있는 라우팅 함수**(`route_*`)를 사용하고, **State 키 기반**으로 판단한다. 인라인 람다는 1줄 분기에만 허용.
5. 모든 경로는 결국 `END`로 수렴해야 한다(고아 노드/무한 분기 금지).
6. 사이클(평가→재작업 루프)에는 **반드시 종료 가드**를 둔다 → §4.4.

### 4.3 라우팅 함수 패턴

```python
def route_after_eval(state) -> str:
    verdict = (state.get("evaluation_result") or {}).get("verdict", "not_enough")
    iteration = state.get("iteration", 0)
    if verdict == "good":
        return "output"          # → END
    if iteration >= MAX_ITERATION:
        return "output"          # 가드: 한도 초과 시 강제 종료
    return "replan"
```

- 반환값은 `add_conditional_edges`의 매핑 키와 **정확히 일치**해야 한다.
- 키 누락 시 기본값을 두어 `KeyError`를 방지한다 (`.get(..., default)`).

### 4.4 반복(Self-correction) 루프 가드 — 공통 규약

평가→재계획/재검색 루프를 두는 에이전트는
**반드시 최대 반복 횟수 가드**를 둔다. 기본값 **`MAX_ITERATION = 3`**.

- 카운터(`iteration`/`retry_count`)는 State에 두고 루프 노드에서 1 증가시킨다.
- 한도 초과는 에러가 아니라 **현재까지의 결과로 graceful 종료**한다.

### 4.5 도메인 컨벤션 (예시 — 보편 규칙 아님)

도메인별로 **권장 시작/종료 노드 컨벤션**이 다를 수 있습니다. 아래는 규칙이 아니라 패턴 예시입니다.

- **risk_analysis**: `condition_check`(선행조건 검증)로 시작 → ... → `result_push`(표준 결과 포맷)로 종료. 조건 실패도 `result_push`로 수렴.
- **researcher**: `search → filter → organize → evaluate`(→ 루프).
- **writer**: `planner → drafting → evaluation`(→ replan 루프).
- **meeting**: `Supervisor` 진입 후 워커 fan-out (§9).

> 새 에이전트는 같은 도메인의 기존 컨벤션을 따르되, 없으면 "검증 → 처리 → 결과 정규화" 3단계를 기본 골격으로 삼는다.

---

## 5. 상태(State) 관리 표준

### 5.1 정의 규칙 (모든 에이전트)

1. State는 **`TypedDict`** 로 정의한다 (Pydantic 모델 아님).
2. **`job_id` 는 모든 State에 포함**한다 (로그·취소·추적).
3. 여러 노드가 **병렬로 같은 키에 쓰면** `Annotated[list, operator.add]`로 누적 정의한다.

```python
from typing import TypedDict, List, Optional, Annotated
import operator
from langchain_core.messages import BaseMessage

class MeetingState(TypedDict):
    job_id: str
    messages: Annotated[List[BaseMessage], operator.add]  # 병렬 누적
    context: str                       # Input
    next: str                          # Control (Supervisor가 결정)
    instruction: Optional[str]
    meeting_minutes_draft: str         # Output (Writer가 채움)
    research_data: str                 # Output (Researcher가 채움)
    is_finished: bool
```

### 5.2 공통 Base State (도메인 컨벤션, 선택)

같은 도메인에서 여러 에이전트가 동일 필드를 공유하면 Base를 만들어 상속한다 (예: `risk_analysis`).

```python
class BaseRiskState(TypedDict):
    job_id: str
    job_type: str
    raw_payload: dict
    condition_passed: bool
    error: Optional[str]
    result: Optional[dict]

class RiskClassifyState(BaseRiskState):
    search_results: Optional[List[dict]]
```

### 5.3 반환 규칙

- 노드는 **변경된 키만** dict로 반환한다. 전체 State 반환 금지.
  ```python
  return {"draft": draft}     # O
  return state                # X
  ```
- 백엔드 원본은 가공 없이 보관한다 (`raw_payload`, `context`).

---

## 6. 노드(Node) 작성 표준

### 6.1 시그니처 (모든 노드 공통)

```python
from langchain_core.runnables import RunnableConfig

async def run_planner(state: dict, config: RunnableConfig) -> dict:
    """STT 원문을 분석해 작성 계획(task_list)을 만든다."""
    await check_if_canceled(state.get("job_id", ""))   # 장기 작업이면 취소 확인
    ...
    return {"task_list": tasks}     # 변경 키만 반환
```

### 6.2 규칙

1. 모든 노드는 **`async`** 이며 `(state, config)` 시그니처를 가진다.
2. 런타임 컨텍스트(ACL·참석자·컬렉션 등)는 `config["configurable"]`에서 읽는다.
3. LLM/DB/도구 호출은 반드시 `await`.
4. 부수효과(콜백 전송 등)는 노드가 아니라 **워커/디스패처**에서 처리한다. 노드는 State만 변형한다.
   - 예외: 진행 알림(`send_step_event`)은 fire-and-forget이라 노드에서 호출 가능.
5. 노드 단위 실패는 **도메인 예외로 변환**해 raise 한다(§17).

---

## 7. 프롬프트 작성 표준 (ChatPromptTemplate)

> **모든 에이전트는 프롬프트를 `langchain_core.prompts.ChatPromptTemplate` 로 작성합니다.**

### 7.1 정의 — `prompts.py`에 분리

프롬프트는 코드에 인라인하지 않고 `prompts.py`에 상수로 모읍니다.

```python
from langchain_core.prompts import ChatPromptTemplate

PLANNER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """당신은 회의록 작성 계획을 세우는 전문가입니다.
규칙:
1. 대화의 전체 흐름을 파악하여 핵심만 요약하세요.
2. ..."""),
    ("human", "{text_input}"),
])
```

### 7.2 사용 — 노드에서

```python
messages = PLANNER_PROMPT.format_messages(text_input=state["context"])
response = await llm.ainvoke(messages)
```

### 7.3 규칙

1. **항상 `from_messages([...])`** 로 정의하고 `("system", ...)` + `("human", ...)` 역할을 분리한다.
2. 변수는 `{var}` 플레이스홀더로 두고 노드에서 `format_messages(**kwargs)`로 주입한다.
3. **JSON 출력을 원할 때**:
   - 시스템 프롬프트에 "오직 JSON 형식으로만 응답하세요"를 명시한다.
   - 템플릿 안의 **리터럴 중괄호는 `{{ }}`로 이스케이프**한다(예시 JSON 스키마).
   - 응답은 노드에서 `extract_json_from_llm_response()`로 파싱한다.
4. 도메인 프롬프트 본문은 한국어로 작성한다. (단, **도구 docstring은 영어** — §11)
5. 프롬프트 상수명은 `<용도>_PROMPT` (§3.2).
6. 긴 컨텍스트는 노드에서 **잘라서**(예: `context[:500]`) 주입해 토큰 초과를 예방한다.

---

## 8. LLM 호출 공통 래퍼 패턴

### 8.1 호출 방법 (모든 노드 공통)

노드는 LLM 구현체를 알 필요 없이 `get_llm_for_agent(agent_name)`만 호출합니다.

```python
from app.core.llm_adapter import get_llm_for_agent
from app.core.utils import extract_json_from_llm_response

llm = get_llm_for_agent("supervisor")          # 설정 기반 어댑터
response = await llm.ainvoke(messages)         # LangChain 인터페이스
parsed = extract_json_from_llm_response(response.content)
```

### 8.2 추상화 구조 (모델 교체 가능)

```
노드 ─get_llm_for_agent("xxx")─► LegacyLLMAdapter(LangChain BaseChatModel)
                                     │ _agenerate / _astream / bind_tools
                                     ▼
                              registry.create_streamer(provider, model)
                                     │ @register("openai"/"gemini"/"huggingface"...)
                                     ▼
                              provider별 Streamer (astream)
```

- **모델/프로바이더 교체 = `config.py`의 `<AGENT>_AGENT` 프로퍼티만 수정.** 노드 코드 불변.
  ```python
  @property
  def SUPERVISOR_AGENT(self) -> Dict[str, Any]:
      return {
          "provider": "huggingface",   # ← "openai"/"gemini"로 교체 가능
          "model_name": "Gemma3-27B",
          "api_key": self.OPENAI_API_KEY,
          "streamer_kwargs": self.DEFAULT_GEN_PARAMS,
      }
  ```
- 새 프로바이더 추가는 `app/core/llms/<provider>/adapter.py`에 `@register("<provider>")` 등록 + `registry._load_adapters()` 목록에 추가.
- 생성 파라미터는 `settings.DEFAULT_GEN_PARAMS`로 통일.

### 8.3 규칙

1. 노드에서 provider SDK/`httpx` **직접 호출 금지** → 반드시 어댑터 경유.
2. LLM JSON 응답은 항상 `extract_json_from_llm_response()`로 파싱(실패 시 `LLMOutputParsingError`).
3. 에이전트마다 `<AGENT>_AGENT` 설정 프로퍼티를 추가한다.
4. 도구 사용 시 `llm.bind_tools(tools)`로 바인딩한다.

---

## 9. 멀티에이전트 오케스트레이션 (Supervisor) 표준

> 에이전트는 항상 독립 실행만 하는 게 아니라, **부모(Supervisor) 그래프가 자식 워커들을 조율**하는 형태로도 구성됩니다.
> 회의록 워크플로우(`app/workflows/meeting/`)가 대표 예시입니다.

### 9.1 구조: Supervisor ↔ Worker

```
        ┌─────────────┐
   ┌───►│ Supervisor  │  (LLM이 다음 워커 결정: next + instruction)
   │    └─────┬───────┘
   │   route_next (조건부 분기)
   │     ├─ Send("Writer", state) ─────────┐  (병렬 fan-out)
   │     ├─ Send("Researcher", state) ──────┤
   │     ├─ Send("ActionItemExtractor",...) ┤
   │     └─ FINISH ─────────────────► END
   │                                        │
   └──────── 워커는 끝나면 Supervisor로 복귀 ◄┘
```

### 9.2 Supervisor 노드

LLM에게 **현재 State 요약**을 주고 다음 워커(들)와 지시를 JSON으로 받습니다.

```python
async def supervisor_node(state: MeetingState, config: RunnableConfig):
    await check_if_canceled(state.get("job_id", ""))
    llm = get_llm_for_agent("supervisor")
    state_desc = f"""
    context: {state.get('context','')[:500]}
    meeting_minutes_draft: {state.get('meeting_minutes_draft') or '(없음)'}
    action_items: {state.get('action_items') or '(없음)'}
    """
    messages = SUPERVISOR_SYSTEM_PROMPT.format_messages(state_desc=state_desc)
    parsed = extract_json_from_llm_response((await llm.ainvoke(messages)).content)

    next_action = parsed.get("next", "FINISH")
    if isinstance(next_action, str):       # 항상 리스트로 정규화 (병렬 대비)
        next_action = [next_action]
    return {"next": next_action, "instruction": parsed.get("instruction", "")}
```

### 9.3 병렬 라우팅 (`Send` fan-out)

```python
from langgraph.types import Send

def route_next(state):
    next_nodes = state["next"]
    if "FINISH" in next_nodes:        # 종료는 FINISH로 일원화
        return END
    routing = [Send(name, state) for name in next_nodes
               if name in ["Writer", "Researcher", "ActionItemExtractor"]]
    return routing or END

workflow.add_conditional_edges("Supervisor", route_next,
    ["Writer", "Researcher", "ActionItemExtractor", END])

# 워커는 끝나면 Supervisor로 복귀
workflow.add_edge("Writer", "Supervisor")
workflow.add_edge("Researcher", "Supervisor")
workflow.add_edge("ActionItemExtractor", "Supervisor")
```

### 9.4 규칙

1. **Supervisor의 `next`는 항상 리스트로 정규화**한다(단일 문자열도 `[...]`로). 병렬 실행 일관성.
2. 동시에 돌려도 안전한 워커는 **`Send`로 fan-out**해 병렬 처리한다(속도↑). 병렬 워커가 같은 State 키에 쓰면 §5.1의 `operator.add` 누적을 쓴다.
3. 워커는 작업 후 **반드시 Supervisor로 복귀**(`add_edge(worker, "Supervisor")`)하여 재판단을 받는다.
4. 종료는 Supervisor가 **`FINISH`** 를 반환할 때만 `END`로 간다(종료 신호 일원화). `is_finished` 같은 상태 플래그는 종료를 직접 결정하지 않고, Supervisor가 읽어 `FINISH`를 내리는 **입력 신호로만** 쓴다.
5. **무한 호출 방지**: 이미 완료된 산출물(초안/액션아이템 등)이 있으면 같은 워커를 다시 부르지 않도록 **프롬프트에 종료 규칙을 명시**한다.
6. Supervisor 프롬프트에는 워커 목록·판단 기준·JSON 출력 스키마를 명시한다(`SUPERVISOR_SYSTEM_PROMPT` 참고).

---

## 10. 서브그래프 합성 & Human-in-the-loop 표준

### 10.1 에이전트 = 서브그래프로 합성

부모의 워커 노드는 **자식 워크플로우를 그대로 호출**할 수 있습니다. 부모/자식 State는 **명시적으로 변환**합니다.

```python
async def writer_node(state: MeetingState, config: RunnableConfig):
    await check_if_canceled(state.get("job_id", ""))
    writer = create_writer_workflow()                      # 자식 그래프

    writer_input = {                                       # MeetingState → WriterState 변환
        "text_input": state.get("context", ""),
        "task_list": [], "draft": "", "iteration": 0,
    }
    result = await writer.ainvoke(writer_input, config=config)
    return {"meeting_minutes_draft":                       # WriterState → MeetingState 변환
            result.get("draft") or result.get("final_output", "")}
```

규칙:
1. 자식 그래프는 **팩토리 함수로 생성**해 호출한다(`create_*_workflow()`).
2. **State 변환은 워커 노드 책임**이다. 자식이 요구하는 키를 빠짐없이 초기화해서 넘긴다.
3. `config`(configurable)는 자식에게 **그대로 전달**해 ACL/컨텍스트가 이어지게 한다.

### 10.2 Human-in-the-loop (위험 작업)

실제 행동(결재 상신 등) 위험 작업은 **사람 승인 단계**를 둡니다(`operator`).

```python
return workflow.compile(
    checkpointer=checkpointer,
    interrupt_before=["human_approval"],   # 승인 직전 일시정지
)
```

규칙:
1. 외부 부작용(쓰기/전송/결재 등)이 있는 에이전트는 **`interrupt_before`로 승인 노드 직전 정지**한다.
2. 일시정지·재개 상태 보존을 위해 **`checkpointer`를 함께 설정**한다.
3. 승인 결과(`is_approved`)에 따라 분기하고, 거절 시 안전하게 `END`로 간다.
4. 평가(`evaluator`)에서 안전성 미달 시 재계획 루프를 돌되 §4.4 가드를 적용한다.

---

## 11. 도구(Tool) 정의 표준

### 11.1 정의 패턴

도구는 `app/tools/`에 `@tool` 데코레이터를 단 **async 함수**로 정의합니다.

```python
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

@tool
async def search_vector_db(query: str, config: RunnableConfig) -> str:
    """Search for relevant information in the Vector Database.
    Use this tool when you need to find factual information by semantic similarity.

    Args:
        query (str): The search query string.
    Returns:
        str: A formatted string containing the top search results.
    """
    ...
```

### 11.2 규칙

1. **docstring은 LLM이 읽는 사용 설명서**다. **영어로** "무엇을/언제 + Args/Returns"를 명확히 적는다.
2. ACL 컨텍스트(`owner_user_id`, `dept_id`, `collection_names`)는 인자가 아니라 `config["configurable"]`에서 읽는다.
3. **도구 내부 예외는 raise 하지 않고 에러 문자열을 반환**한다(에이전트 루프 멈춤 방지).
   ```python
   except Exception as e:
       logger.error(f"Vector search failed: {e}", exc_info=True)
       return f"Error executing vector search: {str(e)}"
   ```
4. 반환은 LLM이 바로 읽을 수 있는 **포맷된 문자열**(점수/출처/컬렉션 포함).

---

## 12. 벡터 DB 인덱싱 / 검색 공통 함수 구조

```
노드/도구 ─► app/tools/rag/vector_tools.py(@tool) ─► app/services/rag/VectorStore ─► Qdrant
```

1. 노드/도구는 **`VectorStore`를 통해서만** 접근한다(Qdrant 클라이언트 직접 호출 금지).
2. 검색은 ACL을 항상 전달한다.
   ```python
   results = await vector_store.search(
       query=query,
       collection_names=collection_names or [],   # 빈 리스트 = 전체
       dept_id=dept_id, owner_user_id=user_id,
   )
   ```
3. Top-K/임계값은 하드코딩 금지 → `settings.VECTOR_SEARCH_TOP_K`, `VECTOR_SEARCH_SIMILARITY_THRESHOLD`.
4. 결과 0건은 에러가 아님 → 안내 문자열 반환.
5. Vector+Graph 통합은 `hybrid_search`로 추상화, Fusion은 `settings.RAG_FUSION_K/WEIGHTS/PREFETCH_LIMIT`.
6. 청킹/임베딩/인덱싱 상세는 **[RAG 개발 표준]** 에서 정의(본 문서는 "검색 호출 방식"까지).

---

## 13. 그래프 DB 쿼리 작성 규칙

```
노드/도구 ─► app/tools/rag/graph_tools.py(@tool) ─► app/services/rag/GraphStore ─► Neo4j(bolt)
```

1. Neo4j 접근은 **`GraphStore`를 통해서만** 한다. Cypher는 `GraphStore` 내부로 캡슐화한다.
2. 연결은 `settings.neo4j_uri`(`bolt://host:port`), 자격증명은 `.env`.
3. 전문 검색 인덱스는 부팅 시 `ensure_fulltext_indexes()`로 보장한다.
4. 검색은 ACL(`dept_id`/`owner_user_id`/`collection_names`)을 강제한다.
5. `collection_names`가 비면 검색하지 말고 안내 문자열을 반환한다.
6. 결과 한도는 `settings.GRAPH_SEARCH_LIMIT`, 반환은 `엔티티 + 관계` 형태로 정리한다.

---

## 14. 워커(Worker) 실행 골격 표준

에이전트 그래프를 **실제로 구동**하는 진입점(워커)은 아래 골격을 따릅니다. 두 가지 진입 경로가 있습니다.

| 진입 경로 | 흐름 |
|---|---|
| HTTP 접수 | `app/api/*` → `BackgroundTasks` → `run_<x>_workflow(...)` → `<graph>.ainvoke(...)` |
| MQ 소비 | `mq_consumer`(`job_type` 분기) → 워커 `run_<x>_workflow(...)` → `<graph>.ainvoke(...)` |

> 두 경로 모두 결국 **워커가 그래프를 `ainvoke`** 한다. `dispatcher`(risk 전용)에 대해서는 §19를 참고.

### 14.1 표준 골격 (HTTP 워커 예시)

```python
@handle_ai_error(retry_count=1, retry_on=(LLMRateLimitError, LLMProviderError))
async def run_meeting_workflow(job_id, context, owner_user_id, ..., request_id=None, ...):
    ctx = JobContext(job_id=job_id, request_id=request_id, ...)   # 추적 메타 묶음
    timer = JobTimer()
    try:
        await send_step_event(job_id, status=JobStatus.RUNNING,
                              internal_step_status=AIStepStatus.REQUEST_RECEIVED, ...)

        config = RunnableConfig(configurable={                    # 런타임 컨텍스트
            "owner_user_id": owner_user_id,
            "collection_names": collection_names,
        })
        result = await meeting_agent_app.ainvoke({"job_id": job_id, "context": context}, config=config)

        await send_final_callback(**ctx.callback_kwargs(),
            status=JobStatus.SUCCEEDED,
            internal_step_status=AIStepStatus.RESPONSE_RETURNED,
            result_payload={...}, timing=timer.elapsed())
    except JobCancelledError:
        raise                                                     # 취소는 정상 중단
    except AICoreError as e:
        await send_error_callback(**ctx.callback_kwargs(),
            error_code=e.error_code, error_message=e.message,
            retryable=getattr(e, "retryable", False), timing=timer.elapsed())
        raise
    except Exception as e:
        await send_error_callback(**ctx.callback_kwargs(),
            error_code="AIJOB-003", error_message=str(e), timing=timer.elapsed())
        raise
```

### 14.2 규칙

1. 추적 메타는 `JobContext`로 묶고 `ctx.callback_kwargs()`로 콜백 인자를 만든다.
2. 시간 측정은 `JobTimer` → `timer.elapsed()`.
3. 런타임 컨텍스트(ACL·참석자·컬렉션)는 **`RunnableConfig.configurable`** 로 그래프에 주입한다.
4. 재시도 가능한 외부 호출은 `@handle_ai_error(retry_on=(...))`로 감싼다.
5. 예외는 `JobCancelledError`(재-raise) / `AICoreError`(코드·메시지 전파) / 그 외(`AIJOB-003`)로 **3분기 처리**한다.
6. MQ 라우팅은 **`mq_consumer`가 `job_type → 워커`** 로 분기한다. 단, 하나의 `job_type` 묶음이 여러 그래프로 다시 갈리는 경우(risk_analysis)만 예외적으로 `dispatcher`(`job_type → 그래프 팩토리`)를 한 단계 더 둔다.

---

## 15. FastAPI 라우터 구조 & 에러코드 정의표

### 15.1 라우터 구조

```
app/api/
├─ jobs.py         # Job 취소, 공통 응답 스키마(JobResponse)
├─ agents.py       # 에이전트 실행 접수 (예: /meeting-agent)
├─ indexing.py     # RAG 인덱싱 Job
└─ dependencies.py # verify_jwt_and_headers (S2S 인증)
```

- 공통 prefix **`/v1/agent`**, 하위 라우터는 `prefix="/execute"` 등으로 구성.
- 모든 실행 라우터에 **JWT 의존성**: `dependencies=[Depends(verify_jwt_and_headers)]`.
- 헬스체크는 `/health/live`(Liveness), `/health/ready`(Readiness; Vector+Graph 점검 후 미연결 시 503).
- 비동기 접수: `BackgroundTasks.add_task(...)` 후 **즉시 `JobResponse(status=RUNNING)`** 반환.

### 15.2 에러코드 정의표

전역 핸들러가 `AICoreError`를 잡아 `{error_code, message, details}` + `status_code`로 응답합니다(`app/core/errors/exceptions.py`).

| error_code | 예외 클래스 | HTTP | 의미 |
|---|---|---|---|
| `AIJOB-001` | `ValidationError` | 400 | 입력값/파라미터 검증 실패 |
| `AIJOB-003` | `AICoreError`(기본) | 500 | 일반 실행 실패(기본값) |
| `AIJOB-006` | `JobCancelledError` | 409 | 사용자 취소 |
| `AIJOB-007` | `JobNotFoundError` | 404 | Job ID 없음 |
| `AGENT-001` | `WorkflowError` / `StateValidationError` | 500 | 워크플로우/상태 검증 실패 |
| `AGENT-002` | `ToolExecutionError` | 500 | 도구 실행 실패 |
| `LLM-001` | `LLMError` | 500 | LLM 일반 오류 |
| `LLM-002` | `LLMTokenLimitError` | 500 | 컨텍스트 토큰 초과 |
| `LLM-003` | `LLMRateLimitError` | 500 | 호출 한도(Rate limit) 초과 |
| `LLM-004` | `LLMProviderError` | 500 | 외부 LLM 제공자 장애/타임아웃 |
| `LLM-005` | `LLMOutputParsingError` | 500 | LLM 응답 JSON 파싱 실패 |
| `RAG-001` | `RetrievalError` | 500 | 검색 일반 오류 |
| `RAG-002` | `VectorDBConnectionError` | 500 | Vector DB 연결 실패 |
| `RAG-003` | `GraphDBConnectionError` | 500 | Graph DB 연결 실패 |
| `RAG-004` | `DocumentParsingError` | 500 | 문서 파싱/청킹 실패 |
| `RAG-005` | `IndexingError` | 500 | 인덱싱(적재) 실패 |
| `RISK-001` | (result_push 기본 에러) | - | 리스크 워크플로우 실패 결과 |
| `RISK-999` | (dispatcher fallback) | - | 분류되지 않은 리스크 런타임 에러 |

> **코드 체계**: `<도메인>-<번호>`. 새 예외는 도메인 prefix를 맞춰 추가하고 본 표를 갱신한다.

---

## 16. 로깅 표준

```python
from app.common import logger
logger = logger(__name__)
```

1. 모든 로거는 `AI-Core` 자식 로거다. 포맷: `시간(KST) | LEVEL | [request_id] | name:line | message`.
2. **`print` 금지 → `logger`.**
3. 작업 로그엔 **식별자 prefix**: `[Job | {job_id}] ...`, `[Tool] ...`, `[result_push] ...`.
4. 레벨: `DEBUG`(페이로드/중간상태) / `INFO`(단계 진입·완료) / `WARNING`(재시도·fire&forget 실패) / `ERROR`(복구가능 실패, `exc_info=True`) / `CRITICAL`(치명).
5. 라이브러리 소음은 `setup_library_logging()`으로 억제(neo4j/httpx).
6. 레벨/컬러는 `settings.LOG_LEVEL`, `LOGGING_NO_COLOR`로 제어(하드코딩 금지).

---

## 17. 예외 처리 표준

### 17.1 계층 / 처리 방침

`AICoreError`(루트) → 도메인 예외(클래스 변수 `error_code`/`status_code`/`default_message`).

| 위치 | 방침 |
|------|------|
| 노드 | 저수준 예외를 잡아 **도메인 예외로 변환해 raise** |
| 도구(@tool) | raise 금지 → **에러 문자열 반환** |
| 워커/디스패처 | 최종 try/except로 잡아 콜백 전송 후 재-raise (§14.1 3분기) |

```python
try:
    response = await llm.ainvoke(messages)
except Exception as e:
    if "rate limit" in str(e).lower():
        raise LLMRateLimitError(message="API 호출 제한 초과", details={"cause": str(e)})
    raise LLMProviderError(message="LLM 제공자 에러", details={"cause": str(e)})
```

### 17.2 재시도 데코레이터

```python
from app.core.errors.error_handler import handle_ai_error

@handle_ai_error(retry_count=2, retry_delay=1.0, retry_on=(LLMProviderError,))
async def call_llm(...): ...
```

- `retry_on`으로 대상 예외를 좁힌다(무차별 재시도 금지). `raise_error=False`+`fallback_value`로 degradation 가능.

### 17.3 취소(Cancellation)

장기 작업/노드는 분기점에서 `await check_if_canceled(job_id)`를 호출한다. DB 상태가 `CANCELED`면 `JobCancelledError(AIJOB-006)`가 발생하고, 워커는 이를 **정상 중단**으로 처리(재-raise)한다.

---

## 18. 응답 포맷 표준 (JSON)

### 18.1 API 즉시 응답 (`JobResponse`)

접수 API는 결과가 아니라 **접수 확인**을 반환한다.

```json
{ "job_id": "...", "status": "RUNNING", "internal_step_status": "REQUEST_RECEIVED",
  "request_id": "...", "trace_id": "...", "step_id": "...", "job_type": "...", "worker_id": "...",
  "message": "작업이 대기열에 추가되었습니다.",
  "result": null, "metadata": null,
  "timing": { "started_at": null, "finished_at": null, "latency_ms": null }, "error": null }
```

### 18.2 콜백 결과 (표준 JSON 포맷)

워크플로우 최종 결과는 아래 표준 포맷으로 백엔드에 콜백한다. (모든 에이전트 공통)

```json
// 성공
{ "status": "SUCCEEDED", "internal_step_status": "MODEL_COMPLETED", "result": { ... }, "error": null }
// 실패
{ "status": "FAILED", "internal_step_status": "RESPONSE_RETURNED", "result": null,
  "error": { "error_code": "...", "message": "...", "retryable": false, "stage": "..." } }
```

> **이 포맷을 만드는 방식은 도메인마다 다르다 (포맷 자체는 공통).**
> - **(a) 노드에서 정리**: `risk_analysis`는 그래프 종료 직전 `result_push` 노드가 `state["result"]`를 표준 포맷으로 채우고, 디스패처가 이를 콜백한다. → **risk 도메인 컨벤션**
> - **(b) 워커에서 조립**: meeting 등은 그래프 결과를 워커(`meeting_worker.py`)가 `result_payload`로 직접 조립해 `send_final_callback`에 넘긴다.
>
> 어느 방식이든 **위 JSON 포맷과 status/error 규칙(§18.3)은 동일하게** 지킨다.

### 18.3 규칙

1. 상태값은 **문자열 리터럴 금지** → `JobStatus` / `AIStepStatus` Enum 사용.
   - `JobStatus`: `PENDING/QUEUED/RUNNING/WAITING_RETRY/SUCCEEDED/PARTIAL_SUCCEEDED/FAILED/CANCELED/TIMEOUT`
   - `AIStepStatus`: `REQUEST_RECEIVED/.../MODEL_COMPLETED/RESPONSE_RETURNED`
2. `error`는 항상 `{error_code, message, retryable, stage}` 형태.
3. 시간은 UTC ISO 8601, `timing={started_at, finished_at, latency_ms}`(`JobTimer.elapsed()`).
4. 추적 메타(`request_id`, `trace_id`, `step_id`, `job_type`, `worker_id`)는 응답·콜백에 항상 함께 흐른다.

---

## 19. 비동기 통신 / 콜백 표준

진입 경로는 두 가지(MQ 소비 / HTTP 접수)이고, **`mq_consumer`가 `job_type`으로 워커를 분기**한다.
어느 경로든 **워커가 그래프를 `ainvoke`하고 결과를 HTTP 콜백으로 백엔드에 보내는** 공통 골격은 동일하다.

```
[MQ 경로]
RabbitMQ(Job) → mq_consumer (_process_job: job_type 분기)
                   ├─ "MEETING_AGENT"  → run_meeting_workflow ─┐  (워커가 직접 실행)
                   ├─ "INDEXING" 등     → run_indexing_job ──────┤
                   └─ RISK_JOB_TYPES    → dispatch_risk_job ──────┤  
                                                                  │
[HTTP 경로]                                                       ▼
POST /v1/agent/... → BackgroundTasks → run_<x>_workflow ──► <graph>.ainvoke()
                                                                  │
                       send_final_callback / send_error_callback (HTTP) → 백엔드
```

> **다이어그램 읽는 법 (도메인 차이)**
> - `mq_consumer`의 `job_type` 분기와 콜백 골격은 **공통**이다.
> - **`dispatch_risk_job`(dispatcher)는 risk_analysis 전용**이다. 한 `job_type`이 4개 UC 그래프로 다시 갈리기 때문에 디스패처를 둔다.
> - meeting 등 단일 그래프 에이전트는 디스패처 없이 **워커(`run_meeting_workflow`)가 그래프를 직접 호출**한다.
> - meeting은 **MQ(`MEETING_AGENT`)와 HTTP(`/meeting-agent`) 두 경로 모두**로 진입할 수 있다.

1. **결과는 동기 응답이 아니라 HTTP 콜백**으로 보낸다. AI Core는 결과를 영구 저장하지 않는다.
2. 추적 메타는 `JobContext`로 묶고 `ctx.callback_kwargs()`로 인자를 구성한다.
3. 최종 콜백 `send_final_callback`(재시도 + DB 기록), 에러 `send_error_callback`(ErrorLog 적재 후 위임).
4. 중간 진행 알림 `send_step_event`는 **fire-and-forget**(실패해도 Job 진행 무관).
5. 콜백 전송 상태는 `CallbackSendStatus`로 기록(`CALLBACK_PENDING → DELIVERED / DEAD`).
6. 후속 작업(예: 회의록 인덱싱)은 MQ로 **새 Job을 발행**하고 `indexing_job_id`를 콜백에 포함해 추적성을 준다.
7. `CALLBACK_URL` 미설정 시 건너뛰되 **WARNING 로그**를 남긴다.

---

## 20. 주석 및 docstring 작성 기준

1. **모든 노드·도구·그래프 팩토리·라우팅 함수·공개 함수는 docstring 필수.**
2. 노드 docstring: "역할 한 줄"(+ 필요 시 입출력 변환 설명).
3. 도구 docstring: **영어**로 "무엇/언제 + Args/Returns"(LLM이 읽는 설명서).
4. 타입 힌트 의무(`state: dict`, `config: RunnableConfig`, `-> dict`).
5. **코드를 그대로 옮긴 주석 금지**(예: `# logger 가져오기`). 주석은 *왜/제약/미정*을 적는다.
6. 미구현/협의 대기는 `TODO:`+사유 또는 `raise NotImplementedError`+설명으로 명시.

---

## 21. 설정 / 환경변수 관리

1. 모든 설정은 `app/core/config.py`의 `Settings`(pydantic-settings) + `.env`.
2. **매직 넘버/URL 하드코딩 금지** → `settings.*`(top_k, timeout, 임계값, DB 주소, `MAX_ITERATION` 등).
3. 에이전트 LLM 설정은 `@property <AGENT>_AGENT`로 추가(§8.2).
4. 시크릿은 코드/이미지에 넣지 않고 `.env`/환경변수로만 주입.
5. 조합형 설정은 `@property`로 파생(`DATABASE_URL`, `neo4j_uri`, `DEFAULT_GEN_PARAMS`).
6. 신규 환경변수는 `.env.example`을 함께 갱신.

---

## 22. 개발 체크리스트

새 에이전트(또는 워커) 추가 시:

**그래프 / 상태 / 노드**
- [ ] 표준 폴더 구조(`graph.py` / `state.py` / `prompts.py` / `nodes/`)
- [ ] State는 `TypedDict`, `job_id` 포함, 병렬 누적 키는 `operator.add`
- [ ] 그래프는 `create_<agent>_workflow()` 팩토리 + `compile()`, 진입점 명시, 모든 경로 `END` 수렴
- [ ] 반복 루프엔 `MAX_ITERATION`(기본 3) 가드
- [ ] 노드는 `async (state, config)`, 변경 키만 반환, 장기작업은 `check_if_canceled`

**프롬프트 / LLM**
- [ ] 프롬프트는 `ChatPromptTemplate.from_messages`로 `prompts.py`에 분리(JSON 출력 시 `{{ }}` 이스케이프)
- [ ] LLM은 `get_llm_for_agent()`만 사용, `config.py`에 `<AGENT>_AGENT` 추가
- [ ] LLM JSON은 `extract_json_from_llm_response()`로 파싱

**오케스트레이션 (해당 시)**
- [ ] Supervisor `next`는 리스트로 정규화, 병렬은 `Send` fan-out
- [ ] 워커는 Supervisor로 복귀, 종료는 `FINISH`로 일원화(상태 플래그는 종료 결정에 직접 쓰지 않음)
- [ ] 서브그래프 호출 시 부모↔자식 State 변환 + `config` 전달
- [ ] 위험 작업은 `interrupt_before` + `checkpointer`

**도구 / DB**
- [ ] 도구는 `@tool` async + 영어 docstring + 에러 문자열 반환 + ACL은 `configurable`
- [ ] DB는 `VectorStore`/`GraphStore` 경유, ACL 필터, 한도/임계값은 `settings`

**실행 / 통신 / 운영**
- [ ] 워커는 `JobContext`+`JobTimer`+`@handle_ai_error`, 예외 3분기 처리
- [ ] 런타임 컨텍스트는 `RunnableConfig.configurable`로 주입
- [ ] 응답/콜백에 추적 메타 + 표준 status/error 포맷
- [ ] MQ면 `mq_consumer`의 `job_type → 워커` 분기에 등록 (risk처럼 한 묶음이 여러 그래프로 갈리면 `dispatcher` 매핑 추가)
- [ ] 예외 신설 시 §15.2 표 갱신, 로그 prefix, `print` 미사용
- [ ] 신규 설정은 `Settings` + `.env.example` 갱신
```
