import torch
import soundfile as sf
import librosa
import numpy as np
import tempfile

# silero-vad 모델 로드 (최초 1회)
model, utils = torch.hub.load(
    repo_or_dir="snakers4/silero-vad",
    model="silero_vad",
    force_reload=False,
    trust_repo=True
)
(get_speech_timestamps, *_) = utils

SAMPLE_RATE = 16000


def remove_silence(audio_path: str) -> str:
    """
    VAD 필터로 침묵 구간을 제거하고 음성 구간만 남긴 wav 파일 경로를 반환합니다.
    """
    audio, _ = librosa.load(audio_path, sr=SAMPLE_RATE, mono=True)
    wav = torch.from_numpy(audio)

    speech_timestamps = get_speech_timestamps(
        wav,
        model,
        sampling_rate=SAMPLE_RATE,
        threshold=0.4,       # 낮을수록 민감 (노인 작은 목소리 고려)
        min_speech_duration_ms=200,
        min_silence_duration_ms=300,
    )

    if not speech_timestamps:
        # 음성 구간 없으면 원본 그대로 반환
        return audio_path

    # 음성 구간만 이어붙이기
    speech_audio = torch.cat([
        wav[ts["start"]:ts["end"]] for ts in speech_timestamps
    ])

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    sf.write(tmp.name, speech_audio.numpy(), SAMPLE_RATE)
    return tmp.name
