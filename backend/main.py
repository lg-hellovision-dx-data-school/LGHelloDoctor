import os
import json
import re
import gc
import tempfile
import torch
import librosa
import soundfile as sf
import numpy as np
import chromadb
import requests
from collections import defaultdict
from sentence_transformers import SentenceTransformer, CrossEncoder
from rank_bm25 import BM25Okapi
from numpy import dot
from numpy.linalg import norm
from transformers import WhisperForConditionalGeneration, WhisperProcessor
from langchain_groq import ChatGroq
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
from langsmith import traceable

load_dotenv()

# ====== 환경 변수 ======
KAKAO_API_KEY     = os.environ.get('KAKAO_API_KEY', '')
GROQ_API_KEY      = os.environ.get('GROQ_API_KEY', '')
# 한국어 fine-tuned whisper-small (244M).
# - openai/whisper-small 대비 한국어 WER 30~40% 개선, 동일 크기·속도
# - 시니어 발화/방언/의료 용어 인식률 향상
# - 환경변수로 override 가능 (예: WHISPER_MODEL_PATH=openai/whisper-small)
WHISPER_MODEL_PATH = os.environ.get('WHISPER_MODEL_PATH', 'SungBeom/whisper-small-ko')
DB_PATH           = os.environ.get('DB_PATH', '/app/RAG/db')

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"[Init] device: {DEVICE}")

# ====== LLM (Groq) — 엔티티 추출 · 답변 생성 ======
llm = ChatGroq(
    temperature=0,
    model_name="llama-3.3-70b-versatile",
    groq_api_key=GROQ_API_KEY,
)
print("[Init] Groq LLM 연결 완료")

# ====== 파인튜닝 LLM (Ollama) ======
# 의도 분류(B팀)와 답변 생성(D팀)을 별도 LoRA 모델로 분리해 각자 특화시킨다.
# 등록은 Ollama Modelfile 로:
#   ollama create hellodoctor-intent -f Modelfile  (intent_finetune 노트북 산출물)
#   ollama create hellodoctor-answer -f Modelfile  (answer_finetune 노트북 산출물)
OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
INTENT_MODEL = os.environ.get('INTENT_MODEL', 'hellodoctor-intent')
ANSWER_MODEL = os.environ.get('ANSWER_MODEL', 'hellodoctor-answer')
print(f"[Init] 파인튜닝 의도 분류 모델: {INTENT_MODEL} ({OLLAMA_URL})")
print(f"[Init] 파인튜닝 답변 생성 모델: {ANSWER_MODEL} ({OLLAMA_URL})")

# ====== STT (Whisper) ======
print(f"[Init] Whisper 모델 로드 중: {WHISPER_MODEL_PATH}")
stt_model = WhisperForConditionalGeneration.from_pretrained(WHISPER_MODEL_PATH).to(DEVICE).float()
stt_processor = WhisperProcessor.from_pretrained(WHISPER_MODEL_PATH)
print("[Init] Whisper 로드 완료")

# ====== VAD (Silero) ======
gc.collect()
if DEVICE == "cuda":
    torch.cuda.empty_cache()

vad_model, vad_utils = torch.hub.load(
    repo_or_dir="snakers4/silero-vad",
    model="silero_vad",
    force_reload=False,
    trust_repo=True,
)
(get_speech_timestamps, *_) = vad_utils
print("[Init] Silero VAD 로드 완료")

# ====== ChromaDB + Sentence Transformers ======
os.makedirs(DB_PATH, exist_ok=True)
embed_model = SentenceTransformer("jhgan/ko-sroberta-multitask")
chroma_client = chromadb.PersistentClient(path=DB_PATH)
collection = chroma_client.get_or_create_collection(
    "medical_knowledge",
    metadata={"hnsw:space": "cosine"},
)
print(f"[Init] ChromaDB 문서 수: {collection.count()}")

# ====== Hybrid RAG v2 — BM25 + CrossEncoder 초기화 ======
# rag_evaluation 노트북 ablation 결과 (Full Pipeline) 기반:
#   Vector only  → recall@3 = 0.74, MRR = 0.72
#   v2 (this)    → recall@3 = 0.85, MRR = 0.86  (+15%)
print("[Init] Hybrid RAG (BM25 + Cross-Encoder Reranker) 초기화 중...")
_all_data = collection.get(include=["documents", "metadatas"])
corpus_doc_ids = list(_all_data["ids"])
corpus_texts   = list(_all_data["documents"])
corpus_meta    = list(_all_data["metadatas"] or [{} for _ in corpus_doc_ids])

