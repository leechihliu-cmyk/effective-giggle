from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class ResearchOutput:
    topic: str
    content_type: str
    trending_angles: list[str]
    emotional_hooks: list[str]
    competitor_analysis: str
    recommended_angle: str


@dataclass
class ScriptOutput:
    title: str
    opening_hook: str
    body: str
    ending: str
    full_narration: str
    character_count: int
    estimated_duration_sec: float
    hashtags: list[str]
    description: str


@dataclass
class Scene:
    scene_number: int
    description: str
    pexels_keywords: list[str]
    duration_sec: float
    emotional_tone: str


@dataclass
class VisualOutput:
    scenes: list[Scene]
    overall_color_mood: str
    transition_style: str
    b_roll_keywords: list[str]


@dataclass
class StrategyApproval:
    approved: bool
    overall_score: int
    audience_fit_score: int
    emotional_impact_score: int
    revision_requests: list[str]
    director_notes: str


@dataclass
class SubtitleChunk:
    text: str
    start_sec: float
    end_sec: float


@dataclass
class VideoAnalytics:
    """YouTube Analytics API로 수집한 영상 성과 데이터"""
    fetched_at: str = ""
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    # YouTube Analytics API (추가 OAuth 스코프 필요)
    avg_watch_duration_sec: float = 0.0
    avg_watch_percentage: float = 0.0
    # 파생 지표
    engagement_rate: float = 0.0       # (likes + comments) / views
    retention_rate: float = 0.0        # avg_watch_duration / video_duration
    # 댓글 감정 분석 결과 (FeedbackAgent가 채움)
    top_comments: list[str] = field(default_factory=list)
    sentiment_summary: str = ""        # "긍정적" | "부정적" | "혼재"
    sentiment_keywords: list[str] = field(default_factory=list)


@dataclass
class StyleProfile:
    """성과 데이터 기반 권장 스타일 (FeedbackAgent 출력)"""
    generated_at: str = ""
    best_content_types: list[str] = field(default_factory=list)    # 조회수 상위 유형
    best_emotional_tones: list[str] = field(default_factory=list)  # 인게이지먼트 높은 감정
    recommended_hooks: list[str] = field(default_factory=list)     # 잘 작동하는 훅 패턴
    recommended_topics: list[str] = field(default_factory=list)    # 다음에 만들 추천 주제
    avoid_patterns: list[str] = field(default_factory=list)        # 성과 낮은 패턴
    strategy_notes: str = ""                                       # 에이전트 전달용 메모


@dataclass
class PipelineState:
    job_id: str
    topic: str
    content_type: str
    research: Optional[ResearchOutput] = None
    script: Optional[ScriptOutput] = None
    visuals: Optional[VisualOutput] = None
    approval: Optional[StrategyApproval] = None
    audio_path: Optional[str] = None
    video_clips: Optional[list[str]] = None
    assembled_video_path: Optional[str] = None
    final_video_path: Optional[str] = None
    youtube_url: Optional[str] = None
    youtube_video_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    analytics: Optional[VideoAnalytics] = None
    style_profile_used: Optional[StyleProfile] = None
