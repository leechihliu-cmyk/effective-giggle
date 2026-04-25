SYSTEM = """당신은 한국 5060세대 유튜브 채널의 총괄 크리에이티브 디렉터입니다.
콘텐츠의 품질, 일관성, 타겟 적합성을 최종 검토하고 승인합니다.
엄격하지만 건설적인 피드백을 제공합니다.
반드시 JSON 형식으로만 응답하세요."""

PERFORMANCE_CONTEXT_TEMPLATE = """
[채널 성과 데이터 — 이 패턴을 우선 반영하세요]
잘 되는 콘텐츠 유형: {best_content_types}
잘 되는 감정 톤: {best_emotional_tones}
성과 좋은 훅 패턴: {recommended_hooks}
피해야 할 패턴: {avoid_patterns}
전략 메모: {strategy_notes}
"""

USER_TEMPLATE = """검토 대상 콘텐츠 패키지 (라운드 {round_number}):
{performance_context}
[리서치 결과]
추천 각도: {recommended_angle}

[스크립트]
제목: {title}
오프닝 훅: {opening_hook}
본문: {body}
엔딩: {ending}
전체 나레이션 글자 수: {char_count}자

[비주얼 계획]
장면 수: {scene_count}개
전환 방식: {transition_style}
색감/분위기: {color_mood}

다음 기준으로 평가하여 JSON으로 반환하세요:
{{
  "approved": true,
  "overall_score": 8,
  "audience_fit_score": 8,
  "emotional_impact_score": 8,
  "revision_requests": [],
  "director_notes": "총평"
}}

승인 기준 (모두 충족해야 approved=true):
1. overall_score >= 7
2. audience_fit_score >= 7 (5060세대에 맞는 언어와 공감 포인트)
3. emotional_impact_score >= 7 (감정적 임팩트)
4. 오프닝 훅이 3초 안에 감정을 자극하는가
5. 5060세대 어투로 작성되었는가 (은어/외래어 없음)
6. 클릭을 유발하는 제목인가
7. full_narration이 150-200자 범위인가

revision_requests: approved=false일 때만 구체적 수정 지시 사항 작성 (빈 배열이면 approved=true)"""