def _bm25_tok(t: str):
    return [tok for tok in re.findall(r"[가-힣]+|[a-zA-Z0-9]+", t) if len(tok) >= 2]

bm25 = BM25Okapi([_bm25_tok(t) for t in corpus_texts]) if corpus_texts else None
reranker = CrossEncoder("Dongjin-kr/ko-reranker", max_length=512)
print(f"[Init] BM25 corpus={len(corpus_texts)}개, Reranker(ko-reranker) 로드 완료")

# ====== 상수 ======
SAMPLE_RATE = 16000
WAKE_WORDS  = ['헬로비야', '헬로비이', '헬로 비', '헬로비']
FILLER_PATTERN = re.compile(r'(?<!\w)(어+~*|음+~*|에+~*|그+~*|뭐+~*|저+~*|아+~*)(?=\s|$)(?!\w)')

# ─────────────────────────────────────────────────────────────────────────────
# MEDICAL_CORRECTIONS — STT 오인식 보정 사전 (진료과명·증상·약물·검사명·질병명)
#
# 🧑‍⚕️ HITL 1차 책임자: 의사 (일반의)
# 📅 검수 주기: 분기 1회 + STT 정확도 회귀 발견 시
# 🔁 추가/수정 절차:
#   1. STT 로그에서 신규 오인식 패턴 발견
#   2. 의사 자문 → 보정 후보 검증 (의학적 정확성)
#   3. PR → tests/test_ai_model.py::test_진료과명_보정 케이스 추가
#   4. /test 통과 → 머지
# 📋 변경 이력: CHANGELOG 또는 git blame 으로 추적
# ─────────────────────────────────────────────────────────────────────────────
MEDICAL_CORRECTIONS = {
    "정형외가": "정형외과", "정형외꽈": "정형외과", "정형외와": "정형외과", "정영외과": "정형외과",
    "이비인후가": "이비인후과", "이비인호과": "이비인후과", "이비인우과": "이비인후과",
    "소화기가": "소화기내과", "피부가": "피부과", "피부부가": "피부과", "안과가": "안과",
    "내과가": "내과", "신경가": "신경과", "신경내가": "신경내과", "산부인가": "산부인과",
    "흉부외가": "흉부외과", "비뇨기가": "비뇨의학과", "재활의학가": "재활의학과", "가정의학가": "가정의학과",
    "무릅": "무릎", "어꺠": "어깨", "머리아포": "두통", "배아포": "복통", "울렁거려": "구역질",
    "체했어": "소화불량", "소화안돼": "소화불량", "오심이": "오심", "구통이": "구토",
    "기침이": "기침", "가래가": "가래", "콧물나": "콧물", "숨차": "호흡곤란", "붓기": "부종",
    "쑤셔": "통증", "결려": "통증", "욱신거려": "통증", "띵해": "두통", "가슴답답": "흉통",
    "혈압야": "혈압약", "혈압아": "혈압약", "혈압박": "혈압약", "당뇨야": "당뇨약", "당뇨약이": "당뇨약",
    "감기야": "감기약", "감기박": "감기약", "수면야": "수면약", "타이래놀": "타이레놀",
    "진통제가": "진통제", "소염제가": "소염제", "항생제가": "항생제",
    "엑스레이": "X-ray", "엑스래이": "X-ray", "엠알아이": "MRI", "씨티": "CT",
    "피검사": "혈액검사", "혈액검사가": "혈액검사", "소변검사가": "소변검사", "초음파가": "초음파",
    "고혈암": "고혈압", "당뇨병이": "당뇨병", "골다골증": "골다공증", "관절염이": "관절염",
    "치매가": "치매", "뇌경색이": "뇌경색", "뇌출혈이": "뇌출혈", "심근경새": "심근경색", "심근경섹": "심근경색",
}

