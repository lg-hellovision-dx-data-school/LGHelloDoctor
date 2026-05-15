"""lg_hellodoctor_intent_finetune_fixed2.ipynb에 GGUF export + Ollama 등록 섹션 추가."""
import json
import sys
import uuid
from pathlib import Path

NB = Path(__file__).parent / "lg_hellodoctor_intent_finetune_fixed2.ipynb"

GGUF_MD = """## 26. GGUF Export → Ollama 등록

학습된 LoRA 어댑터(r=16, 99% 정확도)를 **GGUF 포맷으로 양자화**하여 Ollama에 등록합니다.
backend/main.py의 `INTENT_MODEL = \"hellodoctor-intent\"`가 이 모델을 호출합니다.

**파이프라인:**
1. Drive 저장 LoRA 어댑터 로드 (`intent_lora_rank16/`)
2. unsloth `save_pretrained_gguf` 로 q4_k_m 양자화 GGUF 생성
3. Ollama Modelfile 작성 → 로컬 PC에서 `ollama create`
4. backend/main.py 의 INTENT_MODEL 이름과 일치 확인

**비용:** Colab T4면 충분, 약 5~10분 소요"""

GGUF_CODE = '''# r=16 LoRA 어댑터를 GGUF로 양자화 export
import gc, torch
from unsloth import FastLanguageModel

DRIVE_DIR = "/content/drive/MyDrive/LG_HelloDoctor_혼자_논문"
LORA_PATH = f"{DRIVE_DIR}/intent_lora_rank16"
GGUF_OUTPUT_DIR = f"{DRIVE_DIR}/intent_gguf"

# 메모리 정리
gc.collect()
torch.cuda.empty_cache()

# LoRA 어댑터 로드 (이미 base + LoRA가 통합된 상태)
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=LORA_PATH,
    max_seq_length=MAX_SEQ_LENGTH,
    dtype=None,
    load_in_4bit=False,  # GGUF export는 fp16 필요
)

print("LoRA 어댑터 로드 완료. GGUF 양자화 시작…")
print("(약 5~10분 소요)")

# unsloth 내장 GGUF export
# quantization_method 옵션:
#   q4_k_m  (권장): 4-bit, K-quants medium — 균형
#   q5_k_m         5-bit, 더 정확하지만 약간 큼
#   q8_0           8-bit, 거의 fp16 품질 (큼)
model.save_pretrained_gguf(
    GGUF_OUTPUT_DIR,
    tokenizer,
    quantization_method="q4_k_m",
)

print(f"\\n✅ GGUF 저장 완료: {GGUF_OUTPUT_DIR}")
import os
for f in os.listdir(GGUF_OUTPUT_DIR):
    size_mb = os.path.getsize(os.path.join(GGUF_OUTPUT_DIR, f)) / 1024 / 1024
    print(f"  {f}: {size_mb:.1f} MB")

del model, tokenizer
gc.collect()
torch.cuda.empty_cache()'''

MODELFILE_MD = """### Ollama Modelfile 작성

GGUF 파일을 Ollama가 읽을 수 있도록 Modelfile을 만듭니다.
시스템 프롬프트는 노트북에서 학습에 사용한 SYSTEM_PROMPT와 동일하게 유지해야 합니다."""

