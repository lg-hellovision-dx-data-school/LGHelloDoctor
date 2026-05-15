"""
노트북에 6개 분석 항목 셀 추가:
1. 다중턴 평가
2. 시니어 페르소나 평가
3. 라벨별 Precision/F1
4. Confusion Matrix Heatmap
5. 에러 분석
6. Few-shot prompting 비교

총 8개 섹션 (md + code) = 16 셀 삽입.
"""
import json
import uuid
from pathlib import Path

NB_PATH = Path(__file__).parent / "lg_hellodoctor_intent_finetune_fixed2.ipynb"

with NB_PATH.open("r", encoding="utf-8") as f:
    nb = json.load(f)

cells = nb["cells"]

# ============================================================================
# 섹션 17 — 추가 평가 데이터 로드
# ============================================================================
SEC17_MD = """## 17. 추가 평가 데이터 로드

시니어 페르소나(200개)와 다중턴 시나리오(50개, 176턴) 데이터를 로드합니다.
- valid/test와 동일 구조: 라벨당 40개 (시니어)
- 다중턴: 시나리오 자연스러움 우선 (emergency 비중 낮음)"""

SEC17_CODE = '''import json
from collections import Counter

# 시니어 페르소나 (200개)
senior_path = PROJECT_DIR / "medical_intent_senior_persona.json"
senior_df = pd.read_json(senior_path)

print(f"시니어 페르소나: {senior_df.shape}")
print("\\n[라벨 분포]")
print(senior_df["label"].value_counts().sort_index())

# 다중턴 시나리오
multiturn_path = PROJECT_DIR / "medical_intent_multiturn.json"
with multiturn_path.open("r", encoding="utf-8") as f:
    multiturn_scenarios = json.load(f)

total_turns = sum(len(s["turns"]) for s in multiturn_scenarios)
print(f"\\n다중턴 시나리오: {len(multiturn_scenarios)}개 / 총 {total_turns}턴")

print("\\n[다중턴 라벨 분포]")
all_turn_labels = [t["label"] for s in multiturn_scenarios for t in s["turns"]]
for lbl, cnt in sorted(Counter(all_turn_labels).items()):
    print(f"  {lbl}: {cnt}")

print("\\n[시나리오 타입]")
for stype, cnt in Counter(s["scenario_type"] for s in multiturn_scenarios).items():
    print(f"  {stype}: {cnt}")
'''

# ============================================================================
# 섹션 18 — 통합 추론 수집
# ============================================================================
SEC18_MD = """## 18. 추가 분석을 위한 추론 수집  (Baseline + r=16)

이후 모든 분석(Confusion Matrix, 에러 분석, 다중턴, 시니어, Few-shot)에 필요한 예측 결과를 한 번의 모델 로드로 수집합니다.
- **Baseline**: test/hard/senior + Few-shot prompting
- **r=16 LoRA**: test/hard/senior + 다중턴(history O/X 둘 다)"""

