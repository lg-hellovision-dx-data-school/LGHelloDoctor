from pydantic import BaseModel
from typing import List, Optional, Union


# ---------------------------
# 입력 쪽 세부 구조
# ---------------------------
class InputEntities(BaseModel):
    symptom: Optional[str] = None
    body_part: Optional[str] = None
    location: Optional[str] = None
    emergency: Optional[bool] = None
    medication_1: Optional[str] = None
    medication_2: Optional[str] = None


class CInputPayload(BaseModel):
    session_id: str
    input_text: str
    intent: Union[List[str], str]
    entities: InputEntities


# ---------------------------
# 출력 쪽 세부 구조
# ---------------------------
class HospitalResult(BaseModel):
    name: str
    distance: Optional[str] = None
    phone: Optional[str] = None
    open: Optional[bool] = None
    address: Optional[str] = None


class ToolResult(BaseModel):
    source: Optional[str] = None
    query: Optional[str] = None


class COutputPayload(BaseModel):
    session_id: str
    rag_context: Optional[str] = None
    hospital_results: List[HospitalResult] = []
    severity: Optional[str] = None
    tool_trace: List[str] = []
    tool_result: Optional[ToolResult] = None