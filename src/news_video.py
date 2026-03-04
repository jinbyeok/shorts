import base64
import os
import re
import tempfile
import wave
from pathlib import Path

from google import genai
from google.genai import types
from moviepy import AudioFileClip, ColorClip, CompositeVideoClip, TextClip


def _require_google_api_key():
    if not os.getenv("GOOGLE_API_KEY"):
        raise RuntimeError("환경변수 GOOGLE_API_KEY가 필요합니다.")


def create_short_script_with_google_ai(
    title: str,
    content: str,
    model: str = "gemini-2.0-flash",
) -> str:
    """기사 내용을 30초 내 한국어 내레이션 스크립트로 요약합니다."""
    _require_google_api_key()
    client = genai.Client()
    prompt = f"""
아래 뉴스 기사로 30초 내 쇼츠 내레이션 스크립트를 만들어 주세요.

[제목]
{title}

[본문]
{content}

[조건]
- 한국어 존댓말
- 4~6문장
- 과장/허위 금지, 기사 사실 중심
- 영상 자막으로 그대로 써도 자연스럽게 작성
""".strip()

    response = client.models.generate_content(
        model=model,
        contents=prompt,
    )
    return (response.text or "").strip()


def _save_wave_file(raw_pcm: bytes, output_path: Path, sample_rate: int = 24000):
    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(raw_pcm)


def synthesize_voice_with_google_ai(
    text: str,
    output_audio_path: str,
    voice_name: str = "Kore",
    model: str = "gemini-2.5-flash-preview-tts",
) -> str:
    """Google AI TTS를 사용해 음성을 생성해 WAV 파일로 저장합니다."""
    _require_google_api_key()
    client = genai.Client()
    response = client.models.generate_content(
        model=model,
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                )
            ),
        ),
    )

    audio_part = None
    for candidate in response.candidates or []:
        parts = getattr(getattr(candidate, "content", None), "parts", []) or []
        for part in parts:
            inline_data = getattr(part, "inline_data", None)
            if inline_data and getattr(inline_data, "data", None):
                audio_part = inline_data
                break
        if audio_part:
            break

    if not audio_part:
        raise RuntimeError("Google AI TTS 응답에서 오디오 데이터를 찾지 못했습니다.")

    data = audio_part.data
    if isinstance(data, str):
        raw_audio = base64.b64decode(data)
    else:
        raw_audio = data

    out_path = Path(output_audio_path)
    mime_type = getattr(audio_part, "mime_type", "") or ""

    if "wav" in mime_type:
        out_path.write_bytes(raw_audio)
    else:
        _save_wave_file(raw_audio, out_path)
    return str(out_path)


def _split_sentences(text: str):
    lines = [s.strip() for s in re.split(r"(?<=[.!?。！？])\s+", text) if s.strip()]
    return lines or [text.strip()]


def create_news_video_from_article(
    article_title: str,
    article_content: str,
    output_path: str,
    max_seconds: int = 30,
    voice_name: str = "Kore",
):
    """기사로부터 쇼츠 영상(자막+보이스)을 생성합니다."""
    script = create_short_script_with_google_ai(article_title, article_content)
    if not script:
        raise RuntimeError("스크립트 생성에 실패했습니다.")

    with tempfile.TemporaryDirectory() as tmp_dir:
        audio_path = Path(tmp_dir) / "narration.wav"
        synthesize_voice_with_google_ai(
            text=script,
            output_audio_path=str(audio_path),
            voice_name=voice_name,
        )

        audio_clip = AudioFileClip(str(audio_path))
        duration = min(float(audio_clip.duration), float(max_seconds))
        audio_clip = audio_clip.subclip(0, duration)

        base_clip = ColorClip(size=(1080, 1920), color=(18, 18, 24), duration=duration)

        title_clip = TextClip(
            article_title,
            fontsize=58,
            color="white",
            method="caption",
            size=(980, None),
            align="center",
        ).set_duration(duration).set_position(("center", 140))

        subtitles = []
        sentences = _split_sentences(script)
        total_chars = sum(len(sentence) for sentence in sentences) or 1
        timeline = 0.0

        for sentence in sentences:
            sentence_duration = duration * (len(sentence) / total_chars)
            sub_clip = TextClip(
                sentence,
                fontsize=48,
                color="white",
                bg_color="black",
                method="caption",
                size=(980, None),
                align="center",
            ).set_start(timeline).set_duration(sentence_duration).set_position(("center", 1450))
            subtitles.append(sub_clip)
            timeline += sentence_duration

        final = CompositeVideoClip([base_clip, title_clip, *subtitles])
        final = final.set_audio(audio_clip)
        final.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")

    return output_path, script