SEC18_CODE = '''import gc, torch
from unsloth import FastLanguageModel

eval_predictions = {}

# ── Few-shot 프롬프트 ──────────────────────────────────────────────────
FEW_SHOT_EXAMPLES = [
    ("머리가 아파요", "symptom_inquiry"),
    ("근처 정형외과 알려주세요", "hospital_search"),
    ("타이레놀 먹어도 되나요", "medication_inquiry"),
    ("119 불러야 하나요", "emergency"),
    ("안녕하세요", "general_chat"),
]

def build_messages_fewshot(text):
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    for ex_t, ex_l in FEW_SHOT_EXAMPLES:
        msgs.append({"role": "user", "content": f"사용자 발화: {ex_t}\\n의도 라벨:"})
        msgs.append({"role": "assistant", "content": ex_l})
    msgs.append({"role": "user", "content": f"사용자 발화: {text}\\n의도 라벨:"})
    return msgs

def llm_infer_fewshot(text, model, tokenizer):
    prompt = tokenizer.apply_chat_template(
        build_messages_fewshot(text), tokenize=False, add_generation_prompt=True)
    inputs = tokenizer([prompt], return_tensors="pt", truncation=True,
                        max_length=MAX_SEQ_LENGTH).to(model.device)
    out = model.generate(**inputs, max_new_tokens=10, do_sample=False,
                         pad_token_id=tokenizer.eos_token_id)
    gen = out[0][inputs["input_ids"].shape[-1]:]
    return tokenizer.decode(gen, skip_special_tokens=True).strip()

# ── 다중턴 ─────────────────────────────────────────────────────────────
def build_messages_multiturn(history, current_text):
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    for h in history:
        msgs.append({"role": "user", "content": f"사용자 발화: {h['text']}\\n의도 라벨:"})
        msgs.append({"role": "assistant", "content": h["label"]})
    msgs.append({"role": "user", "content": f"사용자 발화: {current_text}\\n의도 라벨:"})
    return msgs

def llm_infer_multiturn(history, current_text, model, tokenizer):
    prompt = tokenizer.apply_chat_template(
        build_messages_multiturn(history, current_text),
        tokenize=False, add_generation_prompt=True)
    inputs = tokenizer([prompt], return_tensors="pt", truncation=True,
                        max_length=MAX_SEQ_LENGTH).to(model.device)
    out = model.generate(**inputs, max_new_tokens=10, do_sample=False,
                         pad_token_id=tokenizer.eos_token_id)
    gen = out[0][inputs["input_ids"].shape[-1]:]
    return tokenizer.decode(gen, skip_special_tokens=True).strip()

def evaluate_multiturn(scenarios, model, tokenizer, use_history=True):
    rows = []
    for s in scenarios:
        history = []
        for i, t in enumerate(s["turns"]):
            if use_history:
                raw = llm_infer_multiturn(history, t["text"], model, tokenizer)
            else:
                raw = llm_infer(t["text"], model=model, tokenizer=tokenizer)
            pred = parse_label(raw)
            rows.append({
                "scenario_id": s["id"],
                "scenario_type": s["scenario_type"],
                "turn_idx": i,
                "text": t["text"],
                "gold": t["label"],
                "pred": pred,
                "raw": raw,
            })
            history.append({"text": t["text"], "label": t["label"]})
    return pd.DataFrame(rows)

# ════════════════════════════════════════════════════════════════════════
# 1. Baseline 모델 추론
# ════════════════════════════════════════════════════════════════════════
print("="*60)
print("  Baseline 추론 수집")
print("="*60)

base_model, base_tokenizer = FastLanguageModel.from_pretrained(
    model_name=MODEL_ID, max_seq_length=MAX_SEQ_LENGTH,
    dtype=None, load_in_4bit=LOAD_IN_4BIT,
)
FastLanguageModel.for_inference(base_model)

base_infer = lambda t: llm_infer(t, model=base_model, tokenizer=base_tokenizer)

_, eval_predictions["baseline_test"] = evaluate_model(
    base_infer, test_data, desc="Baseline TEST",
    use_keyword=False, show_errors=False)
_, eval_predictions["baseline_hard"] = evaluate_model(
    base_infer, hard_test_data, desc="Baseline HARD",
    use_keyword=False, show_errors=False)
_, eval_predictions["baseline_senior"] = evaluate_model(
    base_infer, senior_df, desc="Baseline SENIOR",
    use_keyword=False, show_errors=False)

# Few-shot
print("\\n[Few-shot prompting on test]")
fs_rows = []
for _, item in test_data.iterrows():
    raw = llm_infer_fewshot(item["text"], base_model, base_tokenizer)
    fs_rows.append({
        "text": item["text"], "gold": item["label"],
        "pred": parse_label(raw), "raw": raw,
    })
eval_predictions["baseline_fewshot_test"] = pd.DataFrame(fs_rows)
fs_m = compute_metrics(
    eval_predictions["baseline_fewshot_test"]["pred"].tolist(),
    eval_predictions["baseline_fewshot_test"]["gold"].tolist())
print(f"Few-shot Acc={fs_m['accuracy']:.4f} | Macro F1={fs_m['macro_f1']:.4f}")

del base_model, base_tokenizer, base_infer
gc.collect(); torch.cuda.empty_cache()
print("\\nBaseline 수집 완료\\n")

# ════════════════════════════════════════════════════════════════════════
# 2. r=16 LoRA 추론
# ════════════════════════════════════════════════════════════════════════
print("="*60)
print("  r=16 LoRA 추론 수집")
print("="*60)

r16_path = "/content/drive/MyDrive/LG_HelloDoctor_혼자_논문/intent_lora_rank16"
model_r16, tokenizer_r16 = FastLanguageModel.from_pretrained(
    model_name=r16_path, max_seq_length=MAX_SEQ_LENGTH,
    dtype=None, load_in_4bit=LOAD_IN_4BIT,
)
FastLanguageModel.for_inference(model_r16)
r16_infer = lambda t: llm_infer(t, model=model_r16, tokenizer=tokenizer_r16)

_, eval_predictions["r16_test"] = evaluate_model(
    r16_infer, test_data, desc="r16 TEST",
    use_keyword=False, show_errors=False)
_, eval_predictions["r16_hard"] = evaluate_model(
    r16_infer, hard_test_data, desc="r16 HARD",
    use_keyword=False, show_errors=False)
_, eval_predictions["r16_senior"] = evaluate_model(
    r16_infer, senior_df, desc="r16 SENIOR",
    use_keyword=False, show_errors=False)

# 다중턴: history O / X 둘 다
print("\\n[다중턴 평가 - history 사용]")
eval_predictions["r16_multiturn"] = evaluate_multiturn(
    multiturn_scenarios, model_r16, tokenizer_r16, use_history=True)
mt_m = compute_metrics(
    eval_predictions["r16_multiturn"]["pred"].tolist(),
    eval_predictions["r16_multiturn"]["gold"].tolist())
print(f"Multiturn Acc={mt_m['accuracy']:.4f} | Macro F1={mt_m['macro_f1']:.4f}")

print("\\n[다중턴 평가 - history 미사용 (단일턴)]")
eval_predictions["r16_multiturn_singleturn"] = evaluate_multiturn(
    multiturn_scenarios, model_r16, tokenizer_r16, use_history=False)
st_m = compute_metrics(
    eval_predictions["r16_multiturn_singleturn"]["pred"].tolist(),
    eval_predictions["r16_multiturn_singleturn"]["gold"].tolist())
print(f"Singleturn Acc={st_m['accuracy']:.4f} | Macro F1={st_m['macro_f1']:.4f}")

del model_r16, tokenizer_r16, r16_infer
gc.collect(); torch.cuda.empty_cache()
print("\\nr=16 수집 완료")

print("\\n[수집된 예측]")
for k, v in eval_predictions.items():
    print(f"  {k}: {len(v)} samples")
'''

