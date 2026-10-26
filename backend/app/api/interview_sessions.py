from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentUser
from app.graphs.turn_graph import (
    SessionConflictError as TurnSessionConflictError,
    SessionNotFoundError as TurnSessionNotFoundError,
    TurnPipelineError,
)
from app.schemas.interviews import (
    InterviewSessionCreateRequest,
    InterviewSessionCreateResponse,
    InterviewSessionGetResponse,
    InterviewSessionListItem,
    InterviewSessionPatchRequest,
    InterviewTurnSubmitRequest,
    SessionStatus,
)
from app.service.interview_session import (
    PlanGenerationError,
    ResumeNotFoundError,
    ResumeNotReadyError,
    SessionConflictError,
    SessionNotFoundError,
    abandon_interview_session_service,
    create_interview_session_service,
    get_interview_session_service,
    list_interview_sessions_service,
)
from app.service.interview_turn import (
    assert_can_submit_turn,
    submit_turn_service,
    submit_turn_sse,
)

router = APIRouter(prefix="/api/v1/interview-sessions", tags=["interview-sessions"])


@router.post("", status_code=status.HTTP_201_CREATED, summary="创建面试场次")
async def create_interview_session(
    body: InterviewSessionCreateRequest,
    current_user: CurrentUser,
    request: Request,
) -> InterviewSessionCreateResponse:
    async with request.app.state.mysql_session_factory() as db:
        try:
            return await create_interview_session_service(
                user_id=current_user.id,
                resume_id=body.resume_id,
                target_role=body.target_role,
                difficulty=body.difficulty,
                db=db,
                llm_client=request.app.state.llm_client,
            )
        except ResumeNotFoundError:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="简历不存在")
        except ResumeNotReadyError:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="简历未就绪")
        except PlanGenerationError:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="生成面试计划失败",
            )


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="面试场次列表",
    description="返回当前用户的场次摘要，不含计划和各轮问答。可按状态和创建时间过滤。",
)
async def list_interview_sessions(
    current_user: CurrentUser,
    request: Request,
    status_filter: SessionStatus | None = Query(default=None, alias="status"),
    created_after: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[InterviewSessionListItem]:
    async with request.app.state.mysql_session_factory() as db:
        return await list_interview_sessions_service(
            user_id=current_user.id,
            db=db,
            status=status_filter,
            created_after=created_after,
            limit=limit,
        )


@router.post(
    "/{session_id}/turns",
    status_code=status.HTTP_200_OK,
    summary="提交本轮回答",
    description="默认返回 JSON。请求头 Accept 包含 text/event-stream 时，评估完成后以 SSE 流式返回下一问。",
)
async def submit_interview_turn(
    session_id: int,
    body: InterviewTurnSubmitRequest,
    current_user: CurrentUser,
    request: Request,
) -> Any:
    wants_sse = "text/event-stream" in request.headers.get("accept", "")
    if wants_sse:
        async with request.app.state.mysql_session_factory() as db:
            try:
                await assert_can_submit_turn(
                    user_id=current_user.id,
                    session_id=session_id,
                    db=db,
                )
            except (TurnSessionNotFoundError, SessionNotFoundError):
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="面试场次不存在")
            except TurnSessionConflictError:
                raise HTTPException(status.HTTP_409_CONFLICT, detail="当前场次无法作答")

        async def events():
            async with request.app.state.mysql_session_factory() as db:
                async for chunk in submit_turn_sse(
                    user_id=current_user.id,
                    session_id=session_id,
                    answer=body.answer,
                    db=db,
                    llm_client=request.app.state.llm_client,
                    turn_graph=request.app.state.turn_graph,
                ):
                    yield chunk

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    async with request.app.state.mysql_session_factory() as db:
        try:
            return await submit_turn_service(
                user_id=current_user.id,
                session_id=session_id,
                answer=body.answer,
                db=db,
                llm_client=request.app.state.llm_client,
                turn_graph=request.app.state.turn_graph,
            )
        except (TurnSessionNotFoundError, SessionNotFoundError):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="面试场次不存在")
        except TurnSessionConflictError:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="当前场次无法作答")
        except TurnPipelineError:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="处理本轮回答失败",
            )

@router.get(
    "/{session_id}",
    status_code=status.HTTP_200_OK,
    summary="获取面试场次",
    description="返回当前用户的场次与问答。不含计划。结束后才返回各轮点评、分数和报告。",
)
async def get_interview_session(
    session_id: int,
    current_user: CurrentUser,
    request: Request,
) -> InterviewSessionGetResponse:
    async with request.app.state.mysql_session_factory() as db:
        try:
            return await get_interview_session_service(
                user_id=current_user.id, 
                session_id=session_id, 
                db=db
            )
        except SessionNotFoundError:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="面试场次不存在")


@router.patch(
    "/{session_id}",
    status_code=status.HTTP_200_OK,
    summary="放弃面试场次",
    description="将进行中的场次标为 abandoned，中途结束。不生成报告。",
)
async def abandon_interview_session(
    session_id: int,
    body: InterviewSessionPatchRequest,
    current_user: CurrentUser,
    request: Request,
) -> InterviewSessionListItem:
    async with request.app.state.mysql_session_factory() as db:
        try:
            return await abandon_interview_session_service(
                user_id=current_user.id,
                session_id=session_id,
                db=db,
            )
        except SessionNotFoundError:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="面试场次不存在")
        except SessionConflictError:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="当前场次无法放弃")
