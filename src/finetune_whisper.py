"""
Whisper 노인 한국어 파인튜닝 스크립트
모델: openai/whisper-large-v3
방법: LoRA (PEFT)
"""
import os
import random
import torch
import argparse

BASE_MODEL    = "openai/whisper-large-v3"
LANGUAGE      = "Korean"
TASK          = "transcribe"
LORA_RANK     = 32   # 16 → 32: A100 여유 활용
LORA_ALPHA    = 64   # rank 2배 유지
LORA_DROPOUT  = 0.05
TRAIN_STEPS   = 1125  # 3000샘플 batch8 기준 3 epoch
BATCH_SIZE    = 8    # 1 → 8: A100(40GB) 최적화
LEARNING_RATE = 5e-5  # 1e-4 → 5e-5: 발산 방지


def load_processor_and_model():
    from transformers import WhisperProcessor, WhisperForConditionalGeneration
    from peft import LoraConfig, get_peft_model, TaskType

    processor = WhisperProcessor.from_pretrained(
        BASE_MODEL, language=LANGUAGE, task=TASK
    )

    model = WhisperForConditionalGeneration.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.float32,
    )

    model.generation_config.forced_decoder_ids = processor.get_decoder_prompt_ids(
        language=LANGUAGE, task=TASK
    )
    model.generation_config.suppress_tokens = []

    lora_cfg = LoraConfig(
        r=LORA_RANK,
        lora_alpha=LORA_ALPHA,
        target_modules=["q_proj", "v_proj"],
        lora_dropout=LORA_DROPOUT,
        bias="none",
        task_type=TaskType.SEQ_2_SEQ_LM,
    )
    model = get_peft_model(model, lora_cfg)
    model.enable_input_require_grads()
    model.print_trainable_parameters()
    return processor, model


def prepare_dataset(batch, processor):
    audio = batch["audio"]

    if hasattr(audio, "get_all_samples"):
        frames = audio.get_all_samples()
        audio_array = frames.data.mean(dim=0).numpy()
        sr = frames.sample_rate
    elif isinstance(audio, dict):
        audio_array = audio["array"]
        sr = audio["sampling_rate"]
    elif hasattr(audio, "array"):
        audio_array = audio.array
        sr = 16000
    else:
        import numpy as np
        audio_array = np.array(audio)
        sr = 16000

    batch["input_features"] = processor.feature_extractor(
        audio_array, sampling_rate=sr
    ).input_features[0]
    batch["labels"] = processor.tokenizer(batch["transcription"]).input_ids
    return batch


def make_data_collator(processor):
    def collate(features):
        input_features = [{"input_features": f["input_features"]} for f in features]
        batch = processor.feature_extractor.pad(input_features, return_tensors="pt")

        label_features = [{"input_ids": f["labels"]} for f in features]
        labels_batch = processor.tokenizer.pad(label_features, return_tensors="pt")
        labels = labels_batch["input_ids"].masked_fill(
            labels_batch.attention_mask.ne(1), -100
        )
        if (labels[:, 0] == processor.tokenizer.bos_token_id).all().cpu().item():
            labels = labels[:, 1:]
        batch["labels"] = labels
        return batch
    return collate


def train(args):
    import evaluate as hf_evaluate
    from datasets import load_from_disk, Audio
    from transformers import Seq2SeqTrainer, Seq2SeqTrainingArguments

    processor, model = load_processor_and_model()

    dataset = load_from_disk(args.data_dir)
    dataset = dataset.cast_column("audio", Audio(sampling_rate=16000))
    dataset = dataset.map(
        lambda b: prepare_dataset(b, processor),
        remove_columns=dataset["train"].column_names,
        num_proc=1,
    )

    random.seed(42)
    val_size = len(dataset["validation"])
    val_indices = random.sample(range(val_size), min(500, val_size))
    val_dataset = dataset["validation"].select(val_indices)
    print(f"validation 전체 {val_size}개 중 {len(val_indices)}개 랜덤 샘플링")

    cer_metric = hf_evaluate.load("cer")
    wer_metric = hf_evaluate.load("wer")

    def compute_metrics(pred):
        pred_ids  = pred.predictions
        label_ids = pred.label_ids
        label_ids[label_ids == -100] = processor.tokenizer.pad_token_id
        pred_str  = processor.tokenizer.batch_decode(pred_ids,  skip_special_tokens=True)
        label_str = processor.tokenizer.batch_decode(label_ids, skip_special_tokens=True)

        cer = cer_metric.compute(predictions=pred_str, references=label_str)
        wer = wer_metric.compute(predictions=pred_str, references=label_str)
        print(f"CER: {cer*100:.1f}%  WER: {wer*100:.1f}%")
        return {"cer": cer, "wer": wer}

    training_args = Seq2SeqTrainingArguments(
        output_dir=args.output_dir,
        per_device_train_batch_size=BATCH_SIZE,
        learning_rate=LEARNING_RATE,
        warmup_steps=50,
        max_steps=TRAIN_STEPS,
        gradient_accumulation_steps=1,  # batch 8로 충분
        gradient_checkpointing=False,   # A100은 불필요, 속도 회복
        fp16=False,
        bf16=True,                      # A100 네이티브 지원, 더 안정적
        eval_strategy="steps",
        eval_steps=100,
        save_steps=100,
        logging_steps=25,
        dataloader_num_workers=2,
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
        eval_dataset=val_dataset,
        data_collator=make_data_collator(processor),
        compute_metrics=compute_metrics,
        processing_class=processor.feature_extractor,
    )

    trainer.train()
    trainer.save_model(args.output_dir)
    processor.save_pretrained(args.output_dir)
    print(f"[파인튜닝 완료] 저장: {args.output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir",   default="./data/processed")
    parser.add_argument("--output_dir", default="./models/whisper-ko-elderly")
    train(parser.parse_args())