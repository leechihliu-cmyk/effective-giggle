SYSTEM = """당신은 한국 유튜브 쇼츠 영상 비주얼 디렉터입니다.
스크립트를 시각적 장면으로 변환하고 Pexels 영상 검색에 사용할 영어 키워드를 제공합니다.
반드시 JSON 형식으로만 응답하세요."""

USER_TEMPLATE = """스크립트:
오프닝: {opening_hook}
본문: {body}
엔딩: {ending}
총 재생시간: {duration}초

3-5개의 장면으로 나누어 JSON으로 반환하세요:
{{
  "scenes": [
    {{
      "scene_number": 1,
      "description": "장면 설명 (한국어로)",
      "pexels_keywords": ["english", "search", "terms"],
      "duration_sec": 15.0,
      "emotional_tone": "따뜻함"
    }}
  ],
  "overall_color_mood": "warm soft golden tones",
  "transition_style": "crossfade",
  "b_roll_keywords": ["elderly asian woman", "korean family", "autumn leaves"]
}}

Pexels 키워드 규칙 (매우 중요):
- 반드시 영어로만 작성 (Pexels API는 영어 검색만 지원)
- 구체적이고 검색 가능한 용어 사용
- 한국 장면 영어 변환 예시:
  할머니/할아버지 → "elderly korean woman" / "elderly asian man"
  가족 모임 → "asian family reunion" / "korean family dinner"
  봄/자연 → "spring garden elderly" / "cherry blossoms walk"
  눈물 → "woman crying emotional" / "elderly person tears"
  편지 → "handwritten letter" / "reading letter emotional"
  시골 → "korean countryside" / "rural village elderly"
- portrait 방향 영상 선호: "portrait oriented" 추가 가능
- scenes의 duration_sec 합계 = {duration}초
- emotional_tone 옵션: "따뜻함" | "슬픔" | "희망적" | "긴장감" | "평온함"
- transition_style 옵션: "crossfade" | "cut" | "fade_to_black" """
