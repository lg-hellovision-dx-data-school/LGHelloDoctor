"""
Whisper 노인 한국어 파인튜닝 스크립트 (프레임워크)
모델: openai/whisper-large-v3
방법: LoRA (PEFT) — GPU 메모리 효율화
데이터: data_prep.py로 전처리된 HuggingFace Dataset

실행:
    python finetune_whisper.py \
        --data_dir  ./data/processed \
        --output_dir ./models/whisper-ko-elderly

의존 패키지 (GPU 환경에서 설치):
    pip install peft datasets evaluate openai-whisper
"""
import argparse
import os

BASE_MODEL   = "openai/whisper-large-v3"
LANGUAGE     = "Korean"
TASK         = "transcribe"
LORA_RANK    = 32
LORA_ALPHA   = 64
LORA_DROPOUT = 0.05
TRAIN_STEPS  = 2000
BATCH_SIZE   = 8
LEARNING_RATE = 1e-4


def load_processor_and_model(output_dir: str):
    """Whisper 프로세서 + LoRA 래핑 모델 반환"""
    import torch
    from transformers import WhisperProcessor, WhisperForConditionalGeneration
    from peft import LoraConfig, get_peft_model, TaskType

    processor = WhisperProcessor.from_pretrained(
        BASE_MODEL, language=LANGUAGE, task=TASK
    )

    model = WhisperForConditionalGeneration.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    )
    model.config.forced_decoder_ids = processor.get_decoder_prompt_ids(
        language=LANGUAGE, task=TASK
    )
    model.config.suppress_tokens = []

    lora_cfg = LoraConfig(
        r=LORA_RANK,
        lora_alpha=LORA_ALPHA,
        target_modules=["q_proj", "v_proj"],
        lora_dropout=LORA_DROPOUT,
        bias="none",
        task_type=TaskType.SEQ_2_SEQ_LM,
    )
    model = get_peft_model(model, lora_cfg)
    model.print_trainable_parameters()
    return processor, model


def prepare_dataset(batch, processor):
    """오디오 → 입력 피처 + 레이블 변환"""
    audio = batch["audio"]
    batch["input_features"] = processor.feature_extractor(
        audio["array"], sampling_rate=audio["sampling_rate"]
    ).input_features[0]
    batch["labels"] = processor.tokenizer(batch["transcription"]).input_ids
    return batch


def make_data_collator(processor):
    """배치 패딩 처리 클로저"""
    import torch

    def collate(features):
        input_features = [{"input_features": f["input_features"]} for f in features]
        batch = processor.feature_extractor.pad(input_features, return_tensors="pt")

        label_features = [{"input_ids": f["labels"]} for f in features]
        labels_batch   = processor.tokenizer.pad(label_features, return_tensors="pt")
        labels = labels_batch["input_ids"].masked_fill(
            labels_batch.attention_mask.ne(1), -100
        )
        if (labels[:, 0] == processor.tokenizer.bos_token_id).all().cpu().item():
            labels = labels[:, 1:]
        batch["labels"] = labels
        return batch

    return collate


def train(args):
    import torch
    import evaluate as hf_evaluate
    from datasets import load_from_disk, Audio
    from transformers import Seq2SeqTrainer, Seq2SeqTrainingArguments

    processor, model = load_processor_and_model(args.output_dir)

    dataset = load_from_disk(args.data_dir)
    dataset = dataset.cast_column("audio", Audio(sampling_rate=16000))
    dataset = dataset.map(
        lambda b: prepare_dataset(b, processor),
        remove_columns=dataset["train"].column_names,
        num_proc=1,
    )

    metric = hf_evaluate.load("cer")

    def compute_metrics(pred):
        pred_ids  = pred.predictions
        label_ids = pred.label_ids
        label_ids[label_ids == -100] = processor.tokenizer.pad_token_id
        pred_str  = processor.tokenizer.batch_decode(pred_ids,  skip_special_tokens=True)
        label_str = processor.tokenizer.batch_decode(label_ids, skip_special_tokens=True)
        return {"cer": metric.compute(predictions=pred_str, references=label_str)}

    training_args = Seq2SeqTrainingArguments(
        output_dir=args.output_dir,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=2,
        learning_rate=LEARNING_RATE,
        warmup_steps=100,
        max_steps=TRAIN_STEPS,
        gradient_checkpointing=True,
        fp16=torch.cuda.is_available(),
        eval_strategy="steps",
        eval_steps=500,
        save_steps=500,
        logging_steps=50,
        predict_with_generate=True,
        generation_max_length=225,
        load_best_model_at_end=True,
        metric_for_best_model="cer",
        greater_is_better=False,
        push_to_hub=False,
        report_to="none",
    )

    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset["train"],
        eval_dataset=dataset["validation"],
        data_collator=make_data_collator(processor),
        compute_metrics=compute_metrics,
        tokenizer=processor.feature_extractor,
    )

    trainer.train()
    trainer.save_model(args.output_dir)
    processor.save_pretrained(args.output_dir)
    print(f"[파인튜닝 완료] 저장: {args.output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Whisper 노인 한국어 LoRA 파인튜닝")
    parser.add_argument("--data_dir",   default="./data/processed",          help="전처리 데이터셋 경로")
    parser.add_argument("--output_dir", default="./models/whisper-ko-elderly", help="모델 저장 경로")
    train(parser.parse_args())
