#!/usr/bin/env python3
"""YouTube Shorts 자동 생성 CLI — 5060 한국 중장년층 타겟"""
import argparse
import sys
import uuid
from pathlib import Path

import config as cfg
from models.data_models import PipelineState, StyleProfile
from agents.research_agent import ResearchAgent
from agents.script_agent import ScriptAgent
from agents.visual_agent import VisualAgent
from agents.strategy_agent import StrategyAgent


CONTENT_TYPES = ["도파민형", "공감썰형", "감동스토리", "노인의지혜"]


def parse_args():
    parser = argparse.ArgumentParser(
        description="YouTube Shorts 자동 생성 (5060 한국 중장년층 타겟)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""예시:
  # 단일 영상 생성
  python main.py --topic "며느리에게 받은 편지" --type 감동스토리

  # 업로드 없이 영상만 생성
  python main.py --topic "살다 보니 알게 된 것들" --type 노인의지혜 --skip-upload

  # 공개로 바로 업로드
  python main.py --topic "뻔한 상황의 반전" --type 도파민형 --privacy public

  # 스크립트 기획만 확인 (제작 없이)
  python main.py --topic "시어머니의 일기" --type 공감썰형 --dry-run

  # YouTube Analytics 동기화 (조회수/댓글 수집)
  python main.py --sync-analytics

  # 성과 대시보드 보기
  python main.py --show-stats

  # 성과 데이터 기반 자동 생성 (추천 주제/유형 자동 선택)
  python main.py --auto

  # 성과 반영 + 특정 주제로 생성
  python main.py --topic "부모님과의 화해" --type 감동스토리 --use-feedback
""",
    )

    # ── 단일 영상 생성 옵션
    parser.add_argument("--topic", "-t", help="콘텐츠 주제")
    parser.add_argument(
        "--type", "-T",
        dest="content_type",
        choices=CONTENT_TYPES,
        default="감동스토리",
        help="콘텐츠 유형 (기본: 감동스토리)",
    )
    parser.add_argument(
        "--privacy",
        choices=["public", "private", "unlisted"],
        default="private",
        help="YouTube 공개 설정 (기본: private)",
    )
    parser.add_argument("--skip-upload", action="store_true", help="YouTube 업로드 건너뛰기")
    parser.add_argument("--dry-run", action="store_true", help="에이전트만 실행 (제작 없음)")
    parser.add_argument("--output-dir", default=cfg.OUTPUT_DIR, help="출력 디렉토리")
    parser.add_argument("--job-id", default=None, help="재시도할 기존 작업 ID")

    # ── 성과 피드백 옵션
    parser.add_argument(
        "--use-feedback",
        action="store_true",
        help="성과 데이터를 분석해 스타일 프로필을 에이전트에 반영",
    )

    # ── Analytics 모드
    parser.add_argument(
        "--sync-analytics",
        action="store_true",
        help="업로드된 모든 영상의 조회수/댓글을 YouTube에서 동기화",
    )
    parser.add_argument(
        "--channel-id",
        default="",
        help="YouTube 채널 ID (Analytics API 시청 유지율 조회에 필요)",
    )

    # ── 대시보드
    parser.add_argument("--show-stats", action="store_true", help="성과 대시보드 출력")

    # ── 자동화 모드
    parser.add_argument(
        "--auto",
        action="store_true",
        help="성과 데이터 분석 후 추천 주제/유형으로 자동 생성 + 업로드",
    )
    parser.add_argument(
        "--auto-count",
        type=int,
        default=1,
        help="--auto 모드에서 생성할 영상 수 (기본: 1)",
    )

    return parser.parse_args()


# ─────────────────────────────────────────────
# Phase 1: 크리에이티브 에이전트 루프
# ─────────────────────────────────────────────

def run_agent_phase(
    state: PipelineState,
    style_profile: StyleProfile | None = None,
) -> PipelineState:
    print("\n[Phase 1] 크리에이티브 에이전트 실행")
    print("-" * 40)

    research_agent = ResearchAgent()
    script_agent = ScriptAgent()
    visual_agent = VisualAgent()
    strategy_agent = StrategyAgent()

    state.research = research_agent.run(state.topic, state.content_type)
    print(f"  → 추천 각도: {state.research.recommended_angle[:60]}...")

    # StyleProfile을 ResearchAgent 결과에 병합 (추천 훅 등 힌트 제공)
    if style_profile:
        _inject_style_hints(state.research, style_profile)

    revision_requests = None
    for round_num in range(1, cfg.MAX_REVISION_ROUNDS + 2):
        state.script = script_agent.run(
            state.research,
            state.content_type,
            revision_requests=revision_requests,
        )
        print(f"  → 제목: {state.script.title}")
        print(f"  → 글자 수: {state.script.character_count}자 ({state.script.estimated_duration_sec:.0f}초)")

        state.visuals = visual_agent.run(state.script, state.research)
        print(f"  → 장면: {len(state.visuals.scenes)}개 / 전환: {state.visuals.transition_style}")

        state.approval = strategy_agent.review(state, round_number=round_num, style_profile=style_profile)
        print(
            f"  → 검토: 종합 {state.approval.overall_score}/10 | "
            f"5060 적합성 {state.approval.audience_fit_score}/10 | "
            f"감정 {state.approval.emotional_impact_score}/10"
        )
        print(f"  → 총평: {state.approval.director_notes[:80]}...")

        if state.approval.approved:
            print("  ✓ 콘텐츠 승인!")
            break

        if round_num > cfg.MAX_REVISION_ROUNDS:
            print(f"  ✗ {cfg.MAX_REVISION_ROUNDS}라운드 초과 — 현재 버전으로 진행합니다.")
            break

        print(f"  → 수정 요청 ({round_num}라운드):")
        for req in state.approval.revision_requests:
            print(f"    • {req}")
        revision_requests = state.approval.revision_requests

    state.style_profile_used = style_profile
    return state


def _inject_style_hints(research, style_profile: StyleProfile):
    """StyleProfile의 추천 훅/패턴을 research.emotional_hooks에 병합"""
    if style_profile.recommended_hooks:
        extra = [h for h in style_profile.recommended_hooks if h not in research.emotional_hooks]
        research.emotional_hooks = extra[:2] + research.emotional_hooks
    if style_profile.strategy_notes:
        research.competitor_analysis += f"\n\n[성과 기반 전략]: {style_profile.strategy_notes}"


# ─────────────────────────────────────────────
# Phase 2: 프로덕션 파이프라인
# ─────────────────────────────────────────────

def run_production_phase(
    state: PipelineState,
    output_dir: str,
    skip_upload: bool,
    privacy: str,
) -> PipelineState:
    from core.tts import generate_audio
    from core.pexels import fetch_scene_clips
    from core.video import assemble_video
    from core.subtitles import chunk_narration, burn_subtitles

    job_dir = Path(output_dir) / state.job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    clips_dir = job_dir / "clips"
    clips_dir.mkdir(exist_ok=True)

    print("\n[Phase 2] 프로덕션 파이프라인")
    print("-" * 40)

    print("  [1/4] 한국어 음성 생성 중...")
    audio_path = str(job_dir / "narration.mp3")
    audio_path, audio_duration = generate_audio(state.script.full_narration, audio_path)
    state.audio_path = audio_path

    print("  [2/4] 스톡 영상 다운로드 중...")
    state.video_clips = fetch_scene_clips(
        state.visuals.scenes,
        str(clips_dir),
        state.visuals.b_roll_keywords,
    )

    print("  [3/4] 영상 조합 중...")
    assembled_path = str(job_dir / "assembled.mp4")
    assemble_video(
        state.video_clips,
        state.audio_path,
        state.visuals.scenes,
        assembled_path,
        transition_style=state.visuals.transition_style,
    )
    state.assembled_video_path = assembled_path

    print("  [4/4] 한글 자막 삽입 중...")
    subtitle_chunks = chunk_narration(state.script.full_narration, audio_duration)
    final_path = str(job_dir / "final.mp4")
    burn_subtitles(assembled_path, subtitle_chunks, final_path)
    state.final_video_path = final_path

    print(f"\n  영상 생성 완료: {final_path}")

    if not skip_upload:
        from core.youtube import get_authenticated_service, upload_short
        yt = get_authenticated_service(cfg.YOUTUBE_CLIENT_SECRETS_FILE)
        result = upload_short(
            yt,
            final_path,
            state.script.title,
            state.script.description,
            state.script.hashtags,
            privacy_status=privacy,
        )
        state.youtube_video_id = result["video_id"]
        state.youtube_url = result["url"]

    return state


# ─────────────────────────────────────────────
# 단일 영상 생성 (전체 파이프라인)
# ─────────────────────────────────────────────

def generate_one(
    topic: str,
    content_type: str,
    args,
    style_profile: StyleProfile | None = None,
) -> PipelineState:
    job_id = args.job_id or str(uuid.uuid4())[:8]
    print(f"\nYouTube Shorts Generator")
    print(f"주제: {topic}")
    print(f"유형: {content_type}")
    print(f"작업 ID: {job_id}")
    if style_profile:
        print(f"성과 기반 스타일 적용: {style_profile.best_content_types}")

    state = PipelineState(job_id=job_id, topic=topic, content_type=content_type)
    state = run_agent_phase(state, style_profile=style_profile)

    if args.dry_run:
        print("\n[dry-run] 에이전트 완료. 영상 생성 건너뜀.")
        _print_summary(state)
        return state

    state = run_production_phase(state, args.output_dir, args.skip_upload, args.privacy)

    # 작업 메타데이터 저장
    from analytics.tracker import save_job
    metadata_path = save_job(state)
    print(f"  메타데이터 저장: {metadata_path}")

    _print_summary(state)
    return state


# ─────────────────────────────────────────────
# --sync-analytics 모드
# ─────────────────────────────────────────────

def cmd_sync_analytics(args):
    print("\n[Analytics 동기화]")
    print("-" * 40)
    from analytics.youtube_analytics import sync_all_videos
    results = sync_all_videos(channel_id=args.channel_id)
    if not results:
        print("동기화할 영상이 없습니다. (YouTube에 업로드된 영상이 있어야 합니다)")
    else:
        print(f"\n총 {len(results)}개 영상 동기화 완료.")


# ─────────────────────────────────────────────
# --show-stats 모드
# ─────────────────────────────────────────────

def cmd_show_stats():
    from analytics.performance_db import print_dashboard
    print_dashboard()


# ─────────────────────────────────────────────
# --auto 모드: 성과 기반 자동 생성
# ─────────────────────────────────────────────

def cmd_auto(args):
    print("\n[자동화 모드] 성과 데이터 분석 후 자동 생성")
    print("-" * 40)

    from agents.feedback_agent import FeedbackAgent
    from analytics.performance_db import build_style_profile

    # FeedbackAgent로 StyleProfile 생성
    feedback_agent = FeedbackAgent()
    style_profile = feedback_agent.analyze()

    if not style_profile.recommended_topics and not style_profile.best_content_types:
        print("  성과 데이터 부족 — 기본 설정으로 진행합니다.")
        style_profile = None

    # 추천 주제 & 유형 선택
    topics_to_generate = _pick_auto_topics(style_profile, args.auto_count)

    print(f"\n  자동 생성 목록:")
    for i, (topic, ct) in enumerate(topics_to_generate, 1):
        print(f"    {i}. [{ct}] {topic}")

    generated = []
    for topic, content_type in topics_to_generate:
        try:
            state = generate_one(topic, content_type, args, style_profile=style_profile)
            generated.append(state)
        except Exception as e:
            print(f"\n  [오류] '{topic}' 생성 실패: {e}")

    print(f"\n자동화 완료: {len(generated)}/{len(topics_to_generate)}개 성공")
    return generated


def _pick_auto_topics(style_profile: StyleProfile | None, count: int) -> list[tuple[str, str]]:
    """StyleProfile의 추천 주제 + 성과 좋은 유형 기반으로 생성 목록 결정"""
    default_pairs = [
        ("며느리가 보낸 편지", "감동스토리"),
        ("살다 보니 알게 된 것들", "노인의지혜"),
        ("뻔한 상황의 놀라운 반전", "도파민형"),
        ("이런 적 있으세요?", "공감썰형"),
    ]

    if not style_profile:
        return default_pairs[:count]

    results = []

    # 추천 주제 우선 사용
    best_ct = style_profile.best_content_types[0] if style_profile.best_content_types else "감동스토리"
    for topic in style_profile.recommended_topics[:count]:
        results.append((topic, best_ct))

    # 부족하면 기본 주제로 채움
    for topic, ct in default_pairs:
        if len(results) >= count:
            break
        ct_to_use = style_profile.best_content_types[0] if style_profile.best_content_types else ct
        results.append((topic, ct_to_use))

    return results[:count]


# ─────────────────────────────────────────────
# --use-feedback 모드: 단일 주제에 피드백 반영
# ─────────────────────────────────────────────

def load_style_profile_with_feedback() -> StyleProfile | None:
    from agents.feedback_agent import FeedbackAgent
    from analytics.performance_db import build_style_profile

    # 우선 DB만으로 빠르게 생성
    profile = build_style_profile()
    if not profile:
        return None

    # Claude로 심층 분석
    feedback_agent = FeedbackAgent()
    return feedback_agent.analyze()


# ─────────────────────────────────────────────
# 요약 출력
# ─────────────────────────────────────────────

def _print_summary(state: PipelineState):
    print("\n" + "=" * 50)
    print("완료!")
    if state.script:
        print(f"  제목: {state.script.title}")
        print(f"  나레이션: {state.script.full_narration[:60]}...")
        print(f"  글자 수: {state.script.character_count}자")
        print(f"  해시태그: {' '.join(state.script.hashtags)}")
    if state.final_video_path:
        print(f"  영상 파일: {state.final_video_path}")
    if state.youtube_url:
        print(f"  YouTube URL: {state.youtube_url}")
    print("=" * 50)


# ─────────────────────────────────────────────
# 진입점
# ─────────────────────────────────────────────

def main():
    args = parse_args()

    # 특수 모드: Analytics / Stats / Auto
    if args.show_stats:
        cmd_show_stats()
        return

    if args.sync_analytics:
        cfg.validate_config(skip_youtube=False)
        cmd_sync_analytics(args)
        return

    if args.auto:
        cfg.validate_config(skip_youtube=args.skip_upload)
        if not args.dry_run:
            cfg.check_font()
        cmd_auto(args)
        return

    # 일반 생성 모드: --topic 필수
    if not args.topic:
        print("오류: --topic 이 필요합니다. python main.py --help 참조")
        sys.exit(1)

    cfg.validate_config(skip_youtube=args.skip_upload or args.dry_run)
    if not args.dry_run:
        cfg.check_font()

    # 피드백 반영 여부
    style_profile = None
    if args.use_feedback:
        print("\n[피드백] 성과 데이터 분석 중...")
        style_profile = load_style_profile_with_feedback()
        if style_profile:
            print(f"  → 적용: {style_profile.best_content_types} / {style_profile.best_emotional_tones}")
        else:
            print("  → 성과 데이터 부족, 기본 설정으로 진행")

    generate_one(args.topic, args.content_type, args, style_profile=style_profile)


if __name__ == "__main__":
    main()
