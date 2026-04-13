# Colab `pipeline_integrated_(5).ipynb` Step 10 — POST /api/stt 404 해결
#
# 프론트: `src/api/stt.ts` → POST multipart 필드 `audio` → JSON { "text", "status" }
#
# ── 방법 A (권장): 이 레포의 `colab_register_api_stt.py` 를 Colab에 업로드한 뒤 ──
#
#   from colab_register_api_stt import register_api_stt_route
#   register_api_stt_route(app, stt_pipeline)
#
#   (uvicorn 실행 전, `app = FastAPI(...)` 및 CORS 설정 직후 한 번만 호출)
#
# ── 방법 B: Step 10 셀에 아래 COLAB_INLINE 만 추가 (import 에 File, UploadFile, HTTPException 포함) ──

COLAB_INLINE = r"""
import os
import tempfile


def _stt_suffix(filename, content_type):
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


@app.post("/api/stt")
async def api_stt(audio: UploadFile = File(...)):
    suffix = _stt_suffix(audio.filename, audio.content_type)
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    try:
        data = await audio.read()
        if not data:
            raise HTTPException(status_code=400, detail="빈 오디오 파일입니다.")
        with open(path, "wb") as f:
            f.write(data)
        out = stt_pipeline(audio_path=path)
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
"""
