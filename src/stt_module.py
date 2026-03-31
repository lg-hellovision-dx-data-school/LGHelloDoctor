import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.environ["GROQ_API_KEY"])

# 파인튜닝 모델 경로 (완성되면 여기만 교체)
FINETUNED_MODEL_PATH = "./models/whisper-ko-elderly"
USE_FINETUNED = os.path.exists(FINETUNED_MODEL_PATH)


def transcribe(audio_path: str) -> dict:
    """
    음성 파일을 텍스트로 변환합니다.
    파인튜닝 모델이 있으면 로컬 모델 사용, 없으면 Groq API 사용.
    """
    if USE_FINETUNED:
        return _transcribe_local(audio_path)
    return _transcribe_groq(audio_path)


def _transcribe_groq(audio_path: str) -> dict:
    with open(audio_path, "rb") as f:
        result = client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=f,
            language="ko",
            response_format="verbose_json",  # confidence 포함
        )
    return {
        "text": result.text,
        "confidence": 0.94,   # Groq은 confidence 미제공, 임시값
        "language": "ko",
        "raw_text": result.text,
    }


def _transcribe_local(audio_path: str) -> dict:
    """파인튜닝 완료 후 활성화됩니다."""
    import torch
    import librosa
    from transformers import WhisperProcessor, WhisperForConditionalGeneration

    processor = WhisperProcessor.from_pretrained(FINETUNED_MODEL_PATH)
    model = WhisperForConditionalGeneration.from_pretrained(FINETUNED_MODEL_PATH)

    audio, _ = librosa.load(audio_path, sr=16000)
    inputs = processor(audio, return_tensors="pt", sampling_rate=16000)

    with torch.no_grad():
        output = model.generate(inputs.input_features)

    text = processor.batch_decode(output, skip_special_tokens=True)[0]
    return {
        "text": text,
        "confidence": 0.94,
        "language": "ko",
        "raw_text": text,
    }
