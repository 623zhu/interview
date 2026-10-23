from app.schemas.interviews import (
    InterviewProgress,
    InterviewStage,
    TurnAction,
    TurnEvaluation,
)


# 根据本轮评估决定下一步动作
def decide_next_action(
    *,
    stage:InterviewStage,
    stages_count:int,
    progress:InterviewProgress,
    evaluation:TurnEvaluation|None,
    already_hinted:bool,
    probe_path_len:int,
)->tuple[TurnAction,InterviewProgress]:
    if progress.turn_in_stage >= stage.max_turns:
        return _advance_stage(progress,stages_count)
        
    if evaluation is None:
        return _stay(progress, "follow_up", progress.consecutive_misses)

    consecutive=(
        progress.consecutive_misses+1
        if evaluation.said_dont_know or evaluation.off_topic or evaluation.depth=="shallow"
        else 0
    )

    if consecutive>=2:
        if already_hinted:
            return _advance_stage(progress,stages_count)
        return _stay(progress,"hint",consecutive)

    if evaluation.vague_quotes or evaluation.missing:
        return _stay(progress, "follow_up", consecutive)
        
    if evaluation.depth == "deep" and probe_path_len > progress.turn_in_stage:
        return _stay(progress, "deepen", consecutive)

    if not evaluation.missing and evaluation.depth in ("adequate", "deep"):
        return _advance_stage(progress, stages_count)
        
    return _stay(progress, "follow_up", consecutive)

# 判断结束还是进入下一个阶段。
def _advance_stage(
    progress:InterviewProgress,
    stages_count:int,
)->tuple[TurnAction,InterviewProgress]:
    if progress.stage_index>=stages_count-1:
        return "end",progress.model_copy(update={"consecutive_misses": 0})
    return "next_stage",progress.model_copy(
        update={
            "stage_index": progress.stage_index + 1, 
            "turn_in_stage": 1,
            "consecutive_misses": 0,
        }
    )

# 停留本阶段，本阶段轮次加1
def _stay(
    progress:InterviewProgress,
    action:TurnAction,
    consecutive_misses:int,
)->tuple[TurnAction,InterviewProgress]:
    return action,progress.model_copy(
        update={
            "turn_in_stage": progress.turn_in_stage + 1,
            "consecutive_misses": consecutive_misses,
        }
    )