"""
STT 정확도 평가 모듈
WER (Word Error Rate), CER (Character Error Rate) 측정

사용 예시:
    from evaluate_stt import evaluate_batch, print_report
    result = evaluate_batch(references=["무릎이 아파요"], hypotheses=["무릎 아파요"])
    print_report(result)

JSONL 파일 평가:
    python evaluate_stt.py --input tests/eval_data.jsonl
    각 줄: {"reference": "정답 텍스트", "hypothesis": "STT 결과"}
"""
import argparse
import json
import re
from typing import List, Dict

from jiwer import wer, cer


# ------------------------------------------------------------------
# 한국어 전처리
# ------------------------------------------------------------------

def _normalize_ko(text: str) -> str:
    """평가용 텍스트 정규화: 구두점 제거, 공백 통일"""
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ------------------------------------------------------------------
# 단일 샘플 평가
# ------------------------------------------------------------------

def compute_wer(reference: str, hypothesis: str) -> float:
    """단어 오류율 (WER) — 0.0(완벽) ~ 1.0 이상"""
    ref = _normalize_ko(reference)
    hyp = _normalize_ko(hypothesis)
    return float(wer(ref, hyp))


def compute_cer(reference: str, hypothesis: str) -> float:
    """문자 오류율 (CER) — 한국어 형태소 특성상 WER보다 직관적"""
    ref = _normalize_ko(reference)
    hyp = _normalize_ko(hypothesis)
    return float(cer(ref, hyp))


# ------------------------------------------------------------------
# 배치 평가
# ------------------------------------------------------------------

def evaluate_batch(references: List[str], hypotheses: List[str]) -> Dict:
    """
    여러 샘플의 WER / CER 집계.

    반환:
    {
        "wer":     float,   # 평균 WER
        "cer":     float,   # 평균 CER
        "samples": int,
        "details": [{"reference", "hypothesis", "wer", "cer"}, ...]
    }
    """
    if len(references) != len(hypotheses):
        raise ValueError("references와 hypotheses 개수가 일치해야 합니다.")

    details = []
    wer_total = 0.0
    cer_total = 0.0

    for ref, hyp in zip(references, hypotheses):
        sample_wer = compute_wer(ref, hyp)
        sample_cer = compute_cer(ref, hyp)
        wer_total += sample_wer
        cer_total += sample_cer
        details.append({
            "reference":  ref,
            "hypothesis": hyp,
            "wer": round(sample_wer, 4),
            "cer": round(sample_cer, 4),
        })

    n = len(references)
    return {
        "wer":     round(wer_total / n, 4),
        "cer":     round(cer_total / n, 4),
        "samples": n,
        "details": details,
    }


def evaluate_from_jsonl(jsonl_path: str) -> Dict:
    """
    JSONL 파일에서 평가 데이터 로드 후 배치 평가.
    각 줄: {"reference": "정답", "hypothesis": "STT결과"}
    """
    references, hypotheses = [], []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            references.append(item["reference"])
            hypotheses.append(item["hypothesis"])
    return evaluate_batch(references, hypotheses)


# ------------------------------------------------------------------
# 리포트 출력
# ------------------------------------------------------------------

def print_report(result: Dict) -> None:
    """평가 결과 콘솔 출력"""
    sep = "=" * 55
    print(sep)
    print("  STT 정확도 평가 리포트")
    print(sep)
    print(f"  평가 샘플 수  : {result['samples']}개")
    print(f"  평균 WER      : {result['wer'] * 100:.2f}%")
    print(f"  평균 CER      : {result['cer'] * 100:.2f}%")
    print("-" * 55)
    for i, d in enumerate(result["details"], 1):
        print(f"  [{i:02d}] 정답  : {d['reference']}")
        print(f"       STT   : {d['hypothesis']}")
        print(f"       WER {d['wer']*100:.1f}%  /  CER {d['cer']*100:.1f}%")
        print()
    print(sep)

# ------------------------------------------------------------------
# CLI 진입점
# ------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="STT 정확도 평가")
    parser.add_argument(
        "--input", required=True,
        help="평가 JSONL 파일 경로 (각 줄: {reference, hypothesis})"
    )
    args = parser.parse_args()

    result = evaluate_from_jsonl(args.input)
    print_report(result)
