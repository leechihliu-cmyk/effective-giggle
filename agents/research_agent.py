from agents.base_agent import BaseAgent, AgentError
from models.data_models import ResearchOutput
from prompts.research_prompt import SYSTEM, USER_TEMPLATE


class ResearchAgent(BaseAgent):
    def __init__(self):
        super().__init__("리서치 에이전트", SYSTEM)

    def run(self, topic: str, content_type: str) -> ResearchOutput:
        print(f"  [리서치] 주제 분석 중: '{topic}' ({content_type})")
        user_msg = USER_TEMPLATE.format(topic=topic, content_type=content_type)
        data = self.call(user_msg, max_tokens=1500)

        return ResearchOutput(
            topic=topic,
            content_type=content_type,
            trending_angles=data.get("trending_angles", []),
            emotional_hooks=data.get("emotional_hooks", []),
            competitor_analysis=data.get("competitor_analysis", ""),
            recommended_angle=data.get("recommended_angle", ""),
        )