# ============================================================================
# 섹션 19 — 라벨별 Precision/Recall/F1
# ============================================================================
SEC19_MD = """## 19. 라벨별 Precision / Recall / F1

5개 라벨 각각의 Precision, Recall, F1을 비교하여 trade-off를 분석합니다.
- **Recall만 보면 안 됨**: emergency_recall이 1.0이어도 precision이 낮으면 일반 증상을 응급으로 오분류 (False Alarm)"""

SEC19_CODE = '''def per_label_table(predictions_dict, focus=None):
    rows = []
    for name, df in predictions_dict.items():
        if focus and name not in focus:
            continue
        report = classification_report(
            df["gold"], df["pred"],
            labels=INTENT_LABELS, output_dict=True, zero_division=0,
        )
        for label in INTENT_LABELS:
            rows.append({
                "eval": name,
                "label": label,
                "precision": round(report[label]["precision"], 4),
                "recall":    round(report[label]["recall"], 4),
                "f1":        round(report[label]["f1-score"], 4),
                "support":   int(report[label]["support"]),
            })
    return pd.DataFrame(rows)

focus = ["baseline_test", "r16_test",
         "baseline_hard", "r16_hard",
         "baseline_senior", "r16_senior"]
table = per_label_table(eval_predictions, focus=focus)

print("[전체 P/R/F1 표]")
display(table)

# Pivot: F1
pivot_f1 = table.pivot(index="label", columns="eval", values="f1")[focus]
print("\\n[F1-score by label × eval]")
display(pivot_f1)

# Pivot: Precision (응급 오탐 분석용)
pivot_p = table.pivot(index="label", columns="eval", values="precision")[focus]
print("\\n[Precision by label × eval]")
display(pivot_p)

# CSV 저장
table.to_csv(
    "/content/drive/MyDrive/LG_HelloDoctor_혼자_논문/per_label_metrics.csv",
    index=False, encoding="utf-8-sig")
print("\\nSaved: per_label_metrics.csv")
'''

# ============================================================================
# 섹션 20 — Confusion Matrix Heatmap
# ============================================================================
SEC20_MD = """## 20. Confusion Matrix Heatmap

Baseline과 r=16의 오분류 패턴을 시각적으로 비교합니다.
TEST set + 시니어 페르소나 4개 그래프 비교."""

