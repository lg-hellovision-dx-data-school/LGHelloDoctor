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
from typing import List, Dict, Iterable, Optional

SAMPLE_RATE  = 16000
MIN_DURATION = 0.5    # 초
MAX_DURATION = 30.0   # 초

# AI Hub 레이블 노이즈 태그
_NOISE_TAG = re.compile(r"\(.*?\)|\[.*?\]|[/+]|[b-z]/")
_AUDIO_EXTS = (".wav", ".WAV", ".flac", ".FLAC", ".mp3", ".MP3")


def _find_existing_dir(base: Path, candidates: Iterable[str]) -> Optional[Path]:
    for name in candidates:
        candidate = base / name
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None


def _find_split_dirs(base: Path) -> tuple[Path, Path]:
    """AI Hub 데이터셋 변형 구조에서 오디오/라벨 디렉터리를 자동 탐색합니다."""
    audio_dir = _find_existing_dir(
        base,
        [
            "원천데이터",
            "audio",
            "Audio",
            "[원천]4.AI스피커",
            "[원천]4.AI스피커 - 복사본",
        ],
    )
    label_dir = _find_existing_dir(
        base,
        ["라벨링데이터", "labels", "label", "[라벨]4.AI스피커"],
    )

    # 최상위 후보가 없으면 하위 경로까지 재귀 탐색해서 가장 그럴듯한 폴더를 선택
    if audio_dir is None:
        audio_candidates = [
            p for p in base.rglob("*")
            if p.is_dir() and (
                p.name in {"원천데이터", "audio", "Audio", "[원천]4.AI스피커", "[원천]4.AI스피커 - 복사본"}
                or "원천" in p.name
            )
        ]
        audio_dir = _pick_best_dir(audio_candidates, _AUDIO_EXTS)

    if label_dir is None:
        label_candidates = [
            p for p in base.rglob("*")
            if p.is_dir() and (
                p.name in {"라벨링데이터", "labels", "label", "[라벨]4.AI스피커"}
                or "라벨" in p.name
                or "label" in p.name.lower()
            )
        ]
        label_dir = _pick_best_dir(label_candidates, (".json",))

    if audio_dir is None:
        raise FileNotFoundError(
            f"'{base}' 아래에서 오디오 폴더를 찾지 못했습니다. "
            "(지원: 원천데이터, audio, Audio)"
        )
    if label_dir is None:
        raise FileNotFoundError(
            f"'{base}' 아래에서 라벨 폴더를 찾지 못했습니다. "
            "(지원: 라벨링데이터, labels, label, [라벨]4.AI스피커)"
        )

    return audio_dir, label_dir


def _pick_best_dir(candidates: Iterable[Path], suffixes: tuple[str, ...]) -> Optional[Path]:
    """후보 중 실제 데이터 파일 수가 많은 디렉터리를 선택합니다."""
    best_dir: Optional[Path] = None
    best_count = -1

    lowered = tuple(s.lower() for s in suffixes)
    for candidate in candidates:
        count = 0
        for p in candidate.rglob("*"):
            if p.is_file() and p.suffix.lower() in lowered:
                count += 1
                if count >= 200:
                    break
        if count > best_count:
            best_dir = candidate
            best_count = count

    return best_dir if best_count > 0 else None


def _audio_index(audio_dir: Path) -> Dict[str, Path]:
    """오디오 파일 탐색 인덱스 (stem/상대경로 기반)"""
    index: Dict[str, Path] = {}
    for p in audio_dir.rglob("*"):
        if not p.is_file() or p.suffix not in _AUDIO_EXTS:
            continue
        stem_key = p.stem.lower()
        rel_key = str(p.relative_to(audio_dir).with_suffix("")).replace("\\", "/").lower()
        index.setdefault(stem_key, p)
        index.setdefault(rel_key, p)
    return index


def _extract_utterances(meta: object) -> List[Dict]:
    """라벨 JSON 스키마 차이를 흡수해 발화 리스트를 추출합니다."""
    if isinstance(meta, dict):
        # 노인남녀 자유대화 데이터셋: {"발화정보": {...}, "대화정보": {...}, ...}
        if "발화정보" in meta and isinstance(meta["발화정보"], dict):
            return [meta["발화정보"]]

        if isinstance(meta.get("utterance"), list):
            return [u for u in meta["utterance"] if isinstance(u, dict)]

        for key in ("dialogue", "dialogs", "sentences", "data", "annotations"):
            value = meta.get(key)
            if isinstance(value, list):
                return [u for u in value if isinstance(u, dict)]

        return [meta]

    if isinstance(meta, list):
        return [u for u in meta if isinstance(u, dict)]

    return []


def _pick_text(utt: Dict) -> str:
    for key in (
        "dialect_form",
        "standard_form",
        "transcription",
        "text",
        "sentence",
        "script",
        "stt",
    ):
        value = utt.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _pick_audio_id(utt: Dict) -> str:
    for key in ("audio_id", "audio", "audio_path", "file", "filename", "wav", "fileNm"):
        value = utt.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _resolve_audio_path(
    audio_id: str,
    label_file: Path,
    label_dir: Path,
    audio_dir: Path,
    index: Dict[str, Path],
) -> Optional[Path]:
    if audio_id:
        norm = audio_id.replace("\\", "/")
        key_candidates = {
            Path(norm).stem.lower(),
            norm.lower(),
            str(Path(norm).with_suffix("")).replace("\\", "/").lower(),
            Path(norm).name.lower(),
            Path(norm).with_suffix("").name.lower(),
        }
        for key in key_candidates:
            if key in index:
                return index[key]

    # 라벨 파일 상대 경로를 오디오 상대 경로로 가정한 fallback
    rel_no_ext = label_file.relative_to(label_dir).with_suffix("")
    rel_key = str(rel_no_ext).replace("\\", "/").lower()
    if rel_key in index:
        return index[rel_key]

    stem_key = label_file.stem.lower()
    if stem_key in index:
        return index[stem_key]

    # 같은 파일명 기반의 마지막 fallback
    for ext in _AUDIO_EXTS:
        guess = audio_dir / (label_file.stem + ext)
        if guess.exists():
            return guess

    return None