# ─────────────────────────────────────────────────────────────────────────────
# EMERGENCY_KEYWORDS — 응급 발화 트리거 (즉시 119 안내 분기)
#
# 🚨 HITL 1차 책임자: 의사 (응급의학)
# 📅 검수 주기: 분기 1회 + 인명 사고/누락 사례 발생 시 즉시
# ⚠️ 위반 시 영향: 인명 사고 — 가장 엄격한 검수 영역
# 🔁 추가/수정 절차:
#   1. 응급의학과 자문 (FAST 기준, golden time, triage 분류)
#   2. tests/test_ai_model.py::EMERGENCY_CASES 에 케이스 추가
#   3. test_응급_키워드_100퍼센트_감지 통과 필수
#   4. /validate 7항목 체크 후 머지
# 📋 회귀 차단: 100% 감지율 — 한 건이라도 누락되면 머지 X
# ─────────────────────────────────────────────────────────────────────────────
EMERGENCY_KEYWORDS = [
    '숨이 안 쉬어', '가슴이 너무 아프', '의식이 없', '쓰러', '피를 토',
    '말이 어눌', '입이 돌아', '한쪽이 마비', '갑자기 안 보여',
]

FOLLOWUP_QUESTIONS = {
    '무릎': '무릎이 많이 아프시군요. 혹시 걷기가 많이 힘드신가요?',
    '허리': '허리가 아프시군요. 혹시 허리를 펴거나 숙이기가 어려우신가요?',
    '어깨': '어깨가 불편하시군요. 팔을 위로 올리기가 힘드신 상태인가요?',
    '머리': '머리가 아프시군요. 갑자기 핑 돌거나 망치로 맞은 듯이 아픈가요?',
    '배': '배가 아프시군요. 속이 메스껍거나 콕콕 찌르는 느낌이 드세요?',
    '가슴': '가슴이 답답하시군요. 숨을 쉬기가 벅차거나 조이는 느낌인가요?',
}

QUERY_REWRITE_MAP = {
    "무릎": "무릎통증 정형외과 관련 증상 치료 방법",
    "허리": "허리디스크 정형외과 척추 관련 증상 치료",
    "어깨": "어깨통증 정형외과 회전근개 관련 증상 치료",
    "머리": "두통이나 어지럼증 관련 증상 치료",
    "배": "복통 소화 소화기로 소화기내과 관련",
    "가래": "기침가래 폐 기관지 관련 증상 치료",
    "비뇨의학과": "비뇨의학과 관련 증상 전문 의원",
    "산부인과": "산부인과 관련 증상 전문 의원",
}

SYMPTOM_DEPT_MAP = {
    "무릎": ("정형외과", "05"),
    "허리": ("정형외과", "05"),
    "어깨": ("정형외과", "05"),
    "눈": ("안과", "12"),
    "귀": ("이비인후과", "13"),
    "코": ("이비인후과", "13"),
    "피부": ("피부과", "14"),
    "산부": ("산부인과", "15"),
    "머리": ("신경과", "02"),
    "가래": ("호흡기내과", "01"),
    "배": ("소화기내과", "01"),
    "가슴": ("내과", "01"),
}

# ─────────────────────────────────────────────────────────────────────────────
# EMERGENCY_SCORES — 응급도 가중치 (0~100, 분기 임계값 결정용)
#
# 🚨 HITL 1차 책임자: 의사 (응급의학) — EMERGENCY_KEYWORDS 와 동일 책임자
# 📅 검수 주기: 분기 1회 + 사고 시
# 💡 점수 의미: ≥80 즉시 119 / 60~79 강한 권고 / <60 일반 RAG 흐름
# ⚠️ 점수 조정 시 임계값 재실험 + 회귀 테스트 필수
# ─────────────────────────────────────────────────────────────────────────────
EMERGENCY_SCORES = {
    "숨이 안 쉬어": 100, "의식이 없": 100, "피를 토": 90,
    "가슴이 너무 아파": 90, "가슴통증이 심해": 90, "쓰러": 85,
    "쓰러졌": 80, "혈압이 200": 80, "혈압약을": 30, "혈압이 높아": 40,
}

# ─────────────────────────────────────────────────────────────────────────────
# FORBIDDEN_WORDS — 의료법 위반 가능 어휘 차단 (단정적 진단·처방 금지)
#
# ⚖️ HITL 1차 책임자: 법률·컴플라이언스
# 📅 검수 주기: 의료법 개정 시 + 분기 1회
# 📜 근거: 의료법 제27조 (무면허 의료행위 금지), 의료광고법
# 🔁 추가/삭제 절차:
#   1. 법률 자문 → 의료법·의료광고법 위반 가능성 검토
#   2. 의사 자문 (보조) → 임상적 단정성 판단
#   3. PR → tests/test_ai_model.py::test_핵심_금지어_포함, test_금지어_필터링 통과
#   4. /test → /validate → 머지
# ⚠️ 절대 금지: 단정성 완화 핑계로 임의 삭제 (예: "AI가 답변 못 함" → 삭제 금지)
# 📋 최소 10개 유지 — test_금지어_개수 가 강제
# ─────────────────────────────────────────────────────────────────────────────
FORBIDDEN_WORDS = ['예후', '처방전', '투약', '병변', '진단', '확정', '완치', '확신', '치료', '부작용']

