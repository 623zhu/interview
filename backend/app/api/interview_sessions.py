from fastapi import APIRouter, HTTPException, Request, status

from app.api.deps import CurrentUser
from app.graphs.turn_graph import (
    SessionConflictError,
    SessionNotFoundError,
    TurnPipelineError,
)
from app.schemas.interviews import (
    InterviewSessionCreateRequest,
    InterviewSessionCreateResponse,
    InterviewTurnSubmitRequest,
    InterviewTurnSubmitResponse,
    InterviewSessionGetResponse,
)
from app.service.interview_session import (
    PlanGenerationError,
    ResumeNotFoundError,
    ResumeNotReadyError,
    create_interview_session_service,
    get_interview_session_service,
    SessionNotFoundError,
)
from app.service.interview_turn import submit_turn_service

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


@router.post(
    "/{session_id}/turns",
    status_code=status.HTTP_200_OK,
    summary="提交本轮回答",
)
async def submit_interview_turn(
    session_id: int,
    body: InterviewTurnSubmitRequest,
    current_user: CurrentUser,
    request: Request,
) -> InterviewTurnSubmitResponse:
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
        except SessionNotFoundError:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="面试场次不存在")
        except SessionConflictError:
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
     description="返回当前用户的场次与问答，不含计划和各轮评估",
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
        