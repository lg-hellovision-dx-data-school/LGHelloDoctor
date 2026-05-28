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
from agent_patterns import (
    AnswerEvaluator,
    IntentRouter,
    PipelineOrchestrator,
    PipelineWorkers,
    generate_with_evaluator,
    run_c_team_parallel,
)
from graph_pipeline import build_graph, run_graph
from ontology_store import ontology
# ── Clean Architecture: 도메인 규칙(domain) · 프리젠터(adapters) 계층 ──
from domain.rules import (
    WAKE_WORDS, FILLER_PATTERN, MEDICAL_CORRECTIONS, EMERGENCY_KEYWORDS,
    FOLLOWUP_QUESTIONS, QUERY_REWRITE_MAP, SYMPTOM_DEPT_MAP, EMERGENCY_SCORES,
    FORBIDDEN_WORDS, preprocess_text, query_rewrite, contains_emergency_keyword,
    score_emergency, classify_emergency, lookup_department,
)
from adapters.presenters import format_response, format_hospital_text
from infra.map_kakao import search_kakao
from usecases.hospital import find_nearby_hospital
from usecases.rag import rrf_fuse, select_confident

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
# 도메인 규칙·상수(WAKE_WORDS·MEDICAL_CORRECTIONS·EMERGENCY_*·SYMPTOM_DEPT_MAP·
# FORBIDDEN_WORDS 등)는 Clean Architecture domain 계층(backend/domain/rules.py)으로
# 분리했고, 상단 import 로 재노출(re-export)하여 기존 호출부·테스트 호환을 유지한다.
# HITL 거버넌스 책임자 주석도 domain/rules.py 로 이동.
SAMPLE_RATE = 16000

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
    if contains_emergency_keyword(text):   # domain.rules — EMERGENCY_KEYWORDS
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

    # 3) RRF fusion — 검색 전략은 usecases.rag (모델 의존 0)
    candidates = rrf_fuse((vec_hits, bm25_hits), k=60, top_n=20)
    if not candidates:
        return {"context": NO_INFO, "sources": []}

    # 4) Cross-Encoder rerank (infra 모델 호출)
    pairs = [[query, c["text"]] for c in candidates]
    rerank_scores = reranker.predict(pairs)
    for c, s in zip(candidates, rerank_scores):
        c["rerank_score"] = float(s)

    # 5) 신뢰도 임계 선택 — usecases.rag
    confident = select_confident(candidates, threshold=0.0, top=3)
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


def search_hospital(symptom_text: str, lat: float = 37.5012, lng: float = 127.0396) -> dict:
    """합성 루트 어댑터 — usecases.find_nearby_hospital 에 infra(Kakao)·Graph DB 주입."""
    return find_nearby_hospital(
        symptom_text, lat, lng,
        map_search=search_kakao,   # infra.map_kakao (MapGateway)
        ontology=ontology,         # infra.ontology_store (OntologyGateway)
    )


def emergency_check(text: str) -> dict:
    """domain 규칙 점수 + Graph DB(온톨로지) SPARQL 점수 중 높은 쪽으로 분류."""
    dom = score_emergency(text)["score"]
    total = max(dom, ontology.emergency_score(text)["score"])
    return classify_emergency(total)


def tool_router(output_from_B: dict, lat: float = 37.5012, lng: float = 127.0396) -> dict:
    """Routing(②) + Parallelization(③) 패턴.

    - 의도(intent)에 따라 필요한 도구만 선별 호출 → Routing
    - 선별된 도구(RAG·Hospital·Emergency)는 ThreadPoolExecutor로 병렬 실행 → Parallelization
    - HIGH 응급은 조기 종료(early exit)로 다른 결과 무시
    """
    intent = output_from_B.get("intent", "symptom_inquiry")
    query = output_from_B.get("query", "")

    parallel = run_c_team_parallel(
        query=query,
        intent=intent,
        lat=lat,
        lng=lng,
        rag_fn=full_rag_pipeline,
        hospital_fn=search_hospital,
        emergency_fn=emergency_check,
    )

    emerg = parallel["emergency"]
    if emerg.get("is_emergency") and emerg.get("severity") == "HIGH":
        return {
            "intent": intent,
            "rag_context": None,
            "rag_sources": [],
            "hospitals": None,
            "emergency": emerg,
        }

    return {
        "intent": intent,
        "rag_context": parallel["rag_context"],
        "rag_sources": parallel["rag_sources"],
        "hospitals": parallel["hospitals"],
        "emergency": emerg if emerg.get("is_emergency") else None,
    }


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


# ====== 통합 파이프라인 (LangGraph StateGraph) ======

# A/B/C/D 워커를 LangGraph 노드로 주입 → 컴파일된 그래프를 1회 생성한다.
_PIPELINE_WORKERS = PipelineWorkers(
    stt=stt_pipeline,
    chat_followup=chat_with_followup,
    tool_router=tool_router,
    answer_generator=generate_answer,
    formatter=format_response,
)
_PIPELINE_EVALUATOR = AnswerEvaluator(forbidden_words=FORBIDDEN_WORDS)
_GRAPH_APP = build_graph(_PIPELINE_WORKERS, evaluator=_PIPELINE_EVALUATOR)
print("[Init] LangGraph 파이프라인 컴파일 완료")


def full_pipeline(
    raw_text: str,
    session_id: str = 'default',
    lat: float = 37.5012,
    lng: float = 127.0396,
) -> dict:
    """LangGraph StateGraph 기반 A→B→C→D 오케스트레이션 진입점.

    그래프 구조: START → stt → intent ─┬─(다중턴)→ followup → END
                                       └─(ready)→ tools → answer → END
    적용 패턴: Prompt Chaining(①) · Routing/Parallelization(② ③ — tool_router) ·
    Orchestrator-Worker(④ — LangGraph) · Evaluator-Optimizer(⑤ — answer 노드).
    상세 매핑: docs/AGENT_PATTERNS.md / backend/graph_pipeline.py
    """
    print(f'\n[Pipeline] 입력: {raw_text}')
    result = run_graph(_GRAPH_APP, raw_text, session_id, lat, lng)
    print(f"[Pipeline] intent={result['intent']} ready_for_c={result['ready_for_c']} "
          f"answer={(result['answer'] or '')[:40]}")
    return result


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


@app.get('/ontology/body-parts/{region}')
def ontology_body_parts(region: str):
    """Graph DB(온톨로지) 추이추론 데모 — hd:partOf* SPARQL property path.

    예: /ontology/body-parts/LowerLimb → ['하지', '무릎']
    코드 사전(dict)으로는 불가능한 형식 온톨로지의 추론을 런타임에 노출한다.
    """
    return {
        "region": region,
        "parts": ontology.body_parts_under(region),
        "available": ontology.available,
    }


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
