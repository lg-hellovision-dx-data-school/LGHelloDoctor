dummy_case_a = {
    "session_id": "test-a",
    "input_text": "무릎이 너무 아파요. 어디 가야 하나요?",
    "intent": ["symptom_inquiry", "hospital_search"],
    "entities": {
        "symptom": "무릎 통증",
        "body_part": "무릎",
        "location": "서울 강남구",
        "emergency": False,
        "medication_1": None,
        "medication_2": None
    }
}

dummy_case_b = {
    "session_id": "test-b",
    "input_text": "가슴이 너무 아프고 숨이 안 쉬어져요",
    "intent": ["emergency"],
    "entities": {
        "symptom": "흉통, 호흡곤란",
        "body_part": "가슴",
        "location": "서울 강남구",
        "emergency": True,
        "medication_1": None,
        "medication_2": None
    }
}

dummy_case_c = {
    "session_id": "test-c",
    "input_text": "혈압약이랑 감기약 같이 먹어도 되나요?",
    "intent": ["medication_info"],
    "entities": {
        "symptom": None,
        "body_part": None,
        "location": "서울 강남구",
        "emergency": False,
        "medication_1": "혈압약",
        "medication_2": "감기약"
    }
}

dummy_case_fallback = {
    "session_id": "test-f1",
    "input_text": "도와주세요",
    "intent": [],
    "entities": {
        "symptom": None,
        "body_part": None,
        "location": None,
        "emergency": False,
        "medication_1": None,
        "medication_2": None
    }
}

dummy_case_e1 = {
    "session_id": "test-e1",
    "input_text": "가슴이 너무 아파요",
    "intent": "emergency",
    "entities": {
        "symptom": "흉통",
        "body_part": "가슴",
        "location": "서울 강남구",
        "emergency": True,
        "medication_1": None,
        "medication_2": None
    }
}

dummy_case_e2 = {
    "session_id": "test-e2",
    "input_text": "약 같이 먹어도 되나요?",
    "intent": ["medication_info"],
    "entities": {
        "symptom": "",
        "body_part": "",
        "location": "서울 강남구",
        "emergency": False,
        "medication_1": "",
        "medication_2": ""
    }
}

dummy_case_e3 = {
    "session_id": "test-e3",
    "input_text": "무릎이 아파요. 어디 가야 하나요?",
    "intent": ["symptom_inquiry", "hospital_search"],
    "entities": {
        "symptom": "무릎 통증",
        "body_part": "무릎",
        "location": None,
        "emergency": False,
        "medication_1": None,
        "medication_2": None
    }
}