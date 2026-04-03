from fastapi import APIRouter
from Opr.schemas import CInputPayload
from Opr.tool_router import run_tools

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/pipeline/tools")
def pipeline_tools(payload: CInputPayload):
    return run_tools(payload)