SEC20_CODE = '''import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os

# 한글 폰트 (Colab)
os.system("apt-get -qq -y install fonts-nanum > /dev/null 2>&1")
for fp in fm.findSystemFonts(fontpaths=["/usr/share/fonts/truetype/nanum"]):
    fm.fontManager.addfont(fp)
plt.rcParams["font.family"] = "NanumGothic"
plt.rcParams["axes.unicode_minus"] = False

def plot_cm(gold, pred, labels, title, ax):
    cm = confusion_matrix(gold, pred, labels=labels)
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=labels, yticklabels=labels,
                ax=ax, cbar=False, annot_kws={"size": 11})
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Gold")
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_xticklabels(ax.get_xticklabels(), rotation=30, ha="right")

fig, axes = plt.subplots(2, 2, figsize=(16, 13))

plot_cm(eval_predictions["baseline_test"]["gold"],
        eval_predictions["baseline_test"]["pred"],
        INTENT_LABELS, "Baseline — TEST", axes[0, 0])
plot_cm(eval_predictions["r16_test"]["gold"],
        eval_predictions["r16_test"]["pred"],
        INTENT_LABELS, "LoRA r=16 — TEST", axes[0, 1])
plot_cm(eval_predictions["baseline_senior"]["gold"],
        eval_predictions["baseline_senior"]["pred"],
        INTENT_LABELS, "Baseline — SENIOR PERSONA", axes[1, 0])
plot_cm(eval_predictions["r16_senior"]["gold"],
        eval_predictions["r16_senior"]["pred"],
        INTENT_LABELS, "LoRA r=16 — SENIOR PERSONA", axes[1, 1])

plt.tight_layout()
plt.savefig("/content/drive/MyDrive/LG_HelloDoctor_혼자_논문/confusion_matrix.png",
            dpi=150, bbox_inches="tight")
plt.show()
print("Saved: confusion_matrix.png")
'''

# ============================================================================
# 섹션 21 — 에러 분석
# ============================================================================
SEC21_MD = """## 21. 에러 패턴 분석

오분류 케이스를 모아 공통 패턴(어떤 라벨이 어떤 라벨로 오분류되는가)을 찾습니다."""

SEC21_CODE = '''def analyze_errors(df, name):
    errors = df[df["pred"] != df["gold"]]
    n_total, n_err = len(df), len(errors)
    print(f"\\n[{name}] 오분류 {n_err}/{n_total} ({n_err/n_total*100:.1f}%)")

    if n_err == 0:
        print("  → 오분류 없음")
        return errors

    pattern = errors.groupby(["gold", "pred"]).size().sort_values(ascending=False)
    print(f"  Top 오분류 패턴 (gold → pred):")
    for (g, p), cnt in pattern.head(5).items():
        sample = errors[(errors["gold"] == g) & (errors["pred"] == p)]["text"].iloc[0]
        print(f"    {g:20s} → {p:20s} ({cnt}건) | 예: \\"{sample}\\"")

    return errors

print("="*70)
err_b_test   = analyze_errors(eval_predictions["baseline_test"],   "Baseline TEST")
err_r16_test = analyze_errors(eval_predictions["r16_test"],        "r=16 TEST")
err_b_sr     = analyze_errors(eval_predictions["baseline_senior"], "Baseline SENIOR")
err_r16_sr   = analyze_errors(eval_predictions["r16_senior"],      "r=16 SENIOR")

# Baseline 오분류 → r=16 회복 케이스
print("\\n" + "="*70)
print("[Baseline 오분류 → r=16에서 회복된 케이스]")
b_test = eval_predictions["baseline_test"]
r_test = eval_predictions["r16_test"]
b_err_idx = set(b_test[b_test["pred"] != b_test["gold"]].index)
r_err_idx = set(r_test[r_test["pred"] != r_test["gold"]].index)
recovered = b_err_idx - r_err_idx
print(f"회복 케이스: {len(recovered)}/{len(b_err_idx)} 건")

if recovered:
    rec_df = b_test.loc[list(recovered)[:10]][["text", "gold", "pred"]]
    rec_df.columns = ["text", "gold", "baseline_pred"]
    print()
    display(rec_df)

# r=16에서도 남아있는 오분류
print("\\n[r=16에서도 남아있는 오분류 — 어려운 케이스]")
remaining = b_err_idx & r_err_idx
print(f"공통 오분류: {len(remaining)}건")
if remaining:
    rem_df = b_test.loc[list(remaining)[:10]][["text", "gold", "pred"]]
    rem_df.columns = ["text", "gold", "still_misclassified"]
    display(rem_df)
'''

