SYSTEM = """당신은 한국 유튜브 쇼츠 채널의 데이터 분석 전문가이자 콘텐츠 전략가입니다.
실제 YouTube 성과 데이터(조회수, 좋아요, 댓글, 시청 유지율)를 분석하여
5060 한국 중장년층 시청자들이 가장 반응하는 콘텐츠 패턴을 파악합니다.
반드시 JSON 형식으로만 응답하세요."""

USER_TEMPLATE = """=== YouTube Shorts 성과 데이터 분석 요청 ===

[콘텐츠 유형별 평균 성과]
{content_type_stats}

[감정 톤별 참여율]
{emotional_tone_stats}

[성과 좋은 오프닝 훅 (상위 5개)]
{top_hooks}

[성과 낮은 패턴]
{low_patterns}

[최근 상위 댓글 모음]
{top_comments}

위 데이터를 분석하여 다음 콘텐츠 생성에 활용할 전략을 JSON으로 반환하세요:
{{
  "best_content_types": ["가장 성과 좋은 유형1", "유형2"],
  "best_emotional_tones": ["참여율 높은 감정1", "감정2", "감정3"],
  "recommended_hooks": ["다음에 써볼 훅 패턴1", "패턴2", "패턴3"],
  "recommended_topics": ["다음에 만들 추천 주제1", "주제2", "주제3"],
  "avoid_patterns": ["성과 낮아 피해야 할 패턴1", "패턴2"],
  "strategy_notes": "에이전트에게 전달할 핵심 전략 요약 (한국어, 200자 이내)",
  "comment_sentiment_summary": "댓글 전반적 감정 분석",
  "comment_sentiment_keywords": ["반응 키워드1", "키워드2", "키워드3"]
}}

분석 기준:
- 5060 시청자가 '공감'하고 '감동'받는 패턴은 무엇인가
- 어떤 오프닝이 3초 안에 시청자를 잡는가
- 댓글에서 어떤 감정/단어가 자주 등장하는가
- 어떤 주제/유형이 '반복 시청'을 유도하는가"""
