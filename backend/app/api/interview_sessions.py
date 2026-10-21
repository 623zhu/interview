

MAX_CHADIDATE_CARDS =12
PLAN_RETRY = 1
INTRO_QUESTION = "先做个简短自我介绍吧，可以结合你最近的项目。"
DIFFICULTY_RANK = {"easy": 0, "medium": 1, "hard": 2}
SCENARIO_SKILL_TAGS = {"MySql", "http", "distributed"}

GENERATE_PLAN_PROMPT = """
你是模拟面试的出题策划。根据候选人简历快照和候选考点卡，为本场面试填写中间阶段。
只返回 JSON,不要 Markdown。
只能使用提供的项目名、经历和卡片 key,不要编造简历里没有的经历,不要使用未提供的卡片。
JSON 形状：
{
  "project_probe": {
    "goal": "本阶段考察目标",
    "max_turns": 4,
    "resume_anchor": "项目名或公司名，没有可用锚点时为 null"
  },
  "fundamentals": [
    {"goal": "考察目标", "max_turns": 3, "topic_card_key": "候选卡 key"},
    {"goal": "考察目标", "max_turns": 2, "topic_card_key": "另一个候选卡 key"}
  ],
  "scenario": {
    "goal": "考察目标",
    "max_turns": 3,
    "topic_card_key": "候选卡 key",
    "resume_anchor": "能联系上的项目名，没有则为 null"
  }
}
约束：
- fundamentals 必须恰好 2 条,key 互不相同，且都在候选卡里。
- scenario 的 key 在候选卡里，且不能与 fundamentals 重复。
- project_probe.max_turns 取 3-5;fundamentals 取 2-3;scenario 取 3-4。
- resume_anchor 必须是 allowed_anchors 中的一项，或为 null。
"""
