import time
from google import genai
from google.genai import types
from moviepy.editor import VideoFileClip, TextClip, concatenate_videoclips, CompositeVideoClip
import os

# Google GenAI 클라이언트
client = genai.Client()

def generate_veo3_clip(text_prompt: str, duration: int = 8, aspect_ratio: str = "9:16") -> str:
    """
    Veo3로 텍스트 프롬프트 기반 영상 클립 하나 생성
    반환값: 클립 파일 경로
    """
    # Gemeni API를 통한 video 생성
    operation = client.models.generate_videos(
        model="veo-3.0-generate-preview",
        prompt=text_prompt,
        config=types.GenerateVideosConfig(
            aspect_ratio=aspect_ratio,  # "9:16" 세로 비율 (쇼츠용)
            resolution="1080p",
            # 기타 옵션 가능: negative_prompt, personSafety, etc.
        )
    )

    # 완성될 때까지 대기
    while not operation.done:
        print("Waiting for Veo3 clip to finish generation...")
        time.sleep(20)
        operation = client.operations.get(operation)

    generated = operation.result.generated_videos[0]
    # video 속성에 다운로드 가능한 URI 또는 byte 정보가 담김
    clip_path = f"clip_{int(time.time())}.mp4"
    client.files.download(file=generated.video)
    generated.video.save(clip_path)
    return clip_path

def make_shorts_video(script_lines: list[str], output_path: str = "shorts_output.mp4"):
    """
    script_lines: 화면 단위 문장 리스트
    각 문장에 대한 Veo3 클립 생성 → 자막 넣고 이어붙이기
    전체 길이 1분 이내 유지
    """
    clips = []
    total_duration = 0
    max_total = 60  # 최대 60초

    for idx, line in enumerate(script_lines):
        # 한 문장당 할당할 시간 계산
        # 예: 전체 문장 수 기준으로 고르게 분배
        # 또는 문장 길이에 비례
        # 간단히: 남은 시간 / 남은 문장 수
        remaining = max_total - total_duration
        remaining_lines = len(script_lines) - idx
        if remaining_lines <= 0:
            break
        alloc_dur = remaining / remaining_lines
        # 최소 시간 보장
        if alloc_dur < 4:
            alloc_dur = 4  # Veo3 최소 duration은 보통 4초 이상 필요할 수 있음 :contentReference[oaicite:1]{index=1}
        if alloc_dur > 8:
            alloc_dur = 8  # 너무 길게 끌지 않도록

        # 클립 생성
        clip_file = generate_veo3_clip(
            text_prompt=line,
            duration=int(alloc_dur),
            aspect_ratio="9:16"
        )

        # 자막(TextClip)
        txt_clip = TextClip(line, fontsize=40, color="white", bg_color="black", size=(1080, None), method="caption")
        txt_clip = txt_clip.set_duration(alloc_dur).set_position(("center", "bottom"))

        # 비디오 클립 읽기
        video_clip = VideoFileClip(clip_file).set_duration(alloc_dur)
        # 자막 합성
        composite = CompositeVideoClip([video_clip, txt_clip])
        clips.append(composite)
        total_duration += alloc_dur

        # 만약 이미 시간이 거의 다 찼으면 종료
        if total_duration >= max_total:
            break

    # 이어붙이기
    final = concatenate_videoclips(clips, method="compose")
    final.write_videofile(output_path, fps=30, codec="libx264", audio_codec="aac")

    # 임시 클립 파일 정리 (원한다면)
    for clip in clips:
        try:
            os.remove(clip.filename)
        except Exception:
            pass

    print(f"쇼츠 영상이 저장되었습니다: {output_path}")