conversation_state: dict = {}


# ====== A팀: STT 파이프라인 ======

def remove_silence(audio_path: str) -> str:
    audio, _ = librosa.load(audio_path, sr=SAMPLE_RATE, mono=True)
    wav = torch.from_numpy(audio)
    speech_timestamps = get_speech_timestamps(wav, vad_model, sampling_rate=SAMPLE_RATE, threshold=0.4)
    if not speech_timestamps:
        return audio_path
    speech_audio = torch.cat([wav[ts["start"]:ts["end"]] for ts in speech_timestamps])
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    sf.write(tmp.name, speech_audio.numpy(), SAMPLE_RATE)
    return tmp.name


def preprocess_text(raw_text: str) -> str:
    text = raw_text
    for ww in WAKE_WORDS:
        text = text.replace(ww, '')
    text = re.sub(r'^[야아아]+\s*', '', text).strip()
    text = FILLER_PATTERN.sub('', text).strip()
    for wrong, correct in MEDICAL_CORRECTIONS.items():
        text = text.replace(wrong, correct)
    words = text.split()
    deduped = [w for i, w in enumerate(words) if i == 0 or w != words[i - 1]]
    text = ' '.join(deduped)
    return re.sub(r'\s+', ' ', text).strip()


def stt_pipeline(audio_path: str = None, raw_text: str = None, confidence: float = 0.94) -> dict:
    if audio_path:
        clean_audio_path = remove_silence(audio_path)
        audio_array, _ = librosa.load(clean_audio_path, sr=16000)
        input_features = stt_processor(
            audio_array, sampling_rate=16000, return_tensors="pt"
        ).input_features.to(DEVICE)
        predicted_ids = stt_model.generate(input_features)
        raw_text = stt_processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
        confidence = 0.90
    clean_text = preprocess_text(raw_text)
    return {'text': clean_text, 'raw_text': raw_text, 'confidence': confidence, 'language': 'ko'}


# ====== B팀: 의도 분류 & 다중턴 ======

@traceable(name="B팀-의도분류-LLaMA3.2")
def classify_intent(text: str) -> dict:
    clean_text = text.strip().replace(" ", "")
    if any(kw.replace(" ", "") in clean_text for kw in EMERGENCY_KEYWORDS):
        return {'intent': 'emergency', 'confidence': 1.0}

    intent_prompt = (
        f"### 지시:\n"
        f"다음 문장의 의도를 아래 4가지 중 하나로만 답하세요.\n"
        f"symptom_inquiry / hospital_search / medication_info / emergency\n\n"
        f"문장: '{text}'\n\n"
        f"### 응답:\n"
    )
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": INTENT_MODEL, "prompt": intent_prompt, "stream": False,
                  "options": {"temperature": 0, "num_predict": 30}},
            timeout=30,
        )
        ans = resp.json().get("response", "").lower().strip()
        for target in ['emergency', 'medication_info', 'hospital_search', 'symptom_inquiry']:
            if target in ans:
                print(f"[B팀] 파인튜닝 모델 의도 분류: {target}")
                return {'intent': target, 'confidence': 0.90}
        raise ValueError(f"파인튜닝 모델 유효 레이블 없음: {ans}")
    except Exception as e:
        print(f"[B팀] 파인튜닝 모델 실패, Groq 폴백: {e}")

    try:
        prompt = (
            f"문장: '{text}'\n"
            "위 문장의 의도를 다음 4개 중 하나로만 대답하세요: "
            "[symptom_inquiry, hospital_search, medication_info, emergency]"
        )
        ans = llm.invoke(prompt).content.lower()
        for target in ['emergency', 'medication_info', 'hospital_search', 'symptom_inquiry']:
            if target in ans:
                return {'intent': target, 'confidence': 0.95}
        return {'intent': 'symptom_inquiry', 'confidence': 0.70}
    except Exception as e:
        print(f"[Error] classify_intent Groq: {e}")
        return {'intent': 'symptom_inquiry', 'confidence': 0.50}


