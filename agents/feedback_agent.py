"""
성과 데이터를 분석해 다음 콘텐츠 생성에 반영할 StyleProfile을 만드는 에이전트.
"""
import json
from datetime import datetime

from agents.base_agent import BaseAgent
from analytics.performance_db import build_performance_summary
from models.data_models import StyleProfile
from prompts.feedback_prompt import SYSTEM, USER_TEMPLATE


class FeedbackAgent(BaseAgent):
    def __init__(self):
        super().__init__("피드백 에이전트", SYSTEM)

    def analyze(self, top_comments_all: list[str] | None = None) -> StyleProfile:
        """
        성과 DB를 읽어 StyleProfile 반환.
        top_comments_all: 수집된 모든 영상의 최근 댓글 (선택)
        """
        summary = build_performance_summary()

        if summary.get("status") == "데이터 없음" or summary.get("job_count", 0) == 0:
            print("  [피드백] 분석 데이터 없음 — 기본 StyleProfile 사용")
            return StyleProfile(
                generated_at=datetime.utcnow().isoformat(),
                strategy_notes="성과 데이터가 아직 없습니다. 기본 전략으로 생성합니다.",
            )

        def _fmt_dict(d: dict) -> str:
            lines = []
            for k, v in d.items():
                if isinstance(v, dict):
                    parts = ", ".join(f"{kk}: {vv}" for kk, vv in v.items())
                    lines.append(f"  {k}: {parts}")
                else:
                    lines.append(f"  {k}: {v}")
            return "\n".join(lines) if lines else "  없음"

        comments_sample = (top_comments_all or [])[:30]
        comments_str = "\n".join(f"  - {c}" for c in comments_sample) or "  (댓글 없음)"

        user_msg = USER_TEMPLATE.format(
            content_type_stats=_fmt_dict(summary.get("by_content_type", {})),
            emotional_tone_stats=_fmt_dict(summary.get("by_emotional_tone", {})),
            top_hooks="\n".join(f"  {i+1}. {h}" for i, h in enumerate(summary.get("top_hooks", []))),
            low_patterns="\n".join(f"  - {p}" for p in summary.get("low_performing_patterns", [])) or "  없음",
            top_comments=comments_str,
        )

        print("  [피드백] Claude로 성과 데이터 분석 중...")
        data = self.call(user_msg, max_tokens=1500)

        return StyleProfile(
            generated_at=datetime.utcnow().isoformat(),
            best_content_types=data.get("best_content_types", []),
            best_emotional_tones=data.get("best_emotional_tones", []),
            recommended_hooks=data.get("recommended_hooks", []),
            recommended_topics=data.get("recommended_topics", []),
            avoid_patterns=data.get("avoid_patterns", []),
            strategy_notes=data.get("strategy_notes", ""),
            # 댓글 감정 분석 결과를 tracker로 전달하려면 별도 처리 필요
        )
