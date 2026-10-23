from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.interviews import InterviewTurnSubmitResponse,InterviewReport,CurrentTurn

async def submit_turn_service(
    *,
    user_id:int,
    session_id:int,
    answer:str,
    db:AsyncSession,
    llm_client:AsyncOpenAI,
    turn_graph,
)->InterviewTurnSubmitResponse:
    final_state = await turn_graph.ainvoke(
        {"session_id":session_id,"answer":answer},
        config={
            "configurable":{
                "db":db,
                "llm_client":llm_client,
                "user_id":user_id,
            },
            "metadata":{
                "session_id":session_id,
                "graph":"turn_graph",
            },
            "recursion_limit":10,
        },
    )
    ended = final_state.get("action") == "end"
    report = final_state.get("report")
    return InterviewTurnSubmitResponse(
        id=session_id,
        status="completed" if ended else "in_progress",
        current_turn=(
            None
            if ended
            else CurrentTurn(
                seq=final_state.get("pending_seq")+1,
                action=final_state.get("action"),
                question=final_state.get("question"),
            )
        ),
        report = InterviewReport.model_validate(report) if report else None,
    )