def extract_entities(text: str) -> dict:
    try:
        prompt = (
            f"문장: '{text}'\n"
            '증상과 신체부위를 JSON 형식으로만 추출하세요. 예: {"symptom": "통증", "body_part": "무릎"}'
        )
        ans = llm.invoke(prompt).content
        match = re.search(r'\{.*?\}', ans, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {'symptom': None, 'body_part': None}
    except Exception:
        return {'symptom': None, 'body_part': None}


def chat_with_followup(user_input: str, session_id: str = 'default') -> dict:
    global conversation_state
    if session_id not in conversation_state:
        conversation_state[session_id] = {'step': 1, 'body_part': None}
    state = conversation_state[session_id]

    intent_res = classify_intent(user_input)

    if intent_res['intent'] == 'emergency':
        conversation_state[session_id] = {'step': 1, 'body_part': None}
        return {
            'answer': '어이구 어르신, 지금 많이 위험하실 수 있어요! 바로 119에 전화하시는 게 좋겠어요.',
            'intent': 'emergency',
            'ready_for_c': True,
            'output_for_c': {'intent': 'emergency', 'entities': {}, 'query': user_input, 'confidence': 0.99},
        }

    if intent_res['intent'] in ['medication_info', 'hospital_search']:
        entities = extract_entities(user_input)
        return {
            'answer': None,
            'intent': intent_res['intent'],
            'ready_for_c': True,
            'output_for_c': {'intent': intent_res['intent'], 'entities': entities, 'query': user_input, 'confidence': 0.90},
        }

    # symptom_inquiry — 다중턴
    if state['step'] == 1:
        for part, question in FOLLOWUP_QUESTIONS.items():
            if part in user_input:
                state['body_part'] = part
                state['step'] = 2
                return {'answer': question, 'intent': 'symptom_inquiry', 'ready_for_c': False, 'output_for_c': None}
        entities = extract_entities(user_input)
        return {
            'answer': None,
            'intent': 'symptom_inquiry',
            'ready_for_c': True,
            'output_for_c': {'intent': 'symptom_inquiry', 'entities': entities, 'query': user_input, 'confidence': 0.85},
        }

    if state['step'] == 2:
        body_part = state['body_part']
        conversation_state[session_id] = {'step': 1, 'body_part': None}
        entities = {'symptom': f"{body_part} 통증 및 {user_input}", 'body_part': body_part}
        return {
            'answer': None,
            'intent': 'symptom_inquiry',
            'ready_for_c': True,
            'output_for_c': {
                'intent': 'symptom_inquiry',
                'entities': entities,
                'query': f"{body_part} 아픔. {user_input}",
                'confidence': 0.91,
            },
        }

    # fallback
    entities = extract_entities(user_input)
    return {
        'answer': None,
        'intent': intent_res['intent'],
        'ready_for_c': True,
        'output_for_c': {'intent': intent_res['intent'], 'entities': entities, 'query': user_input},
    }


# ====== C팀: RAG & 병원 검색 & 응급 판단 ======

def query_rewrite(query: str) -> str:
    for kw, rewritten in QUERY_REWRITE_MAP.items():
        if kw in query:
            return rewritten
    return query


def full_rag_pipeline(query: str) -> dict:
    """Hybrid RAG v2: Vector + BM25 → RRF fusion → CrossEncoder rerank → confidence threshold.

    Returns:
        dict with `context` (str) and `sources` (list of {doc_id, score, source}).
        rag_evaluation 노트북 ablation 검증치: recall@3=0.85, MRR=0.86 (+15% vs Vector only).
    """
    NO_INFO = "관련된 전문적인 의학 정보를 찾지 못했습니다. 일반적인 의료 권고를 따르세요."
    if collection.count() == 0 or bm25 is None:
        return {"context": "", "sources": []}

    rewritten = query_rewrite(query)

    # 1) Vector search (top-20)
    q_emb = embed_model.encode([rewritten]).tolist()
    vec_res = collection.query(query_embeddings=q_emb, n_results=20)
    vec_hits = [
        {"doc_id": d, "text": t, "score": 1 - dist}
        for d, t, dist in zip(vec_res["ids"][0], vec_res["documents"][0], vec_res["distances"][0])
    ]

    # 2) BM25 search (top-20) — 키워드 매칭은 원본 쿼리 사용
    bm_scores = bm25.get_scores(_bm25_tok(query))
    top_idx = np.argsort(bm_scores)[::-1][:20]
    bm25_hits = [
        {"doc_id": corpus_doc_ids[i], "text": corpus_texts[i], "score": float(bm_scores[i])}
        for i in top_idx if bm_scores[i] > 0
    ]

    # 3) RRF fusion (top-20)
    sc = defaultdict(float); info = {}
    for hits in (vec_hits, bm25_hits):
        for rank, r in enumerate(hits, 1):
            sc[r["doc_id"]] += 1.0 / (60 + rank)
            info[r["doc_id"]] = r
    candidates = [info[d] for d in sorted(sc, key=lambda x: -sc[x])[:20]]
    if not candidates:
        return {"context": NO_INFO, "sources": []}

    # 4) Cross-Encoder rerank → top-3
    pairs = [[query, c["text"]] for c in candidates]
    rerank_scores = reranker.predict(pairs)
    for c, s in zip(candidates, rerank_scores):
        c["rerank_score"] = float(s)
    top3 = sorted(candidates, key=lambda x: -x["rerank_score"])[:3]

    # 5) Confidence threshold (rerank_score < 0 → 미사용)
    confident = [c for c in top3 if c["rerank_score"] >= 0]
    if not confident:
        return {"context": NO_INFO, "sources": []}

    # 6) Context + Citation 출처
    context = " ".join(c["text"] for c in confident)
    sources = [
        {
            "doc_id": c["doc_id"],
            "score":  round(c["rerank_score"], 4),
            "source": "질병관리청 국가건강정보포털",
        }
        for c in confident
    ]
    return {"context": context, "sources": sources}


def search_kakao(dept_name: str, lat: float, lng: float) -> list:
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    params = {
        "query": dept_name,
        "x": lng,
        "y": lat,
        "radius": 3000,
        "category_group_code": "HP8",
        "size": 5,
    }
    try:
        res = requests.get(url, headers=headers, params=params, timeout=5)
        docs = res.json().get("documents", [])
        results = []
        for p in docs:
            navi_link = f"https://map.kakao.com/link/to/{p['place_name']},{p['y']},{p['x']}"
            results.append({
                "name": p["place_name"],
                "address": p.get("road_address_name", ""),
                "phone": p.get("phone", ""),
                "distance": int(p.get("distance", 999999)),
                "navi_url": navi_link,
                "lat": p["y"],
                "lng": p["x"],
            })
        return results
    except Exception:
        return []


def search_hospital(symptom_text: str, lat: float = 37.5012, lng: float = 127.0396) -> dict:
    dept_name = "내과"
    for symptom, (name, _) in SYMPTOM_DEPT_MAP.items():
        if symptom in symptom_text:
            dept_name = name
            break
    hospitals = sorted(
        [h for h in search_kakao(dept_name, lat, lng) if h.get("phone")],
        key=lambda x: x["distance"],
    )
    return {"department": dept_name, "nearby": hospitals[:3]}


def emergency_check(text: str) -> dict:
    total, matched = 0, []
    for kw, score in EMERGENCY_SCORES.items():
        if kw in text:
            total += score
            matched.append(kw)
    if len(matched) >= 2:
        total = min(total * 1.2, 100)
    if total >= 70:
        return {"is_emergency": True, "severity": "HIGH", "score": round(total), "action": "지금 바로 119에 전화해 주세요."}
    if total >= 40:
        return {"is_emergency": True, "severity": "MEDIUM", "score": round(total), "action": "응급실에 방문하시는 게 좋을 수 있어요."}
    return {"is_emergency": False, "severity": "LOW", "score": round(total), "action": None}


def tool_router(output_from_B: dict, lat: float = 37.5012, lng: float = 127.0396) -> dict:
    intent = output_from_B.get("intent", "symptom_inquiry")
    query = output_from_B.get("query", "")
    result = {
        "intent": intent,
        "rag_context": None,
        "rag_sources": [],   # v2: citation 출처 리스트 ({doc_id, score, source})
        "hospitals": None,
        "emergency": None,
    }

    emerg = emergency_check(query)
    if emerg["is_emergency"]:
        result["emergency"] = emerg
        if emerg["severity"] == "HIGH":
            return result

    if intent == "symptom_inquiry":
        rag = full_rag_pipeline(query)
        result["rag_context"] = rag["context"]
        result["rag_sources"] = rag["sources"]
        result["hospitals"] = search_hospital(query, lat, lng)
    elif intent == "medication_info":
        rag = full_rag_pipeline(query)
        result["rag_context"] = rag["context"]
        result["rag_sources"] = rag["sources"]
    elif intent == "hospital_search":
        result["hospitals"] = search_hospital(query, lat, lng)

    return result


# ====== D팀: 응답 생성 ======

@traceable(name="D팀-답변생성-LLaMA3.2")
def generate_answer(query: str, context: str, confidence: float = 0.85, entities: dict = None) -> dict:
    body_part = entities.get('body_part') if entities else "해당"
    context_snippet = context[:400] if context else "정보 없음"
    fine_tuned_prompt = (
        f"### 지시:\n"
        f"어르신이 '{body_part}' 부위 불편을 호소하고 있습니다. 아래 참고 정보를 바탕으로 "
        f"따뜻하게 공감하며 3~4문장으로 답변하세요. 한국어로만 답변하세요.\n\n"
        f"참고 정보: {context_snippet}\n"
        f"어르신 질문: {query}\n\n"
        f"### 응답:\n"
    )
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": ANSWER_MODEL,
                "prompt": fine_tuned_prompt,
                "stream": False,
                "options": {"temperature": 0.3, "num_predict": 150},
            },
            timeout=60,
        )
        answer = resp.json().get("response", "").strip()
        korean_chars = len(re.findall(r'[\uAC00-\uD7A3]', answer))
        if answer and len(answer) > 10 and korean_chars / max(len(answer), 1) > 0.4:
            print(f"[D팀] 파인튜닝 모델 답변 생성 완료")
            return {'answer': answer}
        raise ValueError(f"파인튜닝 모델 응답 품질 미달 (한국어 비율: {korean_chars}/{len(answer)})")
    except Exception as e:
        print(f"[Warn] generate_answer 파인튜닝 모델 실패, Groq 폴백: {e}")
    system_prompt = "당신은 어르신을 지극정성으로 모시는 다정한 의료 AI '헬로비'입니다. 반드시 한국어로만 답변하세요. 영어 단어, 영어 접속사(that, which, for, and 등)를 절대 사용하지 마세요."
    user_msg = f"""현재 어르신은 '{body_part}' 부위가 불편하다고 하셨습니다.
아래 [참고 정보]를 바탕으로 어르신의 질문에 답변해 주세요.

### [참고 정보]
{context}

### [어르신의 질문]
{query}

### [출력 규칙]
1. 첫 문장은 무조건 어르신의 통증에 대해 걱정해주는 따뜻한 공감으로 시작하세요.
2. 가장 가까운 병원 한군데의 이름과 거리를 구체적으로 언급하고 조심히 다녀오시라고 다정하게 인사하세요.
3. 답변은 3~4문장 이내로 작성하세요."""
    try:
        response = llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ])
        return {'answer': response.content.strip()}
    except Exception as e:
        print(f"[Error] generate_answer: {e}")
        return {'answer': "어르신, 잠시 정보를 정리하는 데 시간이 조금 걸리네요. 다시 한번 말씀해 주시겠어요?"}


