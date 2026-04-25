#!/usr/bin/env python3
"""YouTube Shorts 자동 생성 CLI — 5060 한국 중장년층 타겟"""
import argparse
import sys
import uuid
from pathlib import Path

import config as cfg
from models.data_models import PipelineState
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
  python main.py --topic "며느리에게 받은 편지" --type 감동스토리
  python main.py --topic "살다 보니 알게 된 것들" --type 노인의지혜 --skip-upload
  python main.py --topic "뻔한 상황의 반전" --type 도파민형 --privacy public
  python main.py --topic "시어머니의 일기" --type 공감썰형 --dry-run
""",
    )
    parser.add_argument("--topic", "-t", required=True, help="콘텐츠 주제")
    parser.add_argument(
        "--type", "-T",
        dest="content_type",
        choices=CONTENT_TYPES,
        default="감동스토리",
        help=f"콘텐츠 유형 (기본: 감동스토리)",
    )
    parser.add_argument(
        "--privacy",
        choices=["public", "private", "unlisted"],
        default="private",
        help="YouTube 공개 설정 (기본: private)",
    )
    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="YouTube 업로드 건너뛰기 (영상 파일만 생성)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="에이전트만 실행 (TTS/영상 생성 안 함)",
    )
    parser.add_argument(
        "--output-dir",
        default=cfg.OUTPUT_DIR,
        help="출력 디렉토리",
    )
    parser.add_argument(
        "--job-id",
        default=None,
        help="재시도할 기존 작업 ID",
    )
    return parser.parse_args()


def run_agent_phase(state: PipelineState) -> PipelineState:
    """Phase 1: 크리에이티브 에이전트 루프"""
    print("\n[Phase 1] 크리에이티브 에이전트 실행")
    print("-" * 40)

    research_agent = ResearchAgent()
    script_agent = ScriptAgent()
    visual_agent = VisualAgent()
    strategy_agent = StrategyAgent()

    # 리서치
    state.research = research_agent.run(state.topic, state.content_type)
    print(f"  → 추천 각도: {state.research.recommended_angle[:60]}...")

    revision_requests = None
    for round_num in range(1, cfg.MAX_REVISION_ROUNDS + 2):
        # 스크립트
        state.script = script_agent.run(
            state.research,
            state.content_type,
            revision_requests=revision_requests,
        )
        print(f"  → 제목: {state.script.title}")
        print(f"  → 글자 수: {state.script.character_count}자 (예상 {state.script.estimated_duration_sec:.0f}초)")

        # 비주얼
        state.visuals = visual_agent.run(state.script, state.research)
        print(f"  → 장면 수: {len(state.visuals.scenes)}개 / 전환: {state.visuals.transition_style}")

        # 품질 검토
        state.approval = strategy_agent.review(state, round_number=round_num)
        print(f"  → 전략 검토: 종합 {state.approval.overall_score}/10 | 5060 적합성 {state.approval.audience_fit_score}/10 | 감정 {state.approval.emotional_impact_score}/10")
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

    return state


def run_production_phase(state: PipelineState, output_dir: str, skip_upload: bool, privacy: str) -> PipelineState:
    """Phase 2: 프로덕션 파이프라인"""
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

    # TTS
    print("  [1/4] 한국어 음성 생성 중...")
    audio_path = str(job_dir / "narration.mp3")
    audio_path, audio_duration = generate_audio(state.script.full_narration, audio_path)
    state.audio_path = audio_path

    # Pexels 클립 다운로드
    print("  [2/4] 스톡 영상 다운로드 중...")
    state.video_clips = fetch_scene_clips(
        state.visuals.scenes,
        str(clips_dir),
        state.visuals.b_roll_keywords,
    )

    # 영상 조합
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

    # 자막 삽입
    print("  [4/4] 한글 자막 삽입 중...")
    subtitle_chunks = chunk_narration(state.script.full_narration, audio_duration)
    final_path = str(job_dir / "final.mp4")
    burn_subtitles(assembled_path, subtitle_chunks, final_path)
    state.final_video_path = final_path

    print(f"\n  영상 생성 완료: {final_path}")

    if not skip_upload:
        print("\n  [YouTube] 업로드 중...")
        cfg.check_font()
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


def print_summary(state: PipelineState):
    print("\n" + "=" * 50)
    print("완료!")
    print(f"  제목: {state.script.title}")
    print(f"  나레이션: {state.script.full_narration[:60]}...")
    print(f"  글자 수: {state.script.character_count}자")
    if state.final_video_path:
        print(f"  영상 파일: {state.final_video_path}")
    if state.youtube_url:
        print(f"  YouTube URL: {state.youtube_url}")
    print(f"  해시태그: {' '.join(state.script.hashtags)}")
    print("=" * 50)


def main():
    args = parse_args()

    # 설정 검증
    cfg.validate_config(skip_youtube=args.skip_upload or args.dry_run)
    if not args.dry_run:
        cfg.check_font()

    job_id = args.job_id or str(uuid.uuid4())[:8]
    print(f"\nYouTube Shorts Generator")
    print(f"주제: {args.topic}")
    print(f"유형: {args.content_type}")
    print(f"작업 ID: {job_id}")

    state = PipelineState(
        job_id=job_id,
        topic=args.topic,
        content_type=args.content_type,
    )

    # Phase 1: 에이전트
    state = run_agent_phase(state)

    if args.dry_run:
        print("\n[dry-run] 에이전트 완료. 영상 생성 건너뜀.")
        print_summary(state)
        return

    # Phase 2: 프로덕션
    state = run_production_phase(state, args.output_dir, args.skip_upload, args.privacy)
    print_summary(state)


if __name__ == "__main__":
    main()
