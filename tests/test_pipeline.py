"""
A팀 STT 파이프라인 테스트 모음

실행:
    pytest tests/test_pipeline.py -v
    pytest tests/test_pipeline.py -v -k "not stt"   # STT(네트워크) 제외 빠른 실행
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from preprocessor import preprocess, correct_medical_terms, remove_fillers, normalize
from evaluate_stt import compute_wer, compute_cer, evaluate_batch, print_report

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "samples")


# ══════════════════════════════════════════════════════════════════
# 1. 전처리 — 간투어 제거
# ══════════════════════════════════════════════════════════════════

class TestFillerRemoval:
    def test_basic_fillers(self):
        result = preprocess("어~ 무릎이 음 너무 아파요")
        assert "어~" not in result["text"]
        assert "음" not in result["text"]
        assert "무릎" in result["text"]

    def test_repeated_filler(self):
        result = preprocess("어어어 가슴이 아파요 그그 숨이 안 쉬어져요")
        assert "가슴" in result["text"]
        assert "숨" in result["text"]

    def test_no_filler(self):
        """간투어 없는 문장은 그대로 통과"""
        text = "혈압약을 먹어도 되나요"
        result = preprocess(text)
        assert "혈압약" in result["text"]

    def test_raw_text_preserved(self):
        """원본 텍스트는 raw_text에 보존"""
        raw = "어~ 무릎이 아파요"
        result = preprocess(raw)
        assert result["raw_text"] == raw


# ══════════════════════════════════════════════════════════════════
# 2. 전처리 — 의료 용어 오탈자 보정
# ══════════════════════════════════════════════════════════════════

class TestMedicalCorrection:
    def test_department_typo(self):
        result = preprocess("무릅이 아파요 정형외가 가야 하나요")
        assert "무릎" in result["text"]
        assert "정형외과" in result["text"]

    def test_ent_typo(self):
        result = preprocess("이비인호과에 가야 하나요")
        assert "이비인후과" in result["text"]

    def test_drug_typo(self):
        result = preprocess("혈압야 먹고 있어요")
        assert "혈압약" in result["text"]

    def test_cold_drug_typo(self):
        result = preprocess("감기야랑 혈압야 같이 먹어도 되나요")
        assert "감기약" in result["text"]
        assert "혈압약" in result["text"]

    def test_body_part_typo(self):
        result = preprocess("어꺠가 아파요")
        assert "어깨" in result["text"]

    def test_disease_typo(self):
        result = preprocess("골다골증 때문에 힘들어요")
        assert "골다공증" in result["text"]

    def test_no_correction_needed(self):
        """오탈자 없으면 원문 유지"""
        result = preprocess("정형외과에 가고 싶어요")
        assert "정형외과" in result["text"]


# ══════════════════════════════════════════════════════════════════
# 3. 전처리 — 정규화
# ══════════════════════════════════════════════════════════════════

class TestNormalization:
    def test_whitespace(self):
        result = normalize("무릎이   너무   아파요")
        assert "  " not in result

    def test_strip(self):
        result = normalize("  무릎이 아파요  ")
        assert result == result.strip()

    def test_combined_pipeline(self):
        """간투어 + 오탈자 + 공백 동시 처리"""
        result = preprocess("어~ 무릅이  음  아파요  정형외가 가야 하나요")
        assert "무릎" in result["text"]
        assert "정형외과" in result["text"]
        assert "  " not in result["text"]


# ══════════════════════════════════════════════════════════════════
# 4. STT 정확도 평가 (evaluate_stt.py)
# ══════════════════════════════════════════════════════════════════

class TestEvaluateSTT:
    def test_perfect_match(self):
        wer = compute_wer("무릎이 아파요", "무릎이 아파요")
        cer = compute_cer("무릎이 아파요", "무릎이 아파요")
        assert wer == 0.0
        assert cer == 0.0

    def test_wer_one_word_error(self):
        wer = compute_wer("무릎이 아파요", "무릎이 좋아요")
        assert 0.0 < wer <= 1.0

    def test_cer_partial_error(self):
        cer = compute_cer("정형외과", "정형외가")
        assert 0.0 < cer < 1.0

    def test_batch_evaluation(self):
        refs  = ["무릎이 아파요", "가슴이 답답해요", "혈압약 먹어도 되나요"]
        hyps  = ["무릎이 아파요", "가슴이 아파요",   "혈압약 먹어도 되나요"]
        result = evaluate_batch(refs, hyps)
        assert result["samples"] == 3
        assert 0.0 <= result["wer"] <= 1.0
        assert 0.0 <= result["cer"] <= 1.0
        assert len(result["details"]) == 3

    def test_batch_perfect(self):
        refs  = ["무릎이 아파요", "정형외과"]
        hyps  = ["무릎이 아파요", "정형외과"]
        result = evaluate_batch(refs, hyps)
        assert result["wer"] == 0.0
        assert result["cer"] == 0.0

    def test_evaluate_report_runs(self, capsys):
        """print_report가 에러 없이 실행되는지 확인"""
        refs  = ["무릎이 아파요"]
        hyps  = ["무릎 아파요"]
        result = evaluate_batch(refs, hyps)
        print_report(result)
        captured = capsys.readouterr()
        assert "CER" in captured.out


# ══════════════════════════════════════════════════════════════════
# 5. STT 실제 파일 테스트 (Groq API 호출 — 네트워크 필요)
# ══════════════════════════════════════════════════════════════════

@pytest.mark.skipif(
    not os.path.exists(os.path.join(SAMPLES_DIR, "case1.mp3")),
    reason="샘플 오디오 파일 없음"
)
class TestSTTWithFiles:
    """실제 오디오 파일로 STT 결과 검증 (pytest -k stt 로 선택 실행)"""

    def _run(self, filename: str):
        from stt_module import transcribe
        path = os.path.join(SAMPLES_DIR, filename)
        result = transcribe(path)
        assert "text" in result
        assert "confidence" in result
        assert isinstance(result["text"], str)
        assert len(result["text"]) > 0
        return result

    def test_case1(self):
        result = self._run("case1.mp3")
        print(f"\n[case1] STT: {result['text']}")

    def test_case2(self):
        result = self._run("case2.mp3")
        print(f"\n[case2] STT: {result['text']}")

    def test_case3(self):
        result = self._run("case3.mp3")
        print(f"\n[case3] STT: {result['text']}")

    def test_case4(self):
        result = self._run("case4.mp3")
        print(f"\n[case4] STT: {result['text']}")


# ══════════════════════════════════════════════════════════════════
# 6. 파이프라인 통합 테스트 (파일 모드)
# ══════════════════════════════════════════════════════════════════

@pytest.mark.skipif(
    not os.path.exists(os.path.join(SAMPLES_DIR, "case1.mp3")),
    reason="샘플 오디오 파일 없음"
)
class TestPipelineIntegration:
    def test_run_with_file(self):
        from pipeline import run
        path = os.path.join(SAMPLES_DIR, "case1.mp3")
        result = run(audio_path=path, skip_vad=True)  # VAD 건너뜀으로 속도 향상
        assert "text" in result
        assert "raw_text" in result
        assert "confidence" in result
        assert "language" in result
        assert result["language"] == "ko"


# ══════════════════════════════════════════════════════════════════
# 직접 실행
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=== 전처리 단위 테스트 ===")
    r = preprocess("어~ 무릅이 음 아파요 정형외가 가야 하나요")
    print(f"  입력  : 어~ 무릅이 음 아파요 정형외가 가야 하나요")
    print(f"  결과  : {r['text']}")

    print("\n=== STT 평가 테스트 ===")
    refs = ["무릎이 아파요 정형외과에 가야 하나요", "가슴이 너무 아프고 숨이 안 쉬어져요"]
    hyps = ["무릅이 아파요 정형외가 가야 하나요",   "가슴이 너무 아프고 숨이 안 쉬어져요"]
    result = evaluate_batch(refs, hyps)
    print_report(result)
