from agents.base_agent import BaseAgent, AgentError
from models.data_models import ResearchOutput, ScriptOutput
from prompts.script_prompt import SYSTEM, USER_TEMPLATE, REVISION_SECTION_TEMPLATE

CHARS_PER_SECOND = 3.2  # 한국어 나레이션 평균 속도


class ScriptAgent(BaseAgent):
    def __init__(self):
        super().__init__("스크립트 에이전트", SYSTEM)

    def run(
        self,
        research: ResearchOutput,
        content_type: str,
        revision_requests: list[str] | None = None,
    ) -> ScriptOutput:
        print(f"  [스크립트] 나레이션 작성 중...")

        revision_section = ""
        if revision_requests:
            numbered = "\n".join(f"{i+1}. {r}" for i, r in enumerate(revision_requests))
            revision_section = REVISION_SECTION_TEMPLATE.format(revision_requests=numbered)

        user_msg = USER_TEMPLATE.format(
            recommended_angle=research.recommended_angle,
            emotional_hooks=", ".join(research.emotional_hooks),
            content_type=content_type,
            revision_section=revision_section,
        )
        data = self.call(user_msg, max_tokens=2000)

        full_narration = data.get("full_narration", "")
        char_count = len(full_narration)
        estimated_duration = char_count / CHARS_PER_SECOND

        # 글자수가 너무 짧으면 한 번 더 시도
        if char_count < 130 and not revision_requests:
            print(f"  [스크립트] 글자 수 부족({char_count}자), 재생성 중...")
            data = self.call(
                user_msg + "\n\n(중요: full_narration은 반드시 150자 이상이어야 합니다)",
                max_tokens=2000,
            )
            full_narration = data.get("full_narration", full_narration)
            char_count = len(full_narration)
            estimated_duration = char_count / CHARS_PER_SECOND

        return ScriptOutput(
            title=data.get("title", ""),
            opening_hook=data.get("opening_hook", ""),
            body=data.get("body", ""),
            ending=data.get("ending", ""),
            full_narration=full_narration,
            character_count=char_count,
            estimated_duration_sec=estimated_duration,
            hashtags=data.get("hashtags", ["#시니어", "#감동사연", "#Shorts"]),
            description=data.get("description", ""),
        )
