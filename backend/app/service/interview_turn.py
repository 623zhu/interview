from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.graphs.turn_graph import (
    SessionConflictError,
    SessionNotFoundError,
    TurnPipelineError,
    sse_token_queue,
)
from app.models.interview_sessions import InterviewSession
from app.models.interview_turn import InterviewTurn
from app.schemas.interviews import (
    CurrentTurn,
    InterviewReport,
    InterviewTurnSubmitResponse,
)


def format_sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _submit_response(session_id: int, final_state: dict[str, Any]) -> InterviewTurnSubmitResponse:
    ended = final_state.get("action") == "end"
    report = final_state.get("report")
    pending_seq = final_state.get("pending_seq")
    return InterviewTurnSubmitResponse(
        id=session_id,
        status="completed" if ended else "in_progress",
        current_turn=(
            None
            if ended
            else CurrentTurn(
                seq=(pending_seq or 0) + 1,
                action=final_state.get("action") or "follow_up",
                question=final_state.get("question") or "",
            )
        ),
        report=InterviewReport.model_validate(report) if report else None,
    )


def _graph_config(
    *,
    db: AsyncSession,
    llm_client: AsyncOpenAI,
    user_id: int,
    session_id: int,
    token_queue: asyncio.Queue[tuple[str, dict[str, Any]] | None] | None = None,
) -> dict[str, Any]:
    configurable: dict[str, Any] = {
        "db": db,
        "llm_client": llm_client,
        "user_id": user_id,
    }
    if token_queue is not None:
        configurable["token_queue"] = token_queue
    return {
        "configurable": configurable,
        "metadata": {
            "session_id": session_id,
            "graph": "turn_graph",
        },
        "recursion_limit": 10,
    }


async def assert_can_submit_turn(
    *,
    user_id: int,
    session_id: int,
    db: AsyncSession,
) -> None:
    result = await db.execute(
        select(InterviewSession).where(
            InterviewSession.id == session_id,
            InterviewSession.user_id == user_id,
        )
    )
    session_row = result.scalar_one_or_none()
    if session_row is None:
        raise SessionNotFoundError()
    if session_row.status != "in_progress":
        raise SessionConflictError()
    pending_result = await db.execute(
        select(InterviewTurn.id).where(
            InterviewTurn.session_id == session_id,
            InterviewTurn.answer == "",
        )
    )
    if pending_result.scalar_one_or_none() is None:
        raise SessionConflictError()


async def submit_turn_service(
    *,
    user_id: int,
    session_id: int,
    answer: str,
    db: AsyncSession,
    llm_client: AsyncOpenAI,
    turn_graph,
) -> InterviewTurnSubmitResponse:
    final_state = await turn_graph.ainvoke(
        {"session_id": session_id, "answer": answer},
        config=_graph_config(
            db=db,
            llm_client=llm_client,
            user_id=user_id,
            session_id=session_id,
        ),
    )
    return _submit_response(session_id, final_state)


async def submit_turn_sse(
    *,
    user_id: int,
    session_id: int,
    answer: str,
    db: AsyncSession,
    llm_client: AsyncOpenAI,
    turn_graph,
) -> AsyncIterator[str]:
    queue: asyncio.Queue[tuple[str, dict[str, Any]] | None] = asyncio.Queue()

    async def run() -> None:
        token = sse_token_queue.set(queue)
        try:
            final_state = await turn_graph.ainvoke(
                {"session_id": session_id, "answer": answer},
                config=_graph_config(
                    db=db,
                    llm_client=llm_client,
                    user_id=user_id,
                    session_id=session_id,
                    token_queue=queue,
                ),
            )
            payload = _submit_response(session_id, final_state).model_dump(mode="json")
            await queue.put(("done", payload))
        except SessionNotFoundError:
            await queue.put(("error", {"detail": "面试场次不存在"}))
        except SessionConflictError:
            await queue.put(("error", {"detail": "当前场次无法作答"}))
        except TurnPipelineError:
            await queue.put(("error", {"detail": "处理本轮回答失败"}))
        except Exception:
            await queue.put(("error", {"detail": "处理本轮回答失败"}))
        finally:
            sse_token_queue.reset(token)
            await queue.put(None)

    task = asyncio.create_task(run())
    try:
        yield format_sse("status", {"phase": "evaluating"})
        while True:
            item = await queue.get()
            if item is None:
                break
            event, data = item
            yield format_sse(event, data)
            if event in ("done", "error"):
                break
    finally:
        await task
