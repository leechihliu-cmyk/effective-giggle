from dataclasses import dataclass, field
from typing import Optional


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
