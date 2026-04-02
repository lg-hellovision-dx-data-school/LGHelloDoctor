# ============================================================
# LGHelloDoctor — Whisper 노인 한국어 파인튜닝 (Colab 실행용)
# Untitled0.ipynb 에 셀별로 복붙하세요
# ============================================================

# ── Cell 1: Drive 마운트 ──────────────────────────────────
from google.colab import drive
drive.mount('/content/drive')

# ── Cell 2: 패키지 설치 ──────────────────────────────────
# (한 번만 실행하면 됨)
import subprocess
subprocess.run([
    "pip", "install", "-q",
    "transformers", "datasets", "peft",
    "evaluate", "jiwer", "accelerate",
    "librosa", "soundfile"
])

# ── Cell 3: 레포 클론 ────────────────────────────────────
import subprocess, os
if not os.path.exists('/content/LGHelloDoctor'):
    subprocess.run([
        "git", "clone", "-b", "stt",
        "https://github.com/lg-hellovision-dx-data-school/LGHelloDoctor.git",
        "/content/LGHelloDoctor"
    ])
os.chdir('/content/LGHelloDoctor')
print("현재 경로:", os.getcwd())

# ── Cell 4: GPU 확인 ─────────────────────────────────────
import torch
print("GPU:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "없음 — 런타임 > 런타임 유형 변경 > T4 GPU 선택")

# ── Cell 5: 경로 설정 ────────────────────────────────────
RAW_DIR    = '/content/drive/MyDrive/LGHelloVision_튜닝/자유대화 음성(노인남녀)'
DATA_DIR   = '/content/drive/MyDrive/LGHelloVision_튜닝/data/processed'
OUTPUT_DIR = '/content/drive/MyDrive/LGHelloVision_튜닝/models/whisper-ko-elderly'

os.makedirs(DATA_DIR,   exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
print("원본:", RAW_DIR)
print("가공:", DATA_DIR)
print("모델:", OUTPUT_DIR)

# ── Cell 6: 데이터 가공 ──────────────────────────────────
# (이미 가공된 DATA_DIR 있으면 스킵 가능)
import sys
sys.path.insert(0, '/content/LGHelloDoctor/src')
from data_prep import build_dataset
build_dataset(RAW_DIR, DATA_DIR)

# ── Cell 7: 파인튜닝 실행 ─────────────────────────────────
import argparse
from finetune_whisper import train

class Args:
    data_dir   = DATA_DIR
    output_dir = OUTPUT_DIR

train(Args())
print("파인튜닝 완료! 모델 저장:", OUTPUT_DIR)