# ============================================================================
# 섹션 22 — 다중턴 분석
# ============================================================================
SEC22_MD = """## 22. 다중턴 평가 결과

이전 턴 정보를 활용했을 때(Multi-turn)와 단일 발화만 사용했을 때(Single-turn)를 비교합니다.
- **history 사용**: 이전 턴들이 모델 입력에 포함됨
- **history 미사용**: 현재 턴 텍스트만 단독 분류"""

SEC22_CODE = '''mt_df = eval_predictions["r16_multiturn"]
st_df = eval_predictions["r16_multiturn_singleturn"]

mt_m = compute_metrics(mt_df["pred"].tolist(), mt_df["gold"].tolist())
st_m = compute_metrics(st_df["pred"].tolist(), st_df["gold"].tolist())

# 비교 표
keys = ["accuracy", "macro_f1"] + [f"{l}_recall" for l in INTENT_LABELS]
comp = pd.DataFrame({
    "metric": keys,
    "Single-turn (history X)": [round(st_m[k], 4) for k in keys],
    "Multi-turn (history O)":  [round(mt_m[k], 4) for k in keys],
    "Δ (Multi - Single)":      [round(mt_m[k] - st_m[k], 4) for k in keys],
})
print("[Single vs Multi-turn 비교]")
display(comp)

# 시나리오 타입별 정확도
mt_df = mt_df.copy()
mt_df["correct"] = (mt_df["pred"] == mt_df["gold"]).astype(int)
type_acc = (
    mt_df.groupby("scenario_type")
    .agg(n_turns=("correct", "size"), correct=("correct", "sum"))
    .assign(accuracy=lambda x: (x["correct"] / x["n_turns"]).round(4))
)
print("\\n[시나리오 타입별 Multi-turn 정확도]")
display(type_acc)

# 턴 위치별 정확도 (history 길이 영향)
turn_acc = (
    mt_df.groupby("turn_idx")
    .agg(n=("correct", "size"), correct=("correct", "sum"))
    .assign(accuracy=lambda x: (x["correct"] / x["n"]).round(4))
)
print("\\n[턴 위치별 정확도]")
display(turn_acc)

# 다중턴 오분류 사례
print("\\n[Multi-turn 오분류 사례]")
errs = mt_df[mt_df["pred"] != mt_df["gold"]]
if len(errs) > 0:
    show = errs[["scenario_id", "turn_idx", "text", "gold", "pred"]].head(10)
    display(show)
else:
    print("  → 오분류 없음")
'''

# ============================================================================
# 섹션 23 — 시니어 페르소나 분석
# ============================================================================
SEC23_MD = """## 23. 시니어 페르소나 평가 결과

방언/구어체/시니어 어조 발화에서의 성능을 표준 test set과 비교합니다.
- **target user**: 시니어 (어르신) 음성 서비스
- **확인 포인트**: test 정확도와 senior 정확도의 격차"""

SEC23_CODE = '''def to_row(name, m, keys):
    return {**{"eval": name}, **{k: round(m[k], 4) for k in keys}}

keys = ["accuracy", "macro_f1"] + [f"{l}_recall" for l in INTENT_LABELS]

senior_comp = pd.DataFrame([
    to_row("Baseline TEST",   compute_metrics(
        eval_predictions["baseline_test"]["pred"].tolist(),
        eval_predictions["baseline_test"]["gold"].tolist()), keys),
    to_row("Baseline SENIOR", compute_metrics(
        eval_predictions["baseline_senior"]["pred"].tolist(),
        eval_predictions["baseline_senior"]["gold"].tolist()), keys),
    to_row("r=16 TEST",       compute_metrics(
        eval_predictions["r16_test"]["pred"].tolist(),
        eval_predictions["r16_test"]["gold"].tolist()), keys),
    to_row("r=16 SENIOR",     compute_metrics(
        eval_predictions["r16_senior"]["pred"].tolist(),
        eval_predictions["r16_senior"]["gold"].tolist()), keys),
])
print("[Standard TEST vs SENIOR PERSONA]")
display(senior_comp)

# 격차 (도메인 갭)
print("\\n[도메인 갭 — TEST 대비 SENIOR 성능 변화]")
gap_rows = []
for k in keys:
    base_test = senior_comp.loc[senior_comp["eval"] == "Baseline TEST",   k].values[0]
    base_sr   = senior_comp.loc[senior_comp["eval"] == "Baseline SENIOR", k].values[0]
    r16_test  = senior_comp.loc[senior_comp["eval"] == "r=16 TEST",       k].values[0]
    r16_sr    = senior_comp.loc[senior_comp["eval"] == "r=16 SENIOR",     k].values[0]
    gap_rows.append({
        "metric":             k,
        "Baseline gap":       round(base_sr - base_test, 4),
        "r=16 gap":           round(r16_sr - r16_test, 4),
    })
display(pd.DataFrame(gap_rows))

# r=16 시니어 오분류 사례
print("\\n[r=16 시니어 오분류 사례 (최대 15개)]")
sr_err = eval_predictions["r16_senior"][
    eval_predictions["r16_senior"]["pred"] != eval_predictions["r16_senior"]["gold"]
]
if len(sr_err) > 0:
    display(sr_err[["text", "gold", "pred"]].head(15))
else:
    print("  → 오분류 없음")
'''

