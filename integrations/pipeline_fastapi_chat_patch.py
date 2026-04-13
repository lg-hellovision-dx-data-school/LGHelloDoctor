# Colab `pipeline_integrated_(5).ipynb` Step 10 FastAPI 셀과 교체·병합용 스니펫입니다.
# 프론트(`src/api/chat.ts`, `useMedicalChat`)는 아래 JSON 필드를 사용합니다.
#
# STT(호출어 녹음): 프론트는 `POST /api/stt`(multipart, 필드 `audio`)를 호출합니다.
# 노트북 기본 셀에 이 경로가 없으면 404 → `integrations/colab_register_api_stt.py` 를 업로드 후
#   `register_api_stt_route(app, stt_pipeline)` 호출, 또는 `fastapi_stt_route_snippet.py` 의 COLAB_INLINE 붙여넣기.
#
# POST /chat  요청: { "text", "session_id", "lat", "lng" }
# 응답 권장:   { "answer", "intent", "hospitals", "emergency", "ready_for_c", "tts_url"? }
#
# 노트북 기본 ChatResponse는 hospitals 평면 리스트 + is_emergency 만 있어
# 연속 대화(ready_for_c)·응급 상세(emergency)가 빠지므로 이 패치를 권장합니다.

from typing import Any, Optional, List

from pydantic import BaseModel


class ChatRequest(BaseModel):
    text: str
    session_id: str = "default"
    lat: float = 37.5012
    lng: float = 127.0396


class ChatResponse(BaseModel):
    answer: str
    intent: str
    hospitals: Optional[List[Any]] = None
    emergency: Optional[dict] = None
    ready_for_c: bool = True
    tts_url: Optional[str] = None
    is_emergency: bool = False
    session_id: str


def build_chat_response(request: ChatRequest, result: dict) -> ChatResponse:
    """full_pipeline(...) 반환 dict → 프론트 계약에 맞게 변환."""
    hospitals_raw = result.get("hospitals")
    if isinstance(hospitals_raw, dict):
        hospitals = hospitals_raw.get("nearby") or []
    elif isinstance(hospitals_raw, list):
        hospitals = hospitals_raw
    else:
        hospitals = []

    em = result.get("emergency")
    if isinstance(em, dict) and isinstance(em.get("is_emergency"), bool):
        emergency = em
        is_emergency = bool(em.get("is_emergency"))
    else:
        emergency = None
        is_emergency = result.get("intent") == "emergency"

    ready = result.get("ready_for_c")
    if isinstance(ready, bool):
        ready_for_c = ready
    elif result.get("intent") == "paging":
        ready_for_c = False
    elif result.get("intent") == "emergency" or is_emergency:
        ready_for_c = True
    elif hospitals:
        ready_for_c = True
    else:
        # 병원 없이 답변만 있는 경우(복약 등) — 한 턴 처리 후 호출어 대기로 복귀
        ready_for_c = True

    tts = result.get("tts_url") or result.get("audio_path")
    if isinstance(tts, str) and tts.startswith("http"):
        tts_url = tts
    else:
        tts_url = None

    return ChatResponse(
        answer=result.get("answer") or "",
        intent=str(result.get("intent") or "symptom_inquiry"),
        hospitals=hospitals or None,
        emergency=emergency,
        ready_for_c=ready_for_c,
        tts_url=tts_url,
        is_emergency=is_emergency,
        session_id=request.session_id,
    )


# --- FastAPI 핸들러 예시 (기존 `def chat` 본문만 교체) ---
#
# @app.post("/chat", response_model=ChatResponse)
# def chat(request: ChatRequest):
#     result = full_pipeline(
#         raw_text=request.text,
#         session_id=request.session_id,
#         lat=request.lat,
#         lng=request.lng,
#     )
#     return build_chat_response(request, result)
