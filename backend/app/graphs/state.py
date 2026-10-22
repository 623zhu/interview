from typing import Any,TypedDict

class TurnState(TypedDict):
    session_id:int
    answer:str
    resume_snapshot:dict
    plan:dict
    progress:dict
    current_card:dict|None
    recent_turns:list[dict[str,Any]]
    evaluation:dict|None
    action:str
    question:str|None
    report:dict|None
    pending_seq:int
    pending_question:str
    next_progress:dict