# ============================================================================
# 섹션 24 — Few-shot prompting 비교
# ============================================================================
SEC24_MD = """## 24. Few-shot Prompting vs LoRA 비교

베이스 모델에 5-shot 예시를 제공한 경우와 LoRA 학습 결과를 비교합니다.
- **Zero-shot** (Baseline): 예시 없음
- **Few-shot (5)**: 라벨당 1개씩 5개 예시 제공
- **LoRA r=16**: 1,600개 학습"""

SEC24_CODE = '''keys = ["accuracy", "macro_f1"] + [f"{l}_recall" for l in INTENT_LABELS]

zero_m = compute_metrics(
    eval_predictions["baseline_test"]["pred"].tolist(),
    eval_predictions["baseline_test"]["gold"].tolist())
fs_m = compute_metrics(
    eval_predictions["baseline_fewshot_test"]["pred"].tolist(),
    eval_predictions["baseline_fewshot_test"]["gold"].tolist())
r16_m = compute_metrics(
    eval_predictions["r16_test"]["pred"].tolist(),
    eval_predictions["r16_test"]["gold"].tolist())

fs_comp = pd.DataFrame([
    {"method": "Zero-shot",     **{k: round(zero_m[k], 4) for k in keys}},
    {"method": "Few-shot (5)",  **{k: round(fs_m[k], 4)   for k in keys}},
    {"method": "LoRA r=16",     **{k: round(r16_m[k], 4)  for k in keys}},
])
print("[Zero-shot / Few-shot / LoRA 비교]")
display(fs_comp)

# 변화 분석
print("\\n[Few-shot 효과 (Δ from Zero-shot)]")
for k in keys:
    delta = fs_m[k] - zero_m[k]
    sign = "+" if delta >= 0 else ""
    print(f"  {k:30s}: {sign}{delta:.4f}")

print("\\n[LoRA 효과 (Δ from Few-shot)]")
for k in keys:
    delta = r16_m[k] - fs_m[k]
    sign = "+" if delta >= 0 else ""
    print(f"  {k:30s}: {sign}{delta:.4f}")
'''

# ============================================================================
# 셀 빌더
# ============================================================================
def md(source):
    return {
        "cell_type": "markdown",
        "id": str(uuid.uuid4())[:8],
        "metadata": {},
        "source": source,
    }

def code(source):
    return {
        "cell_type": "code",
        "id": str(uuid.uuid4())[:8],
        "metadata": {},
        "source": source,
        "outputs": [],
        "execution_count": None,
    }

new_cells = [
    md(SEC17_MD), code(SEC17_CODE),
    md(SEC18_MD), code(SEC18_CODE),
    md(SEC19_MD), code(SEC19_CODE),
    md(SEC20_MD), code(SEC20_CODE),
    md(SEC21_MD), code(SEC21_CODE),
    md(SEC22_MD), code(SEC22_CODE),
    md(SEC23_MD), code(SEC23_CODE),
    md(SEC24_MD), code(SEC24_CODE),
]

# 마지막 발표 markdown 셀 앞에 삽입
# 현재 41 셀 → 마지막 [40] 발표 markdown
insert_idx = len(cells) - 1
for i, c in enumerate(new_cells):
    cells.insert(insert_idx + i, c)

print(f"기존 셀: {len(cells) - len(new_cells)} → 신규 셀: {len(cells)}")
print(f"삽입 위치: index {insert_idx}")

with NB_PATH.open("w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"\nSaved: {NB_PATH}")
print("\n[삽입된 섹션]")
for c in new_cells:
    src = "".join(c["source"]) if isinstance(c["source"], list) else c["source"]
    head = src.split("\n")[0][:70]
    print(f"  [{c['cell_type'][:4]}] {head}")
