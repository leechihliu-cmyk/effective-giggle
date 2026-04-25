from agents.base_agent import BaseAgent
from models.data_models import ResearchOutput, ScriptOutput, VisualOutput, Scene
from prompts.visual_prompt import SYSTEM, USER_TEMPLATE


class VisualAgent(BaseAgent):
    def __init__(self):
        super().__init__("비주얼 에이전트", SYSTEM)

    def run(self, script: ScriptOutput, research: ResearchOutput) -> VisualOutput:
        print(f"  [비주얼] 장면 구성 중...")
        duration = min(max(script.estimated_duration_sec, 45), 60)

        user_msg = USER_TEMPLATE.format(
            opening_hook=script.opening_hook,
            body=script.body,
            ending=script.ending,
            duration=int(duration),
        )
        data = self.call(user_msg, max_tokens=1500)

        scenes_raw = data.get("scenes", [])
        scenes = []
        for s in scenes_raw:
            scenes.append(
                Scene(
                    scene_number=s.get("scene_number", len(scenes) + 1),
                    description=s.get("description", ""),
                    pexels_keywords=s.get("pexels_keywords", ["elderly asian", "nature"]),
                    duration_sec=float(s.get("duration_sec", duration / len(scenes_raw))),
                    emotional_tone=s.get("emotional_tone", "따뜻함"),
                )
            )

        return VisualOutput(
            scenes=scenes,
            overall_color_mood=data.get("overall_color_mood", "warm soft tones"),
            transition_style=data.get("transition_style", "crossfade"),
            b_roll_keywords=data.get("b_roll_keywords", ["elderly asian", "korean countryside"]),
        )
