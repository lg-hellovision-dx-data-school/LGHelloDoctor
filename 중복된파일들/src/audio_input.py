import sounddevice as sd
import soundfile as sf
import numpy as np
import tempfile
import os

SAMPLE_RATE = 16000
CHANNELS = 1


def record_audio(duration: int = 5) -> str:
    """
    마이크에서 음성을 녹음하고 임시 wav 파일 경로를 반환합니다.
    duration: 녹음 시간 (초)
    """
    print(f"[녹음 시작] {duration}초간 녹음합니다...")
    audio = sd.rec(
        int(duration * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32"
    )
    sd.wait()
    print("[녹음 완료]")

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    sf.write(tmp.name, audio, SAMPLE_RATE)
    return tmp.name


def load_audio_file(file_path: str) -> str:
    """
    테스트용: 파일 경로를 그대로 반환합니다.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
    return file_path
