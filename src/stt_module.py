import os
import re
from dotenv import load_dotenv

load_dotenv()

# 파인튜닝된 SenseVoice 모델 경로 (완성되면 여기만 교체)
FINETUNED_MODEL_PATH = "./models/sensevoice-ko-elderly"

# SenseVoice 베이스 모델 (파인튜닝 전 fallback)
BASE_MODEL = "iic/SenseVoiceSmall"

# SenseVoice 출력 태그 제거 패턴 (감정/이벤트 태그)
_TAG_PATTERN = re.compile(r"<[^>]+>")

# 모델 인스턴스 캐시 (매 호출마다 로드하지 않도록)
_model_cache: dict = {}


def _clean_sensevoice_output(text: str) -> str:
    """SenseVoice 출력에서 <emotion> <event> 등 태그 제거"""
    return _TAG_PATTERN.sub("", text).strip()


def _load_model(model_path: str):
    """SenseVoice 모델 lazy loading (최초 1회만 로드)"""
    if model_path not in _model_cache:
        from funasr import AutoModel
        _model_cache[model_path] = AutoModel(
            model=model_path,
            vad_model="fsmn-vad",
            vad_kwargs={"max_single_segment_time": 30000},
            device="cuda" if _is_cuda_available() else "cpu",
        )
    return _model_cache[model_path]


def _is_cuda_available() -> bool:
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


def _has_finetuned_model() -> bool:
    return os.path.exists(FINETUNED_MODEL_PATH)


def transcribe(audio_path: str) -> dict:
    """
    음성 파일을 텍스트로 변환합니다.

    우선순위:
    1. 파인튜닝된 SenseVoice 모델 (./models/sensevoice-ko-elderly)
    2. SenseVoice 베이스 모델 (iic/SenseVoiceSmall) — fallback
    """
    if _has_finetuned_model():
        return _transcribe_sensevoice(audio_path, FINETUNED_MODEL_PATH)
    return _transcribe_sensevoice(audio_path, BASE_MODEL)


def _transcribe_sensevoice(audio_path: str, model_path: str) -> dict:
    """SenseVoice 모델로 한국어 전사 수행"""
    try:
        model = _load_model(model_path)
        result = model.generate(
            input=audio_path,
            language="ko",
            use_itn=True,   # 역텍스트 정규화 (숫자/단위 변환)
        )
        raw_text = result[0]["text"] if result else ""
        text = _clean_sensevoice_output(raw_text)

        return {
            "text": text,
            "confidence": None,   # SenseVoice는 confidence 미제공
            "language": "ko",
            "raw_text": raw_text,
        }
    except Exception as e:
        print(f"[STT 오류] {e}")
        return {
            "text": "",
            "confidence": None,
            "language": "ko",
            "raw_text": "",
        }