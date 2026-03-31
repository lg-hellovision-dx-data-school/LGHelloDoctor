"""
Wake word 감지 모듈
"헬로비" 감지 후 음성 녹음을 시작합니다.

방식: 연속 오디오 스트리밍 → 에너지 VAD → Whisper-tiny 키워드 확인
프로덕션에서는 전용 웨이크워드 엔진(pvporcupine 등)으로 교체 권장
"""
import tempfile
import numpy as np
import sounddevice as sd
import soundfile as sf

SAMPLE_RATE = 16000
WAKE_WORDS = ["헬로비", "헬로 비", "헬로비비", "헬로 비비"]
CHUNK_DURATION = 1.5      # 감지 창 (초)
RECORD_DURATION = 7       # Wake word 감지 후 발화 녹음 시간 (초)
ENERGY_THRESHOLD = 0.008  # RMS 임계값 (노인 작은 목소리 고려해 낮게 설정)


class WakeWordDetector:
    """
    연속 오디오 스트림에서 Wake word를 감지합니다.

    use_whisper=True  : Whisper-tiny로 키워드 확인 (정확, 느림)
    use_whisper=False : 에너지 기반만 사용 (빠름, 모든 음성에 반응)
    """

    def __init__(self, wake_words: list = None, use_whisper: bool = True):
        self.wake_words = wake_words or WAKE_WORDS
        self.use_whisper = use_whisper
        self._model = None
        if use_whisper:
            self._load_whisper()

    def _load_whisper(self):
        try:
            import whisper as _whisper
            self._model = _whisper.load_model("tiny")
            print("[Wake word] Whisper-tiny 로드 완료")
        except ImportError:
            print("[Wake word] openai-whisper 미설치 → 에너지 기반 감지로 전환")
            self.use_whisper = False

    # ------------------------------------------------------------------
    # 내부 유틸
    # ------------------------------------------------------------------

    def _is_speech(self, audio: np.ndarray) -> bool:
        """에너지 기반 음성 여부 판단 (빠른 1차 필터)"""
        rms = float(np.sqrt(np.mean(audio ** 2)))
        return rms > ENERGY_THRESHOLD

    def _contains_wake_word(self, audio_path: str) -> bool:
        """Whisper-tiny로 웨이크워드 포함 여부 확인"""
        if self._model is None:
            return False
        try:
            result = self._model.transcribe(
                audio_path,
                language="ko",
                fp16=False,
                temperature=0.0,
            )
            text = result["text"].strip().replace(" ", "")
            return any(w.replace(" ", "") in text for w in self.wake_words)
        except Exception:
            return False

    def _save_tmp_wav(self, audio: np.ndarray) -> str:
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        sf.write(tmp.name, audio, SAMPLE_RATE)
        return tmp.name

    # ------------------------------------------------------------------
    # 공개 API
    # ------------------------------------------------------------------

    def listen_and_trigger(self) -> str:
        """
        Wake word 감지까지 반복 대기.
        감지 후 발화를 녹음하고 wav 파일 경로를 반환합니다.
        """
        print(f"[대기 중] '{self.wake_words[0]}' 라고 말해주세요...")
        chunk_samples = int(CHUNK_DURATION * SAMPLE_RATE)

        while True:
            chunk = sd.rec(
                chunk_samples,
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
            )
            sd.wait()
            audio = chunk.flatten()

            # 1차 필터: 에너지 없으면 스킵
            if not self._is_speech(audio):
                continue

            # 2차 필터: Whisper로 키워드 확인 (사용 시)
            if self.use_whisper:
                tmp_path = self._save_tmp_wav(audio)
                if not self._contains_wake_word(tmp_path):
                    continue

            print("[웨이크워드 감지] 말씀하세요...")
            return self._record_after_wake()

    def _record_after_wake(self) -> str:
        """웨이크워드 감지 직후 발화 녹음"""
        print(f"[녹음 중] {RECORD_DURATION}초간 말씀해 주세요...")
        audio = sd.rec(
            int(RECORD_DURATION * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
        )
        sd.wait()
        print("[녹음 완료]")
        return self._save_tmp_wav(audio.flatten())


def listen_for_wake_word() -> str:
    """편의 함수: Wake word 감지 후 wav 경로 반환"""
    detector = WakeWordDetector()
    return detector.listen_and_trigger()
