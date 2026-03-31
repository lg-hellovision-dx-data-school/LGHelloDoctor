"""
AI Hub 한국인 노인 음성 데이터셋 가공 모듈 (프레임워크)
원본 데이터 → 학습용 HuggingFace Dataset 변환

AI Hub 데이터: 한국인 노인 음성
  https://aihub.or.kr

원본 폴더 구조:
    data/raw/
        Training/
            원천데이터/   (wav 파일)
            라벨링데이터/ (json 파일)
        Validation/
            원천데이터/
            라벨링데이터/

실행:
    python data_prep.py --raw_dir ./data/raw --output_dir ./data/processed
"""
import argparse
import json
import os
import re
from pathlib import Path
from typing import List, Dict

SAMPLE_RATE  = 16000
MIN_DURATION = 0.5    # 초
MAX_DURATION = 30.0   # 초

# AI Hub 레이블 노이즈 태그
_NOISE_TAG = re.compile(r"\(.*?\)|\[.*?\]|[/+]|[b-z]/")


def clean_label(text: str) -> str:
    """AI Hub 레이블 노이즈 태그 제거"""
    text = _NOISE_TAG.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def load_split(split_dir: str) -> List[Dict]:
    """
    데이터 분할 폴더에서 (오디오 경로, 전사 텍스트) 쌍 로드.
    split_dir/원천데이터/ + split_dir/라벨링데이터/ 구조 가정.
    """
    import librosa

    base      = Path(split_dir)
    audio_dir = base / "원천데이터"
    label_dir = base / "라벨링데이터"

    if not audio_dir.exists() or not label_dir.exists():
        raise FileNotFoundError(
            f"'{split_dir}' 아래에 '원천데이터'와 '라벨링데이터' 폴더가 필요합니다."
        )

    samples = []
    for label_file in sorted(label_dir.glob("*.json")):
        try:
            meta = json.loads(label_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        for utt in meta.get("utterance", []):
            stem      = os.path.splitext(utt.get("audio_id", ""))[0]
            audio_path = next(
                (audio_dir / (stem + ext)
                 for ext in (".wav", ".WAV", ".flac")
                 if (audio_dir / (stem + ext)).exists()),
                None
            )
            if audio_path is None:
                continue

            text = clean_label(utt.get("dialect_form") or utt.get("standard_form", ""))
            if not text:
                continue

            try:
                duration = librosa.get_duration(path=str(audio_path))
            except Exception:
                continue
            if not (MIN_DURATION <= duration <= MAX_DURATION):
                continue

            samples.append({"audio": str(audio_path), "transcription": text})

    return samples


def build_dataset(raw_dir: str, output_dir: str):
    """원본 폴더 → HuggingFace DatasetDict 변환 및 저장"""
    from datasets import Dataset, DatasetDict, Audio

    print("[데이터 가공] 로딩 중...")
    train_samples = load_split(os.path.join(raw_dir, "Training"))
    val_samples   = load_split(os.path.join(raw_dir, "Validation"))
    print(f"  훈련: {len(train_samples):,}개 / 검증: {len(val_samples):,}개")

    dataset = DatasetDict({
        "train":      Dataset.from_list(train_samples),
        "validation": Dataset.from_list(val_samples),
    }).cast_column("audio", Audio(sampling_rate=SAMPLE_RATE))

    os.makedirs(output_dir, exist_ok=True)
    dataset.save_to_disk(output_dir)
    print(f"[완료] {output_dir}")
    return dataset


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Hub 노인 음성 데이터 가공")
    parser.add_argument("--raw_dir",    default="./data/raw")
    parser.add_argument("--output_dir", default="./data/processed")
    args = parser.parse_args()
    build_dataset(args.raw_dir, args.output_dir)