def format_response(raw_answer: str, is_emergency: bool = False) -> str:
    if is_emergency:
        return '지금 바로 119에 전화해 주세요. 매우 위험한 상황일 수 있습니다.'
    if not raw_answer:
        return "죄송합니다. 다시 한번 말씀해 주시겠어요?"
    answer = raw_answer
    for word in FORBIDDEN_WORDS:
        answer = answer.replace(word, '')
    # 영어 단어 제거 (한국어 문장 사이에 섞인 영어 접속사/단어)
    answer = re.sub(r'\b[a-zA-Z]+\b', '', answer)
    answer = re.sub(r'\s+', ' ', answer).strip()
    sentences = re.split(r'([.!?])', answer)
    combined = []
    for i in range(0, len(sentences) - 1, 2):
        s = sentences[i].strip() + sentences[i + 1]
        if s:
            combined.append(s)
    final_text = ' '.join(combined[:6]).strip()
    return final_text if final_text else answer


# ====== 통합 파이프라인 ======

def full_pipeline(
    raw_text: str,
    session_id: str = 'default',
    lat: float = 37.5012,
    lng: float = 127.0396,
) -> dict:
    print(f'\n[Pipeline] 입력: {raw_text}')

    # A: STT
    audio_extensions = ('.wav', '.mp3', '.m4a', '.flac', '.ogg')
    if isinstance(raw_text, str) and raw_text.lower().endswith(audio_extensions):
        stt_output = stt_pipeline(raw_text)
        text = stt_output['text']
    else:
        text = raw_text
    print(f'[A] 인식 문장: {text}')

    # B: 의도 분류 & 다중턴
    b_result = chat_with_followup(text, session_id)
    print(f'[B] 의도: {b_result["intent"]} / ready_for_c: {b_result["ready_for_c"]}')

    if not b_result['ready_for_c']:
        answer = format_response(b_result['answer'])
        return {
            'answer': answer,
            'intent': b_result['intent'],
            'ready_for_c': False,
            'hospitals': None,
            'emergency': None,
        }

    # C: 도구 활용
    
    output_from_B = b_result['output_for_c']
    c_result = tool_router(output_from_B, lat, lng)

    hospital_info_text = ""
    if c_result.get('hospitals') and c_result['hospitals'].get('nearby'):
        h_list = c_result['hospitals']['nearby']
        hospital_info_text = "\n[주변 추천 병원 목록]\n"
        for i, h in enumerate(h_list[:3]):
            walk_time = max(1, round(h['distance'] / 66.6))
            hospital_info_text += (
                f"{i+1}. {h['name']}: 거리 {h['distance']}m, 도보 약 {walk_time}분\n"
                f"   - 주소: {h['address']}\n"
                f"   - 전화: {h['phone']}\n"
            )

    rag_context = c_result.get('rag_context') or ""
    combined_context = f"{rag_context}\n{hospital_info_text}".strip()

    # D: 응답 생성
    if c_result['emergency'] and c_result['emergency']['severity'] == 'HIGH':
        final_answer = format_response('', is_emergency=True)
    else:
        if combined_context:
            answer_result = generate_answer(
                text,
                context=combined_context,
                confidence=output_from_B.get('confidence', 0.85),
                entities=output_from_B.get('entities'),
            )
            raw_answer = answer_result['answer']
        else:
            raw_answer = b_result.get('answer') or "죄송해요, 관련 정보를 찾지 못했습니다."
        final_answer = format_response(raw_answer)

    print(f'[D] 최종 답변: {final_answer}')

    return {
        'answer': final_answer,
        'intent': b_result['intent'],
        'ready_for_c': True,
        'hospitals': c_result.get('hospitals'),
        'emergency': c_result.get('emergency'),
        'rag_sources': c_result.get('rag_sources') or [],
    }


