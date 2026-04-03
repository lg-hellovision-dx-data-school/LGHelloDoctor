"""
A팀 STT 파이프라인 진입점
음성 입력 → VAD → STT → 전처리 → B팀으로 전달

실행 모드:
    1. 파일 모드  : run(audio_path="파일경로")
    2. 마이크 모드: run(record=True, duration=7)
    3. 웨이크워드 : run(use_wake_word=True)   ← 마이크 필요
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from audio_input import record_audio, load_audio_file
from vad_filter import remove_silence
from stt_module import transcribe
from preprocessor import preprocess


def run(
    audio_path: str = None,
    record: bool = False,
    duration: int = 7,
    use_wake_word: bool = False,
    skip_vad: bool = False,
) -> dict:
    """
    파이프라인 전체 실행.

    Args:
        audio_path    : 테스트용 오디오 파일 경로 (파일 모드)
        record        : True → 마이크로 즉시 녹음
        duration      : 마이크 녹음 시간 (초)
        use_wake_word : True → "헬로비" 감지 후 녹음 (마이크 필요)
        skip_vad      : True → VAD 필터 건너뜀 (빠른 테스트용)

    Returns:
        B팀 의도 분류기로 전달되는 dict:
        {
            "text":       "전처리된 텍스트",
            "raw_text":   "STT 원본 텍스트",
            "confidence": 0.94,
            "language":   "ko"
        }
    """

    # ── Step 1 · 음성 입력 ─────────────────────────────────────────
    if use_wake_word:
        from wake_word import listen_for_wake_word
        path = listen_for_wake_word()
    elif record:
        path = record_audio(duration=duration)
    else:
        path = load_audio_file(audio_path)

    # ── Step 2 · VAD 필터 (침묵 제거) ─────────────────────────────
    if not skip_vad:
        path = remove_silence(path)

    # ── Step 3 · Whisper STT ────────────────────────────────────────
    stt_result = transcribe(path)

    # ── Step 4 · 텍스트 전처리 ─────────────────────────────────────
    processed = preprocess(stt_result["text"])

    return {
        **processed,
        "confidence": stt_result["confidence"],
        "language":   stt_result["language"],
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="A팀 STT 파이프라인")
    parser.add_argument("--file",       help="오디오 파일 경로")
    parser.add_argument("--record",     action="store_true", help="마이크 녹음 모드")
    parser.add_argument("--wake_word",  action="store_true", help="웨이크워드 감지 모드")
    parser.add_argument("--duration",   type=int, default=7, help="녹음 시간 (초)")
    parser.add_argument("--skip_vad",   action="store_true", help="VAD 필터 건너뜀")
    args = parser.parse_args()

    result = run(
        audio_path=args.file,
        record=args.record,
        duration=args.duration,
        use_wake_word=args.wake_word,
        skip_vad=args.skip_vad,
    )
    print("\n[파이프라인 결과]")
    for k, v in result.items():
        print(f"  {k}: {v}")