def clean_label(text: str) -> str:
    """AI Hub 레이블 노이즈 태그 제거"""
    text = _NOISE_TAG.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


_DIALECT_KEYWORDS = {
    "제주": "jeju",
    "경상": "gyeongsang",
    "수도권": "sudogwon",
    "전라": "jeolla",
    "충청": "chungcheong",
    "강원": "gangwon",
    "표준": "standard",
}


def _detect_dialect(path: Path) -> str:
    """파일 경로에서 방언 키워드를 감지합니다."""
    path_str = str(path)
    for keyword, tag in _DIALECT_KEYWORDS.items():
        if keyword in path_str:
            return tag
    return "standard"


def load_split(split_dir: str, limit: int = 0) -> List[Dict]:
    """
    데이터 분할 폴더에서 (오디오 경로, 전사 텍스트) 쌍 로드.
    split_dir/원천데이터/ + split_dir/라벨링데이터/ 구조 가정.
    limit > 0 이면 방언별 균등 샘플링 후 섞어서 반환.
    """
    import random
    base = Path(split_dir)
    audio_dir, label_dir = _find_split_dirs(base)

    # 라벨 하위 폴더를 방언별로 분류 (rglob 없이 한 단계만)
    dialect_folders: Dict[str, List[Path]] = {}
    for folder in sorted(label_dir.iterdir()):
        if not folder.is_dir():
            continue
        dialect = _detect_dialect(folder)
        dialect_folders.setdefault(dialect, []).append(folder)

    print(f"  방언 폴더: { {d: len(fs) for d, fs in dialect_folders.items()} }")

    per_dialect_cap = (limit // max(len(dialect_folders), 1)) if limit > 0 else 0

    buckets: Dict[str, List[Dict]] = {}

    for dialect, folders in dialect_folders.items():
        for folder in folders:
            if per_dialect_cap > 0 and len(buckets.get(dialect, [])) >= per_dialect_cap:
                break

            for label_file in sorted(folder.glob("*.json")):
                if per_dialect_cap > 0 and len(buckets.get(dialect, [])) >= per_dialect_cap:
                    break

                try:
                    meta = json.loads(label_file.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue

                # 라벨과 동일한 상대경로로 오디오 직접 찾기 (인덱스 불필요)
                rel = label_file.relative_to(label_dir)
                audio_path = None
                for ext in _AUDIO_EXTS:
                    candidate = audio_dir / rel.with_suffix(ext)
                    if candidate.exists():
                        audio_path = candidate
                        break

                if audio_path is None:
                    continue

                for utt in _extract_utterances(meta):
                    text = clean_label(_pick_text(utt))
                    if not text:
                        continue
                    buckets.setdefault(dialect, []).append({
                        "audio": str(audio_path),
                        "transcription": text,
                        "dialect": dialect,
                    })
                    if per_dialect_cap > 0 and len(buckets[dialect]) >= per_dialect_cap:
                        break

    if not buckets:
        return []

    dialect_list = sorted(buckets.keys())
    print(f"  방언 분포: { {d: len(buckets[d]) for d in dialect_list} }")

    if limit <= 0:
        all_samples = [s for d in dialect_list for s in buckets[d]]
        random.shuffle(all_samples)
        return all_samples

    # 방언별 균등 할당
    per_dialect = limit // len(dialect_list)
    remainder   = limit % len(dialect_list)

    samples = []
    for i, dialect in enumerate(dialect_list):
        n = per_dialect + (1 if i < remainder else 0)
        pool = buckets[dialect]
        chosen = random.sample(pool, min(n, len(pool)))
        samples.extend(chosen)

    random.shuffle(samples)
    return samples


def build_dataset(raw_dir: str, output_dir: str, train_limit: int = 0, val_limit: int = 0):
    """원본 폴더 → HuggingFace DatasetDict 변환 및 저장"""
    from datasets import Dataset, DatasetDict, Audio

    print("[데이터 가공] 로딩 중...")
    training_dir = os.path.join(raw_dir, "Training")
    validation_dir = os.path.join(raw_dir, "Validation")

    if not os.path.isdir(training_dir) or not os.path.isdir(validation_dir):
        raise FileNotFoundError(
            "raw_dir 아래에 Training/Validation 폴더가 필요합니다. "
            f"입력 경로: {raw_dir}"
        )

    train_samples = load_split(training_dir, limit=train_limit)
    val_samples   = load_split(validation_dir, limit=val_limit)
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
    parser.add_argument("--train_limit", type=int, default=0, help="훈련 샘플 최대 개수(0=전체)")
    parser.add_argument("--val_limit", type=int, default=0, help="검증 샘플 최대 개수(0=전체)")
    args = parser.parse_args()
    build_dataset(
        args.raw_dir,
        args.output_dir,
        train_limit=args.train_limit,
        val_limit=args.val_limit,
    )