# ====== FastAPI ======

app = FastAPI(title='LG HelloDoctor API')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


class ChatRequest(BaseModel):
    text: str
    session_id: str = 'default'
    lat: float = 37.5012
    lng: float = 127.0396


class ChatResponse(BaseModel):
    answer: str
    intent: str
    hospitals: Optional[list] = None
    is_emergency: bool = False
    ready_for_c: bool
    session_id: str
    rag_sources: list = []   # v2: citation 출처 [{doc_id, score, source}]


@app.get('/')
def root():
    return {'message': 'LG HelloDoctor API 정상 동작 중'}


@app.post('/api/stt')
async def stt_endpoint(audio: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        content = await audio.read()
        tmp.write(content)
        tmp_path = tmp.name
    try:
        stt_result = stt_pipeline(audio_path=tmp_path)
        return {"text": stt_result['text'], "raw_text": stt_result['raw_text'], "status": "success"}
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.post('/chat', response_model=ChatResponse)
def chat(request: ChatRequest):
    result = full_pipeline(
        raw_text=request.text,
        session_id=request.session_id,
        lat=request.lat,
        lng=request.lng,
    )
    hospitals = result.get('hospitals', {}).get('nearby', []) if result.get('hospitals') else []
    return ChatResponse(
        answer=result['answer'],
        intent=result['intent'],
        hospitals=hospitals,
        is_emergency=result.get('emergency', {}).get('is_emergency', False) if result.get('emergency') else False,
        ready_for_c=result.get('ready_for_c', True),
        session_id=request.session_id,
    )


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
