from pathlib import Path
from models.data_models import Scene
from config import VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS


class VideoAssemblyError(Exception):
    def __init__(self, step: str, message: str):
        super().__init__(f"[영상 조합 오류 - {step}] {message}")


def resize_to_vertical(clip, width: int = VIDEO_WIDTH, height: int = VIDEO_HEIGHT):
    """클립을 9:16 수직 포맷(720x1280)으로 리사이즈 + center-crop"""
    import moviepy.video.fx as vfx

    clip_w, clip_h = clip.size
    scale_w = width / clip_w
    scale_h = height / clip_h
    scale = max(scale_w, scale_h)

    new_w = int(clip_w * scale)
    new_h = int(clip_h * scale)

    resized = clip.with_effects([vfx.Resize((new_w, new_h))])
    cropped = resized.cropped(
        x_center=new_w / 2,
        y_center=new_h / 2,
        width=width,
        height=height,
    )
    return cropped


def _trim_or_loop(clip, target_duration: float):
    """클립을 target_duration에 맞게 자르거나 반복"""
    import moviepy.video.fx as vfx

    if clip.duration >= target_duration:
        return clip.subclipped(0, target_duration)
    return clip.with_effects([vfx.Loop(duration=target_duration)])


def assemble_video(
    clip_paths: list[str],
    audio_path: str,
    scenes: list[Scene],
    output_path: str,
    transition_style: str = "crossfade",
    fps: int = VIDEO_FPS,
) -> str:
    from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips
    import moviepy.video.fx as vfx

    if len(clip_paths) != len(scenes):
        raise VideoAssemblyError("입력 검증", f"클립 수({len(clip_paths)})와 장면 수({len(scenes)}) 불일치")

    print("  [영상] 클립 처리 중...")
    processed_clips = []
    for i, (path, scene) in enumerate(zip(clip_paths, scenes)):
        try:
            clip = VideoFileClip(path)
            clip = resize_to_vertical(clip)
            clip = _trim_or_loop(clip, scene.duration_sec)
            processed_clips.append(clip)
        except Exception as e:
            raise VideoAssemblyError(f"클립 처리 (장면 {i+1})", str(e))

    print(f"  [영상] {len(processed_clips)}개 클립 연결 중 (전환: {transition_style})...")
    if transition_style == "crossfade" and len(processed_clips) > 1:
        fade_dur = min(0.5, min(c.duration for c in processed_clips) / 4)
        faded = []
        for i, clip in enumerate(processed_clips):
            if i > 0:
                clip = clip.with_effects([vfx.CrossFadeIn(fade_dur)])
            faded.append(clip)
        video = concatenate_videoclips(faded, method="compose", padding=-fade_dur)
    else:
        video = concatenate_videoclips(processed_clips, method="compose")

    print("  [영상] 오디오 합성 중...")
    audio = AudioFileClip(audio_path)
    final_duration = min(video.duration, audio.duration)
    video = video.subclipped(0, final_duration)
    audio = audio.subclipped(0, final_duration)
    video = video.with_audio(audio)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    print(f"  [영상] 렌더링 중: {output_path}")
    video.write_videofile(
        output_path,
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        logger=None,
        verbose=False,
    )

    for clip in processed_clips:
        clip.close()
    audio.close()
    video.close()

    print(f"  [영상] 조합 완료: {output_path}")
    return output_path
