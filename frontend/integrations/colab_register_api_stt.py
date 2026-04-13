"""
Colab FastAPI(Step 10)에서 POST /api/stt 404 를 없애기 위한 코드입니다.

사용법 (노트북에서 `stt_pipeline` 과 `app` 이 이미 있을 때):

    from colab_register_api_stt import register_api_stt_route
    register_api_stt_route(app, stt_pipeline)

또는 이 파일 전체를 셀에 붙여 넣은 뒤:

    register_api_stt_route(app, stt_pipeline)

그 다음 `uvicorn` 으로 서버를 띄우면 됩니다.
프론트 계약: multipart 필드명 `audio`, 응답 JSON `{"text":"...","status":"ok"}`.
"""

from __future__ import annotations

import os
import tempfile
from typing import Any, Callable, Dict, Optional

# Colab 한 셀에만 붙여 넣는 경우를 위해 타입만 맞춤
try:
    from fastapi import FastAPI, File, HTTPException, UploadFile
except ImportError as e:  # pragma: no cover
    raise ImportError("pip install fastapi python-multipart") from e


def _suffix_for_upload(filename: Optional[str], content_type: Optional[str]) -> str:
    fn = (filename or "").lower()
    for ext in (".webm", ".wav", ".ogg", ".mp3", ".m4a"):
        if fn.endswith(ext):
            return ext
    ct = (content_type or "").lower()
    if "webm" in ct:
        return ".webm"
    if "wav" in ct:
        return ".wav"
    if "ogg" in ct:
        return ".ogg"
    return ".webm"


def register_api_stt_route(
    app: FastAPI,
    transcribe: Callable[..., Dict[str, Any]],
    *,
    route_path: str = "/api/stt",
) -> None:
    """
    `transcribe` 는 노트북의 `stt_pipeline` 과 동일 시그니처여야 합니다.
    `stt_pipeline(audio_path=path)` → dict 에 최소 `text` 키.
    """

    @app.post(route_path)
    async def api_stt(audio: UploadFile = File(...)):
        suffix = _suffix_for_upload(audio.filename, audio.content_type)
        fd, path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        try:
            raw = await audio.read()
            if not raw:
                raise HTTPException(status_code=400, detail="빈 오디오 파일입니다.")
            with open(path, "wb") as f:
                f.write(raw)
            out = transcribe(audio_path=path)
            text = str((out or {}).get("text") or "").strip()
            if not text:
                raise HTTPException(status_code=400, detail="음성 인식 결과가 비어 있습니다.")
            return {"text": text, "status": "ok"}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