MODELFILE_CODE = """# Ollama Modelfile 생성 (Drive에 같이 저장)
# Modelfile 안에 \\\"\\\"\\\" 가 그대로 들어가야 해서 Python triple-quote 충돌을 피하려고
# 라인 리스트 + replace 방식으로 작성한다.
import os
gguf_files = [f for f in os.listdir(GGUF_OUTPUT_DIR) if f.endswith(".gguf")]
gguf_name = gguf_files[0]

_MODELFILE_LINES = [
    '# LG HelloDoctor 의도 분류 Fine-tuned Model',
    '# Base: unsloth/gemma-3-4b-it',
    '# LoRA: r=16, alpha=32, 5라벨 의료 의도 분류',
    '# Test Accuracy: 99.0% (Macro F1: 0.9901)',
    '',
    'FROM ./__GGUF__',
    '',
    '# Gemma 3 chat template',
    'TEMPLATE \\"\\"\\"<start_of_turn>user',
    '{{ if .System }}{{ .System }}',
    '',
    '{{ end }}{{ .Prompt }}<end_of_turn>',
    '<start_of_turn>model',
    '{{ .Response }}<end_of_turn>\\"\\"\\"',
    '',
    'SYSTEM \\"\\"\\"__SYSTEM__\\"\\"\\"',
    '',
    '# 결정론적 추론 (분류는 sampling 불필요)',
    'PARAMETER temperature 0',
    'PARAMETER top_p 1.0',
    'PARAMETER num_predict 10',
    'PARAMETER stop \\"<end_of_turn>\\"',
    'PARAMETER stop \\"<start_of_turn>\\"',
]
modelfile_content = '\\n'.join(_MODELFILE_LINES)
modelfile_content = modelfile_content.replace('__GGUF__', gguf_name)
modelfile_content = modelfile_content.replace('__SYSTEM__', SYSTEM_PROMPT)

modelfile_path = f"{GGUF_OUTPUT_DIR}/Modelfile"
with open(modelfile_path, "w", encoding="utf-8") as f:
    f.write(modelfile_content)

print(f"✅ Modelfile 작성 완료: {modelfile_path}")
print()
print("=" * 60)
print("Modelfile 미리보기:")
print("=" * 60)
print(modelfile_content[:1000])"""

OLLAMA_INSTRUCTIONS_MD = """### Ollama 등록 (로컬 PC에서)

GGUF + Modelfile은 Drive에 저장됐습니다. 이제 **백엔드 서버 PC에서** Ollama에 등록합니다.

```bash
# 1. Ollama 설치 (이미 있으면 스킵)
#    macOS:    brew install ollama
#    Linux:    curl -fsSL https://ollama.com/install.sh | sh
#    Windows:  https://ollama.com/download

# 2. Ollama 서버 실행
ollama serve  # 별도 터미널

# 3. Drive에서 GGUF + Modelfile 다운로드
#    Drive: /content/drive/MyDrive/LG_HelloDoctor_혼자_논문/intent_gguf/
#    → 로컬: ~/models/intent_gguf/

# 4. 모델 등록 (Modelfile 위치에서 실행)
cd ~/models/intent_gguf
ollama create hellodoctor-intent -f Modelfile

# 5. 동작 확인
ollama run hellodoctor-intent "사용자 발화: 무릎이 아파요\\n의도 라벨:"
# → 출력: symptom_inquiry

# 6. 백엔드 재시작
cd /path/to/LGHelloDoctor
docker compose restart backend
```

### 백엔드와의 연결 확인

`backend/main.py`의 다음 두 줄이 GGUF 모델 이름과 일치하는지 확인:

```python
INTENT_MODEL = "hellodoctor-intent"           # ← Modelfile 등록명과 동일
OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
```

이미 일치하므로 추가 코드 변경은 불필요. **Ollama만 등록되면 노트북 fine-tune 결과가 실서비스에 반영됩니다.**

### 검증 체크리스트

- [ ] `ollama list` 결과에 `hellodoctor-intent` 포함
- [ ] `curl http://localhost:11434/api/tags` 가 모델 목록 반환
- [ ] 백엔드 로그에 `[B팀] 파인튜닝 모델 의도 분류: …` 출력 (폴백 메시지 X)
- [ ] 노트북 r=16 정확도(99%) 와 비슷한 의도 분류 결과"""

def md(s):
    return {
        "cell_type": "markdown",
        "id": str(uuid.uuid4())[:8],
        "metadata": {},
        "source": s,
    }

def code(s):
    return {
        "cell_type": "code",
        "id": str(uuid.uuid4())[:8],
        "metadata": {},
        "source": s,
        "outputs": [],
        "execution_count": None,
    }


def main():
    with NB.open("r", encoding="utf-8") as f:
        nb = json.load(f)
    cells = nb["cells"]
    print(f"기존 셀 수: {len(cells)}")

    new_cells = [
        md(GGUF_MD),
        code(GGUF_CODE),
        md(MODELFILE_MD),
        code(MODELFILE_CODE),
        md(OLLAMA_INSTRUCTIONS_MD),
    ]

    # 노트북 끝에 추가 (마지막 발표 markdown 뒤)
    cells.extend(new_cells)

    with NB.open("w", encoding="utf-8") as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)

    print(f"신규 셀 추가: +{len(new_cells)}")
    print(f"최종 셀 수: {len(cells)}")
    print("Done.")


if __name__ == "__main__":
    main()
