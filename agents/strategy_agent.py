from agents.base_agent import BaseAgent
from models.data_models import PipelineState, StrategyApproval
from prompts.strategy_prompt import SYSTEM, USER_TEMPLATE


class StrategyAgent(BaseAgent):
    def __init__(self):
        super().__init__("전략 에이전트", SYSTEM)

    def review(self, state: PipelineState, round_number: int = 1) -> StrategyApproval:
        print(f"  [전략] 콘텐츠 품질 검토 중 (라운드 {round_number})...")

        scenes = state.visuals.scenes if state.visuals else []
        user_msg = USER_TEMPLATE.format(
            round_number=round_number,
            recommended_angle=state.research.recommended_angle,
            title=state.script.title,
            opening_hook=state.script.opening_hook,
            body=state.script.body,
            ending=state.script.ending,
            char_count=state.script.character_count,
            scene_count=len(scenes),
            transition_style=state.visuals.transition_style if state.visuals else "crossfade",
            color_mood=state.visuals.overall_color_mood if state.visuals else "",
        )
        data = self.call(user_msg, max_tokens=1000)

        approved = bool(data.get("approved", False))
        revision_requests = data.get("revision_requests", [])

        # revision_requests가 있으면 강제 미승인
        if revision_requests and len(revision_requests) > 0:
            approved = False

        return StrategyApproval(
            approved=approved,
            overall_score=int(data.get("overall_score", 0)),
            audience_fit_score=int(data.get("audience_fit_score", 0)),
            emotional_impact_score=int(data.get("emotional_impact_score", 0)),
            revision_requests=revision_requests,
            director_notes=data.get("director_notes", ""),
        )
